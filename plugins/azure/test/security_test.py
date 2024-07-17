from conftest import roundtrip_check
from fix_plugin_azure.resource.base import GraphBuilder
from fix_plugin_azure.resource.security import (
    AzureSecurityAssessment,
    AzureSecurityPricing,
    AzureSecurityServerVulnerabilityAssessmentsSetting,
    AzureSecuritySetting,
)


def test_security_assessment(builder: GraphBuilder) -> None:
    collected = roundtrip_check(AzureSecurityAssessment, builder)
    assert len(collected) == 2


def test_security_pricing(builder: GraphBuilder) -> None:
    collected = roundtrip_check(AzureSecurityPricing, builder)
    assert len(collected) == 13


def test_security_server_vulnerability_assessments_setting(builder: GraphBuilder) -> None:
    collected = roundtrip_check(AzureSecurityServerVulnerabilityAssessmentsSetting, builder)
    assert len(collected) == 1


def test_security_setting(builder: GraphBuilder) -> None:
    collected = roundtrip_check(AzureSecuritySetting, builder)
    assert len(collected) == 4
