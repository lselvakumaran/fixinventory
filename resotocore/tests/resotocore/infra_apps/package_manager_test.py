from typing import cast, Awaitable
from resotocore.infra_apps.package_manager import PackageManager, PackageEntityDb, app_manifest_entity_db, FromGit
import pytest
from resotocore.ids import InfraAppName
from resotocore.db.async_arangodb import AsyncArangoDB
from arango.database import StandardDatabase
from types import SimpleNamespace
from resotocore.config import ConfigHandler
import asyncio
from asyncio import Future
import time
from datetime import timedelta
from tempfile import TemporaryDirectory
from pathlib import Path
import aiofiles.os as aos


@pytest.fixture
async def model_db(test_db: StandardDatabase) -> PackageEntityDb:
    async_db = AsyncArangoDB(test_db)
    entity_db = app_manifest_entity_db(async_db, "test_package_entity_db")
    await entity_db.create_update_schema()
    await entity_db.wipe()
    return entity_db


def async_none() -> Awaitable[None]:
    future: Future[None] = Future()
    future.set_result(None)
    return future


config_handler = cast(
    ConfigHandler,
    SimpleNamespace(
        put_config=lambda config_entity, validate: async_none(),
        delete_config=lambda config_id: async_none(),
        update_configs_model=lambda models: async_none(),
        put_config_validation=lambda config_validation: async_none(),
    ),
)


@pytest.mark.asyncio
async def test_install_delete(model_db: PackageEntityDb) -> None:
    name = InfraAppName("cleanup_untagged")
    repo_url = "https://github.com/someengineering/resoto-apps.git"
    package_manager = PackageManager(model_db, config_handler)
    await package_manager.start()

    manifest = await package_manager.install(name, FromGit(repo_url))
    assert manifest is not None
    assert manifest.name == name

    # check that it is installed
    installed_apps = [name async for name in package_manager.list()]
    assert installed_apps == [name]

    installed_app = await package_manager.info(name)
    assert installed_app is not None
    assert installed_app.name == name

    # update is possible
    updated_manifest = await package_manager.update(name)
    assert updated_manifest is not None
    assert updated_manifest.name == name

    # check that it can be deleted
    await package_manager.delete(name)

    # check that it is not installed anymore
    installed_apps_after_deletion = [name async for name in package_manager.list()]
    assert installed_apps_after_deletion == []


@pytest.mark.asyncio
async def test_cleanup_old_repos(model_db: PackageEntityDb) -> None:
    name = InfraAppName("cleanup_untagged")

    now = [time.time()]

    def fake_clock() -> float:
        return now[0]

    repo_url = "https://github.com/someengineering/resoto-apps.git"
    with TemporaryDirectory(suffix="resoto-package-manager-repo-test") as temp_dir:
        temp_dir = Path(temp_dir)
        package_manager = PackageManager(
            model_db,
            config_handler,
            repos_directory=temp_dir,
            check_interval=timedelta(milliseconds=250),
            cleanup_after=timedelta(seconds=2),
            current_epoch_seconds=fake_clock,
        )
        await package_manager.start()
        await package_manager.install(name, FromGit(repo_url))
        assert len(await aos.listdir(temp_dir)) == 1
        now[0] += 3
        max_tries = 5
        while await aos.listdir(temp_dir) and max_tries > 0:
            max_tries -= 1
            await asyncio.sleep(0.25)
        assert len(await aos.listdir(temp_dir)) == 0
