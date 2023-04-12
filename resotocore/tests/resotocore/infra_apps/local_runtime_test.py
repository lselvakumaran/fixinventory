from resotocore.infra_apps.local_runtime import LocalResotocoreAppRuntime
from resotocore.infra_apps.manifest import AppManifest
from resotocore.infra_apps.runtime import AppResult, Success
from resotocore.ids import InfraAppName
import pytest
from resotocore.cli.model import CLI
from typing import AsyncGenerator, Optional
from argparse import Namespace


@pytest.mark.asyncio
async def test_template_generation(cli: CLI) -> None:
    cleanup_untagged = """
            {%- set tags_part = 'not(has_key(tags, ["' + '", "'.join(config["tags"]) + '"]))' %}
            {%- set kinds_part = 'is(["' + '", "'.join(config["kinds"]) + '"])' %}
            {%- set account_parts = [] %}
            {%- set default_age = config["default"]["age"]|default("2h") %}
            {%- for cloud_id, account in config["accounts"].items() %}
                {%- for account_id, account_data in account.items() %}
                    {%- set age = account_data.get("age", default_age) %}
                    {%- set account_part = '(/ancestors.cloud.reported.id == "' ~ cloud_id ~ '" and /ancestors.account.reported.id == "' ~ account_id ~ '" and age > ' ~ age ~ ')' %}
                    {%- do account_parts.append(account_part) %}
                {%- endfor %}
            {%- endfor %}
            {%- set accounts_part = "(" + " or ".join(account_parts) + ")" %}
            {%- set exclusion_part = "/metadata.protected == false and /metadata.phantom == false and /metadata.cleaned == false" %}
            {%- set required_tags = ", ".join(config["tags"]) %}
            {%- set reason = "Missing one or more of required tags " ~ required_tags ~ " and age more than threshold" %}
            {%- set cleanup_search = 'search ' ~ exclusion_part ~ ' and ' ~ kinds_part ~ ' and ' ~ tags_part ~ ' and ' ~ accounts_part ~ ' | clean "' ~ reason ~ '"' %}
            {{ cleanup_search }}
        """

    config = {
        "tags": ["resoto:cleanup"],
        "kinds": ["instance"],
        "default": {"age": "1s"},
        "accounts": {
            "digitalocean": {
                "12345": {"age": "1s"},
            },
        },
    }

    manifest = AppManifest(
        name=InfraAppName("test-app"),
        description="test app description",
        version="0.0.0",
        readme="",
        language="jinja2",
        url="",
        icon="",
        categories=[],
        default_config=None,
        config_schema=None,
        args_schema=[],
        source=cleanup_untagged,
    )

    runtime = LocalResotocoreAppRuntime(cli)

    lines = [line async for line in runtime._generate_template(manifest, config, stdin(), namespace)]
    assert lines == [
        (
            "search /metadata.protected == false and /metadata.phantom == false and /metadata.cleaned == false "
            'and is(["instance"]) and not(has_key(tags, ["resoto:cleanup"])) and ((/ancestors.cloud.reported.id'
            ' == "digitalocean" and /ancestors.account.reported.id == "12345" and age > 1s)) | '
            'clean "Missing one or more of required tags resoto:cleanup and age more than threshold"'
        ),
    ]


@pytest.mark.asyncio
async def test_execute(cli: CLI) -> None:
    source = "echo foo"
    manifest = AppManifest(
        name=InfraAppName("test-app"),
        description="test app description",
        version="0.0.0",
        readme="",
        language="jinja2",
        url="",
        icon="",
        categories=[],
        default_config=None,
        config_schema=None,
        args_schema=[],
        source=source,
    )

    runtime = LocalResotocoreAppRuntime(cli)
    result: AppResult = await runtime.execute(manifest, config={}, kwargs=namespace, stdin=stdin())
    assert isinstance(result, Success)
    assert result.output == [["foo"]]


@pytest.mark.asyncio
async def test_search(cli: CLI) -> None:
    source = """
    {% for resource in search('is(foo)') %}
    {{ resource.id }}
    {% endfor %}
    """

    manifest = AppManifest(
        name=InfraAppName("test-app"),
        description="test app description",
        version="0.0.0",
        readme="",
        language="jinja2",
        url="",
        icon="",
        categories=[],
        default_config=None,
        config_schema=None,
        args_schema=[],
        source=source,
    )

    runtime = LocalResotocoreAppRuntime(cli)

    lines = [line async for line in runtime._generate_template(manifest, {}, stdin(), namespace)]

    assert lines == ["sub_root", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]


async def stdin() -> AsyncGenerator[Optional[str], None]:
    yield None


namespace = Namespace()
