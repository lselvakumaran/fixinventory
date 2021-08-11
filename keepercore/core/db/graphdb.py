import asyncio
import logging
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Optional, Tuple, List, Union, Callable, AsyncGenerator, Any, Set

from arango import ArangoError
from arango.collection import VertexCollection, StandardCollection, EdgeCollection
from arango.cursor import Cursor
from arango.graph import Graph
from arango.typings import Json
from itertools import chain
from networkx import MultiDiGraph, DiGraph
from toolz import last

from core import feature
from core.db.arangodb_functions import as_arangodb_function
from core.db.async_arangodb import AsyncArangoDB, AsyncArangoTransactionDB
from core.db.model import GraphUpdate, QueryModel
from core.error import InvalidBatchUpdate, ConflictingChangeInProgress, NoSuchBatchError
from core.event_bus import EventBus, CoreEvent
from core.model.graph_access import GraphAccess, GraphBuilder, EdgeType
from core.model.model import Model
from core.query.model import (
    Predicate,
    IsInstanceTerm,
    Part,
    Term,
    CombinedTerm,
    FunctionTerm,
    Navigation,
    IdTerm,
    Aggregate,
)
from core.util import first

log = logging.getLogger(__name__)


class GraphDB(ABC):
    @abstractmethod
    async def get_node(self, node_id: str, result_section: Union[str, List[str]]) -> Optional[Json]:
        pass

    @abstractmethod
    async def create_node(self, model: Model, node_id: str, data: Json, under_node_id: str) -> Json:
        pass

    @abstractmethod
    async def update_node(
        self, model: Model, section: str, result_section: Union[str, List[str]], node_id: str, patch: Json
    ) -> Json:
        pass

    @abstractmethod
    async def delete_node(self, node_id: str) -> None:
        pass

    @abstractmethod
    def search(self, tokens: str, limit: int) -> AsyncGenerator[Json, None]:
        pass

    @abstractmethod
    async def update_sub_graph(
        self, model: Model, sub: MultiDiGraph, under_node_id: str, maybe_batch: Optional[str] = None
    ) -> GraphUpdate:
        pass

    @abstractmethod
    async def list_in_progress_batch_updates(self) -> List[Json]:
        pass

    @abstractmethod
    async def commit_batch_update(self, batch_id: str) -> None:
        pass

    @abstractmethod
    async def abort_batch_update(self, batch_id: str) -> None:
        pass

    @abstractmethod
    def query_list(self, query: QueryModel) -> AsyncGenerator[Json, None]:
        pass

    @abstractmethod
    def query_graph_gen(self, query: QueryModel) -> AsyncGenerator[Tuple[str, Json], None]:
        pass

    @abstractmethod
    async def query_graph(self, query: QueryModel) -> DiGraph:
        pass

    @abstractmethod
    def query_aggregation(self, query: QueryModel) -> AsyncGenerator[Json, None]:
        pass

    @abstractmethod
    async def explain(self, query: QueryModel) -> Json:
        pass

    @abstractmethod
    async def wipe(self) -> None:
        pass

    @abstractmethod
    def to_query(
        self, query_model: QueryModel, all_edges: bool = False, limit: Optional[int] = None
    ) -> Tuple[str, Json]:
        pass

    @abstractmethod
    async def create_update_schema(self) -> None:
        pass


class ArangoGraphDB(GraphDB):
    def __init__(self, db: AsyncArangoDB, name: str) -> None:
        super().__init__()
        self.name = name
        self.vertex_name = name
        self.in_progress = f"{name}_in_progress"
        self.db = db

    def edge_collection(self, edge_type: str) -> str:
        return f"{self.name}_{edge_type}"

    async def search(  # noqa: E501 pylint: disable=invalid-overridden-method
        self, tokens: str, limit: int
    ) -> AsyncGenerator[Json, None]:
        bind = {"tokens": tokens, "limit": limit}
        trafo = self.document_to_instance_fn("reported")
        with await self.db.aql(query=self.query_search_token(), bind_vars=bind) as cursor:
            for element in cursor:
                yield trafo(element)

    async def get_node(self, node_id: str, result_section: Union[str, List[str]]) -> Optional[Json]:
        node = await self.by_id(node_id)
        return self.document_to_instance_fn(result_section)(node) if node is not None else None

    async def create_node(self, model: Model, node_id: str, data: Json, under_node_id: str) -> Json:
        graph = GraphBuilder.graph_from_single_item(model, node_id, data)
        await self.update_sub_graph(model, graph, under_node_id)
        return graph.nodes[node_id]["data"]

    async def update_node(
        self, model: Model, section: str, result_section: Union[str, List[str]], node_id: str, patch: Json
    ) -> Json:
        node = await self.by_id(node_id)
        if node is None:
            raise AttributeError(f"No document found with this id: {node_id}")
        else:
            existing = node[section] if section in node else {}
            node[section] = existing | patch
            kind = model[node["reported"]]
            coerced = kind.check_valid(node[section], ignore_missing=True)
            node[section] = coerced if coerced is not None else node[section]
            node["data"] = node["reported"]
            node_id, _, sha, kinds, flat = GraphAccess.dump(node_id, node)
            update = {"_key": node["_key"], "hash": sha, section: node[section], "kinds": kinds, "flat": flat}
            result = await self.db.update(self.vertex_name, update, return_new=True)
            trafo = self.document_to_instance_fn(result_section)
            return trafo(result["new"])

    async def delete_node(self, node_id: str) -> None:
        with await self.db.aql(query=self.query_count_direct_children(), bind_vars={"rid": node_id}) as cursor:
            count = cursor.next()
            if count > 0:
                raise AttributeError(f"Can not delete node, since it has {count} child(ren)!")

        with await self.db.aql(query=self.query_node_by_id(), bind_vars={"rid": node_id}) as cursor:
            if not cursor.empty():
                await self.db.delete_vertex(self.name, cursor.next())
            else:
                return None

    async def by_id(self, node_id: str) -> Optional[Json]:
        with await self.db.aql(query=self.query_node_by_id(), bind_vars={"rid": node_id}) as cursor:
            return cursor.next() if not cursor.empty() else None

    async def query_list(  # noqa: E501 pylint: disable=invalid-overridden-method
        self, query: QueryModel
    ) -> AsyncGenerator[Json, None]:
        assert query.query.aggregate is None, "Given query is an aggregation function. Use the appropriate endpoint!"
        q_string, bind = self.to_query(query)
        trafo = self.document_to_instance_fn(query.return_section)
        visited = set()
        with await self.db.aql(query=q_string, bind_vars=bind) as cursor:
            for element in cursor:
                if element is not None and element["_id"] not in visited:
                    visited.add(element["_id"])
                    yield trafo(element)

    async def query_graph_gen(  # noqa: E501 pylint: disable=invalid-overridden-method
        self, query: QueryModel
    ) -> AsyncGenerator[Tuple[str, Json], None]:
        assert query.query.aggregate is None, "Given query is an aggregation function. Use the appropriate endpoint!"
        query_string, bind = self.to_query(query, all_edges=True)
        trafo = self.document_to_instance_fn(query.return_section)
        visited_node = {}
        visited_edge = set()
        with await self.db.aql(query=query_string, bind_vars=bind, batch_size=10000) as cursor:
            for element in cursor:
                try:
                    _id = element["_id"]
                    if _id not in visited_node:
                        section = trafo(element)
                        uid = element["id"]
                        yield "node", {"type": "node", "id": uid, "data": section}
                        visited_node[_id] = uid
                    from_id = element.get("_from")
                    to_id = element.get("_to")
                    if from_id in visited_node and to_id in visited_node:
                        edge_key = from_id + to_id
                        if edge_key not in visited_edge:
                            yield "edge", {"type": "edge", "from": visited_node[from_id], "to": visited_node[to_id]}
                            visited_edge.add(edge_key)
                except Exception as ex:
                    log.warning(f"Could not read element {element}: {ex}. Ignore.")

    async def query_graph(self, query: QueryModel) -> DiGraph:
        result = self.query_graph_gen(query)
        graph = DiGraph()
        async for kind, item in result:
            if kind == "node":
                graph.add_node(item["id"], **item["data"])
            elif kind == "edge":
                graph.add_edge(item["from"], item["to"])
        return graph

    async def query_aggregation(  # noqa: E501 pylint: disable=invalid-overridden-method
        self, query: QueryModel
    ) -> AsyncGenerator[Json, None]:
        q_string, bind = self.to_query(query)
        assert query.query.aggregate is not None, "Given query has no aggregation section"
        with await self.db.aql(query=q_string, bind_vars=bind) as cursor:
            for element in cursor:
                yield element

    async def explain(self, query: QueryModel) -> Json:
        q_string, bind = self.to_query(query, all_edges=True)
        return await self.db.explain(query=q_string, bind_vars=bind)

    async def wipe(self) -> None:
        await self.db.truncate(self.vertex_name)
        for edge_type in EdgeType.allowed_edge_types:
            await self.db.truncate(self.edge_collection(edge_type))
        await self.insert_genesis_data()

    @staticmethod
    def document_to_instance_fn(section: Union[str, List[str]]) -> Callable[[Json], Optional[Json]]:
        def single_prop(doc: Json) -> Optional[Json]:
            return doc[section] if section in doc else None

        def multi_prop(doc: Json) -> Optional[Json]:
            return {prop: doc[prop] if prop in doc else {} for prop in section}

        return single_prop if isinstance(section, str) else multi_prop

    async def list_in_progress_batch_updates(self) -> List[Json]:
        with await self.db.aql(self.query_active_batches()) as cursor:
            return list(cursor)

    async def get_tmp_collection(self, change_id: str, create: bool = True) -> StandardCollection:
        id_part = str(uuid.uuid5(uuid.NAMESPACE_DNS, change_id)).replace("-", "")
        temp_name = f"{self.vertex_name}_temp_{id_part}"
        if await self.db.has_collection(temp_name):
            return self.db.collection(temp_name)
        elif create:
            temp = await self.db.create_collection(temp_name, replication_factor=1)
            temp.add_persistent_index(["action"])
            return temp
        else:
            raise NoSuchBatchError(change_id)

    async def move_temp_to_proper(self, change_id: str, temp_name: str) -> None:
        change_key = str(uuid.uuid5(uuid.NAMESPACE_DNS, change_id))
        log.info(f"Move to temp: change_id={change_id}, change_key={change_key}, temp_name={temp_name}")
        edge_inserts = [
            f'for e in {temp_name} filter e.action=="edge_insert" and e.edge_type=="{a}" '
            f"insert e.data in {self.edge_collection(a)}"
            for a in EdgeType.allowed_edge_types
        ]
        edge_deletes = [
            f'for e in {temp_name} filter e.action=="edge_delete" and e.edge_type=="{a}" '
            f"remove e.data in {self.edge_collection(a)}"
            for a in EdgeType.allowed_edge_types
        ]
        updates = "\n".join(
            map(
                lambda aql: f"db._createStatement({{ query: `{aql}` }}).execute();",
                [
                    f'for e in {temp_name} filter e.action=="node_insert" insert e.data in {self.vertex_name}',
                    f'for e in {temp_name} filter e.action=="node_update" replace e.data in {self.vertex_name}',
                    f'for e in {temp_name} filter e.action=="node_delete" remove e.data in {self.vertex_name}',
                ]
                + edge_inserts
                + edge_deletes
                + [
                    f'remove {{_key: "{change_key}"}} in {self.in_progress}',
                ],
            )
        )
        await self.db.execute_transaction(
            f'function () {{\nvar db=require("@arangodb").db;\n{updates}\n}}',
            read=[temp_name],
            write=[self.edge_collection(a) for a in EdgeType.allowed_edge_types] + [self.vertex_name, self.in_progress],
        )

    async def mark_update(
        self, node_id: str, parent_node_id: str, change_id: str, is_batch: bool, edge_types: Set[str]
    ) -> None:
        tx = await self.db.begin_transaction(
            read=[self.in_progress, self.vertex_name, self.edge_collection(EdgeType.default)],
            write=[self.in_progress],
        )
        try:
            existing = next(await tx.aql(self.query_active_change(), bind_vars={"root_node_id": node_id}), None)
            if existing is not None:
                other = existing["change"]
                if change_id == other:
                    raise InvalidBatchUpdate()
                else:
                    raise ConflictingChangeInProgress(other)
            await tx.aql(
                self.aql_create_update_change(),
                bind_vars={
                    "root_node_id": node_id,
                    "parent_node_id": parent_node_id,
                    "change": change_id,
                    "is_batch": is_batch,
                    "change_key": str(uuid.uuid5(uuid.NAMESPACE_DNS, change_id)),
                    "edge_types": list(edge_types),
                },
            )
            await tx.commit_transaction()
        except Exception as ex:
            await tx.abort_transaction()
            raise ex

    async def delete_marked_update(self, change_id: str, tx: Optional[AsyncArangoTransactionDB] = None) -> None:
        db = tx if tx else self.db
        doc = {"_key": str(uuid.uuid5(uuid.NAMESPACE_DNS, change_id))}
        await db.delete(self.in_progress, doc, ignore_missing=True)

    def prepare_nodes(
        self, access: GraphAccess, node_cursor: Cursor
    ) -> Tuple[GraphUpdate, List[Json], List[Json], List[Json]]:
        sub_root_id = access.root()
        info = GraphUpdate()
        resource_inserts: List[Json] = []
        resource_updates: List[Json] = []
        resource_deletes: List[Json] = []

        def insert_node(id_string: str, js: Json, hash_string: str, kinds: List[str], flat: str) -> None:
            js_doc: Json = {
                "_key": id_string,
                "id": id_string,
                "hash": hash_string,
                "reported": js,
                "kinds": kinds,
                "flat": flat,
                "update_id": sub_root_id,
            }
            resource_inserts.append(js_doc)
            info.nodes_created += 1

        def update_or_delete_node(node: Json) -> None:
            key = node["_key"]
            rid = node["id"]
            hash_string = node["hash"]
            elem = access.node(rid)
            if elem is None:
                # node is in db, but not in the graph any longer: delete node
                resource_deletes.append({"_key": key})
                info.nodes_deleted += 1
            elif elem[2] != hash_string:
                _, js, current_hash, kinds, flat = elem
                # node is in db and in the graph, content is different
                js = {
                    "_key": key,
                    "id": rid,
                    "hash": current_hash,
                    "reported": js,
                    "kinds": kinds,
                    "flat": flat,
                    "update_id": sub_root_id,
                }
                resource_updates.append({"_key": key} | js)
                info.nodes_updated += 1

        for doc in node_cursor:
            update_or_delete_node(doc)

        for ids, node_js, sha, node_kinds, flattened in access.not_visited_nodes():
            insert_node(ids, node_js, sha, node_kinds, flattened)
        return info, resource_inserts, resource_updates, resource_deletes

    def prepare_edges(
        self, access: GraphAccess, edge_cursor: Cursor, edge_type: str
    ) -> Tuple[GraphUpdate, List[Json], List[Json]]:
        sub_root_id = access.root()
        info = GraphUpdate()
        edges_inserts: List[Json] = []
        edges_deletes: List[Json] = []

        def insert_edge(from_node: str, to_node: str) -> None:
            key = str(uuid.uuid1())
            js = {
                "_key": key,
                "_from": f"{self.vertex_name}/{from_node}",
                "_to": f"{self.vertex_name}/{to_node}",
                "update_id": sub_root_id,
            }
            edges_inserts.append(js)
            info.edges_created += 1

        def update_edge(edge: Json) -> None:
            from_node = edge["_from"].split("/")[1]  # vertex/id
            to_node = edge["_to"].split("/")[1]  # vertex/id
            if not access.has_edge(from_node, to_node, edge_type):
                edges_deletes.append(edge)
                info.edges_deleted += 1

        for doc in edge_cursor:
            update_edge(doc)

        for edge_from, edge_to in access.not_visited_edges(edge_type):
            insert_edge(edge_from, edge_to)

        return info, edges_inserts, edges_deletes

    def link_subgraph(self, access: GraphAccess, cursor: Cursor, under_node_id: str) -> Tuple[GraphUpdate, List[Json]]:
        if cursor.empty():
            return GraphUpdate(edges_created=1), [
                {
                    "_key": str(uuid.uuid1()),
                    "_from": f"{self.vertex_name}/{under_node_id}",
                    "_to": f"{self.vertex_name}/{access.root()}",
                    "update_id": "link",
                }
            ]
        else:
            return GraphUpdate(), []

    async def update_sub_graph(
        self, model: Model, sub: MultiDiGraph, under_node_id: str, maybe_batch: Optional[str] = None
    ) -> GraphUpdate:
        access = GraphAccess(sub)
        change_id = maybe_batch if maybe_batch else str(uuid.uuid1())

        async def query(aql: str, bind_vars: Json) -> Cursor:
            return await self.db.aql(query=aql, bind_vars=bind_vars)

        async def execute_many_async(async_fn: Callable[[str, List[Json]], Any], name: str, array: List[Json]) -> None:
            if array:
                result = await async_fn(name, array)
                ex: Optional[Exception] = first(lambda x: isinstance(x, Exception), result)
                if ex:
                    raise ex  # pylint: disable=raising-bad-type

        async def trafo_many(
            async_fn: Callable[[str, List[Json]], Any], name: str, array: List[Json], template: Json
        ) -> None:
            # update the array in place to not create another intermediate array
            for idx, item in enumerate(array):
                entry = template.copy()
                entry["data"] = item
                array[idx] = entry
            await execute_many_async(async_fn, name, array)

        try:
            # mark this update as early as possible to avoid useless double work
            await self.mark_update(access.root(), under_node_id, change_id, maybe_batch is not None, access.edge_types)

            # check all nodes for this subgraph
            with await query(self.query_update_nodes(), {"update_id": access.root()}) as node_cursor:
                info, resource_inserts, resource_updates, resource_deletes = self.prepare_nodes(access, node_cursor)

            # check all edges in all relevant edge-collections
            edge_inserts = defaultdict(list)
            edge_deletes = defaultdict(list)
            for edge_type in EdgeType.allowed_edge_types:
                with await query(self.query_update_edges(edge_type), {"update_id": access.root()}) as edge_cursor:
                    edge_info, eis, eds = self.prepare_edges(access, edge_cursor, edge_type)
                    info += edge_info
                    edge_inserts[edge_type] = eis
                    edge_deletes[edge_type] = eds

            # make sure the graph is linked to the given parent
            bind_vars = {"from": f"{self.vertex_name}/{under_node_id}", "to": f"{self.vertex_name}/{access.root()}"}
            with await query(self.query_update_parent_linked(), bind_vars) as crs:
                inf, links = self.link_subgraph(access, crs, under_node_id)
                info += inf
                edge_inserts[EdgeType.default].extend(links)

            async def update_directly() -> None:
                edge_collections = [self.edge_collection(a) for a in EdgeType.allowed_edge_types]
                tx = await self.db.begin_transaction(write=edge_collections + [self.vertex_name, self.in_progress])
                try:
                    # note: all requests are done sequentially on purpose
                    # https://www.arangodb.com/docs/stable/http/transaction-stream-transaction.html#concurrent-requests
                    await execute_many_async(self.db.insert_many, self.vertex_name, resource_inserts)
                    await execute_many_async(self.db.update_many, self.vertex_name, resource_updates)
                    await execute_many_async(self.db.delete_many, self.vertex_name, resource_deletes)
                    for ed_i_type, ed_insert in edge_inserts.items():
                        await execute_many_async(self.db.insert_many, self.edge_collection(ed_i_type), ed_insert)
                    for ed_d_type, ed_delete in edge_deletes.items():
                        await execute_many_async(self.db.delete_many, self.edge_collection(ed_d_type), ed_delete)
                    await self.delete_marked_update(change_id, tx)
                    await tx.commit_transaction()
                except ArangoError as ex:
                    log.info(f"Could not perform update: {ex}")
                    await tx.abort_transaction()
                    raise ex

            async def store_to_tmp_collection(temp: StandardCollection) -> None:
                tmp = temp.name
                ri = trafo_many(self.db.insert_many, tmp, resource_inserts, {"action": "node_insert"})
                ru = trafo_many(self.db.insert_many, tmp, resource_updates, {"action": "node_update"})
                rd = trafo_many(self.db.insert_many, tmp, resource_deletes, {"action": "node_delete"})
                edge_i = [
                    trafo_many(self.db.insert_many, tmp, inserts, {"action": "edge_insert", "edge_type": tpe})
                    for tpe, inserts in edge_inserts.items()
                ]
                edge_u = [
                    trafo_many(self.db.insert_many, tmp, deletes, {"action": "edge_delete", "edge_type": tpe})
                    for tpe, deletes in edge_deletes.items()
                ]
                await asyncio.gather(*([ri, ru, rd] + edge_i + edge_u))

            async def update_via_temp_collection() -> None:
                temp = await self.get_tmp_collection(change_id)
                try:
                    await store_to_tmp_collection(temp)
                    await self.move_temp_to_proper(change_id, temp.name)
                finally:
                    await self.db.delete_collection(temp.name)

            async def update_batch() -> None:
                temp_table = await self.get_tmp_collection(change_id)
                await store_to_tmp_collection(temp_table)

            if maybe_batch is not None:
                await update_batch()
            elif info.all_changes() < 100000:  # work around to not run into the 128MB tx limit
                await update_directly()
            else:
                await update_via_temp_collection()
        except InvalidBatchUpdate as ex:
            raise ex
        except Exception as ex:
            await self.delete_marked_update(change_id)
            raise ex

        return info

    async def commit_batch_update(self, batch_id: str) -> None:
        temp_table = await self.get_tmp_collection(batch_id, False)
        await self.move_temp_to_proper(batch_id, temp_table.name)
        await self.db.delete_collection(temp_table.name)

    async def abort_batch_update(self, batch_id: str) -> None:
        temp_table = await self.get_tmp_collection(batch_id, False)
        await self.delete_marked_update(batch_id)
        await self.db.delete_collection(temp_table.name)

    def to_query(
        self, query_model: QueryModel, all_edges: bool = False, limit: Optional[int] = None
    ) -> Tuple[str, Json]:
        query = query_model.query
        model = query_model.model
        section = query_model.query_section
        bind_vars: Json = {}

        def aggregate(cursor: str, a: Aggregate) -> Tuple[str, str]:
            variables = ", ".join(f"{v.get_as_name()}={cursor}.{section}.{v.name}" for v in a.group_by)
            funcs = ", ".join(f"{v.get_as_name()}={v.function}({cursor}.{section}.{v.name})" for v in a.group_func)
            agg = ", ".join(chain((v.get_as_name() for v in a.group_by), (f.get_as_name() for f in a.group_func)))
            return f"collect {variables} aggregate {funcs}", f"{{{agg}}}"

        def predicate(cursor: str, p: Predicate) -> str:
            extra = ""
            path = p.name

            # handle that property is an array
            if "array" in p.args:
                arr_filter = p.args["filter"] if "filter" in p.args else "any"
                extra = f" {arr_filter} "
                path = f"{p.name}[]"
            elif "[*]" in p.name:
                extra = " any " if "[*]" in p.name else " "
                path = p.name.replace("[*]", "[]")

            # key of the predicate is the len of the dict as string
            length = str(len(bind_vars))
            bind_vars[length] = model.kind_by_path(path).coerce(p.value)
            return f"{cursor}.{section}.{p.name}{extra} {p.op} @{length}"

        def with_id(cursor: str, t: IdTerm) -> str:
            length = str(len(bind_vars))
            bind_vars[length] = t.id
            return f"{cursor}.id == @{length}"

        def is_instance(cursor: str, t: IsInstanceTerm) -> str:
            if t.kind not in model:
                raise AttributeError(f"Given kind does not exist: {t.kind}")
            length = str(len(bind_vars))
            bind_vars[length] = t.kind
            return f"{cursor}.kinds ANY == @{length}"

        def term(cursor: str, ab_term: Term) -> str:
            if isinstance(ab_term, Predicate):
                return predicate(cursor, ab_term)
            elif isinstance(ab_term, FunctionTerm):
                return as_arangodb_function(cursor, bind_vars, ab_term, query_model)
            elif isinstance(ab_term, IdTerm):
                return with_id(cursor, ab_term)
            elif isinstance(ab_term, IsInstanceTerm):
                return is_instance(cursor, ab_term)
            elif isinstance(ab_term, CombinedTerm):
                left = term(cursor, ab_term.left)
                right = term(cursor, ab_term.right)
                return f"({left}) {ab_term.op} ({right})"
            else:
                raise AttributeError(f"Do not understand: {ab_term}")

        def part(p: Part, idx: int) -> Tuple[Part, int, str, str]:
            nav = p.navigation
            collection = self.vertex_name if idx == 0 else f"step{idx - 1}"
            out = f"step{idx}"
            cursor = f"r{idx}"
            subcrs = f"sub{idx}"
            link = f"link{idx}"
            trm = term(cursor, p.term)
            unique = "uniqueEdges: 'path'" if all_edges else "uniqueVertices: 'global'"

            def inout(navigation: Navigation) -> str:
                direction = "OUTBOUND" if navigation.is_out() else "INBOUND"
                return (
                    f"FOR {subcrs}, {link} IN {navigation.start}..{navigation.until} {direction} {cursor} "
                    f"{self.edge_collection(navigation.edge_type)} OPTIONS {{ bfs: true, {unique} }} "
                    f"RETURN MERGE({subcrs}, {{_from:{link}._from, _to:{link}._to}})"
                )

            rtn = f"RETURN {cursor}" if nav is None else inout(nav)
            query_part = f"LET {out} = (FOR {cursor} in {collection} FILTER {trm} {rtn})"
            return p, idx, out, query_part

        parts = [part(p, idx) for idx, p in enumerate(reversed(query.parts))]
        all_parts = " ".join(p[3] for p in parts)
        limited = f" LIMIT {limit} " if limit else ""
        if query.aggregate:  # return aggregate
            group_by, return_spec = aggregate("r", query.aggregate)
            return f"""{all_parts} FOR r in {last(parts)[2]} {group_by}{limited} RETURN {return_spec}""", bind_vars
        else:  # return results
            # return all pinned parts (last result is "pinned" automatically)
            pinned = set(map(lambda x: x[2], filter(lambda x: x[0].pinned, parts)))
            result = f'UNION({",".join(pinned)},{last(parts)[2]})' if pinned else last(parts)[2]
            return f"""{all_parts} FOR r in {result}{limited} RETURN r""", bind_vars

    async def insert_genesis_data(self) -> None:
        root_data = {"kind": "graph_root", "name": "root"}
        sha = GraphBuilder.content_hash(root_data)
        root_node = {"_key": "root", "id": "root", "reported": root_data, "kinds": ["graph_root"], "hash": sha}
        try:
            await self.db.insert(self.vertex_name, root_node)
        except Exception:
            # ignore if the root not is already created
            return None

    async def create_update_schema(self) -> None:
        db = self.db

        async def create_update_graph(
            graph_name: str, vertex_name: str, edge_name: str
        ) -> Tuple[Graph, VertexCollection, EdgeCollection]:
            graph = db.graph(graph_name) if await db.has_graph(graph_name) else await db.create_graph(graph_name)
            vertex_collection = (
                graph.vertex_collection(vertex_name)
                if await db.has_vertex_collection(graph_name, vertex_name)
                else await db.create_vertex_collection(graph_name, vertex_name)
            )
            edge_collection = (
                graph.edge_collection(edge_name)
                if await db.has_edge_definition(graph_name, edge_name)
                else await db.create_edge_definition(graph_name, edge_name, [vertex_name], [vertex_name])
            )
            return graph, vertex_collection, edge_collection

        def create_update_indexes(nodes: VertexCollection, progress: StandardCollection) -> None:
            node_idxes = {idx["name"]: idx for idx in nodes.indexes()}
            if "node_id" not in node_idxes:
                nodes.add_persistent_index(["id"], unique=True, sparse=False, name="unique_node_id")
            progress_idxes = {idx["name"]: idx for idx in progress.indexes()}
            if "parent_nodes" not in progress_idxes:
                progress.add_persistent_index(["parent_nodes[*]"])
            if "root_nodes" not in progress_idxes:
                progress.add_persistent_index(["root_nodes[*]"])

        async def create_collection(name: str) -> StandardCollection:
            return db.collection(name) if await db.has_collection(name) else await db.create_collection(name)

        async def create_update_views(nodes: VertexCollection) -> None:
            name = f"search_{nodes.name}"
            views = {view["name"]: view for view in await db.views()}
            if name not in views:
                await db.create_view(
                    name,
                    "arangosearch",
                    {
                        "links": {
                            nodes.name: {"analyzers": ["identity"], "fields": {"flat": {"analyzers": ["text_en"]}}}
                        },
                    },
                )

        for edge_type in EdgeType.allowed_edge_types:
            edge_type_name = self.edge_collection(edge_type)
            await create_update_graph(self.name, self.vertex_name, edge_type_name)

        vertex = db.graph(self.name).vertex_collection(self.vertex_name)
        in_progress = await create_collection(self.in_progress)
        create_update_indexes(vertex, in_progress)
        if feature.DB_SEARCH:
            await create_update_views(vertex)
        await self.insert_genesis_data()

    def query_search_token(self) -> str:
        return f"""
        FOR doc IN search_{self.vertex_name}
        SEARCH ANALYZER(doc.flat IN TOKENS(@tokens, 'text_en'), 'text_en')
        SORT BM25(doc) DESC
        LIMIT @limit
        RETURN doc
        """

    # parameter: rid
    # return: the complete document
    def query_node_by_id(self) -> str:
        return f"""
      FOR resource in {self.vertex_name}
      FILTER resource.id==@rid
      LIMIT 1
      RETURN resource
      """

    def query_update_nodes(self) -> str:
        return f"""
        FOR a IN {self.vertex_name}
        FILTER a.update_id==@update_id
        RETURN {{_key: a._key, id:a.id, hash:a.hash}}
        """

    def query_update_edges(self, edge_type: str) -> str:
        collection = self.edge_collection(edge_type)
        return f"""
        FOR a IN {collection}
        FILTER a.update_id==@update_id
        RETURN {{_key: a._key, _from: a._from, _to: a._to}}
        """

    def query_update_parent_linked(self) -> str:
        return f"""
        FOR a IN {self.edge_collection(EdgeType.default)}
        FILTER a._from==@from and a._to==@to
        RETURN true
        """

    def query_count_direct_children(self) -> str:
        return f"""
        FOR pn in {self.vertex_name} FILTER pn.id==@rid LIMIT 1
        FOR c IN 1..1 OUTBOUND pn {self.edge_collection(EdgeType.default)} COLLECT WITH COUNT INTO length
        RETURN length
        """

    def query_active_batches(self) -> str:
        return f"""
        FOR c IN {self.in_progress} FILTER c.batch==true
        RETURN {{id: c.change, created: c.created, affected_nodes: c.root_nodes}}
        """

    def query_active_change(self) -> str:
        return f"""
        FOR change IN {self.in_progress}
        FILTER @root_node_id in change.parent_nodes OR @root_node_id in change.root_nodes
        RETURN change
        """

    def aql_create_update_change(self) -> str:
        return f"""
        LET parents = (
        FOR cn in {self.vertex_name} FILTER cn.id == @parent_node_id
            FOR pn IN 0..{Navigation.Max} INBOUND cn GRAPH {self.name}
            OPTIONS {{ bfs: true, uniqueVertices: 'global' }}
            RETURN pn.id
        )
        UPSERT {{_key: @change_key}}
        INSERT {{
                _key: @change_key,
                change: @change,
                root_nodes: [@root_node_id],
                parent_nodes: parents,
                batch: @is_batch,
                edge_types: @edge_types,
                created: DATE_ISO8601(DATE_NOW())
               }}
        UPDATE {{
                root_nodes: APPEND(OLD.root_nodes, [@root_node_id], true),
                parent_nodes: APPEND(OLD.parent_nodes, parents, true),
                edge_types: APPEND(OLD.edge_types, @edge_types, true)
               }}
        IN {self.in_progress} OPTIONS {{ exclusive: true }}
        """


class EventGraphDB(GraphDB):
    def __init__(self, real: ArangoGraphDB, event_bus: EventBus):
        self.real = real
        self.event_bus = event_bus
        self.graph_name = real.name

    async def get_node(self, node_id: str, result_section: Union[str, List[str]]) -> Optional[Json]:
        return await self.real.get_node(node_id, result_section)

    async def create_node(self, model: Model, node_id: str, data: Json, under_node_id: str) -> Json:
        result = await self.real.create_node(model, node_id, data, under_node_id)
        await self.event_bus.emit_event(
            CoreEvent.NodeCreated, {"graph": self.graph_name, "id": node_id, "parent": under_node_id}
        )
        return result

    async def update_node(
        self, model: Model, section: str, result_section: Union[str, List[str]], node_id: str, patch: Json
    ) -> Json:
        result = await self.real.update_node(model, section, result_section, node_id, patch)
        await self.event_bus.emit_event(
            CoreEvent.NodeUpdated, {"graph": self.graph_name, "id": node_id, "section": section}
        )
        return result

    async def delete_node(self, node_id: str) -> None:
        result = await self.real.delete_node(node_id)
        await self.event_bus.emit_event(CoreEvent.NodeDeleted, {"graph": self.graph_name, "id": node_id})
        return result

    def search(self, tokens: str, limit: int) -> AsyncGenerator[Json, None]:
        return self.real.search(tokens, limit)

    async def update_sub_graph(
        self, model: Model, sub: MultiDiGraph, under_node_id: str, maybe_batch: Optional[str] = None
    ) -> GraphUpdate:
        result = await self.real.update_sub_graph(model, sub, under_node_id, maybe_batch)
        even_data = {"graph": self.graph_name, "id": GraphAccess.root_id(sub), "parent": under_node_id}
        if maybe_batch:
            await self.event_bus.emit_event(CoreEvent.BatchUpdateSubGraphAdded, even_data)
        else:
            await self.event_bus.emit_event(CoreEvent.SubGraphUpdated, even_data)
        return result

    async def list_in_progress_batch_updates(self) -> List[Json]:
        return await self.real.list_in_progress_batch_updates()

    async def commit_batch_update(self, batch_id: str) -> None:
        info = first(lambda x: x["id"] == batch_id, await self.real.list_in_progress_batch_updates())  # type: ignore
        await self.real.commit_batch_update(batch_id)
        await self.event_bus.emit_event(CoreEvent.BatchUpdateCommitted, {"graph": self.graph_name, "batch": info})

    async def abort_batch_update(self, batch_id: str) -> None:
        info = first(lambda x: x["id"] == batch_id, await self.real.list_in_progress_batch_updates())  # type: ignore
        await self.real.abort_batch_update(batch_id)
        await self.event_bus.emit_event(CoreEvent.BatchUpdateAborted, {"graph": self.graph_name, "batch": info})

    def query_list(self, query: QueryModel) -> AsyncGenerator[Json, None]:
        return self.real.query_list(query)

    def query_graph_gen(self, query: QueryModel) -> AsyncGenerator[Tuple[str, Json], None]:
        return self.real.query_graph_gen(query)

    def query_aggregation(self, query: QueryModel) -> AsyncGenerator[Json, None]:
        return self.real.query_aggregation(query)

    async def query_graph(self, query: QueryModel) -> DiGraph:
        return await self.real.query_graph(query)

    async def explain(self, query: QueryModel) -> Json:
        return await self.real.explain(query)

    async def wipe(self) -> None:
        result = await self.real.wipe()
        await self.event_bus.emit_event(CoreEvent.GraphDBWiped, {"graph": self.graph_name})
        return result

    def to_query(
        self, query_model: QueryModel, all_edges: bool = False, limit: Optional[int] = None
    ) -> Tuple[str, Json]:
        return self.real.to_query(query_model, all_edges, limit)

    async def create_update_schema(self) -> None:
        await self.real.create_update_schema()
