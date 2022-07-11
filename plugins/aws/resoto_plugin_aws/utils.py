import uuid
from typing import Iterable, List, Dict, Optional, Any, Callable

from boto3.session import Session as BotoSession
from botocore.exceptions import ConnectionClosedError, CredentialRetrievalError
from prometheus_client import Counter
from retrying import retry

from resotolib.baseresources import BaseRegion, BaseResource
from resotolib.config import Config
from resotolib.graph import Graph
from resotolib.json_bender import Bender
from resotolib.types import Json

metrics_session_exceptions = Counter(
    "resoto_plugin_aws_session_exceptions_total",
    "Unhandled AWS Plugin Session Exceptions",
)


def retry_on_session_error(e: Exception) -> bool:
    if isinstance(e, (ConnectionClosedError, CredentialRetrievalError)):
        metrics_session_exceptions.inc()
        return True
    return False


@retry(  # type: ignore
    stop_max_attempt_number=10,
    wait_random_min=1000,
    wait_random_max=6000,
    retry_on_exception=retry_on_session_error,
)
def aws_session(aws_account: Optional[str] = None, aws_role: Optional[str] = None) -> BotoSession:
    if Config.aws.role_override:
        aws_role = Config.aws.role
    if aws_role and aws_account:
        role_arn = f"arn:aws:iam::{aws_account}:role/{aws_role}"
        session = BotoSession(
            aws_access_key_id=Config.aws.access_key_id,
            aws_secret_access_key=Config.aws.secret_access_key,
            region_name="us-east-1",
        )
        sts = session.client("sts")
        token = sts.assume_role(RoleArn=role_arn, RoleSessionName=f"{aws_account}-{str(uuid.uuid4())}")
        credentials = token["Credentials"]
        return BotoSession(
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"],
        )
    else:
        return BotoSession(
            aws_access_key_id=Config.aws.access_key_id,
            aws_secret_access_key=Config.aws.secret_access_key,
        )


def aws_client(resource: BaseResource, service: str, graph: Optional[Graph] = None) -> BotoSession:
    ac = resource.account(graph)
    return aws_session(ac.id, ac.role).client(service, region_name=resource.region(graph).id)  # type: ignore


def aws_resource(resource: BaseResource, service: str, graph: Optional[Graph] = None) -> BotoSession:
    ac = resource.account(graph)
    return aws_session(ac.id, ac.role).resource(service, region_name=resource.region(graph).id)  # type: ignore


def paginate(method: Callable[[], List[Any]], **kwargs: Any) -> Iterable[Any]:
    """Get a paginator for a boto3 list/describe method

    Example Usage:
    session = aws_session(self.account.id, self.account.role)
    client = session.client('autoscaling', region_name=region.id)
    for autoscaling_group in paginate(client.describe_auto_scaling_groups):
        print(autoscaling_group)
    """
    client = method.__self__  # type: ignore
    paginator = client.get_paginator(method.__name__)
    for page in paginator.paginate(**kwargs).result_key_iters():
        for result in page:
            yield result


def arn_partition(region: BaseRegion) -> str:
    arn_partition = "aws"
    if region.id.startswith("cn-"):
        arn_partition = "aws-cn"
    elif region.id.startswith("us-gov-"):
        arn_partition = "aws-us-gov"
    return arn_partition


def tags_as_dict(tags: List[Json]) -> Dict[str, Optional[str]]:
    return {tag["Key"]: tag["Value"] for tag in tags or []}


class ToDict(Bender):
    def __init__(self, key: str = "Key", value: str = "Value") -> None:
        self.key = key
        self.value = value

    def execute(self, source: List[Json]) -> Dict[str, str]:
        return {k.get(self.key, self.key): k.get(self.value, "") for k in source}


class TagsValue(Bender):
    def __init__(self, name: str) -> None:
        self.name = name

    def execute(self, source: List[Json]) -> Optional[str]:
        for k in source:
            if k.get("Key") == self.name:
                return k.get("Value", "")
        return None
