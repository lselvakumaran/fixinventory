from datetime import datetime
from typing import ClassVar, Dict, Optional, List, Type

from attrs import define, field

from resoto_plugin_aws.resource.base import AwsResource, AwsApiSpec
from resoto_plugin_aws.utils import TagsValue, ToDict
from resotolib.json_bender import Bender, S, Bend

service_name = "ecs"


@define(eq=False, slots=False)
class AwsEcrEncryptionConfiguration:
    kind: ClassVar[str] = "aws_ecr_encryption_configuration"
    mapping: ClassVar[Dict[str, Bender]] = {"encryption_type": S("encryptionType"), "kms_key": S("kmsKey")}
    encryption_type: Optional[str] = field(default=None, metadata={"description": "The encryption type to use. If you use the KMS encryption type, the contents of the repository will be encrypted using server-side encryption with Key Management Service key stored in KMS. When you use KMS to encrypt your data, you can either use the default Amazon Web Services managed KMS key for Amazon ECR, or specify your own KMS key, which you already created. For more information, see Protecting data using server-side encryption with an KMS key stored in Key Management Service (SSE-KMS) in the Amazon Simple Storage Service Console Developer Guide. If you use the AES256 encryption type, Amazon ECR uses server-side encryption with Amazon S3-managed encryption keys which encrypts the images in the repository using an AES-256 encryption algorithm. For more information, see Protecting data using server-side encryption with Amazon S3-managed encryption keys (SSE-S3) in the Amazon Simple Storage Service Console Developer Guide."})  # fmt: skip
    kms_key: Optional[str] = field(default=None, metadata={"description": "If you use the KMS encryption type, specify the KMS key to use for encryption. The alias, key ID, or full ARN of the KMS key can be specified. The key must exist in the same Region as the repository. If no key is specified, the default Amazon Web Services managed KMS key for Amazon ECR will be used."})  # fmt: skip


@define(eq=False, slots=False)
class AwsEcrRepository(AwsResource):
    kind: ClassVar[str] = "aws_ecr_repository"
    api_spec: ClassVar[AwsApiSpec] = AwsApiSpec("ecr", "describe-repositories", "repositories")
    mapping: ClassVar[Dict[str, Bender]] = {
        "id": S("repositoryName"),
        "tags": S("Tags", default=[]) >> ToDict(),
        "name": S("repositoryName"),
        "ctime": S("createdAt"),
        "repository_arn": S("repositoryArn"),
        "registry_id": S("registryId"),
        "repository_uri": S("repositoryUri"),
        "image_tag_mutability": S("imageTagMutability"),
        "image_scanning_configuration": S("imageScanningConfiguration", "scanOnPush"),
        "encryption_configuration": S("encryptionConfiguration") >> Bend(AwsEcrEncryptionConfiguration.mapping),
    }
    repository_arn: Optional[str] = field(default=None, metadata={"description": "The Amazon Resource Name (ARN) that identifies the repository. The ARN contains the arn:aws:ecr namespace, followed by the region of the repository, Amazon Web Services account ID of the repository owner, repository namespace, and repository name. For example, arn:aws:ecr:region:012345678910:repository-namespace/repository-name."})  # fmt: skip
    registry_id: Optional[str] = field(default=None, metadata={"description": "The Amazon Web Services account ID associated with the registry that contains the repository."})  # fmt: skip
    repository_uri: Optional[str] = field(default=None, metadata={"description": "The URI for the repository. You can use this URI for container image push and pull operations."})  # fmt: skip
    image_tag_mutability: Optional[str] = field(default=None, metadata={"description": "The tag mutability setting for the repository."})  # fmt: skip
    image_scanning_configuration: Optional[bool] = field(default=None, metadata={"description": "The image scanning configuration for a repository."})  # fmt: skip
    encryption_configuration: Optional[AwsEcrEncryptionConfiguration] = field(default=None, metadata={"description": "The encryption configuration for the repository. This determines how the contents of your repository are encrypted at rest."})  # fmt: skip


# @define(eq=False, slots=False)
# class AwsEcrImageIdentifier:
#     kind: ClassVar[str] = "aws_ecr_image_identifier"
#     mapping: ClassVar[Dict[str, Bender]] = {"image_digest": S("imageDigest"), "image_tag": S("imageTag")}
#     image_digest: Optional[str] = field(default=None, metadata={"description": "The sha256 digest of the image manifest."})  # fmt: skip
#     image_tag: Optional[str] = field(default=None, metadata={"description": "The tag used for the image."})  # fmt: skip
#
#
# @define(eq=False, slots=False)
# class AwsEcrImage(AwsResource):
#     kind: ClassVar[str] = "aws_ecr_image"
#     api_spec: ClassVar[AwsApiSpec] = AwsApiSpec("ecr", "describe-images", "images")
#     mapping: ClassVar[Dict[str, Bender]] = {
#         "id": S("id"),
#         "tags": S("Tags", default=[]) >> ToDict(),
#         "name": S("Tags", default=[]) >> TagsValue("Name"),
#         "registry_id": S("registryId"),
#         "repository_name": S("repositoryName"),
#         "image_id": S("imageId") >> Bend(AwsEcrImageIdentifier.mapping),
#         "image_manifest": S("imageManifest"),
#         "image_manifest_media_type": S("imageManifestMediaType"),
#     }
#     registry_id: Optional[str] = field(default=None, metadata={"description": "The Amazon Web Services account ID associated with the registry containing the image."})  # fmt: skip
#     repository_name: Optional[str] = field(default=None, metadata={"description": "The name of the repository associated with the image."})  # fmt: skip
#     image_id: Optional[AwsEcrImageIdentifier] = field(default=None, metadata={"description": "An object containing the image tag and image digest associated with an image."})  # fmt: skip
#     image_manifest: Optional[str] = field(default=None, metadata={"description": "The image manifest associated with the image."})  # fmt: skip
#     image_manifest_media_type: Optional[str] = field(default=None, metadata={"description": "The manifest media type of the image."})  # fmt: skip


resources: List[Type[AwsResource]] = [AwsEcrRepository]
