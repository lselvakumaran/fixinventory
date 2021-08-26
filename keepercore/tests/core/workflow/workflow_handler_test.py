import asyncio
from datetime import timedelta

import pytest
from contextlib import asynccontextmanager
from pytest import fixture
from typing import Type, AsyncGenerator

from core.db.workflowinstancedb import WorkflowInstanceDb
from core.event_bus import EventBus, Event, Message, ActionDone, Action
from core.util import first, AnyT, utc
from core.workflow.model import Subscriber
from core.workflow.scheduler import Scheduler
from core.workflow.subscribers import SubscriptionHandler
from core.workflow.workflow_handler import WorkflowHandler
from tests.core.db.entitydb import InMemoryDb

# noinspection PyUnresolvedReferences
from tests.core.db.graphdb_test import test_db

# noinspection PyUnresolvedReferences
from tests.core.event_bus_test import event_bus, all_events

# noinspection PyUnresolvedReferences
from tests.core.db.workflowinstancedb_test import workflow_instance_db


@fixture
async def subscription_handler(event_bus: EventBus) -> SubscriptionHandler:
    in_mem = InMemoryDb(Subscriber, lambda x: x.id)
    result = SubscriptionHandler(in_mem, event_bus)
    return result


@fixture
async def workflow_handler(
    workflow_instance_db: WorkflowInstanceDb, event_bus: EventBus, subscription_handler: SubscriptionHandler
) -> WorkflowHandler:
    return WorkflowHandler(workflow_instance_db, event_bus, subscription_handler, Scheduler())


@pytest.mark.asyncio
async def test_recover(
    workflow_instance_db: WorkflowInstanceDb,
    event_bus: EventBus,
    subscription_handler: SubscriptionHandler,
    all_events: list[Message],
) -> None:
    @asynccontextmanager
    async def handler() -> AsyncGenerator[WorkflowHandler, None]:
        wfh = WorkflowHandler(workflow_instance_db, event_bus, subscription_handler, Scheduler())
        await wfh.start()
        try:
            yield wfh
        finally:
            await wfh.stop()

    async def wait_for_message(message_type: str, t: Type[AnyT], timeout: timedelta = timedelta(seconds=1)) -> AnyT:
        stop_at = utc() + timeout

        async def find() -> AnyT:
            result = first(lambda m: isinstance(m, t) and m.message_type == message_type, all_events)  # type: ignore
            if result:
                return result  # type: ignore
            elif utc() > stop_at:
                raise TimeoutError()
            else:
                await asyncio.sleep(0.1)
                return await find()

        return await find()

    await subscription_handler.add_subscription("sub_1", "start_collect", True, timedelta(seconds=30))
    sub1 = await subscription_handler.add_subscription("sub_1", "collect", True, timedelta(seconds=30))
    sub2 = await subscription_handler.add_subscription("sub_2", "collect", True, timedelta(seconds=30))

    async with handler() as wf1:
        # kick off a new workflow
        await wf1.handle_event(Event("start_collect_workflow"))
        assert len(wf1.workflow_instances) == 1
        # expect a start_collect action message
        a: Action = await wait_for_message("start_collect", Action)
        await wf1.handle_action_done(ActionDone(a.message_type, a.workflow_instance_id, a.step_name, sub1.id, a.data))

        # expect a collect action message
        b: Action = await wait_for_message("collect", Action)
        await wf1.handle_action_done(ActionDone(b.message_type, b.workflow_instance_id, b.step_name, sub1.id, b.data))

    # subscriber 3 is also registering for collect
    # since the collect phase is already started, it should not participate in this round
    sub3 = await subscription_handler.add_subscription("sub_3", "collect", True, timedelta(seconds=30))

    # simulate a restart, wf1 is stopped and wf2 needs to recover from database
    async with handler() as wf2:
        assert len(wf2.workflow_instances) == 1
        wfi = list(wf2.workflow_instances.values())[0]
        assert wfi.current_state.name == "act"
        assert (await wf2.list_all_pending_actions_for(sub1)) == []
        assert (await wf2.list_all_pending_actions_for(sub2)) == [Action("collect", wfi.id, "act", {})]
        assert (await wf2.list_all_pending_actions_for(sub3)) == []
        await wf2.handle_action_done(ActionDone("collect", wfi.id, "act", sub2.id, {}))
        # expect an event workflow_end
        await wait_for_message("workflow_end", Event)
        # all workflow instances are gone
        assert len(wf2.workflow_instances) == 0

    # simulate a restart, wf3 should start from a clean slate, since all instances are done
    async with handler() as wf3:
        assert len(wf3.workflow_instances) == 0
