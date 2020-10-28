import time
import cloudkeeper.logging
import copy
from datetime import date
from enum import Enum, auto
from cloudkeeper.baseresources import *
from cloudkeeper.graph import Graph
from cloudkeeper.utils import make_valid_timestamp
from .utils import aws_client, aws_resource


default_ctime = make_valid_timestamp(date(2006, 3, 19))  # AWS public launch date
log = cloudkeeper.logging.getLogger("cloudkeeper." + __name__)


# derived from https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-template-resource-type-ref.html
class AWSAccount(BaseAccount):
    resource_type = "aws_account"

    def __init__(self, *args, role: str = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.account_alias = ""
        self.role = role

    def delete(self, graph) -> bool:
        return False


class AWSRegion(BaseRegion):
    resource_type = "aws_region"

    def __init__(self, *args, role: str = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.ctime = default_ctime

    def delete(self, graph) -> bool:
        return False


class AWSResource:
    def __init__(self, *args, arn: str = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.arn = arn

    def delete(self, graph) -> bool:
        return False


class AWSEC2InstanceType(AWSResource, BaseInstanceType):
    resource_type = "aws_ec2_instance_type"


class AWSEC2InstanceQuota(AWSResource, BaseInstanceQuota):
    resource_type = "aws_ec2_instance_quota"


class AWSEC2Instance(AWSResource, BaseInstance):
    resource_type = "aws_ec2_instance"

    instance_status_map = {
        "pending": InstanceStatus.BUSY,
        "running": InstanceStatus.RUNNING,
        "shutting-down": InstanceStatus.BUSY,
        "terminated": InstanceStatus.TERMINATED,
        "stopping": InstanceStatus.BUSY,
        "stopped": InstanceStatus.STOPPED,
    }

    @BaseInstance.instance_status.setter
    def instance_status(self, value: str) -> None:
        self._instance_status = self.instance_status_map.get(
            value, InstanceStatus.UNKNOWN
        )

    def delete(self, graph: Graph) -> bool:
        if self.instance_status == InstanceStatus.TERMINATED.value:
            log.error(
                (
                    f"AWS EC2 Instance {self.dname} in"
                    f" account {self.account(graph).dname}"
                    f" region {self.region(graph).name}"
                    " is already terminated"
                )
            )
            return False
        ec2 = aws_resource(self, "ec2", graph)
        instance = ec2.Instance(self.id)
        instance.terminate()
        return True

    def update_tag(self, key, value) -> bool:
        ec2 = aws_resource(self, "ec2")
        instance = ec2.Instance(self.id)
        instance.create_tags(Tags=[{"Key": key, "Value": value}])
        return True

    def delete_tag(self, key) -> bool:
        ec2 = aws_resource(self, "ec2")
        instance = ec2.Instance(self.id)
        instance.delete_tags(Tags=[{"Key": key}])
        return True


class AWSEC2KeyPair(AWSResource, BaseKeyPair):
    resource_type = "aws_ec2_keypair"

    def delete(self, graph: Graph) -> bool:
        ec2 = aws_client(self, "ec2", graph)
        ec2.delete_key_pair(KeyName=self.name)
        return True

    def update_tag(self, key, value) -> bool:
        ec2 = aws_client(self, "ec2")
        ec2.create_tags(Resources=[self.id], Tags=[{"Key": key, "Value": value}])
        return True

    def delete_tag(self, key) -> bool:
        ec2 = aws_client(self, "ec2")
        ec2.delete_tags(Resources=[self.id], Tags=[{"Key": key}])
        return True


class AWSEC2VolumeType(AWSResource, BaseVolumeType):
    resource_type = "aws_ec2_volume_type"


class AWSEC2Volume(AWSResource, BaseVolume):
    resource_type = "aws_ec2_volume"

    volume_status_map = {
        "creating": VolumeStatus.BUSY,
        "available": VolumeStatus.AVAILABLE,
        "in-use": VolumeStatus.IN_USE,
        "deleting": VolumeStatus.BUSY,
        "deleted": VolumeStatus.DELETED,
        "error": VolumeStatus.ERROR,
    }

    @BaseVolume.volume_status.setter
    def volume_status(self, value: str) -> None:
        self._volume_status = self.volume_status_map.get(value, VolumeStatus.UNKNOWN)

    def delete(
        self,
        graph: Graph,
        snapshot_before_delete: bool = False,
        snapshot_timeout: int = 3600,
    ) -> bool:
        ec2 = aws_resource(self, "ec2", graph)
        volume = ec2.Volume(self.id)
        if snapshot_before_delete or self.snapshot_before_delete:
            log_msg = "Creating snapshot before deletion"
            self.log(log_msg)
            log.debug(f"{log_msg} of {self.resource_type} {self.dname}")
            snapshot = volume.create_snapshot(
                Description=f"Cloudkeeper created snapshot for volume {self.id}",
                TagSpecifications=[
                    {
                        "ResourceType": "snapshot",
                        "Tags": [
                            {"Key": "Name", "Value": f"CK snap of {self.id}"},
                            {"Key": "owner", "Value": "cloudkeeper"},
                        ],
                    },
                ],
            )
            start_utime = time.time()
            while snapshot.state == "pending":
                if time.time() > start_utime + snapshot_timeout:
                    raise TimeoutError(
                        (
                            f"AWS EC2 Volume Snapshot {self.dname} tag update timed out after "
                            f"{snapshot_timeout} seconds with status {snapshot.state} ({snapshot.state_message})"
                        )
                    )
                time.sleep(10)
                log.debug(
                    (
                        f"Waiting for snapshot {snapshot.id} to finish before deletion of "
                        f"{self.resource_type} {self.dname} - progress {snapshot.progress}"
                    )
                )
                snapshot = ec2.Snapshot(snapshot.id)
            if snapshot.state != "completed":
                log_msg = f"Failed to create snapshot - status {snapshot.state} ({snapshot.state_message})"
                self.log(log_msg)
                log.error(
                    (
                        f"{log_msg} for {self.resource_type} {self.dname} in "
                        f"account {self.account(graph).dname} region {self.region(graph).name}"
                    )
                )
                return False
        volume.delete()
        return True

    def update_tag(self, key, value) -> bool:
        ec2 = aws_resource(self, "ec2")
        volume = ec2.Volume(self.id)
        volume.create_tags(Tags=[{"Key": key, "Value": value}])
        return True

    def delete_tag(self, key) -> bool:
        ec2 = aws_client(self, "ec2")
        ec2.delete_tags(Resources=[self.id], Tags=[{"Key": key}])
        return True


class AWSEC2Snapshot(AWSResource, BaseSnapshot):
    resource_type = "aws_ec2_snapshot"

    def delete(self, graph: Graph) -> bool:
        ec2 = aws_resource(self, "ec2", graph)
        snapshot = ec2.Snapshot(self.id)
        snapshot.delete()
        return True

    def update_tag(self, key, value) -> bool:
        ec2 = aws_client(self, "ec2")
        ec2.create_tags(Resources=[self.id], Tags=[{"Key": key, "Value": value}])
        return True

    def delete_tag(self, key) -> bool:
        ec2 = aws_client(self, "ec2")
        ec2.delete_tags(Resources=[self.id], Tags=[{"Key": key}])
        return True


class AWSEC2Subnet(AWSResource, BaseSubnet):
    resource_type = "aws_ec2_subnet"

    def delete(self, graph: Graph) -> bool:
        ec2 = aws_resource(self, "ec2", graph)
        subnet = ec2.Subnet(self.id)
        subnet.delete()
        return True

    def update_tag(self, key, value) -> bool:
        ec2 = aws_client(self, "ec2")
        ec2.create_tags(Resources=[self.id], Tags=[{"Key": key, "Value": value}])
        return True

    def delete_tag(self, key) -> bool:
        ec2 = aws_client(self, "ec2")
        ec2.delete_tags(Resources=[self.id], Tags=[{"Key": key}])
        return True


class AWSEC2ElasticIP(AWSResource, BaseIPAddress):
    resource_type = "aws_ec2_elastic_ip"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.instance_id = None
        self.public_ip = None
        self.allocation_id = None
        self.association_id = None
        self.domain = None
        self.network_interface_id = None
        self.network_interface_owner_id = None
        self.private_ip_address = None
        self.release_on_delete = False

    def pre_delete(self, graph: Graph) -> bool:
        if self.association_id is not None:
            ec2 = aws_client(self, "ec2", graph=graph)
            ec2.disassociate_address(AssociationId=self.association_id)
        else:
            log.debug(f"No association for {self.rtdname}")
        return True

    def delete(self, graph: Graph) -> bool:
        if self.release_on_delete:
            ec2 = aws_client(self, "ec2", graph=graph)
            ec2.release_address(AllocationId=self.allocation_id)
            return True
        else:
            log.debug(f"Attribute release_on_delete not set for {self.rtdname}")
        return False

    def update_tag(self, key, value) -> bool:
        ec2 = aws_client(self, "ec2")
        ec2.create_tags(Resources=[self.id], Tags=[{"Key": key, "Value": value}])
        return True

    def delete_tag(self, key) -> bool:
        ec2 = aws_client(self, "ec2")
        ec2.delete_tags(Resources=[self.id], Tags=[{"Key": key}])
        return True


class AWSVPC(AWSResource, BaseNetwork):
    resource_type = "aws_vpc"

    def __init__(self, *args, is_default: bool = False, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.is_default = is_default

    def delete(self, graph: Graph) -> bool:
        if self.is_default:
            log_msg = (
                f"Not removing the default VPC {self.id} - aborting delete request"
            )
            log.debug(log_msg)
            self.log(log_msg)
            return False

        ec2 = aws_resource(self, "ec2", graph)
        vpc = ec2.Vpc(self.id)
        vpc.delete()
        return True

    def update_tag(self, key, value) -> bool:
        ec2 = aws_resource(self, "ec2")
        vpc = ec2.Vpc(self.id)
        vpc.create_tags(Tags=[{"Key": key, "Value": value}])
        return True

    def delete_tag(self, key) -> bool:
        ec2 = aws_client(self, "ec2")
        ec2.delete_tags(Resources=[self.id], Tags=[{"Key": key}])
        return True


class AWSVPCQuota(AWSResource, BaseNetworkQuota):
    resource_type = "aws_vpc_quota"


class AWSS3Bucket(AWSResource, BaseBucket):
    resource_type = "aws_s3_bucket"

    def delete(self, graph: Graph) -> bool:
        s3 = aws_resource(self, "s3", graph)
        bucket = s3.Bucket(self.name)
        bucket.objects.delete()
        bucket.delete()
        return True


class AWSS3BucketQuota(AWSResource, BaseBucketQuota):
    resource_type = "aws_s3_bucket_quota"


class AWSELB(AWSResource, BaseLoadBalancer):
    resource_type = "aws_elb"

    def delete(self, graph: Graph) -> bool:
        client = aws_client(self, "elb", graph)
        _ = client.delete_load_balancer(LoadBalancerName=self.name)
        # todo: parse result
        return True

    def update_tag(self, key, value) -> bool:
        client = aws_client(self, "elb")
        client.add_tags(
            LoadBalancerNames=[self.name], Tags=[{"Key": key, "Value": value}]
        )
        return True

    def delete_tag(self, key) -> bool:
        client = aws_client(self, "elb")
        client.remove_tags(LoadBalancerNames=[self.name], Tags=[{"Key": key}])
        return True


class AWSALB(AWSResource, BaseLoadBalancer):
    resource_type = "aws_alb"

    def delete(self, graph: Graph) -> bool:
        client = aws_client(self, "elbv2", graph)
        _ = client.delete_load_balancer(LoadBalancerArn=self.arn)
        # todo: block until loadbalancer is gone
        return True

    def update_tag(self, key, value) -> bool:
        client = aws_client(self, "elbv2")
        client.add_tags(ResourceArns=[self.arn], Tags=[{"Key": key, "Value": value}])
        return True

    def delete_tag(self, key) -> bool:
        client = aws_client(self, "elbv2")
        client.remove_tags(ResourceArns=[self.arn], TagKeys=[key])
        return True


class AWSALBTargetGroup(AWSResource, BaseResource):
    resource_type = "aws_alb_target_group"

    metrics_description = {
        "aws_alb_target_groups_total": {
            "help": "Number of AWS ALB Target Groups",
            "labels": ["cloud", "account", "region"],
        },
        "cleaned_aws_alb_target_groups_total": {
            "help": "Cleaned number of AWS ALB Target Groups",
            "labels": ["cloud", "account", "region"],
        },
    }

    def __init__(self, *args, role: str = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.target_type = ""

    def metrics(self, graph) -> Dict:
        metrics_keys = (
            self.cloud(graph).name,
            self.account(graph).dname,
            self.region(graph).name,
        )
        self._metrics["aws_alb_target_groups_total"][metrics_keys] = 1
        if self._cleaned:
            self._metrics["cleaned_aws_alb_target_groups_total"][metrics_keys] = 1
        return self._metrics

    def delete(self, graph: Graph) -> bool:
        client = aws_client(self, "elbv2", graph)
        _ = client.delete_target_group(TargetGroupArn=self.arn)
        # todo: parse result
        return True

    def update_tag(self, key, value) -> bool:
        client = aws_client(self, "elbv2")
        client.add_tags(ResourceArns=[self.arn], Tags=[{"Key": key, "Value": value}])
        return True

    def delete_tag(self, key) -> bool:
        client = aws_client(self, "elbv2")
        client.remove_tags(ResourceArns=[self.arn], TagKeys=[key])
        return True


class AWSELBQuota(AWSResource, BaseLoadBalancerQuota):
    resource_type = "aws_elb_quota"


class AWSALBQuota(AWSResource, BaseLoadBalancerQuota):
    resource_type = "aws_alb_quota"


class AWSEC2InternetGateway(AWSResource, BaseGateway):
    resource_type = "aws_ec2_internet_gateway"

    def pre_delete(self, graph: Graph) -> bool:
        ec2 = aws_resource(self, "ec2", graph)
        internet_gateway = ec2.InternetGateway(self.id)
        for predecessor in self.predecessors(graph):
            if isinstance(predecessor, AWSVPC):
                log_msg = f"Detaching {predecessor.resource_type} {predecessor.dname}"
                self.log(log_msg)
                log.debug(
                    f"{log_msg} for deletion of {self.resource_type} {self.dname}"
                )
                internet_gateway.detach_from_vpc(VpcId=predecessor.id)
        return True

    def delete(self, graph: Graph) -> bool:
        ec2 = aws_resource(self, "ec2", graph)
        internet_gateway = ec2.InternetGateway(self.id)
        internet_gateway.delete()
        return True

    def update_tag(self, key, value) -> bool:
        ec2 = aws_client(self, "ec2")
        ec2.create_tags(Resources=[self.id], Tags=[{"Key": key, "Value": value}])
        return True

    def delete_tag(self, key) -> bool:
        ec2 = aws_client(self, "ec2")
        ec2.delete_tags(Resources=[self.id], Tags=[{"Key": key}])
        return True


class AWSEC2NATGateway(AWSResource, BaseGateway):
    resource_type = "aws_ec2_nat_gateway"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.nat_gateway_status = ""

    def delete(self, graph: Graph) -> bool:
        ec2 = aws_client(self, "ec2", graph)
        ec2.delete_nat_gateway(NatGatewayId=self.id)
        return True

    def update_tag(self, key, value) -> bool:
        ec2 = aws_client(self, "ec2")
        ec2.create_tags(Resources=[self.id], Tags=[{"Key": key, "Value": value}])
        return True

    def delete_tag(self, key) -> bool:
        ec2 = aws_client(self, "ec2")
        ec2.delete_tags(Resources=[self.id], Tags=[{"Key": key}])
        return True


class AWSEC2InternetGatewayQuota(AWSResource, BaseGatewayQuota):
    resource_type = "aws_ec2_internet_gateway_quota"


class AWSEC2SecurityGroup(AWSResource, BaseSecurityGroup):
    resource_type = "aws_ec2_security_group"

    def pre_delete(self, graph: Graph) -> bool:
        ec2 = aws_resource(self, "ec2", graph)
        security_group = ec2.SecurityGroup(self.id)
        remove_ingress = []
        remove_egress = []

        for permission in security_group.ip_permissions:
            if (
                "UserIdGroupPairs" in permission
                and len(permission["UserIdGroupPairs"]) > 0
            ):
                p = copy.deepcopy(permission)
                remove_ingress.append(p)
                log.debug(
                    f"Adding incoming permission {p} of {self.resource_type} {self.dname} to removal list"
                )

        for permission in security_group.ip_permissions_egress:
            if (
                "UserIdGroupPairs" in permission
                and len(permission["UserIdGroupPairs"]) > 0
            ):
                p = copy.deepcopy(permission)
                remove_egress.append(p)
                log.debug(
                    f"Adding outgoing permission {p} of {self.resource_type} {self.dname} to removal list"
                )

        if len(remove_ingress) > 0:
            security_group.revoke_ingress(IpPermissions=remove_ingress)

        if len(remove_egress) > 0:
            security_group.revoke_egress(IpPermissions=remove_egress)

        return True

    def delete(self, graph: Graph) -> bool:
        ec2 = aws_resource(self, "ec2", graph)
        security_group = ec2.SecurityGroup(self.id)
        security_group.delete()
        return True

    def update_tag(self, key, value) -> bool:
        ec2 = aws_client(self, "ec2")
        ec2.create_tags(Resources=[self.id], Tags=[{"Key": key, "Value": value}])
        return True

    def delete_tag(self, key) -> bool:
        ec2 = aws_client(self, "ec2")
        ec2.delete_tags(Resources=[self.id], Tags=[{"Key": key}])
        return True


class AWSEC2RouteTable(AWSResource, BaseRoutingTable):
    resource_type = "aws_ec2_route_table"

    def pre_delete(self, graph: Graph) -> bool:
        ec2 = aws_resource(self, "ec2", graph)
        rt = ec2.RouteTable(self.id)
        for rta in rt.associations:
            if not rta.main:
                log_msg = f"Deleting route table association {rta.id}"
                self.log(log_msg)
                log.debug(f"{log_msg} for cleanup of {self.resource_type} {self.dname}")
                rta.delete()
        return True

    def delete(self, graph: Graph) -> bool:
        ec2 = aws_resource(self, "ec2", graph)
        rt = ec2.RouteTable(self.id)
        rt.delete()
        return True

    def update_tag(self, key, value) -> bool:
        ec2 = aws_client(self, "ec2")
        ec2.create_tags(Resources=[self.id], Tags=[{"Key": key, "Value": value}])
        return True

    def delete_tag(self, key) -> bool:
        ec2 = aws_client(self, "ec2")
        ec2.delete_tags(Resources=[self.id], Tags=[{"Key": key}])
        return True


class AWSVPCPeeringConnection(AWSResource, BasePeeringConnection):
    resource_type = "aws_vpc_peering_connection"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.vpc_peering_connection_status = ""

    def delete(self, graph: Graph) -> bool:
        ec2 = aws_client(self, "ec2", graph)
        ec2.delete_vpc_peering_connection(VpcPeeringConnectionId=self.id)
        return True

    def update_tag(self, key, value) -> bool:
        ec2 = aws_client(self, "ec2")
        ec2.create_tags(Resources=[self.id], Tags=[{"Key": key, "Value": value}])
        return True

    def delete_tag(self, key) -> bool:
        ec2 = aws_client(self, "ec2")
        ec2.delete_tags(Resources=[self.id], Tags=[{"Key": key}])
        return True


class AWSVPCEndpoint(AWSResource, BaseEndpoint):
    resource_type = "aws_vpc_endpoint"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.vpc_endpoint_type = ""
        self.vpc_endpoint_status = ""

    def delete(self, graph: Graph) -> bool:
        ec2 = aws_client(self, "ec2", graph)
        ec2.delete_vpc_endpoints(VpcEndpointIds=[self.id])
        return True

    def update_tag(self, key, value) -> bool:
        ec2 = aws_client(self, "ec2")
        ec2.create_tags(Resources=[self.id], Tags=[{"Key": key, "Value": value}])
        return True

    def delete_tag(self, key) -> bool:
        ec2 = aws_client(self, "ec2")
        ec2.delete_tags(Resources=[self.id], Tags=[{"Key": key}])
        return True


class AWSEC2NetworkAcl(AWSResource, BaseNetworkAcl):
    resource_type = "aws_ec2_network_acl"

    def __init__(self, *args, is_default: bool = False, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.is_default = is_default

    def delete(self, graph: Graph) -> bool:
        ec2 = aws_client(self, "ec2", graph)
        ec2.delete_network_acl(NetworkAclId=self.id)
        return True

    def update_tag(self, key, value) -> bool:
        ec2 = aws_client(self, "ec2")
        ec2.create_tags(Resources=[self.id], Tags=[{"Key": key, "Value": value}])
        return True

    def delete_tag(self, key) -> bool:
        ec2 = aws_client(self, "ec2")
        ec2.delete_tags(Resources=[self.id], Tags=[{"Key": key}])
        return True


class AWSEC2NetworkInterface(AWSResource, BaseNetworkInterface):
    resource_type = "aws_ec2_network_interface"

    def delete(self, graph: Graph) -> bool:
        ec2 = aws_resource(self, "ec2", graph)
        network_interface = ec2.NetworkInterface(self.id)
        network_interface.delete()
        return True

    def update_tag(self, key, value) -> bool:
        ec2 = aws_client(self, "ec2")
        ec2.create_tags(Resources=[self.id], Tags=[{"Key": key, "Value": value}])
        return True

    def delete_tag(self, key) -> bool:
        ec2 = aws_client(self, "ec2")
        ec2.delete_tags(Resources=[self.id], Tags=[{"Key": key}])
        return True


class AWSRDSInstance(AWSResource, BaseDatabase):
    resource_type = "aws_rds_instance"


class AWSIAMUser(AWSResource, BaseUser):
    resource_type = "aws_iam_user"

    def delete(self, graph: Graph) -> bool:
        iam = aws_resource(self, "iam", graph)
        user = iam.User(self.name)
        user.delete()
        return True


class AWSIAMGroup(AWSResource, BaseGroup):
    resource_type = "aws_iam_group"

    def delete(self, graph: Graph) -> bool:
        iam = aws_resource(self, "iam", graph)
        group = iam.Group(self.name)
        group.delete()
        return True


class AWSIAMRole(AWSResource, BaseRole):
    resource_type = "aws_iam_role"

    def pre_delete(self, graph: Graph) -> bool:
        iam = aws_resource(self, "iam", graph)
        role = iam.Role(self.name)
        for successor in self.successors(graph):
            if isinstance(successor, AWSIAMPolicy):
                log_msg = f"Detaching {successor.rtdname}"
                self.log(log_msg)
                log.debug(f"{log_msg} for deletion of {self.rtdname}")
                role.detach_policy(PolicyArn=successor.arn)
        return True

    def delete(self, graph: Graph) -> bool:
        iam = aws_resource(self, "iam", graph)
        role = iam.Role(self.name)
        role.delete()
        return True


class AWSIAMPolicy(AWSResource, BasePolicy):
    resource_type = "aws_iam_policy"

    def delete(self, graph: Graph) -> bool:
        iam = aws_resource(self, "iam", graph)
        policy = iam.Policy(self.arn)
        policy.delete()
        return True


class AWSIAMInstanceProfile(AWSResource, BaseInstanceProfile):
    resource_type = "aws_iam_instance_profile"

    def pre_delete(self, graph: Graph) -> bool:
        iam = aws_resource(self, "iam", graph)
        instance_profile = iam.InstanceProfile(self.name)
        for predecessor in self.predecessors(graph):
            if isinstance(predecessor, AWSIAMRole):
                log_msg = f"Detaching {predecessor.rtdname}"
                self.log(log_msg)
                log.debug(f"{log_msg} for deletion of {self.rtdname}")
                instance_profile.remove_role(RoleName=predecessor.name)
        return True

    def delete(self, graph: Graph) -> bool:
        iam = aws_resource(self, "iam", graph)
        instance_profile = iam.InstanceProfile(self.name)
        instance_profile.delete()
        return True


class AWSIAMAccessKey(AWSResource, BaseAccessKey):
    resource_type = "aws_iam_access_key"

    def __init__(self, *args, user_name: str = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.user_name = user_name

    def delete(self, graph: Graph) -> bool:
        iam = aws_resource(self, "iam", graph)
        access_key = iam.AccessKey(self.user_name, self.id)
        access_key.delete()
        return True


class AWSIAMServerCertificate(AWSResource, BaseCertificate):
    resource_type = "aws_iam_server_certificate"

    def __init__(self, *args, path: str = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.path = path

    def delete(self, graph: Graph) -> bool:
        iam = aws_resource(self, "iam", graph)
        certificate = iam.ServerCertificate(self.name)
        certificate.delete()
        return True


class AWSIAMServerCertificateQuota(AWSResource, BaseCertificateQuota):
    resource_type = "aws_iam_server_certificate_quota"


class AWSCloudFormationStack(AWSResource, BaseStack):
    resource_type = "aws_cloudformation_stack"

    def delete(self, graph: Graph) -> bool:
        cf = aws_resource(self, "cloudformation", graph)
        stack = cf.Stack(self.name)
        stack.delete()
        return True

    class ModificationMode(Enum):
        """Defines Tag modification mode"""

        UPDATE = auto()
        DELETE = auto()

    def update_tag(self, key, value) -> bool:
        return self._modify_tag(
            key, value, mode=AWSCloudFormationStack.ModificationMode.UPDATE
        )

    def delete_tag(self, key) -> bool:
        return self._modify_tag(
            key, mode=AWSCloudFormationStack.ModificationMode.DELETE
        )

    def _modify_tag(self, key, value=None, mode=None, wait=False) -> bool:
        tags = dict(self.tags)
        if mode == AWSCloudFormationStack.ModificationMode.DELETE:
            if not self.tags.get(key):
                raise KeyError(key)
            del tags[key]
        elif mode == AWSCloudFormationStack.ModificationMode.UPDATE:
            if self.tags.get(key) == value:
                return True
            tags.update({key: value})
        else:
            return False

        cf = aws_resource(self, "cloudformation")
        stack = cf.Stack(self.name)
        stack = self.wait_for_completion(stack, cf)
        response = stack.update(
            Capabilities=["CAPABILITY_NAMED_IAM"],
            UsePreviousTemplate=True,
            Tags=[{"Key": label, "Value": value} for label, value in tags.items()],
            Parameters=[
                {"ParameterKey": parameter, "UsePreviousValue": True}
                for parameter in self.stack_parameters.keys()
            ],
        )
        if response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0) != 200:
            raise RuntimeError(
                f"Error updating AWS Cloudformation Stack {self.dname} for {mode.name} of tag {key}"
            )
        if wait:
            self.wait_for_completion(stack, cf)
        self.tags = tags
        return True

    def wait_for_completion(self, stack, cloudformation_resource, timeout=300):
        start_utime = time.time()
        while stack.stack_status.endswith("_IN_PROGRESS"):
            if time.time() > start_utime + timeout:
                raise TimeoutError(
                    (
                        f"AWS Cloudformation Stack {self.dname} tag update timed out "
                        f"after {timeout} seconds with status {stack.stack_status}"
                    )
                )
            time.sleep(5)
            stack = cloudformation_resource.Stack(stack.name)
        return stack


class AWSEKSCluster(AWSResource, BaseResource):
    resource_type = "aws_eks_cluster"

    metrics_description = {
        "aws_eks_clusters_total": {
            "help": "Number of AWS EKS Clusters",
            "labels": ["cloud", "account", "region"],
        },
        "cleaned_aws_eks_clusters_total": {
            "help": "Cleaned number of AWS EKS Clusters",
            "labels": ["cloud", "account", "region"],
        },
    }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.cluster_status = ""
        self.cluster_endpoint = ""

    def metrics(self, graph) -> Dict:
        metrics_keys = (
            self.cloud(graph).name,
            self.account(graph).dname,
            self.region(graph).name,
        )
        self._metrics["aws_eks_clusters_total"][metrics_keys] = 1
        if self._cleaned:
            self._metrics["cleaned_aws_eks_clusters_total"][metrics_keys] = 1
        return self._metrics

    def delete(self, graph: Graph) -> bool:
        eks = aws_client(self, "eks", graph)
        eks.delete_cluster(name=self.name)
        return True

    def update_tag(self, key, value) -> bool:
        eks = aws_client(self, "eks")
        eks.tag_resource(resourceArn=self.arn, tags={key: value})
        return True

    def delete_tag(self, key) -> bool:
        eks = aws_client(self, "eks")
        eks.untag_resource(resourceArn=self.arn, tagKeys=[key])
        return True


class AWSEKSNodegroup(AWSResource, BaseResource):
    resource_type = "aws_eks_nodegroup"

    metrics_description = {
        "aws_eks_nodegroups_total": {
            "help": "Number of AWS EKS Nodegroups",
            "labels": ["cloud", "account", "region"],
        },
        "cleaned_aws_eks_nodegroups_total": {
            "help": "Cleaned number of AWS EKS Nodegroups",
            "labels": ["cloud", "account", "region"],
        },
    }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.cluster_name = ""
        self.nodegroup_status = ""

    def metrics(self, graph) -> Dict:
        metrics_keys = (
            self.cloud(graph).name,
            self.account(graph).dname,
            self.region(graph).name,
        )
        self._metrics["aws_eks_nodegroups_total"][metrics_keys] = 1
        if self._cleaned:
            self._metrics["cleaned_aws_eks_nodegroups_total"][metrics_keys] = 1
        return self._metrics

    def delete(self, graph: Graph) -> bool:
        eks = aws_client(self, "eks", graph)
        eks.delete_nodegroup(clusterName=self.cluster_name, nodegroupName=self.name)
        return True

    def update_tag(self, key, value) -> bool:
        eks = aws_client(self, "eks")
        eks.tag_resource(resourceArn=self.arn, tags={key: value})
        return True

    def delete_tag(self, key) -> bool:
        eks = aws_client(self, "eks")
        eks.untag_resource(resourceArn=self.arn, tagKeys=[key])
        return True


class AWSAutoScalingGroup(AWSResource, BaseAutoScalingGroup):
    resource_type = "aws_autoscaling_group"

    def delete(self, graph: Graph, force_delete: bool = True) -> bool:
        client = aws_client(self, "autoscaling", graph)
        client.delete_auto_scaling_group(
            AutoScalingGroupName=self.name, ForceDelete=force_delete
        )
        return True

    def update_tag(self, key, value) -> bool:
        client = aws_client(self, "autoscaling")
        client.create_or_update_tags(
            Tags=[
                {
                    "ResourceId": self.name,
                    "ResourceType": "auto-scaling-group",
                    "Key": key,
                    "Value": value,
                    "PropagateAtLaunch": True,
                }
            ]
        )
        return True

    def delete_tag(self, key) -> bool:
        client = aws_client(self, "autoscaling")
        client.delete_tags(
            Tags=[
                {
                    "ResourceId": self.name,
                    "ResourceType": "auto-scaling-group",
                    "Key": key,
                    "Value": self.tags[key],
                    "PropagateAtLaunch": True,
                }
            ]
        )
        return True
