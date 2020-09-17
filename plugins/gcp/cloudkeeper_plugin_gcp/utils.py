from cloudkeeper.baseresources import BaseResource
from cloudkeeper.args import ArgumentParser
from cloudkeeper.utils import RWLock
import cloudkeeper.logging
from typing import Iterable, List, Union, Callable, Any, Dict
from googleapiclient import discovery
from googleapiclient.errors import HttpError as GoogleApiClientHttpError
from googleapiclient.discovery_cache.base import Cache as GoogleApiClientCache
from google.oauth2 import service_account
from datetime import datetime

# from google.oauth2.credentials import UserAccessTokenCredentials

log = cloudkeeper.logging.getLogger("cloudkeeper." + __name__)
cloudkeeper.logging.getLogger("googleapiclient").setLevel(cloudkeeper.logging.ERROR)


SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]


class MemoryCache(GoogleApiClientCache):
    _cache = {}

    def get(self, url):
        return MemoryCache._cache.get(url)

    def set(self, url, content):
        MemoryCache._cache[url] = content


class Credentials:
    _credentials = {}
    _initialized = False
    _lock = RWLock()

    @staticmethod
    def load():
        with Credentials._lock.write_access:
            if not Credentials._initialized:
                for sa_file in ArgumentParser.args.gcp_service_account:
                    credentials = load_credentials(sa_file)
                    for project in list_credential_projects(credentials):
                        Credentials._credentials[project["id"]] = credentials
                Credentials._initialized = True

    @staticmethod
    def get(project_id: str):
        Credentials.load()
        with Credentials._lock.read_access:
            return Credentials._credentials.get(project_id)

    @staticmethod
    def all() -> Dict:
        Credentials.load()
        with Credentials._lock.read_access:
            return dict(Credentials._credentials)

    @staticmethod
    def reload():
        with Credentials._lock.write_access:
            Credentials._initialized = False
        Credentials.load()


def load_credentials(sa_file: str):
    return service_account.Credentials.from_service_account_file(sa_file, scopes=SCOPES)


def gcp_client(service: str, version: str, credentials: str):
    client = discovery.build(
        service, version, credentials=credentials, cache=MemoryCache()
    )
    return client


def list_credential_projects(credentials) -> List:
    ret = []
    try:
        client = gcp_client("cloudresourcemanager", "v1", credentials=credentials)
        projects = client.projects()
        for project in paginate(projects, "list", "projects"):
            ctime = project.get("createTime")
            if ctime is not None:
                ctime = iso2datetime(ctime)
            project_name = project.get("name")
            project_id = project.get("projectId")
            p = {
                "id": project_id,
                "name": project_name,
                "ctime": ctime,
            }
            ret.append(p)
    except GoogleApiClientHttpError:
        log.error(
            (
                "Unable to load projects from cloudresourcemanager"
                " - falling back to local credentials information"
            )
        )
        p = {
            "id": credentials.project_id,
            "name": credentials.project_id,
        }
        ret.append(p)
    return ret


def iso2datetime(ts: str) -> datetime:
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    if ts is not None:
        return datetime.fromisoformat(ts)


def paginate(
    gcp_resource, method_name, items_name, subitems_name=None, **kwargs
) -> Iterable:
    next_method_name = method_name + "_next"
    method = getattr(gcp_resource, method_name)
    request = method(**kwargs)
    while request is not None:
        result = request.execute()
        if items_name in result:
            items = result[items_name]
            if isinstance(items, dict):
                for item in items.values():
                    if subitems_name in item:
                        yield from item[subitems_name]
            else:
                yield from items
        if hasattr(gcp_resource, next_method_name):
            method = getattr(gcp_resource, next_method_name)
            request = method(request, result)
        else:
            request = None


def compute_client(credentials):
    return gcp_client("compute", "v1", credentials=credentials)


def get_result_data(result: Dict, value: Union[str, Callable]) -> Any:
    data = None
    if callable(value):
        try:
            data = value(result)
        except Exception:
            log.exception(f"Exception while trying to fetch data calling {value}")
    elif value in result:
        data = result[value]
    return data


def common_client_kwargs(resource: BaseResource) -> Dict:
    common_kwargs = {}
    if resource.account().id != "undefined":
        common_kwargs["project"] = resource.account().id
    if resource.zone().name != "undefined":
        common_kwargs["zone"] = resource.zone().name
    elif resource.region().name != "undefined":
        common_kwargs["region"] = resource.region().name
    return common_kwargs


def delete_resource(resource: BaseResource) -> bool:
    delete_kwargs = {str(resource.delete_identifier): resource.name}
    common_kwargs = common_client_kwargs(resource)
    delete_kwargs.update(common_kwargs)

    gr = gcp_resource(resource)
    request = gr.delete(**delete_kwargs)
    request.execute()
    return True


def update_label(resource: BaseResource, key: str, value: str) -> bool:
    get_kwargs = {str(resource.get_identifier): resource.name}
    set_labels_kwargs = {str(resource.set_label_identifier): resource.name}

    common_kwargs = common_client_kwargs(resource)
    get_kwargs.update(common_kwargs)
    set_labels_kwargs.update(common_kwargs)

    labels = dict(resource.tags)
    if value is None:
        if key in labels:
            del labels[key]
        else:
            return False
    else:
        labels.update({key: value})
    body = {"labels": labels, "labelFingerprint": resource.label_fingerprint}
    set_labels_kwargs["body"] = body
    gr = gcp_resource(resource)
    request = gr.setLabels(**set_labels_kwargs)
    response = request.execute()
    # Update label_fingerprint
    request = gr.get(**get_kwargs)
    response = request.execute()
    resource.label_fingerprint = response.get("labelFingerprint")
    return True


def gcp_resource(resource: BaseResource):
    client_kwargs = {}
    if resource.account().id != "undefined":
        client_kwargs["credentials"] = Credentials.get(resource.account().id)

    client = compute_client(**client_kwargs)
    client_method_name = resource.api_identifier + "s"
    gr = getattr(client, client_method_name)
    return gr()
