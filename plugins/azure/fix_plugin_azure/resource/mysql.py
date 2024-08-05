from datetime import datetime
import logging
from typing import ClassVar, Dict, Optional, List, Any, Type

from attr import define, evolve, field

from fix_plugin_azure.azure_client import AzureResourceSpec
from fix_plugin_azure.resource.base import (
    AzurePrivateLinkServiceConnectionState,
    AzureSku,
    GraphBuilder,
    MicrosoftResource,
    AzureSystemData,
)
from fix_plugin_azure.resource.microsoft_graph import MicrosoftGraphServicePrincipal, MicrosoftGraphUser
from fix_plugin_azure.utils import from_str_to_typed
from fixlib.baseresources import (
    BaseDatabase,
    BaseDatabaseInstanceType,
    DatabaseInstanceStatus,
    EdgeType,
    ModelReference,
)
from fixlib.graph import BySearchCriteria
from fixlib.json_bender import K, Bender, S, ForallBend, Bend, MapEnum, MapValue
from fixlib.types import Json

service_name = "azure_mysql"
log = logging.getLogger("fix.plugins.azure")


@define(eq=False, slots=False)
class AzureServerDataEncryption:
    kind: ClassVar[str] = "azure_server_data_encryption"
    mapping: ClassVar[Dict[str, Bender]] = {
        "geo_backup_key_uri": S("geoBackupKeyURI"),
        "geo_backup_user_assigned_identity_id": S("geoBackupUserAssignedIdentityId"),
        "primary_key_uri": S("primaryKeyURI"),
        "primary_user_assigned_identity_id": S("primaryUserAssignedIdentityId"),
        "type": S("type"),
    }
    geo_backup_key_uri: Optional[str] = field(default=None, metadata={'description': 'Geo backup key uri as key vault can t cross region, need cmk in same region as geo backup'})  # fmt: skip
    geo_backup_user_assigned_identity_id: Optional[str] = field(default=None, metadata={'description': 'Geo backup user identity resource id as identity can t cross region, need identity in same region as geo backup'})  # fmt: skip
    primary_key_uri: Optional[str] = field(default=None, metadata={"description": "Primary key uri"})
    primary_user_assigned_identity_id: Optional[str] = field(default=None, metadata={'description': 'Primary user identity resource id'})  # fmt: skip
    type: Optional[str] = field(default=None, metadata={'description': 'The key type, AzureKeyVault for enable cmk, SystemManaged for disable cmk.'})  # fmt: skip


@define(eq=False, slots=False)
class AzureServerBackup:
    kind: ClassVar[str] = "azure_server_backup"
    mapping: ClassVar[Dict[str, Bender]] = {
        "backup_interval_hours": S("backupIntervalHours"),
        "backup_retention_days": S("backupRetentionDays"),
        "earliest_restore_date": S("earliestRestoreDate"),
        "geo_redundant_backup": S("geoRedundantBackup"),
    }
    backup_interval_hours: Optional[int] = field(default=None, metadata={'description': 'Backup interval hours for the server.'})  # fmt: skip
    backup_retention_days: Optional[int] = field(default=None, metadata={'description': 'Backup retention days for the server.'})  # fmt: skip
    earliest_restore_date: Optional[datetime] = field(default=None, metadata={'description': 'Earliest restore point creation time (ISO8601 format)'})  # fmt: skip
    geo_redundant_backup: Optional[str] = field(default=None, metadata={'description': 'Enum to indicate whether value is Enabled or Disabled '})  # fmt: skip


@define(eq=False, slots=False)
class AzureServerNetwork:
    kind: ClassVar[str] = "azure_server_network"
    mapping: ClassVar[Dict[str, Bender]] = {
        "delegated_subnet_resource_id": S("delegatedSubnetResourceId"),
        "private_dns_zone_resource_id": S("privateDnsZoneResourceId"),
        "public_network_access": S("publicNetworkAccess"),
    }
    delegated_subnet_resource_id: Optional[str] = field(default=None, metadata={'description': 'Delegated subnet resource id used to setup vnet for a server.'})  # fmt: skip
    private_dns_zone_resource_id: Optional[str] = field(default=None, metadata={'description': 'Private DNS zone resource id.'})  # fmt: skip
    public_network_access: Optional[str] = field(default=None, metadata={'description': 'Enum to indicate whether value is Enabled or Disabled '})  # fmt: skip


@define(eq=False, slots=False)
class AzureServerHighAvailability:
    kind: ClassVar[str] = "azure_server_high_availability"
    mapping: ClassVar[Dict[str, Bender]] = {
        "mode": S("mode"),
        "standby_availability_zone": S("standbyAvailabilityZone"),
        "state": S("state"),
    }
    mode: Optional[str] = field(default=None, metadata={"description": "High availability mode for a server."})
    standby_availability_zone: Optional[str] = field(default=None, metadata={'description': 'Availability zone of the standby server.'})  # fmt: skip
    state: Optional[str] = field(default=None, metadata={"description": "The state of server high availability."})


@define(eq=False, slots=False)
class AzureServerMaintenanceWindow:
    kind: ClassVar[str] = "azure_server_maintenance_window"
    mapping: ClassVar[Dict[str, Bender]] = {
        "custom_window": S("customWindow"),
        "day_of_week": S("dayOfWeek"),
        "start_hour": S("startHour"),
        "start_minute": S("startMinute"),
    }
    custom_window: Optional[str] = field(default=None, metadata={'description': 'indicates whether custom window is enabled or disabled'})  # fmt: skip
    day_of_week: Optional[int] = field(default=None, metadata={"description": "day of week for maintenance window"})
    start_hour: Optional[int] = field(default=None, metadata={"description": "start hour for maintenance window"})
    start_minute: Optional[int] = field(default=None, metadata={"description": "start minute for maintenance window"})


@define(eq=False, slots=False)
class AzureMysqlServerADAdministrator(MicrosoftResource):
    kind: ClassVar[str] = "azure_mysql_server_ad_administrator"
    # Collect via AzureMysqlServer()
    mapping: ClassVar[Dict[str, Bender]] = {
        "id": S("id"),
        "tags": S("tags", default={}),
        "name": S("name"),
        "system_data": S("systemData") >> Bend(AzureSystemData.mapping),
        "ctime": S("systemData", "createdAt"),
        "mtime": S("systemData", "lastModifiedAt"),
        "type": S("type"),
        "administrator_type": S("properties", "administratorType"),
        "identity_resource_id": S("properties", "identityResourceId"),
        "login": S("properties", "login"),
        "sid": S("properties", "sid"),
        "tenant_id": S("properties", "tenantId"),
    }
    administrator_type: Optional[str] = field(default=None, metadata={'description': 'Type of the sever administrator.'})  # fmt: skip
    identity_resource_id: Optional[str] = field(default=None, metadata={'description': 'The resource id of the identity used for AAD Authentication.'})  # fmt: skip
    login: Optional[str] = field(default=None, metadata={"description": "Login name of the server administrator."})
    sid: Optional[str] = field(default=None, metadata={"description": "SID (object ID) of the server administrator."})
    tenant_id: Optional[str] = field(default=None, metadata={"description": "Tenant ID of the administrator."})
    system_data: Optional[AzureSystemData] = field(default=None, metadata={'description': 'Metadata pertaining to creation and last modification of the resource.'})  # fmt: skip
    type: Optional[str] = field(default=None, metadata={'description': 'The type of the resource. E.g. Microsoft.Compute/virtualMachines or Microsoft.Storage/storageAccounts '})  # fmt: skip

    def connect_in_graph(self, builder: GraphBuilder, source: Json) -> None:
        # principal: collected via ms graph -> create a deferred edge
        if user_id := self.sid:
            builder.add_deferred_edge(
                from_node=self,
                to_node=BySearchCriteria(f'is({MicrosoftGraphUser.kind}) and reported.id=="{user_id}"'),
            )


@define(eq=False, slots=False)
class AzureStorageEditionCapability:
    kind: ClassVar[str] = "azure_storage_edition_capability"
    mapping: ClassVar[Dict[str, Bender]] = {
        "max_backup_interval_hours": S("maxBackupIntervalHours"),
        "max_backup_retention_days": S("maxBackupRetentionDays"),
        "max_storage_size": S("maxStorageSize"),
        "min_backup_interval_hours": S("minBackupIntervalHours"),
        "min_backup_retention_days": S("minBackupRetentionDays"),
        "min_storage_size": S("minStorageSize"),
        "name": S("name"),
    }
    max_backup_interval_hours: Optional[int] = field(default=None, metadata={'description': 'Maximum backup interval hours'})  # fmt: skip
    max_backup_retention_days: Optional[int] = field(default=None, metadata={'description': 'Maximum backup retention days'})  # fmt: skip
    max_storage_size: Optional[int] = field(default=None, metadata={'description': 'The maximum supported storage size.'})  # fmt: skip
    min_backup_interval_hours: Optional[int] = field(default=None, metadata={'description': 'Minimal backup interval hours'})  # fmt: skip
    min_backup_retention_days: Optional[int] = field(default=None, metadata={'description': 'Minimal backup retention days'})  # fmt: skip
    min_storage_size: Optional[int] = field(default=None, metadata={'description': 'The minimal supported storage size.'})  # fmt: skip
    name: Optional[str] = field(default=None, metadata={"description": "storage edition name"})


@define(eq=False, slots=False)
class AzureSkuCapability:
    kind: ClassVar[str] = "azure_sku_capability"
    mapping: ClassVar[Dict[str, Bender]] = {
        "name": S("name"),
        "supported_ha_mode": S("supportedHAMode"),
        "supported_zones": S("supportedZones"),
        "supported_iops": S("supportedIops"),
        "supported_memory_per_v_core_mb": S("supportedMemoryPerVCoreMB"),
        "v_cores": S("vCores"),
    }
    name: Optional[str] = field(default=None, metadata={"description": "vCore name"})
    supported_iops: Optional[int] = field(default=None, metadata={"description": "supported IOPS"})
    supported_memory_per_v_core_mb: Optional[int] = field(default=None, metadata={'description': 'supported memory per vCore in MB'})  # fmt: skip
    v_cores: Optional[int] = field(default=None, metadata={"description": "supported vCores"})
    supported_ha_mode: Optional[List[str]] = field(default=None, metadata={'description': 'Supported high availability mode'})  # fmt: skip
    supported_zones: Optional[List[str]] = field(default=None, metadata={"description": "Supported zones"})


@define(eq=False, slots=False)
class AzureServerVersionCapability:
    kind: ClassVar[str] = "azure_server_version_capability"
    mapping: ClassVar[Dict[str, Bender]] = {
        "name": S("name"),
        "supported_skus": S("supportedSkus") >> ForallBend(AzureSkuCapability.mapping),
    }
    name: Optional[str] = field(default=None, metadata={"description": "server version"})
    supported_skus: Optional[List[AzureSkuCapability]] = field(default=None, metadata={'description': 'A list of supported Skus'})  # fmt: skip


@define(eq=False, slots=False)
class AzureServerEditionCapability:
    kind: ClassVar[str] = "azure_server_edition_capability"
    mapping: ClassVar[Dict[str, Bender]] = {
        "default_sku": S("defaultSku"),
        "default_storage_size": S("defaultStorageSize"),
        "name": S("name"),
        "supported_server_versions": S("supportedServerVersions") >> ForallBend(AzureServerVersionCapability.mapping),
        "supported_storage_editions": S("supportedStorageEditions")
        >> ForallBend(AzureStorageEditionCapability.mapping),
        "supported_skus": S("supportedSkus") >> ForallBend(AzureSkuCapability.mapping),
    }
    default_sku: Optional[str] = field(default=None, metadata={"description": "Default Sku name"})
    default_storage_size: Optional[int] = field(default=None, metadata={"description": "Default storage size"})
    name: Optional[str] = field(default=None, metadata={"description": "Server edition name"})
    supported_server_versions: Optional[List[AzureServerVersionCapability]] = field(default=None, metadata={'description': 'A list of supported server versions.'})  # fmt: skip
    supported_storage_editions: Optional[List[AzureStorageEditionCapability]] = field(default=None, metadata={'description': 'A list of supported storage editions'})  # fmt: skip
    supported_skus: Optional[List[AzureSkuCapability]] = field(default=None, metadata={'description': 'A list of supported Skus'})  # fmt: skip


@define(eq=False, slots=False)
class AzureMysqlServerType(MicrosoftResource, BaseDatabaseInstanceType):
    kind: ClassVar[str] = "azure_mysql_server_type"
    # Collect via AzureMysqlServer()
    mapping: ClassVar[Dict[str, Bender]] = {
        "id": S("id"),
        "name": S("name"),
        "tags": S("tags", default={}),
        "supported_geo_backup_regions": S("supportedGeoBackupRegions"),
        "supported_ha_mode": S("supportedHAMode"),
        "capability_zone": S("zone"),
        "server_edition_name": S("server_edition_name"),
        "storage_edition": S("storage_edition") >> Bend(AzureStorageEditionCapability.mapping),
        "server_version": S("server_version"),
        "capability_sku": S("sku") >> Bend(AzureSkuCapability.mapping),
        "location": S("location"),
        # NOTE: Azure defines location-aware capabilities for several editions.
        # Separate server types are created for all used editions.
        "_supported_flexible_server_editions": S("supportedFlexibleServerEditions")
        >> ForallBend(AzureServerEditionCapability.mapping),
    }
    _is_provider_link: ClassVar[bool] = False
    supported_geo_backup_regions: Optional[List[str]] = field(default=None, metadata={'description': 'supported geo backup regions'})  # fmt: skip
    supported_ha_mode: Optional[List[str]] = field(default=None, metadata={'description': 'Supported high availability mode'})  # fmt: skip
    capability_zone: Optional[str] = field(default=None, metadata={"description": "zone name"})
    location: Optional[str] = field(default=None, metadata={"description": "Resource location."})
    # See mapping note: The following properties are not coming from the API directly.
    server_edition_name: Optional[str] = field(default=None)
    storage_edition: Optional[AzureStorageEditionCapability] = field(default=None)
    server_version: Optional[str] = field(default=None)
    capability_sku: Optional[AzureSkuCapability] = field(default=None)
    # See mapping note: only here to map to separate resources for all used editions
    _supported_flexible_server_editions: Optional[List[AzureServerEditionCapability]] = field(default=None, metadata={'description': 'A list of supported flexible server editions.'})  # fmt: skip

    @classmethod
    def collect(
        cls,
        raw: List[Json],
        builder: GraphBuilder,
    ) -> List["AzureMysqlServerType"]:
        result = []

        for js in raw:
            instance = cls.from_api(js)
            if isinstance(instance, AzureMysqlServerType) and instance._supported_flexible_server_editions:
                location = instance.location
                expected_sku_name = js.get("expected_sku_name")
                expected_sku_tier = js.get("expected_sku_tier")
                expected_version = js.get("expected_version")
                for edition in instance._supported_flexible_server_editions:
                    edition_name = edition.name
                    if edition_name != expected_sku_tier:
                        continue
                    storage_editions = edition.supported_storage_editions or []
                    server_versions = edition.supported_server_versions or []
                    for storage_edition in storage_editions:
                        storage_edition_dict: Json = {
                            "max_backup_interval_hours": storage_edition.max_backup_interval_hours,
                            "max_backup_retention_days": storage_edition.max_backup_retention_days,
                            "max_storage_size": storage_edition.max_storage_size,
                            "min_backup_interval_hours": storage_edition.min_backup_interval_hours,
                            "min_backup_retention_days": storage_edition.min_backup_retention_days,
                            "min_storage_size": storage_edition.min_storage_size,
                            "name": storage_edition.name,
                        }
                        for version in server_versions:
                            version_name = version.name
                            if version_name != expected_version:
                                continue
                            skus = version.supported_skus or []

                            for sku in skus:
                                if sku.name != expected_sku_name:
                                    continue
                                sku_dict: Json = {
                                    "name": sku.name,
                                    "v_cores": sku.v_cores,
                                    "supported_iops": sku.supported_iops,
                                    "supported_memory_per_v_core_mb": sku.supported_memory_per_v_core_mb,
                                }
                                instance_cores = sku_dict.get("v_cores") or 0
                                supported_memory_per_v_core_mb = sku_dict.get("supported_memory_per_v_core_mb")
                                if supported_memory_per_v_core_mb is not None:
                                    instance_memory = supported_memory_per_v_core_mb // 1024
                                else:
                                    instance_memory = 0
                                server_type = evolve(
                                    instance,
                                    id=f"{sku.name}",
                                    name=f"{edition_name}_{sku.name}",
                                    server_edition_name=edition_name,
                                    storage_edition=AzureStorageEditionCapability(**storage_edition_dict),
                                    server_version=version_name,
                                    capability_sku=AzureSkuCapability(**sku_dict),
                                    location=location,
                                    instance_cores=instance_cores,
                                    instance_memory=instance_memory,
                                    instance_type=sku.name,
                                    capability_zone=instance.capability_zone,
                                    supported_ha_mode=instance.supported_ha_mode,
                                    supported_geo_backup_regions=instance.supported_geo_backup_regions,
                                )
                                if graph_node := builder.add_node(server_type, js):
                                    result.append(graph_node)
        return result


@define(eq=False, slots=False)
class AzureMysqlServerConfiguration(MicrosoftResource):
    kind: ClassVar[str] = "azure_mysql_server_configuration"
    # Collect via AzureMysqlServer()
    config: Json = field(factory=dict)

    @classmethod
    def collect_configs(
        cls,
        server_id: str,
        raw: List[Json],
        builder: GraphBuilder,
    ) -> List["AzureMysqlServerConfiguration"]:
        if not raw:
            return []
        configuration_instance = AzureMysqlServerConfiguration(id=server_id)
        for js in raw:
            properties = js.get("properties")
            if not properties:
                continue
            if (
                (data_type := properties.get("dataType"))
                and (val := properties.get("currentValue") or properties.get("value"))
                and (config_name := js.get("name"))
            ):
                value = from_str_to_typed(data_type, val)
                if not value:
                    continue
                configuration_instance.config[config_name] = value
        if (added := builder.add_node(configuration_instance, configuration_instance.config)) is not None:
            return [added]
        return []


@define(eq=False, slots=False)
class AzureMysqlServerDatabase(MicrosoftResource):
    kind: ClassVar[str] = "azure_mysql_server_database"
    # Collect via AzureMysqlServer()
    mapping: ClassVar[Dict[str, Bender]] = {
        "id": S("id"),
        "tags": S("tags", default={}),
        "name": S("name"),
        "type": S("type"),
        "ctime": S("systemData", "createdAt"),
        "mtime": S("systemData", "lastModifiedAt"),
        "charset": S("properties", "charset"),
        "collation": S("properties", "collation"),
        "system_data": S("systemData") >> Bend(AzureSystemData.mapping),
    }
    charset: Optional[str] = field(default=None, metadata={"description": "The charset of the database."})
    collation: Optional[str] = field(default=None, metadata={"description": "The collation of the database."})
    system_data: Optional[AzureSystemData] = field(default=None, metadata={'description': 'Metadata pertaining to creation and last modification of the resource.'})  # fmt: skip
    type: Optional[str] = field(default=None, metadata={'description': 'The type of the resource. E.g. Microsoft.Compute/virtualMachines or Microsoft.Storage/storageAccounts '})  # fmt: skip


@define(eq=False, slots=False)
class AzureMysqlServerFirewallRule(MicrosoftResource):
    kind: ClassVar[str] = "azure_mysql_server_firewall_rule"
    # Collect via AzureMysqlServer()
    mapping: ClassVar[Dict[str, Bender]] = {
        "id": S("id"),
        "tags": S("tags", default={}),
        "name": S("name"),
        "type": S("type"),
        "ctime": S("systemData", "createdAt"),
        "mtime": S("systemData", "lastModifiedAt"),
        "end_ip_address": S("properties", "endIpAddress"),
        "start_ip_address": S("properties", "startIpAddress"),
        "system_data": S("systemData") >> Bend(AzureSystemData.mapping),
    }
    end_ip_address: Optional[str] = field(default=None, metadata={'description': 'The end IP address of the server firewall rule. Must be IPv4 format.'})  # fmt: skip
    start_ip_address: Optional[str] = field(default=None, metadata={'description': 'The start IP address of the server firewall rule. Must be IPv4 format.'})  # fmt: skip
    system_data: Optional[AzureSystemData] = field(default=None, metadata={'description': 'Metadata pertaining to creation and last modification of the resource.'})  # fmt: skip
    type: Optional[str] = field(default=None, metadata={'description': 'The type of the resource. E.g. Microsoft.Compute/virtualMachines or Microsoft.Storage/storageAccounts '})  # fmt: skip


@define(eq=False, slots=False)
class AzureMysqlServerLogFile(MicrosoftResource):
    kind: ClassVar[str] = "azure_mysql_server_log_file"
    # Collect via AzureMysqlServer()
    mapping: ClassVar[Dict[str, Bender]] = {
        "id": S("id"),
        "tags": S("tags", default={}),
        "name": S("name"),
        "system_data": S("systemData") >> Bend(AzureSystemData.mapping),
        "type": S("type"),
        "ctime": S("properties", "createdTime"),
        "mtime": S("properties", "lastModifiedTime"),
        "created_time": S("properties", "createdTime"),
        "last_modified_time": S("properties", "lastModifiedTime"),
        "size_in_kb": S("properties", "sizeInKB"),
        "url": S("properties", "url"),
    }
    created_time: Optional[datetime] = field(default=None, metadata={'description': 'Creation timestamp of the log file.'})  # fmt: skip
    last_modified_time: Optional[datetime] = field(default=None, metadata={'description': 'Last modified timestamp of the log file.'})  # fmt: skip
    size_in_kb: Optional[int] = field(default=None, metadata={"description": "The size in kb of the logFile."})
    url: Optional[str] = field(default=None, metadata={"description": "The url to download the log file from."})
    system_data: Optional[AzureSystemData] = field(default=None, metadata={'description': 'Metadata pertaining to creation and last modification of the resource.'})  # fmt: skip
    type: Optional[str] = field(default=None, metadata={'description': 'The type of the resource. E.g. Microsoft.Compute/virtualMachines or Microsoft.Storage/storageAccounts '})  # fmt: skip


@define(eq=False, slots=False)
class AzureMysqlServerMaintenance(MicrosoftResource):
    kind: ClassVar[str] = "azure_mysql_server_maintenance"
    # Collect via AzureMysqlServer()
    mapping: ClassVar[Dict[str, Bender]] = {
        "id": S("id"),
        "tags": S("tags", default={}),
        "name": S("name"),
        "system_data": S("systemData") >> Bend(AzureSystemData.mapping),
        "type": S("type"),
        "ctime": S("systemData", "createdAt"),
        "mtime": S("systemData", "lastModifiedAt"),
        "maintenance_available_schedule_max_time": S("properties", "maintenanceAvailableScheduleMaxTime"),
        "maintenance_available_schedule_min_time": S("properties", "maintenanceAvailableScheduleMinTime"),
        "maintenance_description": S("properties", "maintenanceDescription"),
        "maintenance_end_time": S("properties", "maintenanceEndTime"),
        "maintenance_execution_end_time": S("properties", "maintenanceExecutionEndTime"),
        "maintenance_execution_start_time": S("properties", "maintenanceExecutionStartTime"),
        "maintenance_start_time": S("properties", "maintenanceStartTime"),
        "maintenance_state": S("properties", "maintenanceState"),
        "maintenance_title": S("properties", "maintenanceTitle"),
        "maintenance_type": S("properties", "maintenanceType"),
        "provisioning_state": S("properties", "provisioningState"),
    }
    maintenance_available_schedule_max_time: Optional[datetime] = field(default=None, metadata={'description': 'The max time the maintenance can be rescheduled.'})  # fmt: skip
    maintenance_available_schedule_min_time: Optional[datetime] = field(default=None, metadata={'description': 'The min time the maintenance can be rescheduled.'})  # fmt: skip
    maintenance_description: Optional[str] = field(default=None, metadata={'description': 'The maintenance description.'})  # fmt: skip
    maintenance_end_time: Optional[datetime] = field(default=None, metadata={'description': 'The end time for a maintenance.'})  # fmt: skip
    maintenance_execution_end_time: Optional[datetime] = field(default=None, metadata={'description': 'The end time for a maintenance execution.'})  # fmt: skip
    maintenance_execution_start_time: Optional[datetime] = field(default=None, metadata={'description': 'The start time for a maintenance execution.'})  # fmt: skip
    maintenance_start_time: Optional[datetime] = field(default=None, metadata={'description': 'The start time for a maintenance.'})  # fmt: skip
    maintenance_state: Optional[str] = field(default=None, metadata={'description': 'The current status of this maintenance.'})  # fmt: skip
    maintenance_title: Optional[str] = field(default=None, metadata={"description": "The maintenance title."})
    maintenance_type: Optional[str] = field(default=None, metadata={"description": "The type of this maintenance."})
    provisioning_state: Optional[str] = field(default=None, metadata={'description': 'The current provisioning state.'})  # fmt: skip
    system_data: Optional[AzureSystemData] = field(default=None, metadata={'description': 'Metadata pertaining to creation and last modification of the resource.'})  # fmt: skip
    type: Optional[str] = field(default=None, metadata={'description': 'The type of the resource. E.g. Microsoft.Compute/virtualMachines or Microsoft.Storage/storageAccounts '})  # fmt: skip


@define(eq=False, slots=False)
class AzurePrivateEndpointConnection:
    kind: ClassVar[str] = "azure_private_endpoint_connection"
    mapping: ClassVar[Dict[str, Bender]] = {
        "group_ids": S("properties", "groupIds"),
        "id": S("id"),
        "name": S("name"),
        "private_endpoint": S("properties", "privateEndpoint", "id"),
        "private_link_service_connection_state": S("properties", "privateLinkServiceConnectionState")
        >> Bend(AzurePrivateLinkServiceConnectionState.mapping),
        "provisioning_state": S("properties", "provisioningState"),
        "system_data": S("systemData") >> Bend(AzureSystemData.mapping),
        "type": S("type"),
    }
    group_ids: Optional[List[str]] = field(default=None, metadata={'description': 'The group ids for the private endpoint resource.'})  # fmt: skip
    id: Optional[str] = field(default=None, metadata={'description': 'Fully qualified resource ID for the resource. E.g. /subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/{resourceProviderNamespace}/{resourceType}/{resourceName} '})  # fmt: skip
    name: Optional[str] = field(default=None, metadata={"description": "The name of the resource"})
    private_endpoint: Optional[str] = field(default=None, metadata={"description": "The private endpoint resource."})
    private_link_service_connection_state: Optional[AzurePrivateLinkServiceConnectionState] = field(default=None, metadata={'description': 'A collection of information about the state of the connection between service consumer and provider.'})  # fmt: skip
    provisioning_state: Optional[str] = field(default=None, metadata={'description': 'The current provisioning state.'})  # fmt: skip
    system_data: Optional[AzureSystemData] = field(default=None, metadata={'description': 'Metadata pertaining to creation and last modification of the resource.'})  # fmt: skip
    type: Optional[str] = field(default=None, metadata={'description': 'The type of the resource. E.g. Microsoft.Compute/virtualMachines or Microsoft.Storage/storageAccounts '})  # fmt: skip


@define(eq=False, slots=False)
class AzureMySQLServerIdentity:
    kind: ClassVar[str] = "azure_my_sql_server_identity"
    mapping: ClassVar[Dict[str, Bender]] = {
        "principal_id": S("principalId"),
        "tenant_id": S("tenantId"),
        "type": S("type"),
        "user_assigned_identities": S("userAssignedIdentities"),
    }
    principal_id: Optional[str] = field(default=None, metadata={"description": "ObjectId from the KeyVault"})
    tenant_id: Optional[str] = field(default=None, metadata={"description": "TenantId from the KeyVault"})
    type: Optional[str] = field(default=None, metadata={"description": "Type of managed service identity."})
    user_assigned_identities: Optional[Dict[str, Any]] = field(default=None, metadata={'description': 'Metadata of user assigned identity.'})  # fmt: skip


@define(eq=False, slots=False)
class AzureStorage:
    kind: ClassVar[str] = "azure_storage"
    mapping: ClassVar[Dict[str, Bender]] = {
        "auto_grow": S("autoGrow"),
        "auto_io_scaling": S("autoIoScaling"),
        "iops": S("iops"),
        "log_on_disk": S("logOnDisk"),
        "storage_size_gb": S("storageSizeGB"),
        "storage_sku": S("storageSku"),
    }
    auto_grow: Optional[str] = field(default=None, metadata={'description': 'Enum to indicate whether value is Enabled or Disabled '})  # fmt: skip
    auto_io_scaling: Optional[str] = field(default=None, metadata={'description': 'Enum to indicate whether value is Enabled or Disabled '})  # fmt: skip
    iops: Optional[int] = field(default=None, metadata={"description": "Storage IOPS for a server."})
    log_on_disk: Optional[str] = field(default=None, metadata={'description': 'Enum to indicate whether value is Enabled or Disabled '})  # fmt: skip
    storage_size_gb: Optional[int] = field(default=None, metadata={'description': 'Max storage size allowed for a server.'})  # fmt: skip
    storage_sku: Optional[str] = field(default=None, metadata={"description": "The sku name of the server storage."})


@define(eq=False, slots=False)
class AzureImportSourceProperties:
    kind: ClassVar[str] = "azure_import_source_properties"
    mapping: ClassVar[Dict[str, Bender]] = {
        "data_dir_path": S("dataDirPath"),
        "sas_token": S("sasToken"),
        "storage_type": S("storageType"),
        "storage_url": S("storageUrl"),
    }
    data_dir_path: Optional[str] = field(default=None, metadata={'description': 'Relative path of data directory in storage.'})  # fmt: skip
    sas_token: Optional[str] = field(default=None, metadata={'description': 'Sas token for accessing source storage. Read and list permissions are required for sas token.'})  # fmt: skip
    storage_type: Optional[str] = field(default=None, metadata={"description": "Storage type of import source."})
    storage_url: Optional[str] = field(default=None, metadata={"description": "Uri of the import source storage."})


@define(eq=False, slots=False)
class AzureMysqlServer(MicrosoftResource, BaseDatabase):
    kind: ClassVar[str] = "azure_mysql_server"
    api_spec: ClassVar[AzureResourceSpec] = AzureResourceSpec(
        service="mysql",
        version="2023-12-30",
        path="/subscriptions/{subscriptionId}/providers/Microsoft.DBforMySQL/flexibleServers",
        path_parameters=["subscriptionId"],
        query_parameters=["api-version"],
        access_path="value",
        expect_array=True,
    )
    reference_kinds: ClassVar[ModelReference] = {
        "successors": {
            "default": [
                "azure_mysql_server_backup",
                "azure_mysql_server_maintenance",
                "azure_mysql_server_log_file",
                "azure_mysql_server_firewall_rule",
                "azure_mysql_server_database",
                "azure_mysql_server_configuration",
                "azure_mysql_server_ad_administrator",
                "azure_mysql_server_type",
                "microsoft_graph_service_principal",
                "microsoft_graph_user",
            ]
        },
    }
    mapping: ClassVar[Dict[str, Bender]] = {
        "id": S("id"),
        "tags": S("tags", default={}),
        "name": S("name"),
        "system_data": S("systemData") >> Bend(AzureSystemData.mapping),
        "type": S("type"),
        "location": S("location"),
        "ctime": S("systemData", "createdAt"),
        "mtime": S("systemData", "lastModifiedAt"),
        "administrator_login": S("properties", "administratorLogin"),
        "administrator_login_password": S("properties", "administratorLoginPassword"),
        "availability_zone": S("properties", "availabilityZone"),
        "backup": S("properties", "backup") >> Bend(AzureServerBackup.mapping),
        "create_mode": S("properties", "createMode"),
        "data_encryption": S("properties", "dataEncryption") >> Bend(AzureServerDataEncryption.mapping),
        "fully_qualified_domain_name": S("properties", "fullyQualifiedDomainName"),
        "high_availability": S("properties", "highAvailability") >> Bend(AzureServerHighAvailability.mapping),
        "mysql_server_identity": S("identity") >> Bend(AzureMySQLServerIdentity.mapping),
        "import_source_properties": S("properties", "importSourceProperties")
        >> Bend(AzureImportSourceProperties.mapping),
        "server_maintenance_window": S("properties", "maintenanceWindow") >> Bend(AzureServerMaintenanceWindow.mapping),
        "server_network": S("properties", "network") >> Bend(AzureServerNetwork.mapping),
        "mysql_server_private_endpoint_connections": S("properties", "privateEndpointConnections")
        >> ForallBend(AzurePrivateEndpointConnection.mapping),
        "replica_capacity": S("properties", "replicaCapacity"),
        "replication_role": S("properties", "replicationRole"),
        "restore_point_in_time": S("properties", "restorePointInTime"),
        "server_sku": S("sku") >> Bend(AzureSku.mapping),
        "source_server_resource_id": S("properties", "sourceServerResourceId"),
        "state": S("properties", "state"),
        "storage": S("properties", "storage") >> Bend(AzureStorage.mapping),
        "version": S("properties", "version"),
        "db_type": K("mysql"),
        "db_status": S("properties", "state")
        >> MapEnum(
            {
                "Disabled": DatabaseInstanceStatus.FAILED,
                "Dropping": DatabaseInstanceStatus.TERMINATED,
                "Ready": DatabaseInstanceStatus.AVAILABLE,
                "Starting": DatabaseInstanceStatus.BUSY,
                "Stopped": DatabaseInstanceStatus.STOPPED,
                "Stopping": DatabaseInstanceStatus.BUSY,
                "Updating": DatabaseInstanceStatus.BUSY,
            }
        ),
        "db_endpoint": S("properties", "fullyQualifiedDomainName"),
        "db_version": S("properties", "version"),
        "db_publicly_accessible": S("properties", "network", "publicNetworkAccess")
        >> MapValue(
            {
                "Disabled": False,
                "Enabled": True,
            },
            default=False,
        ),
        "instance_type": S("sku", "name"),
        "volume_size": S("properties", "storage", "storageSizeGB"),
        "volume_iops": S("properties", "storage", "iops"),
    }
    administrator_login: Optional[str] = field(default=None, metadata={'description': 'The administrator s login name of a server. Can only be specified when the server is being created (and is required for creation).'})  # fmt: skip
    administrator_login_password: Optional[str] = field(default=None, metadata={'description': 'The password of the administrator login (required for server creation).'})  # fmt: skip
    availability_zone: Optional[str] = field(default=None, metadata={'description': 'availability Zone information of the server.'})  # fmt: skip
    backup: Optional[AzureServerBackup] = field(default=None, metadata={'description': 'Storage Profile properties of a server'})  # fmt: skip
    create_mode: Optional[str] = field(default=None, metadata={'description': 'The mode to create a new MySQL server.'})  # fmt: skip
    data_encryption: Optional[AzureServerDataEncryption] = field(default=None, metadata={'description': 'The date encryption for cmk.'})  # fmt: skip
    fully_qualified_domain_name: Optional[str] = field(default=None, metadata={'description': 'The fully qualified domain name of a server.'})  # fmt: skip
    high_availability: Optional[AzureServerHighAvailability] = field(default=None, metadata={'description': 'High availability properties of a server'})  # fmt: skip
    mysql_server_identity: Optional[AzureMySQLServerIdentity] = field(default=None, metadata={'description': 'Properties to configure Identity for Bring your Own Keys'})  # fmt: skip
    import_source_properties: Optional[AzureImportSourceProperties] = field(default=None, metadata={'description': 'Import source related properties.'})  # fmt: skip
    server_maintenance_window: Optional[AzureServerMaintenanceWindow] = field(default=None, metadata={'description': 'Maintenance window of a server.'})  # fmt: skip
    server_network: Optional[AzureServerNetwork] = field(default=None, metadata={'description': 'Network related properties of a server'})  # fmt: skip
    mysql_server_private_endpoint_connections: Optional[List[AzurePrivateEndpointConnection]] = field(default=None, metadata={'description': 'PrivateEndpointConnections related properties of a server.'})  # fmt: skip
    replica_capacity: Optional[int] = field(default=None, metadata={'description': 'The maximum number of replicas that a primary server can have.'})  # fmt: skip
    replication_role: Optional[str] = field(default=None, metadata={"description": "The replication role."})
    restore_point_in_time: Optional[datetime] = field(default=None, metadata={'description': 'Restore point creation time (ISO8601 format), specifying the time to restore from.'})  # fmt: skip
    server_sku: Optional[AzureSku] = field(default=None, metadata={'description': 'Billing information related properties of a server.'})  # fmt: skip
    source_server_resource_id: Optional[str] = field(default=None, metadata={'description': 'The source MySQL server id.'})  # fmt: skip
    state: Optional[str] = field(default=None, metadata={"description": "The state of a server."})
    storage: Optional[AzureStorage] = field(default=None, metadata={'description': 'Storage Profile properties of a server'})  # fmt: skip
    version: Optional[str] = field(default=None, metadata={"description": "The version of a server."})
    system_data: Optional[AzureSystemData] = field(default=None, metadata={'description': 'Metadata pertaining to creation and last modification of the resource.'})  # fmt: skip
    type: Optional[str] = field(default=None, metadata={'description': 'The type of the resource. E.g. Microsoft.Compute/virtualMachines or Microsoft.Storage/storageAccounts '})  # fmt: skip
    location: Optional[str] = field(default=None, metadata={'description': 'The geo-location where the resource lives'})  # fmt: skip

    def _collect_items(
        self,
        graph_builder: GraphBuilder,
        server_id: str,
        resource_type: str,
        class_instance: MicrosoftResource,
        api_version: str,
        expected_errors: Optional[List[str]] = None,
    ) -> None:
        path = f"{server_id}/{resource_type}"
        api_spec = AzureResourceSpec(
            service="mysql",
            version=api_version,
            path=path,
            path_parameters=[],
            query_parameters=["api-version"],
            access_path="value",
            expect_array=True,
            expected_error_codes=expected_errors or [],
        )
        items = graph_builder.client.list(api_spec)
        if not items:
            return
        if issubclass(AzureMysqlServerConfiguration, class_instance):  # type: ignore
            collected = class_instance.collect_configs(self.id, items, graph_builder)  # type: ignore
        else:
            collected = class_instance.collect(items, graph_builder)
        for resource in collected:
            graph_builder.add_edge(self, node=resource)

    def post_process(self, graph_builder: GraphBuilder, source: Json) -> None:
        if server_id := self.id:
            resources_to_collect = [
                ("backupsV2", AzureMysqlServerBackup, "2023-12-30", ["ServerNotExist"]),
                ("backups", AzureMysqlServerBackup, "2021-05-01", ["ServerNotExist"]),
                ("maintenances", AzureMysqlServerMaintenance, "2023-12-30", None),
                ("logFiles", AzureMysqlServerLogFile, "2023-12-30", ["ServerNotExist"]),
                ("firewallRules", AzureMysqlServerFirewallRule, "2021-05-01", None),
                ("databases", AzureMysqlServerDatabase, "2021-05-01", ["ServerUnavailableForOperation", "ServiceBusy"]),
                (
                    "configurations",
                    AzureMysqlServerConfiguration,
                    "2023-12-30",
                    ["ServerUnavailableForOperation", "ServiceBusy"],
                ),
                ("administrators", AzureMysqlServerADAdministrator, "2023-12-30", None),
            ]

            for resource_type, resource_class, api_version, expected_errors in resources_to_collect:
                graph_builder.submit_work(
                    service_name,
                    self._collect_items,
                    graph_builder,
                    server_id,
                    resource_type,
                    resource_class,
                    api_version,
                    expected_errors,
                )
        if self.data_encryption:
            self.volume_encrypted = True
        else:
            self.volume_encrypted = False

        if (location := self.location) and (sku := self.server_sku) and (version := self.version):

            def collect_capabilities() -> None:
                api_spec = AzureResourceSpec(
                    service="mysql",
                    version="2023-12-30",
                    path="/subscriptions/{subscriptionId}/providers/Microsoft.DBforMySQL/locations/"
                    + f"{location}/capabilities",
                    path_parameters=["subscriptionId"],
                    query_parameters=["api-version"],
                    access_path="value",
                    expect_array=True,
                )
                items = graph_builder.client.list(api_spec)
                if not items:
                    return
                for item in items:
                    # Set location for further connect_in_graph method
                    item["location"] = location
                    # Set sku name and tier for SKUs filtering
                    item["expected_sku_name"] = sku.name
                    item["expected_sku_tier"] = sku.tier
                    item["expected_version"] = version
                AzureMysqlServerType.collect(items, graph_builder)

            graph_builder.submit_work(service_name, collect_capabilities)

    def connect_in_graph(self, builder: GraphBuilder, source: Json) -> None:
        if (
            (location := self.location)
            and (version := self.version)
            and (sku := self.server_sku)
            and (sku_type := sku.name)
        ):
            builder.add_edge(
                self,
                edge_type=EdgeType.default,
                clazz=AzureMysqlServerType,
                location=location,
                server_version=version,
                id=sku_type,
            )

        # principal: collected via ms graph -> create a deferred edge
        if mii := self.mysql_server_identity:
            if pid := mii.principal_id:
                builder.add_deferred_edge(
                    from_node=self,
                    to_node=BySearchCriteria(f'is({MicrosoftGraphServicePrincipal.kind}) and reported.id=="{pid}"'),
                )
            if uai := mii.user_assigned_identities:
                for _, identity_info in uai.items():
                    if identity_info and identity_info.principal_id:
                        builder.add_deferred_edge(
                            from_node=self,
                            to_node=BySearchCriteria(
                                f'is({MicrosoftGraphUser.kind}) and reported.id=="{identity_info.principal_id}"'
                            ),
                        )


@define(eq=False, slots=False)
class AzureMysqlServerBackup(MicrosoftResource):
    kind: ClassVar[str] = "azure_mysql_server_backup"
    # Collect via AzureMysqlServer()
    mapping: ClassVar[Dict[str, Bender]] = {
        "id": S("id"),
        "tags": S("tags", default={}),
        "name": S("name"),
        "system_data": S("systemData") >> Bend(AzureSystemData.mapping),
        "type": S("type"),
        "ctime": S("systemData", "createdAt"),
        "mtime": S("systemData", "lastModifiedAt"),
        "backup_name_v2": S("properties", "backupNameV2"),
        "backup_type": S("properties", "backupType"),
        "completed_time": S("properties", "completedTime"),
        "provisioning_state": S("properties", "provisioningState"),
        "backup_source": S("properties", "source"),
    }
    backup_name_v2: Optional[str] = field(default=None, metadata={"description": "Backup name"})
    backup_type: Optional[str] = field(default=None, metadata={"description": ""})
    completed_time: Optional[datetime] = field(default=None, metadata={'description': 'Backup completed time (ISO8601 format).'})  # fmt: skip
    provisioning_state: Optional[str] = field(default=None, metadata={'description': 'The current provisioning state.'})  # fmt: skip
    backup_source: Optional[str] = field(default=None, metadata={"description": "Backup source"})
    system_data: Optional[AzureSystemData] = field(default=None, metadata={'description': 'Metadata pertaining to creation and last modification of the resource.'})  # fmt: skip
    type: Optional[str] = field(default=None, metadata={'description': 'The type of the resource. E.g. Microsoft.Compute/virtualMachines or Microsoft.Storage/storageAccounts '})  # fmt: skip


resources: List[Type[MicrosoftResource]] = [
    AzureMysqlServerADAdministrator,
    AzureMysqlServerType,
    AzureMysqlServerConfiguration,
    AzureMysqlServerDatabase,
    AzureMysqlServerFirewallRule,
    AzureMysqlServerLogFile,
    AzureMysqlServerMaintenance,
    AzureMysqlServer,
    AzureMysqlServerBackup,
]
