from functools import partial
import time
import os
import threading
import multiprocessing
from cklib.baseresources import BaseResource
from concurrent import futures
from networkx.algorithms.dag import is_directed_acyclic_graph
import requests
import json
import cklib.signal
from pydoc import locate
from datetime import datetime, date, timedelta, timezone
from typing import List, Optional, Dict
from dataclasses import fields
from cklib.logging import log, add_args as logging_add_args
from cklib.graph import GraphContainer, Graph, sanitize, GraphExportIterator
from cklib.graph.export import optional_origin, node_to_dict
from cklib.pluginloader import PluginLoader
from cklib.baseplugin import BaseCollectorPlugin, PluginType
from cklib.utils import log_stats, increase_limits, str2timedelta, str2timezone
from cklib.args import ArgumentParser
from cklib.cleaner import Cleaner
from cklib.event import (
    add_event_listener,
    Event,
    EventType,
    CkEvents,
    CkCoreTasks,
    add_args as event_add_args,
)


# This will be used in main() and shutdown()
shutdown_event = threading.Event()
collect_event = threading.Event()


def main() -> None:
    log.info("Cloudkeeper collectord initializing")
    # Try to run in a new process group and
    # ignore if not possible for whatever reason
    try:
        os.setpgid(0, 0)
    except Exception:
        pass

    cklib.signal.parent_pid = os.getpid()

    # Add cli args
    # The following double parsing of cli args is done so that when
    # a user specifies e.g. `--collector aws --help`  they would
    # no longer be shown cli args for other collectors like gcp.
    collector_arg_parser = ArgumentParser(
        description="Cloudkeeper Worker",
        env_args_prefix="CKWORKER_",
        add_help=False,
    )
    PluginLoader.add_args(collector_arg_parser)
    (args, _) = collector_arg_parser.parse_known_args()
    ArgumentParser.args = args

    arg_parser = ArgumentParser(
        description="Cloudkeeper Worker",
        env_args_prefix="CKWORKER_",
    )
    logging_add_args(arg_parser)
    PluginLoader.add_args(arg_parser)
    GraphContainer.add_args(arg_parser)
    Cleaner.add_args(arg_parser)
    event_add_args(arg_parser)
    add_args(arg_parser)

    # Find cloudkeeper Plugins in the cloudkeeper.plugins module
    plugin_loader = PluginLoader(PluginType.COLLECTOR)
    plugin_loader.add_plugin_args(arg_parser)

    # At this point the CLI, all Plugins as well as the WebServer have
    # added their args to the arg parser
    arg_parser.parse_args()

    # Handle Ctrl+c and other means of termination/shutdown
    cklib.signal.initializer()
    add_event_listener(EventType.SHUTDOWN, shutdown, blocking=False)

    # Try to increase nofile and nproc limits
    increase_limits()

    all_collector_plugins = plugin_loader.plugins(PluginType.COLLECTOR)
    message_processor = partial(ckcore_message_processor, all_collector_plugins)

    ke = CkEvents(
        identifier="workerd-events",
        ckcore_uri=ArgumentParser.args.ckcore_uri,
        ckcore_ws_uri=ArgumentParser.args.ckcore_ws_uri,
        events={
            "collect": {
                "timeout": ArgumentParser.args.timeout,
                "wait_for_completion": True,
            },
            "cleanup": {
                "timeout": ArgumentParser.args.timeout,
                "wait_for_completion": True,
            },
        },
        message_processor=message_processor,
    )
    kt = CkCoreTasks(
        identifier="workerd-tasks",
        ckcore_ws_uri=ArgumentParser.args.ckcore_ws_uri,
        tasks=["tag"],
        task_queue_filter={},
        message_processor=tasks_processor,
    )
    ke.start()
    kt.start()

    # We wait for the shutdown Event to be set() and then end the program
    # While doing so we print the list of active threads once per 15 minutes
    shutdown_event.wait()
    time.sleep(1)  # everything gets 1000ms to shutdown gracefully before we force it
    cklib.signal.kill_children(cklib.signal.SIGTERM, ensure_death=True)
    log.info("Shutdown complete")
    os._exit(0)


def tasks_processor(message: Dict) -> None:
    task_id = message.get("task_id")
    # task_name = message.get("task_name")
    # task_attrs = message.get("attrs", {})
    task_data = message.get("data", {})
    delete_tags = task_data.get("delete", [])
    update_tags = task_data.get("update", {})
    node_data = task_data.get("node")
    node_id = node_data.get("id")
    node_revision = node_data.get("revision")
    result = "done"
    extra_data = {}

    try:
        node = node_from_dict(node_data)
        for delete_tag in delete_tags:
            del node.tags[delete_tag]

        for k, v in update_tags.items():
            node.tags[k] = v

        if node_id and node_revision:
            node_dict = node_to_dict(node)
            node_dict.update({"id": node_id, "revision": node_revision})
            extra_data.update({"data": node_dict})
    except Exception as e:
        log.exception("Error while updating tags")
        result = "error"
        extra_data["error"] = repr(e)

    reply_message = {
        "task_id": task_id,
        "result": result,
    }
    reply_message.update(extra_data)
    return reply_message


def ckcore_message_processor(
    collectors: List[BaseCollectorPlugin], message: Dict
) -> None:
    if not isinstance(message, dict):
        log.error(f"Invalid message: {message}")
        return
    kind = message.get("kind")
    message_type = message.get("message_type")
    data = message.get("data")
    log.debug(f"Received message of kind {kind}, type {message_type}, data: {data}")
    if kind == "action":
        try:
            if message_type == "collect":
                collect(collectors)
            elif message_type == "cleanup":
                cleanup()
            else:
                raise ValueError(f"Unknown message type {message_type}")
        except Exception as e:
            log.exception(f"Failed to {message_type}: {e}")
            reply_kind = "action_error"
        else:
            reply_kind = "action_done"

        reply_message = {
            "kind": reply_kind,
            "message_type": message_type,
            "data": data,
        }
        return reply_message


def node_from_dict(node_data: Dict) -> BaseResource:
    """Create a resource from ckcore graph node data"""
    log.debug(f"Making node from {node_data}")
    node_data_reported = node_data.get("reported", {})
    if node_data_reported is None:
        node_data_reported = {}
    node_data_desired = node_data.get("desired", {})
    if node_data_desired is None:
        node_data_desired = {}
    node_data_metadata = node_data.get("metadata", {})
    if node_data_metadata is None:
        node_data_metadata = {}

    new_node_data = dict(node_data_reported)
    del new_node_data["kind"]

    python_type = node_data_metadata.get("python_type", "NoneExisting")
    node_type = locate(python_type)
    if node_type is None:
        raise ValueError(f"Do not know how to handle {node_data_reported}")

    restore_node_field_types(node_type, new_node_data)
    cleanup_node_field_types(node_type, new_node_data)

    ancestors = {}
    for ancestor in ("cloud", "account", "region", "zone"):
        if node_data_reported.get(ancestor) and node_data_metadata.get(ancestor):
            ancestors[f"_{ancestor}"] = node_from_dict(
                {
                    "reported": node_data_reported[ancestor],
                    "metadata": node_data_metadata[ancestor],
                }
            )
    new_node_data.update(ancestors)

    node = node_type(**new_node_data)

    protect_node = node_data_metadata.get("protected", False)
    if protect_node:
        node.protected = protect_node
    clean_node = node_data_desired.get("clean", False)
    if clean_node:
        node.clean = clean_node
    node._raise_tags_exceptions = True
    return node


def cleanup():
    """Run resource cleanup"""

    def process_data_line(data: Dict, graph: Graph):
        """Process a single line of ckcore graph data"""

        if data.get("type") == "node":
            node_id = data.get("id")
            node = node_from_dict(data)
            node_mapping[node_id] = node
            log.debug(f"Adding node {node} to the graph")
            graph.add_node(node)
            if node.kind == "graph_root":
                log.debug(f"Setting graph root {node}")
                graph.root = node
        elif data.get("type") == "edge":
            node_from = data.get("from")
            node_to = data.get("to")
            if node_from not in node_mapping or node_to not in node_mapping:
                raise ValueError(f"One of {node_from} -> {node_to} unknown")
            graph.add_edge(node_mapping[node_from], node_mapping[node_to])

    log.info("Running cleanup")
    base_uri = ArgumentParser.args.ckcore_uri.strip("/")
    ckcore_graph = ArgumentParser.args.ckcore_graph
    graph_uri = f"{base_uri}/graph/{ckcore_graph}"
    query_uri = f"{graph_uri}/query/graph"
    query_filter = ""
    if ArgumentParser.args.collector and len(ArgumentParser.args.collector) > 0:
        clouds = '["' + '", "'.join(ArgumentParser.args.collector) + '"]'
        query_filter = f"and metadata.ancestors.cloud.id in {clouds} "
    query = f"desired.clean == true {query_filter}<-[0:]->"
    log.debug(f"Sending query {query}")
    r = requests.post(
        query_uri, data=query, headers={"accept": "application/x-ndjson"}, stream=True
    )
    if r.status_code != 200:
        log.error(r.content)
        raise RuntimeError(f"Failed to query graph: {r.content}")
    graph = Graph()
    node_mapping = {}

    for line in r.iter_lines():
        if not line:
            continue
        data = json.loads(line.decode("utf-8"))
        try:
            process_data_line(data, graph)
        except ValueError as e:
            log.error(e)
            continue
    sanitize(graph)
    cleaner = Cleaner(graph)
    cleaner.cleanup()


def cleanup_node_field_types(node_type: BaseResource, node_data_reported: Dict):
    valid_fields = set(field.name for field in fields(node_type))
    for field_name in list(node_data_reported.keys()):
        if field_name not in valid_fields:
            log.debug(
                f"Removing extra field {field_name} from new node of type {node_type}"
            )
            del node_data_reported[field_name]


def restore_node_field_types(node_type: BaseResource, node_data_reported: Dict):
    for field in fields(node_type):
        if field.name not in node_data_reported:
            continue
        field_type = optional_origin(field.type)

        if field_type == datetime:
            datetime_str = str(node_data_reported[field.name])
            if datetime_str.endswith("Z"):
                datetime_str = datetime_str[:-1] + "+00:00"
            node_data_reported[field.name] = datetime.fromisoformat(datetime_str)
        elif field_type == date:
            node_data_reported[field.name] = date.fromisoformat(
                node_data_reported[field.name]
            )
        elif field_type == timedelta:
            node_data_reported[field.name] = str2timedelta(
                node_data_reported[field.name]
            )
        elif field_type == timezone:
            node_data_reported[field.name] = str2timezone(
                node_data_reported[field.name]
            )


def collect(collectors: List[BaseCollectorPlugin]):
    graph_container = GraphContainer(cache_graph=False)
    graph = graph_container.graph
    max_workers = (
        len(collectors)
        if len(collectors) < ArgumentParser.args.pool_size
        else ArgumentParser.args.pool_size
    )
    pool_args = {"max_workers": max_workers}
    if ArgumentParser.args.fork:
        pool_args["mp_context"] = multiprocessing.get_context("spawn")
        pool_args["initializer"] = cklib.signal.initializer
        pool_executor = futures.ProcessPoolExecutor
        collect_args = {"args": ArgumentParser.args}
    else:
        pool_executor = futures.ThreadPoolExecutor
        collect_args = {}

    with pool_executor(**pool_args) as executor:
        wait_for = [
            executor.submit(
                collect_plugin_graph,
                collector,
                **collect_args,
            )
            for collector in collectors
        ]
        for future in futures.as_completed(wait_for):
            cluster_graph = future.result()
            if not isinstance(cluster_graph, Graph):
                log.error(f"Skipping invalid cluster_graph {type(cluster_graph)}")
                continue
            graph.merge(cluster_graph)
    sanitize(graph)
    send_to_ckcore(graph)


def collect_plugin_graph(
    collector_plugin: BaseCollectorPlugin, args=None
) -> Optional[Graph]:
    collector: BaseCollectorPlugin = collector_plugin()
    collector_name = f"collector_{collector.cloud}"
    cklib.signal.set_thread_name(collector_name)

    if args is not None:
        ArgumentParser.args = args

    log.debug(f"Starting new collect process for {collector.cloud}")
    collector.start()
    collector.join(ArgumentParser.args.timeout)
    if not collector.is_alive():  # The plugin has finished its work
        if not collector.finished:
            log.error(
                f"Plugin {collector.cloud} did not finish collection"
                " - ignoring plugin results"
            )
            return None
        if not is_directed_acyclic_graph(collector.graph):
            log.error(
                f"Graph of plugin {collector.cloud} is not acyclic"
                " - ignoring plugin results"
            )
            return None
        log.info(f"Collector of plugin {collector.cloud} finished")
        return collector.graph
    else:
        log.error(f"Plugin {collector.cloud} timed out - discarding Plugin graph")
        return None


def send_to_ckcore(graph: Graph):
    if not ArgumentParser.args.ckcore_uri:
        return

    log.info("ckcore Event Handler called")
    base_uri = ArgumentParser.args.ckcore_uri.strip("/")
    ckcore_graph = ArgumentParser.args.ckcore_graph
    model_uri = f"{base_uri}/model"
    graph_uri = f"{base_uri}/graph/{ckcore_graph}"
    merge_uri = f"{graph_uri}/merge"
    log.debug(f"Creating graph {ckcore_graph} via {graph_uri}")
    r = requests.post(graph_uri, data="", headers={"accept": "application/json"})
    if r.status_code != 200:
        log.error(r.content)
        raise RuntimeError(f"Failed to create graph: {r.content}")
    log.debug(f"Updating model via {model_uri}")
    model_json = json.dumps(graph.export_model(), indent=4)
    if ArgumentParser.args.debug_dump_json:
        with open("model.dump.json", "w") as model_outfile:
            model_outfile.write(model_json)
    r = requests.patch(model_uri, data=model_json)
    if r.status_code != 200:
        log.error(r.content)
        raise RuntimeError(f"Failed to create model: {r.content}")
    graph_outfile = None
    if ArgumentParser.args.debug_dump_json:
        graph_outfile = open("graph.dump.json", "w")
    graph_export_iterator = GraphExportIterator(graph, graph_outfile)
    log.debug(f"Sending subgraph via {merge_uri}")
    r = requests.post(
        merge_uri,
        data=graph_export_iterator,
        headers={"Content-Type": "application/x-ndjson"},
    )
    if graph_outfile is not None:
        graph_outfile.close()
    if r.status_code != 200:
        log.error(r.content)
        raise RuntimeError(f"Failed to send graph: {r.content}")
    log.debug(f"ckcore reply: {r.content.decode()}")
    log.debug(
        f"Sent {graph_export_iterator.nodes_sent} nodes and {graph_export_iterator.edges_sent} edges to ckcore"
    )


def add_args(arg_parser: ArgumentParser) -> None:
    arg_parser.add_argument(
        "--ckcore-uri",
        help="ckcore URI (default: http://localhost:8900)",
        default="http://localhost:8900",
        dest="ckcore_uri",
    )
    arg_parser.add_argument(
        "--ckcore-ws-uri",
        help="ckcore Websocket URI (default: ws://localhost:8900)",
        default="ws://localhost:8900",
        dest="ckcore_ws_uri",
    )
    arg_parser.add_argument(
        "--ckcore-graph",
        help="ckcore graph name (default: ck)",
        default="ck",
        dest="ckcore_graph",
    )
    arg_parser.add_argument(
        "--pool-size",
        help="Collector Thread/Process Pool Size (default: 5)",
        dest="pool_size",
        default=5,
        type=int,
    )
    arg_parser.add_argument(
        "--fork",
        help="Use forked process instead of threads (default: False)",
        dest="fork",
        action="store_true",
    )
    arg_parser.add_argument(
        "--timeout",
        help="Collection Timeout in seconds (default: 10800)",
        default=10800,
        dest="timeout",
        type=int,
    )
    arg_parser.add_argument(
        "--debug-dump-json",
        help="Dump the generated json data (default: False)",
        dest="debug_dump_json",
        action="store_true",
    )


def shutdown(event: Event) -> None:
    reason = event.data.get("reason")
    emergency = event.data.get("emergency")

    if emergency:
        cklib.signal.emergency_shutdown(reason)

    current_pid = os.getpid()
    if current_pid != cklib.signal.parent_pid:
        return

    if reason is None:
        reason = "unknown reason"
    log.info(
        (
            f"Received shut down event {event.event_type}:"
            f" {reason} - killing all threads and child processes"
        )
    )
    shutdown_event.set()  # and then end the program


def force_shutdown(delay: int = 10) -> None:
    time.sleep(delay)
    log_stats()
    log.error(
        (
            "Some child process or thread timed out during shutdown"
            " - forcing shutdown completion"
        )
    )
    os._exit(0)


if __name__ == "__main__":
    main()
