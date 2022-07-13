from resoto_plugin_aws.resource.base import GraphBuilder, AwsRegion
from resoto_plugin_aws.resource.ec2 import AwsEc2InstanceType

from test import builder, aws_client  # noqa: F401


def test_price_region(builder: GraphBuilder) -> None:  # noqa: F811
    assert builder.price_region == "US East (N. Virginia)"


def test_instance_type(builder: GraphBuilder) -> None:  # noqa: F811
    builder.global_instance_types["m4.large"] = AwsEc2InstanceType(id="m4.large")
    m4l: AwsEc2InstanceType = builder.instance_type("m4.large")  # type: ignore
    assert m4l == builder.instance_type("m4.large")
    assert m4l.ondemand_cost == 0.051
    eu_builder = builder.for_region(AwsRegion(id="eu-central-1"))
    m4l_eu: AwsEc2InstanceType = eu_builder.instance_type("m4.large")  # type: ignore
    assert m4l != m4l_eu
    assert m4l_eu == eu_builder.instance_type("m4.large")
    assert m4l_eu.ondemand_cost == 0.12
