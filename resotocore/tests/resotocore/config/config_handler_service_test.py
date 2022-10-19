from textwrap import dedent
from typing import List, Any

import pytest
from pytest import fixture

from resotocore.config import ConfigHandler, ConfigEntity, ConfigValidation
from resotocore.config.config_handler_service import ConfigHandlerService
from resotocore.ids import ConfigId
from resotocore.message_bus import MessageBus, CoreMessage, Event, Message
from resotocore.model.model import Kind, ComplexKind, Property
from resotocore.model.typed_model import to_js, from_js
from resotocore.worker_task_queue import WorkerTaskQueue
from tests.resotocore.db.entitydb import InMemoryDb

# noinspection PyUnresolvedReferences
from tests.resotocore.worker_task_queue_test import worker, task_queue, performed_by, incoming_tasks

# noinspection PyUnresolvedReferences
from tests.resotocore.message_bus_test import message_bus, wait_for_message, all_events


@fixture
def config_handler(task_queue: WorkerTaskQueue, worker: Any, message_bus: MessageBus) -> ConfigHandler:
    # Note: the worker fixture is required, since it starts worker tasks
    cfg_db = InMemoryDb(ConfigEntity, lambda c: c.id)
    validation_db = InMemoryDb(ConfigValidation, lambda c: c.id)
    model_db = InMemoryDb(Kind, lambda c: c.fqn)  # type: ignore
    return ConfigHandlerService(cfg_db, validation_db, model_db, task_queue, message_bus)


@fixture
def config_model() -> List[Kind]:
    return [
        ComplexKind(
            "sub_section",
            [],
            [
                Property("num", "int32", description="Some arbitrary number."),
                Property("str", "string", description="Some arbitrary string."),
            ],
        ),
        ComplexKind(
            "section",
            [],
            [
                Property("some_number", "int32", required=True, description="Some number.\nAnd some description."),
                Property("some_string", "string", required=True, description="Some string.\nAnd some description."),
                Property("some_sub", "sub_section", required=True, description="Some sub.\nAnd some description."),
            ],
        ),
    ]


@pytest.mark.asyncio
async def test_config(config_handler: ConfigHandler) -> None:
    # list is empty on start
    assert [a async for a in config_handler.list_config_ids()] == []

    config_id = ConfigId("test")
    # add one entry
    entity = ConfigEntity(config_id, {"test": True})
    assert await config_handler.put_config(entity) == entity

    # get one entry
    assert await config_handler.get_config(config_id) == entity

    # patch the config
    assert await config_handler.patch_config(ConfigEntity(config_id, {"rest": False})) == ConfigEntity(
        config_id, {"test": True, "rest": False}
    )

    # list all configs
    assert [a async for a in config_handler.list_config_ids()] == ["test"]

    # delete the config
    await config_handler.delete_config(config_id)

    # list all configs
    assert [a async for a in config_handler.list_config_ids()] == []


@pytest.mark.asyncio
async def test_config_validation(config_handler: ConfigHandler, config_model: List[Kind]) -> None:
    await config_handler.update_configs_model(config_model)
    valid_config = {"section": {"some_number": 32, "some_string": "test", "some_sub": {"num": 32}}}

    # define the model
    await config_handler.put_config_validation(ConfigValidation("test", True))

    # list all available models
    assert [a async for a in config_handler.list_config_validation_ids()] == ["test"]

    # get the model
    model: ConfigValidation = await config_handler.get_config_validation("test")  # type: ignore
    assert model.external_validation is True

    # check the config against the model
    invalid_config = {"section": {"some_number": "no number"}}
    invalid_config_id = ConfigId("invalid_config")
    with pytest.raises(AttributeError) as reason:
        await config_handler.put_config(ConfigEntity(invalid_config_id, invalid_config))
    assert "some_number is not valid: Expected type int32 but got str" in str(reason.value)

    # External validation turned on: config with name "invalid_config" is rejected by the configured worker
    await config_handler.put_config_validation(ConfigValidation(invalid_config_id, True))
    with pytest.raises(AttributeError) as reason:
        # The config is actually valid, but the external validation will fail
        await config_handler.put_config(ConfigEntity(invalid_config_id, valid_config))
    assert "Error executing task: Invalid Config ;)" in str(reason)

    # If external validation is turned off, the configuration can be updated
    await config_handler.put_config_validation(ConfigValidation(invalid_config_id, False))
    await config_handler.put_config(ConfigEntity(invalid_config_id, valid_config))


@pytest.mark.asyncio
async def test_config_yaml(config_handler: ConfigHandler, config_model: List[Kind]) -> None:
    await config_handler.update_configs_model(config_model)
    config = {"some_number": 32, "some_string": "test", "some_sub": {"num": 32}}
    expect_comment = dedent(
        """
        section:
          # Some number.
          # And some description.
          some_number: 32
          # Some string.
          # And some description.
          some_string: 'test'
          # Some sub.
          # And some description.
          some_sub:
            # Some arbitrary number.
            num: 32
        """
    ).strip()
    expect_no_comment = dedent(
        """
        another_section:
          some_number: 32
          some_string: test
          some_sub:
            num: 32
        """
    ).strip()
    # config has section with attached model
    test_config_id = ConfigId("test")
    await config_handler.put_config(ConfigEntity(test_config_id, {"section": config}))
    assert expect_comment in (await config_handler.config_yaml(test_config_id) or "")
    # different section with no attached model
    nomodel_config_id = ConfigId("no_model")
    await config_handler.put_config(ConfigEntity(nomodel_config_id, {"another_section": config}))
    assert expect_no_comment in (await config_handler.config_yaml(nomodel_config_id) or "")


@pytest.mark.asyncio
async def test_config_change_emits_event(config_handler: ConfigHandler, all_events: List[Message]) -> None:
    # Put a config
    all_events.clear()
    config_id = ConfigId("foo")
    cfg = await config_handler.put_config(ConfigEntity(config_id, dict(test=1)))
    message = await wait_for_message(all_events, CoreMessage.ConfigUpdated, Event)
    assert message.data["id"] == cfg.id
    assert message.data["revision"] == cfg.revision

    # Patch a config
    all_events.clear()
    cfg = await config_handler.patch_config(ConfigEntity(config_id, dict(foo=2)))
    message = await wait_for_message(all_events, CoreMessage.ConfigUpdated, Event)
    assert message.data["id"] == cfg.id
    assert message.data["revision"] == cfg.revision

    # Delete a config
    all_events.clear()
    await config_handler.delete_config(config_id)
    message = await wait_for_message(all_events, CoreMessage.ConfigDeleted, Event)
    assert message.data["id"] == config_id
    assert "revision" not in message.data


def test_config_entity_roundtrip() -> None:
    entity = ConfigEntity(ConfigId("test"), {"test": 1}, "test")
    again = from_js(to_js(entity), ConfigEntity)
    assert entity == again
