from types import SimpleNamespace
from typing import Any, cast
from resoto_plugin_aws.aws_client import AwsClient
from test.resources import round_trip_for
from resoto_plugin_aws.resource.apigateway import AwsApiGatewayRestApi


def test_data_catalogs() -> None:
    api, builder = round_trip_for(AwsApiGatewayRestApi)
    assert len(builder.resources_of(AwsApiGatewayRestApi)) == 1
    assert len(api.tags) == 1
    assert api.arn == "arn:aws:apigateway:eu-central-1::/restapis/2lsd9i45ub"


def test_api_tagging() -> None:
    api, builder = round_trip_for(AwsApiGatewayRestApi)

    def validate_update_args(**kwargs: Any) -> None:
        assert kwargs["action"] == "tag-resource"
        assert kwargs["resourceArn"] == api.arn
        assert kwargs["tags"] == {"foo": "bar"}

    def validate_delete_args(**kwargs: Any) -> None:
        assert kwargs["action"] == "untag-resource"
        assert kwargs["resourceArn"] == api.arn
        assert kwargs["tagKeys"] == ["foo"]

    client = cast(AwsClient, SimpleNamespace(call=validate_update_args))
    api.update_resource_tag(client, "foo", "bar")

    client = cast(AwsClient, SimpleNamespace(call=validate_delete_args))
    api.delete_resource_tag(client, "foo")


def test_delete_api() -> None:
    api, _ = round_trip_for(AwsApiGatewayRestApi)

    def validate_delete_args(**kwargs: Any) -> Any:
        assert kwargs["action"] == "delete-rest-api"
        assert kwargs["restApiId"] == api.id

    client = cast(AwsClient, SimpleNamespace(call=validate_delete_args))
    api.delete_resource(client)
