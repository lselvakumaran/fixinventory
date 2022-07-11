from attrs import define, field
from datetime import datetime
from typing import ClassVar, Dict, Optional, List, Type

from resoto_plugin_aws.resource.base import AwsResource, GraphBuilder, AwsApiSpec
from resoto_plugin_aws.utils import TagsToDict, TagsValue

from resotolib.baseresources import (  # noqa: F401
    BaseInstance,
    EdgeType,
    BaseVolume,
    BaseInstanceType,
    BaseAccount,
    VolumeStatus,
    InstanceStatus,
)
from resotolib.json_bender import Bender, S, Bend, ForallBend, bend, MapEnum, F
from resotolib.types import Json


# region InstanceType
@define(eq=False, slots=False)
class AwsEc2ProcessorInfo:
    kind: ClassVar[str] = "aws_ec2_processor_info"
    mapping: ClassVar[Dict[str, Bender]] = {
        "supported_architectures": S("SupportedArchitectures", default=[]),
        "sustained_clock_speed_in_ghz": S("SustainedClockSpeedInGhz"),
    }
    supported_architectures: List[str] = field(factory=list)
    sustained_clock_speed_in_ghz: Optional[float] = field(default=None)


@define(eq=False, slots=False)
class AwsEc2VCpuInfo:
    kind: ClassVar[str] = "aws_ec2_v_cpu_info"
    mapping: ClassVar[Dict[str, Bender]] = {
        "default_v_cpus": S("DefaultVCpus"),
        "default_cores": S("DefaultCores"),
        "default_threads_per_core": S("DefaultThreadsPerCore"),
        "valid_cores": S("ValidCores", default=[]),
        "valid_threads_per_core": S("ValidThreadsPerCore", default=[]),
    }
    default_v_cpus: Optional[int] = field(default=None)
    default_cores: Optional[int] = field(default=None)
    default_threads_per_core: Optional[int] = field(default=None)
    valid_cores: List[int] = field(factory=list)
    valid_threads_per_core: List[int] = field(factory=list)


@define(eq=False, slots=False)
class AwsEc2DiskInfo:
    kind: ClassVar[str] = "aws_ec2_disk_info"
    mapping: ClassVar[Dict[str, Bender]] = {"size_in_gb": S("SizeInGB"), "count": S("Count"), "type": S("Type")}
    size_in_gb: Optional[int] = field(default=None)
    count: Optional[int] = field(default=None)
    type: Optional[str] = field(default=None)


@define(eq=False, slots=False)
class AwsEc2InstanceStorageInfo:
    kind: ClassVar[str] = "aws_ec2_instance_storage_info"
    mapping: ClassVar[Dict[str, Bender]] = {
        "total_size_in_gb": S("TotalSizeInGB"),
        "disks": S("Disks", default=[]) >> ForallBend(AwsEc2DiskInfo.mapping),
        "nvme_support": S("NvmeSupport"),
        "encryption_support": S("EncryptionSupport"),
    }
    total_size_in_gb: Optional[int] = field(default=None)
    disks: List[AwsEc2DiskInfo] = field(factory=list)
    nvme_support: Optional[str] = field(default=None)
    encryption_support: Optional[str] = field(default=None)


@define(eq=False, slots=False)
class AwsEc2EbsOptimizedInfo:
    kind: ClassVar[str] = "aws_ec2_ebs_optimized_info"
    mapping: ClassVar[Dict[str, Bender]] = {
        "baseline_bandwidth_in_mbps": S("BaselineBandwidthInMbps"),
        "baseline_throughput_in_m_bps": S("BaselineThroughputInMBps"),
        "baseline_iops": S("BaselineIops"),
        "maximum_bandwidth_in_mbps": S("MaximumBandwidthInMbps"),
        "maximum_throughput_in_m_bps": S("MaximumThroughputInMBps"),
        "maximum_iops": S("MaximumIops"),
    }
    baseline_bandwidth_in_mbps: Optional[int] = field(default=None)
    baseline_throughput_in_m_bps: Optional[float] = field(default=None)
    baseline_iops: Optional[int] = field(default=None)
    maximum_bandwidth_in_mbps: Optional[int] = field(default=None)
    maximum_throughput_in_m_bps: Optional[float] = field(default=None)
    maximum_iops: Optional[int] = field(default=None)


@define(eq=False, slots=False)
class AwsEc2EbsInfo:
    kind: ClassVar[str] = "aws_ec2_ebs_info"
    mapping: ClassVar[Dict[str, Bender]] = {
        "ebs_optimized_support": S("EbsOptimizedSupport"),
        "encryption_support": S("EncryptionSupport"),
        "ebs_optimized_info": S("EbsOptimizedInfo") >> Bend(AwsEc2EbsOptimizedInfo.mapping),
        "nvme_support": S("NvmeSupport"),
    }
    ebs_optimized_support: Optional[str] = field(default=None)
    encryption_support: Optional[str] = field(default=None)
    ebs_optimized_info: Optional[AwsEc2EbsOptimizedInfo] = field(default=None)
    nvme_support: Optional[str] = field(default=None)


@define(eq=False, slots=False)
class AwsEc2NetworkCardInfo:
    kind: ClassVar[str] = "aws_ec2_network_card_info"
    mapping: ClassVar[Dict[str, Bender]] = {
        "network_card_index": S("NetworkCardIndex"),
        "network_performance": S("NetworkPerformance"),
        "maximum_network_interfaces": S("MaximumNetworkInterfaces"),
    }
    network_card_index: Optional[int] = field(default=None)
    network_performance: Optional[str] = field(default=None)
    maximum_network_interfaces: Optional[int] = field(default=None)


@define(eq=False, slots=False)
class AwsEc2NetworkInfo:
    kind: ClassVar[str] = "aws_ec2_network_info"
    mapping: ClassVar[Dict[str, Bender]] = {
        "network_performance": S("NetworkPerformance"),
        "maximum_network_interfaces": S("MaximumNetworkInterfaces"),
        "maximum_network_cards": S("MaximumNetworkCards"),
        "default_network_card_index": S("DefaultNetworkCardIndex"),
        "network_cards": S("NetworkCards", default=[]) >> ForallBend(AwsEc2NetworkCardInfo.mapping),
        "ipv4_addresses_per_interface": S("Ipv4AddressesPerInterface"),
        "ipv6_addresses_per_interface": S("Ipv6AddressesPerInterface"),
        "ipv6_supported": S("Ipv6Supported"),
        "ena_support": S("EnaSupport"),
        "efa_supported": S("EfaSupported"),
        "efa_info": S("EfaInfo", "MaximumEfaInterfaces"),
        "encryption_in_transit_supported": S("EncryptionInTransitSupported"),
    }
    network_performance: Optional[str] = field(default=None)
    maximum_network_interfaces: Optional[int] = field(default=None)
    maximum_network_cards: Optional[int] = field(default=None)
    default_network_card_index: Optional[int] = field(default=None)
    network_cards: List[AwsEc2NetworkCardInfo] = field(factory=list)
    ipv4_addresses_per_interface: Optional[int] = field(default=None)
    ipv6_addresses_per_interface: Optional[int] = field(default=None)
    ipv6_supported: Optional[bool] = field(default=None)
    ena_support: Optional[str] = field(default=None)
    efa_supported: Optional[bool] = field(default=None)
    efa_info: Optional[int] = field(default=None)
    encryption_in_transit_supported: Optional[bool] = field(default=None)


@define(eq=False, slots=False)
class AwsEc2GpuDeviceInfo:
    kind: ClassVar[str] = "aws_ec2_gpu_device_info"
    mapping: ClassVar[Dict[str, Bender]] = {
        "name": S("Name"),
        "manufacturer": S("Manufacturer"),
        "count": S("Count"),
        "memory_info": S("MemoryInfo", "SizeInMiB"),
    }
    name: Optional[str] = field(default=None)
    manufacturer: Optional[str] = field(default=None)
    count: Optional[int] = field(default=None)
    memory_info: Optional[int] = field(default=None)


@define(eq=False, slots=False)
class AwsEc2GpuInfo:
    kind: ClassVar[str] = "aws_ec2_gpu_info"
    mapping: ClassVar[Dict[str, Bender]] = {
        "gpus": S("Gpus", default=[]) >> ForallBend(AwsEc2GpuDeviceInfo.mapping),
        "total_gpu_memory_in_mi_b": S("TotalGpuMemoryInMiB"),
    }
    gpus: List[AwsEc2GpuDeviceInfo] = field(factory=list)
    total_gpu_memory_in_mi_b: Optional[int] = field(default=None)


@define(eq=False, slots=False)
class AwsEc2FpgaDeviceInfo:
    kind: ClassVar[str] = "aws_ec2_fpga_device_info"
    mapping: ClassVar[Dict[str, Bender]] = {
        "name": S("Name"),
        "manufacturer": S("Manufacturer"),
        "count": S("Count"),
        "memory_info": S("MemoryInfo", "SizeInMiB"),
    }
    name: Optional[str] = field(default=None)
    manufacturer: Optional[str] = field(default=None)
    count: Optional[int] = field(default=None)
    memory_info: Optional[int] = field(default=None)


@define(eq=False, slots=False)
class AwsEc2FpgaInfo:
    kind: ClassVar[str] = "aws_ec2_fpga_info"
    mapping: ClassVar[Dict[str, Bender]] = {
        "fpgas": S("Fpgas", default=[]) >> ForallBend(AwsEc2FpgaDeviceInfo.mapping),
        "total_fpga_memory_in_mi_b": S("TotalFpgaMemoryInMiB"),
    }
    fpgas: List[AwsEc2FpgaDeviceInfo] = field(factory=list)
    total_fpga_memory_in_mi_b: Optional[int] = field(default=None)


@define(eq=False, slots=False)
class AwsEc2PlacementGroupInfo:
    kind: ClassVar[str] = "aws_ec2_placement_group_info"
    mapping: ClassVar[Dict[str, Bender]] = {"supported_strategies": S("SupportedStrategies", default=[])}
    supported_strategies: List[str] = field(factory=list)


@define(eq=False, slots=False)
class AwsEc2InferenceDeviceInfo:
    kind: ClassVar[str] = "aws_ec2_inference_device_info"
    mapping: ClassVar[Dict[str, Bender]] = {"count": S("Count"), "name": S("Name"), "manufacturer": S("Manufacturer")}
    count: Optional[int] = field(default=None)
    name: Optional[str] = field(default=None)
    manufacturer: Optional[str] = field(default=None)


@define(eq=False, slots=False)
class AwsEc2InferenceAcceleratorInfo:
    kind: ClassVar[str] = "aws_ec2_inference_accelerator_info"
    mapping: ClassVar[Dict[str, Bender]] = {
        "accelerators": S("Accelerators", default=[]) >> ForallBend(AwsEc2InferenceDeviceInfo.mapping)
    }
    accelerators: List[AwsEc2InferenceDeviceInfo] = field(factory=list)


@define(eq=False, slots=False)
class AwsEc2InstanceType(AwsResource, BaseInstanceType):
    kind: ClassVar[str] = "aws_ec2_instance_type"
    api_spec: ClassVar[AwsApiSpec] = AwsApiSpec("ec2", "describe-instance-types", "InstanceTypes")
    mapping: ClassVar[Dict[str, Bender]] = {
        "id": S("InstanceType"),
        "tags": S("Tags", default=[]) >> TagsToDict(),
        "name": S("InstanceType"),
        "instance_type": S("InstanceType"),
        "instance_cores": S("VCpuInfo", "DefaultVCpus"),
        "instance_memory": S("MemoryInfo", "SizeInMiB") >> F(lambda x: int(x) / 1024),
        "current_generation": S("CurrentGeneration"),
        "free_tier_eligible": S("FreeTierEligible"),
        "supported_usage_classes": S("SupportedUsageClasses", default=[]),
        "supported_root_device_types": S("SupportedRootDeviceTypes", default=[]),
        "supported_virtualization_types": S("SupportedVirtualizationTypes", default=[]),
        "bare_metal": S("BareMetal"),
        "hypervisor": S("Hypervisor"),
        "instance_type_processor_info": S("ProcessorInfo") >> Bend(AwsEc2ProcessorInfo.mapping),
        "instance_type_v_cpu_info": S("VCpuInfo") >> Bend(AwsEc2VCpuInfo.mapping),
        "memory_info": S("MemoryInfo", "SizeInMiB"),
        "instance_storage_supported": S("InstanceStorageSupported"),
        "instance_type_instance_storage_info": S("InstanceStorageInfo") >> Bend(AwsEc2InstanceStorageInfo.mapping),
        "instance_type_ebs_info": S("EbsInfo") >> Bend(AwsEc2EbsInfo.mapping),
        "instance_type_network_info": S("NetworkInfo") >> Bend(AwsEc2NetworkInfo.mapping),
        "instance_type_gpu_info": S("GpuInfo") >> Bend(AwsEc2GpuInfo.mapping),
        "instance_type_fpga_info": S("FpgaInfo") >> Bend(AwsEc2FpgaInfo.mapping),
        "instance_type_placement_group_info": S("PlacementGroupInfo") >> Bend(AwsEc2PlacementGroupInfo.mapping),
        "instance_type_inference_accelerator_info": S("InferenceAcceleratorInfo")
        >> Bend(AwsEc2InferenceAcceleratorInfo.mapping),
        "hibernation_supported": S("HibernationSupported"),
        "burstable_performance_supported": S("BurstablePerformanceSupported"),
        "dedicated_hosts_supported": S("DedicatedHostsSupported"),
        "auto_recovery_supported": S("AutoRecoverySupported"),
        "supported_boot_modes": S("SupportedBootModes", default=[]),
    }
    current_generation: Optional[bool] = field(default=None)
    free_tier_eligible: Optional[bool] = field(default=None)
    supported_usage_classes: List[str] = field(factory=list)
    supported_root_device_types: List[str] = field(factory=list)
    supported_virtualization_types: List[str] = field(factory=list)
    bare_metal: Optional[bool] = field(default=None)
    hypervisor: Optional[str] = field(default=None)
    instance_type_processor_info: Optional[AwsEc2ProcessorInfo] = field(default=None)
    instance_type_v_cpu_info: Optional[AwsEc2VCpuInfo] = field(default=None)
    memory_info: Optional[int] = field(default=None)
    instance_storage_supported: Optional[bool] = field(default=None)
    instance_type_instance_storage_info: Optional[AwsEc2InstanceStorageInfo] = field(default=None)
    instance_type_ebs_info: Optional[AwsEc2EbsInfo] = field(default=None)
    instance_type_network_info: Optional[AwsEc2NetworkInfo] = field(default=None)
    instance_type_gpu_info: Optional[AwsEc2GpuInfo] = field(default=None)
    instance_type_fpga_info: Optional[AwsEc2FpgaInfo] = field(default=None)
    instance_type_placement_group_info: Optional[AwsEc2PlacementGroupInfo] = field(default=None)
    instance_type_inference_accelerator_info: Optional[AwsEc2InferenceAcceleratorInfo] = field(default=None)
    hibernation_supported: Optional[bool] = field(default=None)
    burstable_performance_supported: Optional[bool] = field(default=None)
    dedicated_hosts_supported: Optional[bool] = field(default=None)
    auto_recovery_supported: Optional[bool] = field(default=None)
    supported_boot_modes: List[str] = field(factory=list)

    @classmethod
    def collect(cls: Type[AwsResource], json: List[Json], builder: GraphBuilder) -> None:
        for js in json:
            it = AwsEc2InstanceType.from_api(js)
            # only store this information in the builder, not directly in the graph
            # reason: pricing is region-specific - this is enriched in the builder on demand
            builder.global_instance_types[it.name] = it


# endregion

# region Volume


@define(eq=False, slots=False)
class AwsEc2VolumeAttachment:
    kind: ClassVar[str] = "aws_ec2_volume_attachment"
    mapping: ClassVar[Dict[str, Bender]] = {
        "attach_time": S("AttachTime"),
        "device": S("Device"),
        "instance_id": S("InstanceId"),
        "state": S("State"),
        "volume_id": S("VolumeId"),
        "delete_on_termination": S("DeleteOnTermination"),
    }
    attach_time: Optional[datetime] = field(default=None)
    device: Optional[str] = field(default=None)
    instance_id: Optional[str] = field(default=None)
    state: Optional[str] = field(default=None)
    volume_id: Optional[str] = field(default=None)
    delete_on_termination: Optional[bool] = field(default=None)


VolumeStatusMapping = {
    "creating": VolumeStatus.BUSY,
    "available": VolumeStatus.AVAILABLE,
    "in-use": VolumeStatus.IN_USE,
    "deleting": VolumeStatus.DELETED,
    "deleted": VolumeStatus.DELETED,
    "error": VolumeStatus.ERROR,
}


@define(eq=False, slots=False)
class AwsEc2Volume(AwsResource, BaseVolume):
    kind: ClassVar[str] = "aws_ec2_volume"
    api_spec: ClassVar[AwsApiSpec] = AwsApiSpec("ec2", "describe-volumes", "Volumes")
    mapping: ClassVar[Dict[str, Bender]] = {
        "id": S("VolumeId"),
        "tags": S("Tags", default=[]) >> TagsToDict(),
        "name": S("Tags", default=[]) >> TagsValue("Name"),
        "ctime": S("CreateTime"),
        "volume_size": S("Size"),
        "volume_type": S("VolumeType"),
        "volume_status": S("State") >> MapEnum(VolumeStatusMapping, default=VolumeStatus.UNKNOWN),
        "volume_iops": S("Iops"),
        "volume_throughput": S("Throughput"),
        "volume_encrypted": S("Encrypted"),
        "volume_attachments": S("Attachments", default=[]) >> ForallBend(AwsEc2VolumeAttachment.mapping),
        "availability_zone": S("AvailabilityZone"),
        "volume_kms_key_id": S("KmsKeyId"),
        "volume_outpost_arn": S("OutpostArn"),
        "volume_snapshot_id": S("SnapshotId"),
        "volume_fast_restored": S("FastRestored"),
        "volume_multi_attach_enabled": S("MultiAttachEnabled"),
    }
    volume_attachments: List[AwsEc2VolumeAttachment] = field(factory=list)
    availability_zone: Optional[str] = field(default=None)
    volume_encrypted: Optional[bool] = field(default=None)
    volume_kms_key_id: Optional[str] = field(default=None)
    volume_outpost_arn: Optional[str] = field(default=None)
    volume_snapshot_id: Optional[str] = field(default=None)
    volume_iops: Optional[int] = field(default=None)
    volume_fast_restored: Optional[bool] = field(default=None)
    volume_multi_attach_enabled: Optional[bool] = field(default=None)
    volume_throughput: Optional[int] = field(default=None)

    def connect_in_graph(self, builder: GraphBuilder, source: Json) -> None:
        super().connect_in_graph(builder, source)
        builder.add_edge(self, EdgeType.default, reverse=True, name=self.volume_type)
        for attachment in self.volume_attachments:
            builder.add_edge(self, EdgeType.default, clazz=AwsEc2Instance, id=attachment.instance_id)
            builder.add_edge(self, EdgeType.delete, reverse=True, clazz=AwsEc2Instance, id=attachment.instance_id)


# endregion

# region KeyPair


@define(eq=False, slots=False)
class AwsEc2KeyPair(AwsResource):
    kind: ClassVar[str] = "aws_ec2_key_pair_info"
    api_spec: ClassVar[AwsApiSpec] = AwsApiSpec("ec2", "describe-key-pairs", "KeyPairs")
    mapping: ClassVar[Dict[str, Bender]] = {
        "id": S("KeyPairId"),
        "name": S("KeyName"),
        "tags": S("Tags", default=[]) >> TagsToDict(),
        "key_fingerprint": S("KeyFingerprint"),
        "key_type": S("KeyType"),
        "public_key": S("PublicKey"),
        "ctime": S("CreateTime"),
    }
    key_fingerprint: Optional[str] = field(default=None)
    key_type: Optional[str] = field(default=None)
    public_key: Optional[str] = field(default=None)


# endregion

# region Instance


@define(eq=False, slots=False)
class AwsEc2Placement:
    kind: ClassVar[str] = "aws_ec2_placement"
    mapping: ClassVar[Dict[str, Bender]] = {
        "availability_zone": S("AvailabilityZone"),
        "affinity": S("Affinity"),
        "group_name": S("GroupName"),
        "partition_number": S("PartitionNumber"),
        "host_id": S("HostId"),
        "tenancy": S("Tenancy"),
        "spread_domain": S("SpreadDomain"),
        "host_resource_group_arn": S("HostResourceGroupArn"),
    }
    availability_zone: Optional[str] = field(default=None)
    affinity: Optional[str] = field(default=None)
    group_name: Optional[str] = field(default=None)
    partition_number: Optional[int] = field(default=None)
    host_id: Optional[str] = field(default=None)
    tenancy: Optional[str] = field(default=None)
    spread_domain: Optional[str] = field(default=None)
    host_resource_group_arn: Optional[str] = field(default=None)


@define(eq=False, slots=False)
class AwsEc2ProductCode:
    kind: ClassVar[str] = "aws_ec2_product_code"
    mapping: ClassVar[Dict[str, Bender]] = {
        "product_code_id": S("ProductCodeId"),
        "product_code_type": S("ProductCodeType"),
    }
    product_code_id: Optional[str] = field(default=None)
    product_code_type: Optional[str] = field(default=None)


@define(eq=False, slots=False)
class AwsEc2InstanceState:
    kind: ClassVar[str] = "aws_ec2_instance_state"
    mapping: ClassVar[Dict[str, Bender]] = {"code": S("Code"), "name": S("Name")}
    code: Optional[int] = field(default=None)
    name: Optional[str] = field(default=None)


@define(eq=False, slots=False)
class AwsEc2EbsInstanceBlockDevice:
    kind: ClassVar[str] = "aws_ec2_ebs_instance_block_device"
    mapping: ClassVar[Dict[str, Bender]] = {
        "attach_time": S("AttachTime"),
        "delete_on_termination": S("DeleteOnTermination"),
        "status": S("Status"),
        "volume_id": S("VolumeId"),
    }
    attach_time: Optional[datetime] = field(default=None)
    delete_on_termination: Optional[bool] = field(default=None)
    status: Optional[str] = field(default=None)
    volume_id: Optional[str] = field(default=None)


@define(eq=False, slots=False)
class AwsEc2InstanceBlockDeviceMapping:
    kind: ClassVar[str] = "aws_ec2_instance_block_device_mapping"
    mapping: ClassVar[Dict[str, Bender]] = {
        "device_name": S("DeviceName"),
        "ebs": S("Ebs") >> Bend(AwsEc2EbsInstanceBlockDevice.mapping),
    }
    device_name: Optional[str] = field(default=None)
    ebs: Optional[AwsEc2EbsInstanceBlockDevice] = field(default=None)


@define(eq=False, slots=False)
class AwsEc2IamInstanceProfile:
    kind: ClassVar[str] = "aws_ec2_iam_instance_profile"
    mapping: ClassVar[Dict[str, Bender]] = {"arn": S("Arn"), "id": S("Id")}
    arn: Optional[str] = field(default=None)
    id: Optional[str] = field(default=None)


@define(eq=False, slots=False)
class AwsEc2ElasticGpuAssociation:
    kind: ClassVar[str] = "aws_ec2_elastic_gpu_association"
    mapping: ClassVar[Dict[str, Bender]] = {
        "elastic_gpu_id": S("ElasticGpuId"),
        "elastic_gpu_association_id": S("ElasticGpuAssociationId"),
        "elastic_gpu_association_state": S("ElasticGpuAssociationState"),
        "elastic_gpu_association_time": S("ElasticGpuAssociationTime"),
    }
    elastic_gpu_id: Optional[str] = field(default=None)
    elastic_gpu_association_id: Optional[str] = field(default=None)
    elastic_gpu_association_state: Optional[str] = field(default=None)
    elastic_gpu_association_time: Optional[str] = field(default=None)


@define(eq=False, slots=False)
class AwsEc2ElasticInferenceAcceleratorAssociation:
    kind: ClassVar[str] = "aws_ec2_elastic_inference_accelerator_association"
    mapping: ClassVar[Dict[str, Bender]] = {
        "elastic_inference_accelerator_arn": S("ElasticInferenceAcceleratorArn"),
        "elastic_inference_accelerator_association_id": S("ElasticInferenceAcceleratorAssociationId"),
        "elastic_inference_accelerator_association_state": S("ElasticInferenceAcceleratorAssociationState"),
        "elastic_inference_accelerator_association_time": S("ElasticInferenceAcceleratorAssociationTime"),
    }
    elastic_inference_accelerator_arn: Optional[str] = field(default=None)
    elastic_inference_accelerator_association_id: Optional[str] = field(default=None)
    elastic_inference_accelerator_association_state: Optional[str] = field(default=None)
    elastic_inference_accelerator_association_time: Optional[datetime] = field(default=None)


@define(eq=False, slots=False)
class AwsEc2InstanceNetworkInterfaceAssociation:
    kind: ClassVar[str] = "aws_ec2_instance_network_interface_association"
    mapping: ClassVar[Dict[str, Bender]] = {
        "carrier_ip": S("CarrierIp"),
        "customer_owned_ip": S("CustomerOwnedIp"),
        "ip_owner_id": S("IpOwnerId"),
        "public_dns_name": S("PublicDnsName"),
        "public_ip": S("PublicIp"),
    }
    carrier_ip: Optional[str] = field(default=None)
    customer_owned_ip: Optional[str] = field(default=None)
    ip_owner_id: Optional[str] = field(default=None)
    public_dns_name: Optional[str] = field(default=None)
    public_ip: Optional[str] = field(default=None)


@define(eq=False, slots=False)
class AwsEc2InstanceNetworkInterfaceAttachment:
    kind: ClassVar[str] = "aws_ec2_instance_network_interface_attachment"
    mapping: ClassVar[Dict[str, Bender]] = {
        "attach_time": S("AttachTime"),
        "attachment_id": S("AttachmentId"),
        "delete_on_termination": S("DeleteOnTermination"),
        "device_index": S("DeviceIndex"),
        "status": S("Status"),
        "network_card_index": S("NetworkCardIndex"),
    }
    attach_time: Optional[datetime] = field(default=None)
    attachment_id: Optional[str] = field(default=None)
    delete_on_termination: Optional[bool] = field(default=None)
    device_index: Optional[int] = field(default=None)
    status: Optional[str] = field(default=None)
    network_card_index: Optional[int] = field(default=None)


@define(eq=False, slots=False)
class AwsEc2GroupIdentifier:
    kind: ClassVar[str] = "aws_ec2_group_identifier"
    mapping: ClassVar[Dict[str, Bender]] = {"group_name": S("GroupName"), "group_id": S("GroupId")}
    group_name: Optional[str] = field(default=None)
    group_id: Optional[str] = field(default=None)


@define(eq=False, slots=False)
class AwsEc2InstancePrivateIpAddress:
    kind: ClassVar[str] = "aws_ec2_instance_private_ip_address"
    mapping: ClassVar[Dict[str, Bender]] = {
        "association": S("Association") >> Bend(AwsEc2InstanceNetworkInterfaceAssociation.mapping),
        "primary": S("Primary"),
        "private_dns_name": S("PrivateDnsName"),
        "private_ip_address": S("PrivateIpAddress"),
    }
    association: Optional[AwsEc2InstanceNetworkInterfaceAssociation] = field(default=None)
    primary: Optional[bool] = field(default=None)
    private_dns_name: Optional[str] = field(default=None)
    private_ip_address: Optional[str] = field(default=None)


@define(eq=False, slots=False)
class AwsEc2InstanceNetworkInterface:
    kind: ClassVar[str] = "aws_ec2_instance_network_interface"
    mapping: ClassVar[Dict[str, Bender]] = {
        "association": S("Association") >> Bend(AwsEc2InstanceNetworkInterfaceAssociation.mapping),
        "attachment": S("Attachment") >> Bend(AwsEc2InstanceNetworkInterfaceAttachment.mapping),
        "description": S("Description"),
        "groups": S("Groups", default=[]) >> ForallBend(AwsEc2GroupIdentifier.mapping),
        "ipv6_addresses": S("Ipv6Addresses", default=[]) >> ForallBend(S("Ipv6Address")),
        "mac_address": S("MacAddress"),
        "network_interface_id": S("NetworkInterfaceId"),
        # "owner_id": S("OwnerId"),
        "private_dns_name": S("PrivateDnsName"),
        "private_ip_address": S("PrivateIpAddress"),
        "private_ip_addresses": S("PrivateIpAddresses", default=[])
        >> ForallBend(AwsEc2InstancePrivateIpAddress.mapping),
        "source_dest_check": S("SourceDestCheck"),
        "status": S("Status"),
        # "subnet_id": S("SubnetId"),
        # "vpc_id": S("VpcId"),
        "interface_type": S("InterfaceType"),
        "ipv4_prefixes": S("Ipv4Prefixes", default=[]) >> ForallBend(S("Ipv4Prefix")),
        "ipv6_prefixes": S("Ipv6Prefixes", default=[]) >> ForallBend(S("Ipv6Prefix")),
    }
    association: Optional[AwsEc2InstanceNetworkInterfaceAssociation] = field(default=None)
    attachment: Optional[AwsEc2InstanceNetworkInterfaceAttachment] = field(default=None)
    description: Optional[str] = field(default=None)
    groups: List[AwsEc2GroupIdentifier] = field(factory=list)
    ipv6_addresses: List[str] = field(factory=list)
    mac_address: Optional[str] = field(default=None)
    network_interface_id: Optional[str] = field(default=None)
    private_dns_name: Optional[str] = field(default=None)
    private_ip_address: Optional[str] = field(default=None)
    private_ip_addresses: List[AwsEc2InstancePrivateIpAddress] = field(factory=list)
    source_dest_check: Optional[bool] = field(default=None)
    status: Optional[str] = field(default=None)
    interface_type: Optional[str] = field(default=None)
    ipv4_prefixes: List[str] = field(factory=list)
    ipv6_prefixes: List[str] = field(factory=list)


@define(eq=False, slots=False)
class AwsEc2StateReason:
    kind: ClassVar[str] = "aws_ec2_state_reason"
    mapping: ClassVar[Dict[str, Bender]] = {"code": S("Code"), "message": S("Message")}
    code: Optional[str] = field(default=None)
    message: Optional[str] = field(default=None)


@define(eq=False, slots=False)
class AwsEc2CpuOptions:
    kind: ClassVar[str] = "aws_ec2_cpu_options"
    mapping: ClassVar[Dict[str, Bender]] = {"core_count": S("CoreCount"), "threads_per_core": S("ThreadsPerCore")}
    core_count: Optional[int] = field(default=None)
    threads_per_core: Optional[int] = field(default=None)


@define(eq=False, slots=False)
class AwsEc2CapacityReservationTargetResponse:
    kind: ClassVar[str] = "aws_ec2_capacity_reservation_target_response"
    mapping: ClassVar[Dict[str, Bender]] = {
        "capacity_reservation_id": S("CapacityReservationId"),
        "capacity_reservation_resource_group_arn": S("CapacityReservationResourceGroupArn"),
    }
    capacity_reservation_id: Optional[str] = field(default=None)
    capacity_reservation_resource_group_arn: Optional[str] = field(default=None)


@define(eq=False, slots=False)
class AwsEc2CapacityReservationSpecificationResponse:
    kind: ClassVar[str] = "aws_ec2_capacity_reservation_specification_response"
    mapping: ClassVar[Dict[str, Bender]] = {
        "capacity_reservation_preference": S("CapacityReservationPreference"),
        "capacity_reservation_target": S("CapacityReservationTarget")
        >> Bend(AwsEc2CapacityReservationTargetResponse.mapping),
    }
    capacity_reservation_preference: Optional[str] = field(default=None)
    capacity_reservation_target: Optional[AwsEc2CapacityReservationTargetResponse] = field(default=None)


@define(eq=False, slots=False)
class AwsEc2InstanceMetadataOptionsResponse:
    kind: ClassVar[str] = "aws_ec2_instance_metadata_options_response"
    mapping: ClassVar[Dict[str, Bender]] = {
        "state": S("State"),
        "http_tokens": S("HttpTokens"),
        "http_put_response_hop_limit": S("HttpPutResponseHopLimit"),
        "http_endpoint": S("HttpEndpoint"),
        "http_protocol_ipv6": S("HttpProtocolIpv6"),
        "instance_metadata_tags": S("InstanceMetadataTags"),
    }
    state: Optional[str] = field(default=None)
    http_tokens: Optional[str] = field(default=None)
    http_put_response_hop_limit: Optional[int] = field(default=None)
    http_endpoint: Optional[str] = field(default=None)
    http_protocol_ipv6: Optional[str] = field(default=None)
    instance_metadata_tags: Optional[str] = field(default=None)


@define(eq=False, slots=False)
class AwsEc2PrivateDnsNameOptionsResponse:
    kind: ClassVar[str] = "aws_ec2_private_dns_name_options_response"
    mapping: ClassVar[Dict[str, Bender]] = {
        "hostname_type": S("HostnameType"),
        "enable_resource_name_dns_a_record": S("EnableResourceNameDnsARecord"),
        "enable_resource_name_dns_aaaa_record": S("EnableResourceNameDnsAAAARecord"),
    }
    hostname_type: Optional[str] = field(default=None)
    enable_resource_name_dns_a_record: Optional[bool] = field(default=None)
    enable_resource_name_dns_aaaa_record: Optional[bool] = field(default=None)


InstanceStatusMapping = {
    "pending": InstanceStatus.BUSY,
    "running": InstanceStatus.RUNNING,
    "shutting-down": InstanceStatus.STOPPED,
    "terminated": InstanceStatus.TERMINATED,
    "stopping": InstanceStatus.STOPPED,
    "stopped": InstanceStatus.STOPPED,
}


@define(eq=False, slots=False)
class AwsEc2Instance(AwsResource, BaseInstance):
    kind: ClassVar[str] = "aws_ec2_instance"
    api_spec: ClassVar[AwsApiSpec] = AwsApiSpec("ec2", "describe-instances", "Reservations")
    mapping: ClassVar[Dict[str, Bender]] = {
        # base properties
        "id": S("InstanceId"),
        "tags": S("Tags", default=[]) >> TagsToDict(),
        "name": S("Tags", default=[]) >> TagsValue("Name"),
        "ctime": S("LaunchTime"),
        "instance_status": S("State", "Name") >> MapEnum(InstanceStatusMapping, default=InstanceStatus.UNKNOWN),
        "instance_cores": S("CpuOptions", "CoreCount"),
        "instance_ami_launch_index": S("AmiLaunchIndex"),
        "instance_image_id": S("ImageId"),
        "instance_type": S("InstanceType"),
        "instance_kernel_id": S("KernelId"),
        "instance_key_name": S("KeyName"),
        "instance_launch_time": S("LaunchTime"),
        "instance_monitoring": S("Monitoring", "State"),
        "instance_placement": S("Placement") >> Bend(AwsEc2Placement.mapping),
        "instance_platform": S("Platform"),
        "instance_private_dns_name": S("PrivateDnsName"),
        "instance_private_ip_address": S("PrivateIpAddress"),
        "instance_product_codes": S("ProductCodes", default=[]) >> ForallBend(AwsEc2ProductCode.mapping),
        "instance_public_dns_name": S("PublicDnsName"),
        "instance_public_ip_address": S("PublicIpAddress"),
        "instance_ramdisk_id": S("RamdiskId"),
        "instance_state": S("State") >> Bend(AwsEc2InstanceState.mapping),
        "instance_state_transition_reason": S("StateTransitionReason"),
        "instance_subnet_id": S("SubnetId"),
        # "instance_vpc_id": S("VpcId"), # TODO: add link
        "instance_architecture": S("Architecture"),
        "instance_block_device_mappings": S("BlockDeviceMappings", default=[])
        >> ForallBend(AwsEc2InstanceBlockDeviceMapping.mapping),
        "instance_client_token": S("ClientToken"),
        "instance_ebs_optimized": S("EbsOptimized"),
        "instance_ena_support": S("EnaSupport"),
        "instance_hypervisor": S("Hypervisor"),
        "instance_iam_instance_profile": S("IamInstanceProfile") >> Bend(AwsEc2IamInstanceProfile.mapping),
        "instance_lifecycle": S("InstanceLifecycle"),
        "instance_elastic_gpu_associations": S("ElasticGpuAssociations", default=[])
        >> ForallBend(AwsEc2ElasticGpuAssociation.mapping),
        "instance_elastic_inference_accelerator_associations": S("ElasticInferenceAcceleratorAssociations", default=[])
        >> ForallBend(AwsEc2ElasticInferenceAcceleratorAssociation.mapping),
        "instance_network_interfaces": S("NetworkInterfaces", default=[])
        >> ForallBend(AwsEc2InstanceNetworkInterface.mapping),
        "instance_outpost_arn": S("OutpostArn"),
        "instance_root_device_name": S("RootDeviceName"),
        "instance_root_device_type": S("RootDeviceType"),
        "instance_security_groups": S("SecurityGroups", default=[]) >> ForallBend(AwsEc2GroupIdentifier.mapping),
        "instance_source_dest_check": S("SourceDestCheck"),
        "instance_spot_instance_request_id": S("SpotInstanceRequestId"),
        "instance_sriov_net_support": S("SriovNetSupport"),
        "instance_state_reason": S("StateReason") >> Bend(AwsEc2StateReason.mapping),
        "instance_virtualization_type": S("VirtualizationType"),
        "instance_cpu_options": S("CpuOptions") >> Bend(AwsEc2CpuOptions.mapping),
        "instance_capacity_reservation_id": S("CapacityReservationId"),
        "instance_capacity_reservation_specification": S("CapacityReservationSpecification")
        >> Bend(AwsEc2CapacityReservationSpecificationResponse.mapping),
        "instance_hibernation_options": S("HibernationOptions", "Configured"),
        "instance_licenses": S("Licenses", default=[]) >> ForallBend(S("LicenseConfigurationArn")),
        "instance_metadata_options": S("MetadataOptions") >> Bend(AwsEc2InstanceMetadataOptionsResponse.mapping),
        "instance_enclave_options": S("EnclaveOptions", "Enabled"),
        "instance_boot_mode": S("BootMode"),
        "instance_platform_details": S("PlatformDetails"),
        "instance_usage_operation": S("UsageOperation"),
        "instance_usage_operation_update_time": S("UsageOperationUpdateTime"),
        "instance_private_dns_name_options": S("PrivateDnsNameOptions")
        >> Bend(AwsEc2PrivateDnsNameOptionsResponse.mapping),
        "instance_ipv6_address": S("Ipv6Address"),
        "instance_tpm_support": S("TpmSupport"),
        "instance_maintenance_options": S("MaintenanceOptions", "AutoRecovery"),
    }
    instance_ami_launch_index: Optional[int] = field(default=None)
    instance_image_id: Optional[str] = field(default=None)
    instance_kernel_id: Optional[str] = field(default=None)
    instance_key_name: Optional[str] = field(default=None)
    instance_launch_time: Optional[datetime] = field(default=None)
    instance_monitoring: Optional[str] = field(default=None)
    instance_placement: Optional[AwsEc2Placement] = field(default=None)
    instance_platform: Optional[str] = field(default=None)
    instance_private_dns_name: Optional[str] = field(default=None)
    instance_private_ip_address: Optional[str] = field(default=None)
    instance_product_codes: List[AwsEc2ProductCode] = field(factory=list)
    instance_public_dns_name: Optional[str] = field(default=None)
    instance_public_ip_address: Optional[str] = field(default=None)
    instance_ramdisk_id: Optional[str] = field(default=None)
    instance_state: Optional[AwsEc2InstanceState] = field(default=None)
    instance_state_transition_reason: Optional[str] = field(default=None)
    instance_subnet_id: Optional[str] = field(default=None)
    instance_architecture: Optional[str] = field(default=None)
    instance_block_device_mappings: List[AwsEc2InstanceBlockDeviceMapping] = field(factory=list)
    instance_client_token: Optional[str] = field(default=None)
    instance_ebs_optimized: Optional[bool] = field(default=None)
    instance_ena_support: Optional[bool] = field(default=None)
    instance_hypervisor: Optional[str] = field(default=None)
    instance_iam_instance_profile: Optional[AwsEc2IamInstanceProfile] = field(default=None)
    instance_lifecycle: Optional[str] = field(default=None)
    instance_elastic_gpu_associations: List[AwsEc2ElasticGpuAssociation] = field(factory=list)
    instance_elastic_inference_accelerator_associations: List[AwsEc2ElasticInferenceAcceleratorAssociation] = field(
        factory=list
    )
    instance_network_interfaces: List[AwsEc2InstanceNetworkInterface] = field(factory=list)
    instance_outpost_arn: Optional[str] = field(default=None)
    instance_root_device_name: Optional[str] = field(default=None)
    instance_root_device_type: Optional[str] = field(default=None)
    instance_security_groups: List[AwsEc2GroupIdentifier] = field(factory=list)
    instance_source_dest_check: Optional[bool] = field(default=None)
    instance_spot_instance_request_id: Optional[str] = field(default=None)
    instance_sriov_net_support: Optional[str] = field(default=None)
    instance_state_reason: Optional[AwsEc2StateReason] = field(default=None)
    instance_virtualization_type: Optional[str] = field(default=None)
    instance_cpu_options: Optional[AwsEc2CpuOptions] = field(default=None)
    instance_capacity_reservation_id: Optional[str] = field(default=None)
    instance_capacity_reservation_specification: Optional[AwsEc2CapacityReservationSpecificationResponse] = field(
        default=None
    )
    instance_hibernation_options: Optional[bool] = field(default=None)
    instance_licenses: List[str] = field(factory=list)
    instance_metadata_options: Optional[AwsEc2InstanceMetadataOptionsResponse] = field(default=None)
    instance_enclave_options: Optional[bool] = field(default=None)
    instance_boot_mode: Optional[str] = field(default=None)
    instance_platform_details: Optional[str] = field(default=None)
    instance_usage_operation: Optional[str] = field(default=None)
    instance_usage_operation_update_time: Optional[datetime] = field(default=None)
    instance_private_dns_name_options: Optional[AwsEc2PrivateDnsNameOptionsResponse] = field(default=None)
    instance_ipv6_address: Optional[str] = field(default=None)
    instance_tpm_support: Optional[str] = field(default=None)
    instance_maintenance_options: Optional[str] = field(default=None)

    @classmethod
    def collect(cls: Type[AwsResource], json: List[Json], builder: GraphBuilder) -> None:
        for reservation in json:
            for instance_in in reservation["Instances"]:
                mapped = bend(cls.mapping, instance_in)
                instance = AwsEc2Instance.from_json(mapped)
                # copy data from the instance type
                if instance_type := builder.instance_type(instance.instance_type):
                    builder.add_node(instance_type, {})
                    instance.instance_cores = instance_type.instance_cores
                    instance.instance_memory = instance_type.instance_memory
                builder.add_node(instance, instance_in)

    def connect_in_graph(self, builder: GraphBuilder, source: Json) -> None:
        super().connect_in_graph(builder, source)
        builder.add_edge(self, EdgeType.default, reverse=True, clazz=AwsEc2InstanceType, name=self.instance_type)
        if self.instance_key_name:
            builder.add_edge(self, EdgeType.default, clazz=AwsEc2KeyPair, name=self.instance_key_name)
            builder.add_edge(self, EdgeType.delete, reverse=True, clazz=AwsEc2KeyPair, name=self.instance_key_name)


# endregion

# region ReservedInstances


@define(eq=False, slots=False)
class AwsEc2RecurringCharge:
    kind: ClassVar[str] = "aws_ec2_recurring_charge"
    mapping: ClassVar[Dict[str, Bender]] = {"amount": S("Amount"), "frequency": S("Frequency")}
    amount: Optional[float] = field(default=None)
    frequency: Optional[str] = field(default=None)


@define(eq=False, slots=False)
class AwsEc2ReservedInstances(AwsResource):
    kind: ClassVar[str] = "aws_ec2_reserved_instances"
    api_spec: ClassVar[AwsApiSpec] = AwsApiSpec("ec2", "describe-reserved-instances", "ReservedInstances")
    mapping: ClassVar[Dict[str, Bender]] = {
        "id": S("ReservedInstancesId"),
        "tags": S("Tags", default=[]) >> TagsToDict(),
        "name": S("Tags", default=[]) >> TagsValue("Name"),
        "availability_zone": S("AvailabilityZone"),
        "reservation_duration": S("Duration"),
        "reservation_end": S("End"),
        "reservation_fixed_price": S("FixedPrice"),
        "reservation_instance_count": S("InstanceCount"),
        "reservation_instance_type": S("InstanceType"),
        "reservation_product_description": S("ProductDescription"),
        "reservation_reserved_instances_id": S("ReservedInstancesId"),
        "reservation_start": S("Start"),
        "reservation_state": S("State"),
        "reservation_usage_price": S("UsagePrice"),
        "reservation_currency_code": S("CurrencyCode"),
        "reservation_instance_tenancy": S("InstanceTenancy"),
        "reservation_offering_class": S("OfferingClass"),
        "reservation_offering_type": S("OfferingType"),
        "reservation_recurring_charges": S("RecurringCharges", default=[]) >> ForallBend(AwsEc2RecurringCharge.mapping),
        "reservation_scope": S("Scope"),
    }
    availability_zone: Optional[str] = field(default=None)
    reservation_duration: Optional[int] = field(default=None)
    reservation_end: Optional[datetime] = field(default=None)
    reservation_fixed_price: Optional[float] = field(default=None)
    reservation_instance_count: Optional[int] = field(default=None)
    reservation_instance_type: Optional[str] = field(default=None)
    reservation_product_description: Optional[str] = field(default=None)
    reservation_reserved_instances_id: Optional[str] = field(default=None)
    reservation_start: Optional[datetime] = field(default=None)
    reservation_state: Optional[str] = field(default=None)
    reservation_usage_price: Optional[float] = field(default=None)
    reservation_currency_code: Optional[str] = field(default=None)
    reservation_instance_tenancy: Optional[str] = field(default=None)
    reservation_offering_class: Optional[str] = field(default=None)
    reservation_offering_type: Optional[str] = field(default=None)
    reservation_recurring_charges: List[AwsEc2RecurringCharge] = field(factory=list)
    reservation_scope: Optional[str] = field(default=None)

    def connect_in_graph(self, builder: GraphBuilder, source: Json) -> None:
        super().connect_in_graph(builder, source)
        builder.add_edge(
            self, EdgeType.default, reverse=True, clazz=AwsEc2InstanceType, name=self.reservation_instance_type
        )


# endregion

# region Network ACLs


@define(eq=False, slots=False)
class AwsEc2NetworkAclAssociation:
    kind: ClassVar[str] = "aws_ec2_network_acl_association"
    mapping: ClassVar[Dict[str, Bender]] = {
        "network_acl_association_id": S("NetworkAclAssociationId"),
        "network_acl_id": S("NetworkAclId"),
        "subnet_id": S("SubnetId"),
    }
    network_acl_association_id: Optional[str] = field(default=None)
    network_acl_id: Optional[str] = field(default=None)
    subnet_id: Optional[str] = field(default=None)


@define(eq=False, slots=False)
class AwsEc2IcmpTypeCode:
    kind: ClassVar[str] = "aws_ec2_icmp_type_code"
    mapping: ClassVar[Dict[str, Bender]] = {"code": S("Code"), "type": S("Type")}
    code: Optional[int] = field(default=None)
    type: Optional[int] = field(default=None)


@define(eq=False, slots=False)
class AwsEc2PortRange:
    kind: ClassVar[str] = "aws_ec2_port_range"
    mapping: ClassVar[Dict[str, Bender]] = {"from_range": S("From"), "to_range": S("To")}
    from_range: Optional[int] = field(default=None)
    to_range: Optional[int] = field(default=None)


@define(eq=False, slots=False)
class AwsEc2NetworkAclEntry:
    kind: ClassVar[str] = "aws_ec2_network_acl_entry"
    mapping: ClassVar[Dict[str, Bender]] = {
        "cidr_block": S("CidrBlock"),
        "egress": S("Egress"),
        "icmp_type_code": S("IcmpTypeCode") >> Bend(AwsEc2IcmpTypeCode.mapping),
        "ipv6_cidr_block": S("Ipv6CidrBlock"),
        "port_range": S("PortRange") >> Bend(AwsEc2PortRange.mapping),
        "protocol": S("Protocol"),
        "rule_action": S("RuleAction"),
        "rule_number": S("RuleNumber"),
    }
    cidr_block: Optional[str] = field(default=None)
    egress: Optional[bool] = field(default=None)
    icmp_type_code: Optional[AwsEc2IcmpTypeCode] = field(default=None)
    ipv6_cidr_block: Optional[str] = field(default=None)
    port_range: Optional[AwsEc2PortRange] = field(default=None)
    protocol: Optional[str] = field(default=None)
    rule_action: Optional[str] = field(default=None)
    rule_number: Optional[int] = field(default=None)


@define(eq=False, slots=False)
class AwsEc2NetworkAcl(AwsResource):
    kind: ClassVar[str] = "aws_ec2_network_acl"
    api_spec: ClassVar[AwsApiSpec] = AwsApiSpec("ec2", "describe-network-acls", "NetworkAcls")
    mapping: ClassVar[Dict[str, Bender]] = {
        "id": S("NetworkAclId"),
        "tags": S("Tags", default=[]) >> TagsToDict(),
        "name": S("Tags", default=[]) >> TagsValue("Name"),
        "acl_associations": S("Associations", default=[]) >> ForallBend(AwsEc2NetworkAclAssociation.mapping),
        "acl_entries": S("Entries", default=[]) >> ForallBend(AwsEc2NetworkAclEntry.mapping),
        "is_default": S("IsDefault"),
        # "vpc_id": S("VpcId"), # TODO: add link
        # "owner_id": S("OwnerId") # TODO: add link
    }
    acl_associations: List[AwsEc2NetworkAclAssociation] = field(factory=list)
    acl_entries: List[AwsEc2NetworkAclEntry] = field(factory=list)
    is_default: Optional[bool] = field(default=None)


# endregion

global_resources: List[Type[AwsResource]] = [
    AwsEc2InstanceType,
]
resources: List[Type[AwsResource]] = [
    AwsEc2Instance,
    AwsEc2NetworkAcl,
    AwsEc2ReservedInstances,
    AwsEc2KeyPair,
    AwsEc2Volume,
]
