import multiprocessing
import threading
from queue import Queue
import resotolib.proc
from time import time
from concurrent import futures
from threading import Lock
from resotoworker.exceptions import DuplicateMessageError
from resotoworker.resotocore import Resotocore
from resotolib.baseplugin import BaseCollectorPlugin
from resotolib.baseresources import GraphRoot, BaseCloud, BaseAccount, BaseResource
from resotolib.core.actions import CoreFeedback
from resotolib.graph import Graph, sanitize, GraphMergeKind
from resotolib.logger import log, setup_logger
from resotolib.args import ArgumentParser
from argparse import Namespace
from typing import List, Optional, Type, Dict, Any, Set
from resotolib.config import Config, RunningConfig
from resotolib.types import Json

TaskId = str


class Collector:
    def __init__(self, config: Config, resotocore: Resotocore, core_messages: Queue[Json]) -> None:
        self._resotocore = resotocore
        self._config = config
        self.core_messages = core_messages
        self.processing: Set[str] = set()
        self.processing_lock = Lock()

    def graph_sender(self, graph_queue: Queue[Optional[Graph]], task_id: TaskId) -> None:
        log.debug("Waiting for collector graphs")
        start_time = time()
        while True:
            collector_graph = graph_queue.get()
            if collector_graph is None:
                run_time = time() - start_time
                log.debug(f"Ending graph sender thread for task id {task_id} after {run_time} seconds")
                break

            graph = Graph(root=GraphRoot(id="root", tags={}))
            graph.merge(collector_graph)
            sanitize(graph)

            graph_info = ""
            assert isinstance(graph.root, BaseResource)
            for cloud in graph.successors(graph.root):
                if isinstance(cloud, BaseCloud):
                    graph_info += f" {cloud.kdname}"
                for account in graph.successors(cloud):
                    if isinstance(account, BaseAccount):
                        graph_info += f" {account.kdname}"

            log.info(f"Received collector graph for{graph_info}")

            if (cycle := graph.find_cycle()) is not None:
                desc = ", ".join, [f"{key.edge_type}: {key.src.kdname}-->{key.dst.kdname}" for key in cycle]
                log.error(f"Graph of {graph_info} is not acyclic - ignoring. Cycle {desc}")
                continue

            self._resotocore.send_to_resotocore(graph, task_id)

    def collect_and_send(
        self,
        collectors: List[Type[BaseCollectorPlugin]],
        task_id: TaskId,
        step_name: str,
    ) -> None:
        core_feedback = CoreFeedback(task_id, step_name, "collect", self.core_messages)

        def collect(collectors: List[Type[BaseCollectorPlugin]], graph_queue: Queue[Optional[Graph]]) -> bool:
            all_success = True
            graph_merge_kind = self._config.resotoworker.graph_merge_kind

            max_workers = (
                len(collectors)
                if len(collectors) < self._config.resotoworker.pool_size
                else self._config.resotoworker.pool_size
            )
            if max_workers == 0:
                log.error("No workers configured or no collector plugins loaded - skipping collect")
                return False
            pool_args = {"max_workers": max_workers}
            pool_executor: Type[futures.Executor]
            collect_args: Dict[str, Any]
            if self._config.resotoworker.fork_process:
                pool_args["mp_context"] = multiprocessing.get_context("spawn")
                pool_args["initializer"] = resotolib.proc.initializer
                pool_executor = futures.ProcessPoolExecutor
                collect_args = {
                    "args": ArgumentParser.args,
                    "running_config": self._config.running_config,
                }
            else:
                pool_executor = futures.ThreadPoolExecutor
                collect_args = {}

            with pool_executor(**pool_args) as executor:
                wait_for = [
                    executor.submit(
                        collect_plugin_graph,
                        collector,
                        core_feedback,
                        graph_queue,
                        graph_merge_kind,
                        **collect_args,
                    )
                    for collector in collectors
                ]
                for future in futures.as_completed(wait_for):
                    collector_success = future.result()
                    if not collector_success:
                        all_success = False
            return all_success

        processing_id = f"{task_id}:{step_name}"
        try:
            with self.processing_lock:
                if processing_id in self.processing:
                    raise DuplicateMessageError(f"Already processing {processing_id} - ignoring message")
                self.processing.add(processing_id)

            mp_manager = multiprocessing.Manager()
            graph_queue: Queue[Optional[Graph]] = mp_manager.Queue()
            graph_sender_threads = []
            graph_sender_pool_size = self._config.resotoworker.graph_sender_pool_size
            try:
                for i in range(graph_sender_pool_size):
                    graph_queue_t = threading.Thread(
                        target=self.graph_sender, args=(graph_queue, task_id), name=f"graph_sender_{i}"
                    )
                    graph_queue_t.daemon = True
                    graph_queue_t.start()
                    graph_sender_threads.append(graph_queue_t)

                self._resotocore.create_graph_and_update_model()
                collect(collectors, graph_queue)
            finally:
                log.debug("Telling graph sender threads to end")
                for _ in range(graph_sender_pool_size):
                    graph_queue.put(None)
                for t in graph_sender_threads:
                    t.join()

        finally:
            with self.processing_lock:
                if processing_id in self.processing:
                    self.processing.remove(processing_id)


def collect_plugin_graph(
    collector_plugin: Type[BaseCollectorPlugin],
    core_feedback: CoreFeedback,
    graph_queue: Queue[Optional[Graph]],
    graph_merge_kind: GraphMergeKind,
    args: Optional[Namespace] = None,
    running_config: Optional[RunningConfig] = None,
) -> bool:
    try:
        collector: BaseCollectorPlugin = collector_plugin(graph_queue=graph_queue, graph_merge_kind=graph_merge_kind)
        core_feedback.progress_done(collector.cloud, 0, 1)
        if core_feedback and hasattr(collector, "core_feedback"):
            setattr(collector, "core_feedback", core_feedback)
        collector_name = f"collector_{collector.cloud}"
        resotolib.proc.set_thread_name(collector_name)

        if args is not None:
            ArgumentParser.args = args  # type: ignore
            setup_logger("resotoworker")
        if running_config is not None:
            Config.running_config.apply(running_config)

        log.debug(f"Starting new collect process for {collector.cloud}")
        start_time = time()
        collector.start()
        collector.join(Config.resotoworker.timeout)
        core_feedback.progress_done(collector.cloud, 1, 1)
        elapsed = time() - start_time
        if not collector.is_alive():  # The plugin has finished its work
            if not collector.finished:
                log.error(f"Plugin {collector.cloud} did not finish collection" " - ignoring plugin results")
                return False
            log.info(f"Collector of plugin {collector.cloud} finished in {elapsed:.4f}s")
            return True
        else:
            log.error(f"Plugin {collector.cloud} timed out - discarding plugin graph")
            return False
    except Exception as e:
        log.exception(f"Unhandled exception in {collector_plugin}: {e} - ignoring plugin")
        return False
