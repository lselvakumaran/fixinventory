from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Mapping, List, Union

from core.types import JsonElement
from core.util import utc

log = logging.getLogger(__name__)


class CoreEvent:
    SystemStarted = "system.started"
    SystemStopped = "system.stopped"
    NodeCreated = "graphdb.node-created"
    NodeUpdated = "graphdb.node-updated"
    NodesDesiredUpdated = "graphdb.nodes-desired-updated"
    NodesMetadataUpdated = "graphdb.nodes-metadata-updated"
    NodeDeleted = "graphdb.node-deleted"
    GraphMerged = "graphdb.graph-merged"
    BatchUpdateGraphMerged = "graphdb.batch-update-graph-merged"
    BatchUpdateCommitted = "graphdb.batch-update-committed"
    BatchUpdateAborted = "graphdb.batch-update-aborted"
    GraphDBWiped = "graphdb.wiped"
    CLICommand = "cli.command"
    Query = "graphdb.query"
    ModelInfo = "model.info"
    SubscriberInfo = "subscriber.info"
    WorkerQueueInfo = "worker-queue.info"


@dataclass(frozen=True)
class AnalyticsEvent:
    system: str  # e.g. creator of the event: ckcore, ckui, cksh, etc.
    kind: str  # kind of the event. Every kind has a specific set of data and context vars
    context: Mapping[str, JsonElement]  # context properties
    counters: Mapping[str, Union[int, float]]  # all counters of this event
    at: datetime  # time, when this event has been created


class AnalyticsEventSender(ABC):
    async def core_event(
        self, kind: str, context: Optional[Mapping[str, JsonElement]] = None, **counters: Union[int, float]
    ) -> AnalyticsEvent:
        event = AnalyticsEvent("ckcore", kind, context if context else {}, counters, utc())
        await self.send_event(event)
        return event

    @abstractmethod
    async def send_event(self, event: AnalyticsEvent) -> None:
        pass

    @staticmethod
    async def flush() -> None:
        """
        Override this method to allow explicit flushing of events.
        """
        return None


class NoEventSender(AnalyticsEventSender):
    """
    Use this sender to not emit any events other than writing it to the log file.
    """

    async def send_event(self, event: AnalyticsEvent) -> None:
        log.debug(event)


class InMemoryEventSender(AnalyticsEventSender):
    """
    This sender is used to collect events happening in other processes as well as for testing purposes.
    """

    def __init__(self) -> None:
        self.events: List[AnalyticsEvent] = []

    async def send_event(self, event: AnalyticsEvent) -> None:
        self.events.append(event)
