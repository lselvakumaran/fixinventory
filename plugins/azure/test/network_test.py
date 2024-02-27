from conftest import roundtrip_check, connect_resources
from fix_plugin_azure.resource.base import GraphBuilder, AzureResource
from fix_plugin_azure.resource.containerservice import AzureManagedCluster
from fix_plugin_azure.resource.network import *

from typing import List, Type


def test_application_gateway_available_waf_rule_set(builder: GraphBuilder) -> None:
    collected = roundtrip_check(AzureApplicationGatewayFirewallRuleSet, builder)
    assert len(collected) == 1


def test_application_gateway(builder: GraphBuilder) -> None:
    collected = roundtrip_check(AzureApplicationGateway, builder)
    assert len(collected) == 1

    resource_types: List[Type[AzureResource]] = [AzureWebApplicationFirewallPolicy]
    connect_resources(builder, resource_types)

    assert len(builder.edges_of(AzureApplicationGateway, AzureWebApplicationFirewallPolicy)) == 1


def test_application_gateway_web_application_firewall_policy(builder: GraphBuilder) -> None:
    collected = roundtrip_check(AzureWebApplicationFirewallPolicy, builder)
    assert len(collected) == 1


def test_available_service_alias(builder: GraphBuilder) -> None:
    collected = roundtrip_check(AzureAvailableServiceAlias, builder)
    assert len(collected) == 2


def test_azure_firewall_fqdn_tag(builder: GraphBuilder) -> None:
    collected = roundtrip_check(AzureFirewallFqdnTag, builder)
    assert len(collected) == 1


def test_azure_firewall(builder: GraphBuilder) -> None:
    collected = roundtrip_check(AzureFirewall, builder)
    assert len(collected) == 1

    resource_types: List[Type[AzureResource]] = [AzureFirewallPolicy, AzureFirewallFqdnTag, AzureVirtualHub]
    connect_resources(builder, resource_types)

    assert len(builder.edges_of(AzureFirewall, AzureFirewallPolicy)) == 1
    assert len(builder.edges_of(AzureFirewall, AzureVirtualHub)) == 1


def test_azure_web_category(builder: GraphBuilder) -> None:
    collected = roundtrip_check(AzureWebCategory, builder)
    assert len(collected) == 1


def test_bastion_host(builder: GraphBuilder) -> None:
    collected = roundtrip_check(AzureBastionHost, builder)
    assert len(collected) == 2

    resource_types: List[Type[AzureResource]] = [AzureVirtualNetwork, AzurePublicIPAddress]
    connect_resources(builder, resource_types)

    assert len(builder.edges_of(AzureVirtualNetwork, AzureBastionHost)) == 1
    assert len(builder.edges_of(AzureBastionHost, AzurePublicIPAddress)) == 1


def test_custom_ip_prefix(builder: GraphBuilder) -> None:
    collected = roundtrip_check(AzureCustomIpPrefix, builder)
    assert len(collected) == 12


def test_ddos_protection_plan(builder: GraphBuilder) -> None:
    collected = roundtrip_check(AzureDdosProtectionPlan, builder)
    assert len(collected) == 2

    resource_types: List[Type[AzureResource]] = [AzureVirtualNetwork, AzurePublicIPAddress]
    connect_resources(builder, resource_types)

    assert len(builder.edges_of(AzureDdosProtectionPlan, AzureVirtualNetwork)) == 1
    assert len(builder.edges_of(AzureDdosProtectionPlan, AzurePublicIPAddress)) == 1


def test_dscp_configuration(builder: GraphBuilder) -> None:
    collected = roundtrip_check(AzureDscpConfiguration, builder)
    assert len(collected) == 2


def test_express_route_circuit(builder: GraphBuilder) -> None:
    collected = roundtrip_check(AzureExpressRouteCircuit, builder)
    assert len(collected) == 2

    resource_types: List[Type[AzureResource]] = [AzureExpressRoutePort, AzureExpressRoutePortsLocation]
    roundtrip_check(AzureExpressRoutePortsLocation, builder)
    connect_resources(builder, resource_types)

    assert len(builder.edges_of(AzureExpressRouteCircuit, AzureExpressRoutePort)) == 1
    assert len(builder.edges_of(AzureExpressRouteCircuit, AzureExpressRoutePortsLocation)) == 1


def test_express_route_gateway(builder: GraphBuilder) -> None:
    collected = roundtrip_check(AzureExpressRouteGateway, builder)
    assert len(collected) == 1


def test_express_route_port(builder: GraphBuilder) -> None:
    collected = roundtrip_check(AzureExpressRoutePort, builder)
    assert len(collected) == 1


def test_express_route_port_location(builder: GraphBuilder) -> None:
    collected = roundtrip_check(AzureExpressRoutePortsLocation, builder)
    assert len(collected) == 1


def test_firewall_policy(builder: GraphBuilder) -> None:
    collected = roundtrip_check(AzureFirewallPolicy, builder)
    assert len(collected) == 1


def test_ip_allocation(builder: GraphBuilder) -> None:
    collected = roundtrip_check(AzureIpAllocation, builder)
    assert len(collected) == 2

    resource_types: List[Type[AzureResource]] = [AzureVirtualNetwork]
    connect_resources(builder, resource_types)

    assert len(builder.edges_of(AzureVirtualNetwork, AzureIpAllocation)) == 1


def test_ip_group(builder: GraphBuilder) -> None:
    collected = roundtrip_check(AzureIpGroup, builder)
    assert len(collected) == 2

    resource_types: List[Type[AzureResource]] = [AzureVirtualNetwork]
    roundtrip_check(AzureVirtualNetwork, builder)
    connect_resources(builder, resource_types)

    assert len(builder.edges_of(AzureVirtualNetwork, AzureIpGroup)) == 1


def test_load_balancer(builder: GraphBuilder) -> None:
    collected = roundtrip_check(AzureLoadBalancer, builder)
    assert collected[0].lb_type == "Microsoft.Network/loadBalancers"
    assert collected[0].backends == [
        "/subscriptions/subid/resourceGroups/rg1/providers/Microsoft.Network/virtualNetworks/vnet1",
        "/subscriptions/subid/resourceGroups/rg1/providers/Microsoft.Network/virtualNetworks/vnet2",
    ]
    assert len(collected) == 2

    resource_types: List[Type[AzureResource]] = [AzureVirtualNetwork, AzureManagedCluster]
    roundtrip_check(AzurePublicIPAddress, builder)
    connect_resources(builder, resource_types)

    assert collected[0].aks_public_ip_address == "41.85.154.247"
    assert len(builder.edges_of(AzureVirtualNetwork, AzureLoadBalancer)) == 1
    assert len(builder.edges_of(AzureManagedCluster, AzureLoadBalancer)) == 1


def test_network_profile(builder: GraphBuilder) -> None:
    from fix_plugin_azure.resource.compute import AzureVirtualMachine  # pylint: disable=import-outside-toplevel

    collected = roundtrip_check(AzureNetworkProfile, builder)

    assert len(collected) == 2

    resource_types: List[Type[AzureResource]] = [AzureVirtualMachine]
    roundtrip_check(AzureNetworkInterface, builder)
    connect_resources(builder, resource_types)

    assert len(builder.edges_of(AzureNetworkProfile, AzureVirtualMachine)) == 1


def test_network_virtual_appliance(builder: GraphBuilder) -> None:
    collected = roundtrip_check(AzureNetworkVirtualAppliance, builder)
    assert len(collected) == 1

    resource_types: List[Type[AzureResource]] = [AzureNetworkVirtualApplianceSku]
    roundtrip_check(AzureNetworkVirtualApplianceSku, builder)
    connect_resources(builder, resource_types)

    assert len(builder.edges_of(AzureNetworkVirtualAppliance, AzureNetworkVirtualApplianceSku)) == 1


def test_network_virtual_appliance_sku(builder: GraphBuilder) -> None:
    collected = roundtrip_check(AzureNetworkVirtualApplianceSku, builder)
    assert len(collected) == 1


def test_network_watcher(builder: GraphBuilder) -> None:
    collected = roundtrip_check(AzureNetworkWatcher, builder)
    assert len(collected) == 2

    resource_types: List[Type[AzureResource]] = [AzureVirtualNetwork]
    roundtrip_check(AzureVirtualNetwork, builder)
    connect_resources(builder, resource_types)

    assert len(builder.edges_of(AzureVirtualNetwork, AzureNetworkWatcher)) == 2


def test_p2s_vpn_gateway(builder: GraphBuilder) -> None:
    collected = roundtrip_check(AzureP2SVpnGateway, builder)
    assert len(collected) == 2

    resource_types: List[Type[AzureResource]] = [AzureVirtualHub]
    connect_resources(builder, resource_types)

    assert len(builder.edges_of(AzureP2SVpnGateway, AzureVirtualHub)) == 2


def test_public_ip_prefix(builder: GraphBuilder) -> None:
    collected = roundtrip_check(AzurePublicIPPrefix, builder)
    assert len(collected) == 3


def test_route_filter(builder: GraphBuilder) -> None:
    collected = roundtrip_check(AzureRouteFilter, builder)
    assert len(collected) == 1


def test_security_partner_provider(builder: GraphBuilder) -> None:
    collected = roundtrip_check(AzureSecurityPartnerProvider, builder)
    assert len(collected) == 1


def test_usage(builder: GraphBuilder) -> None:
    collected = roundtrip_check(AzureUsage, builder)
    assert len(collected) == 25


def test_virtual_hub(builder: GraphBuilder) -> None:
    collected = roundtrip_check(AzureVirtualHub, builder)
    assert len(collected) == 2

    resource_types: List[Type[AzureResource]] = [
        AzureExpressRouteGateway,
        AzureVpnGateway,
        AzureVirtualWAN,
        AzurePublicIPAddress,
    ]
    roundtrip_check(AzureNetworkInterface, builder)
    connect_resources(builder, resource_types)

    assert len(builder.edges_of(AzureExpressRouteGateway, AzureVirtualHub)) == 1
    assert len(builder.edges_of(AzureVpnGateway, AzureVirtualHub)) == 1
    assert len(builder.edges_of(AzureVirtualWAN, AzureVirtualHub)) == 1
    assert len(builder.edges_of(AzureVirtualHub, AzurePublicIPAddress)) == 1


def test_virtual_network(builder: GraphBuilder) -> None:
    collected = roundtrip_check(AzureVirtualNetwork, builder)
    assert len(collected) == 2


def test_virtual_router(builder: GraphBuilder) -> None:
    collected = roundtrip_check(AzureVirtualRouter, builder)
    assert len(collected) == 1


def test_virtual_wan(builder: GraphBuilder) -> None:
    collected = roundtrip_check(AzureVirtualWAN, builder)
    assert len(collected) == 2


def test_vpn_gateway(builder: GraphBuilder) -> None:
    collected = roundtrip_check(AzureVpnGateway, builder)
    assert len(collected) == 2


def test_vpn_server_configuration(builder: GraphBuilder) -> None:
    collected = roundtrip_check(AzureVpnServerConfiguration, builder)
    assert len(collected) == 2


def test_vpn_site(builder: GraphBuilder) -> None:
    collected = roundtrip_check(AzureVpnSite, builder)
    assert len(collected) == 2

    resource_types: List[Type[AzureResource]] = [AzureVirtualWAN]
    connect_resources(builder, resource_types)

    assert len(builder.edges_of(AzureVirtualWAN, AzureVpnSite)) == 1


def test_nat_gateway(builder: GraphBuilder) -> None:
    collected = roundtrip_check(AzureNatGateway, builder)
    assert len(collected) == 2


def test_network_interface(builder: GraphBuilder) -> None:
    collected = roundtrip_check(AzureNetworkInterface, builder)
    assert len(collected) == 2

    resource_types: List[Type[AzureResource]] = [
        AzureVirtualNetworkTap,
        AzureDscpConfiguration,
        AzureNetworkSecurityGroup,
        AzurePrivateLinkService,
    ]
    connect_resources(builder, resource_types)

    assert len(builder.edges_of(AzureVirtualNetworkTap, AzureNetworkInterface)) == 1
    assert len(builder.edges_of(AzurePrivateLinkService, AzureNetworkInterface)) == 1
    assert len(builder.edges_of(AzureNetworkSecurityGroup, AzureNetworkInterface)) == 1
    assert len(builder.edges_of(AzureNetworkInterface, AzureDscpConfiguration)) == 1


def test_network_security_group(builder: GraphBuilder) -> None:
    collected = roundtrip_check(AzureNetworkSecurityGroup, builder)
    assert len(collected) == 2


def test_private_link_service(builder: GraphBuilder) -> None:
    collected = roundtrip_check(AzurePrivateLinkService, builder)
    assert len(collected) == 2


def test_public_ip_address(builder: GraphBuilder) -> None:
    collected = roundtrip_check(AzurePublicIPAddress, builder)
    assert len(collected) == 3

    resource_types: List[Type[AzureResource]] = [AzureNatGateway, AzurePublicIPPrefix]
    connect_resources(builder, resource_types)

    assert len(builder.edges_of(AzureNatGateway, AzurePublicIPAddress)) == 1
    assert len(builder.edges_of(AzurePublicIPPrefix, AzurePublicIPAddress)) == 1


def test_virtual_network_tap(builder: GraphBuilder) -> None:
    collected = roundtrip_check(AzureVirtualNetworkTap, builder)
    assert len(collected) == 2
