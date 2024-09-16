import logging
from datetime import datetime
from typing import ClassVar, Dict, Optional, List, Type, Any

from attrs import define, field

from fix_plugin_aws.aws_client import AwsClient
from fix_plugin_aws.resource.base import AwsResource, AwsApiSpec, GraphBuilder
from fixlib.baseresources import BaseAiResource, ModelReference
from fixlib.graph import Graph
from fixlib.json_bender import Bender, S, ForallBend, Bend
from fixlib.types import Json

log = logging.getLogger("fix.plugins.aws")
service_name = "bedrock"


class BedrockTaggable:
    def update_resource_tag(self, client: AwsClient, key: str, value: str) -> bool:
        if isinstance(self, AwsResource):
            if self.service_name() == "bedrock":
                client.call(
                    aws_service=self.service_name(),
                    action="tag-resource",
                    result_name=None,
                    resourceARN=self.arn,
                    tags=[{"key": key, "value": value}],
                )
            else:
                client.call(
                    aws_service=self.service_name(),
                    action="tag-resource",
                    result_name=None,
                    resourceArn=self.arn,
                    tags={key: value},
                )
            return True
        return False

    def delete_resource_tag(self, client: AwsClient, key: str) -> bool:
        if isinstance(self, AwsResource):
            if self.service_name() == "bedrock":
                client.call(
                    aws_service=self.service_name(),
                    action="untag-resource",
                    result_name=None,
                    resourceARN=self.arn,
                    tagKeys=[key],
                )
            else:
                client.call(
                    aws_service=self.service_name(),
                    action="untag-resource",
                    result_name=None,
                    resourceArn=self.arn,
                    tagKeys=[key],
                )
            return True
        return False

    @classmethod
    def called_collect_apis(cls) -> List[AwsApiSpec]:
        return [
            AwsApiSpec(cls.service_name(), "list-tags-for-resource"),
        ]

    @classmethod
    def called_mutator_apis(cls) -> List[AwsApiSpec]:
        return [
            AwsApiSpec(cls.service_name(), "tag-resource"),
            AwsApiSpec(cls.service_name(), "untag-resource"),
        ]

    @classmethod
    def service_name(cls) -> str:
        return service_name


@define(eq=False, slots=False)
class AwsBedrockValidationDataConfig:
    kind: ClassVar[str] = "aws_bedrock_validation_data_config"
    mapping: ClassVar[Dict[str, Bender]] = {"validators": S("validators", default=[]) >> ForallBend(S("s3Uri"))}
    validators: Optional[List[str]] = field(factory=list, metadata={"description": "Information about the validators."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockCustomModel(BedrockTaggable, BaseAiResource, AwsResource):
    kind: ClassVar[str] = "aws_bedrock_custom_model"
    kind_display: ClassVar[str] = "AWS Bedrock Custom Model"
    kind_description: ClassVar[str] = (
        "AWS Bedrock Custom Model enables users to create and train machine learning models "
        "tailored to specific needs, providing flexibility in model customization for a variety of applications."
    )
    kind_service: ClassVar[Optional[str]] = service_name
    aws_metadata: ClassVar[Dict[str, Any]] = {"provider_link_tpl": "https://{region_id}.console.aws.amazon.com/bedrock/home?region={region_id}#/custom-models/{name}"}  # fmt: skip
    reference_kinds: ClassVar[ModelReference] = {
        "successors": {"default": ["aws_bedrock_model_customization_job"]},
    }
    api_spec: ClassVar[AwsApiSpec] = AwsApiSpec("bedrock", "list-custom-models", "modelSummaries")
    mapping: ClassVar[Dict[str, Bender]] = {
        "id": S("modelArn"),
        "name": S("modelName"),
        "ctime": S("creationTime"),
        "arn": S("modelArn"),
        "model_arn": S("modelArn"),
        "model_name": S("modelName"),
        "job_name": S("jobName"),
        "job_arn": S("jobArn"),
        "base_model_arn": S("baseModelArn"),
        "customization_type": S("customizationType"),
        "model_kms_key_arn": S("modelKmsKeyArn"),
        "hyper_parameters": S("hyperParameters"),
        "training_data_config": S("trainingDataConfig", "s3Uri"),
        "validation_data_config": S("validationDataConfig") >> Bend(AwsBedrockValidationDataConfig.mapping),
        "output_data_config": S("outputDataConfig", "s3Uri"),
        "training_metrics": S("trainingMetrics", "trainingLoss"),
        "validation_metrics": S("validationMetrics", default=[]) >> ForallBend(S("validationLoss")),
        "creation_time": S("creationTime"),
    }
    model_arn: Optional[str] = field(default=None, metadata={"description": "Amazon Resource Name (ARN) associated with this model."})  # fmt: skip
    model_name: Optional[str] = field(default=None, metadata={"description": "Model name associated with this model."})  # fmt: skip
    job_name: Optional[str] = field(default=None, metadata={"description": "Job name associated with this model."})  # fmt: skip
    job_arn: Optional[str] = field(default=None, metadata={"description": "Job Amazon Resource Name (ARN) associated with this model."})  # fmt: skip
    base_model_arn: Optional[str] = field(default=None, metadata={"description": "Amazon Resource Name (ARN) of the base model."})  # fmt: skip
    customization_type: Optional[str] = field(default=None, metadata={"description": "The type of model customization."})  # fmt: skip
    model_kms_key_arn: Optional[str] = field(default=None, metadata={"description": "The custom model is encrypted at rest using this key."})  # fmt: skip
    hyper_parameters: Optional[Dict[str, str]] = field(default=None, metadata={"description": "Hyperparameter values associated with this model. For details on the format for different models, see Custom model hyperparameters."})  # fmt: skip
    training_data_config: Optional[str] = field(default=None, metadata={"description": "Contains information about the training dataset."})  # fmt: skip
    validation_data_config: Optional[AwsBedrockValidationDataConfig] = field(default=None, metadata={"description": "Contains information about the validation dataset."})  # fmt: skip
    output_data_config: Optional[str] = field(default=None, metadata={"description": "Output data configuration associated with this custom model."})  # fmt: skip
    training_metrics: Optional[float] = field(default=None, metadata={"description": "Contains training metrics from the job creation."})  # fmt: skip
    validation_metrics: Optional[List[float]] = field(factory=list, metadata={"description": "The validation metrics from the job creation."})  # fmt: skip
    creation_time: Optional[datetime] = field(default=None, metadata={"description": "Creation time of the model."})  # fmt: skip

    def delete_resource(self, client: AwsClient, graph: Graph) -> bool:
        client.call(
            aws_service=service_name,
            action="delete-custom-model",
            result_name=None,
            modelIdentifier=self.name,
        )
        return True

    @classmethod
    def called_mutator_apis(cls) -> List[AwsApiSpec]:
        return super().called_mutator_apis() + [AwsApiSpec(service_name, "delete-custom-model")]

    def connect_in_graph(self, builder: GraphBuilder, source: Json) -> None:
        if job_arn := self.job_arn:
            builder.add_edge(self, clazz=AwsBedrockModelCustomizationJob, id=job_arn)

    @classmethod
    def called_collect_apis(cls) -> List[AwsApiSpec]:
        return super().called_collect_apis() + [cls.api_spec, AwsApiSpec(service_name, "get-custom-model")]

    @classmethod
    def collect(cls: Type[AwsResource], json: List[Json], builder: GraphBuilder) -> None:
        def add_tags(job: AwsResource) -> None:
            tags = builder.client.list(
                service_name,
                "list-tags-for-resource",
                "tags",
                expected_errors=["ResourceNotFoundException"],
                resourceARN=job.arn,
            )
            if tags:
                for tag in tags:
                    job.tags.update({tag.get("key"): tag.get("value")})

        for js in json:
            for result in builder.client.list(
                service_name,
                "get-custom-model",
                modelIdentifier=js["modelArn"],
            ):
                if instance := cls.from_api(result, builder):
                    builder.add_node(instance, js)
                    builder.submit_work(service_name, add_tags, instance)


@define(eq=False, slots=False)
class AwsBedrockProvisionedModelThroughput(BedrockTaggable, BaseAiResource, AwsResource):
    kind: ClassVar[str] = "aws_bedrock_provisioned_model_throughput"
    kind_display: ClassVar[str] = "AWS Bedrock Provisioned Model Throughput"
    kind_description: ClassVar[str] = (
        "AWS Bedrock Provisioned Model Throughput manages the throughput capacity for machine learning models, "
        "ensuring consistent performance and scalability to handle varying workloads."
    )
    reference_kinds: ClassVar[ModelReference] = {
        "predecessors": {"default": [AwsBedrockCustomModel.kind]},
    }
    api_spec: ClassVar[AwsApiSpec] = AwsApiSpec(
        "bedrock", "list-provisioned-model-throughputs", "provisionedModelSummaries"
    )
    aws_metadata: ClassVar[Dict[str, Any]] = {"provider_link_tpl": "https://{region_id}.console.aws.amazon.com/bedrock/home?region={region_id}#/provisioned-throughput/{name}"}  # fmt: skip
    kind_service: ClassVar[Optional[str]] = service_name
    mapping: ClassVar[Dict[str, Bender]] = {
        "id": S("provisionedModelArn"),
        "name": S("provisionedModelName"),
        "ctime": S("creationTime"),
        "mtime": S("lastModifiedTime"),
        "provisioned_model_name": S("provisionedModelName"),
        "provisioned_model_arn": S("provisionedModelArn"),
        "model_arn": S("modelArn"),
        "desired_model_arn": S("desiredModelArn"),
        "foundation_model_arn": S("foundationModelArn"),
        "model_units": S("modelUnits"),
        "desired_model_units": S("desiredModelUnits"),
        "status": S("status"),
        "commitment_duration": S("commitmentDuration"),
        "commitment_expiration_time": S("commitmentExpirationTime"),
        "creation_time": S("creationTime"),
        "last_modified_time": S("lastModifiedTime"),
    }
    provisioned_model_name: Optional[str] = field(default=None, metadata={"description": "The name of the Provisioned Throughput."})  # fmt: skip
    provisioned_model_arn: Optional[str] = field(default=None, metadata={"description": "The Amazon Resource Name (ARN) of the Provisioned Throughput."})  # fmt: skip
    model_arn: Optional[str] = field(default=None, metadata={"description": "The Amazon Resource Name (ARN) of the model associated with the Provisioned Throughput."})  # fmt: skip
    desired_model_arn: Optional[str] = field(default=None, metadata={"description": "The Amazon Resource Name (ARN) of the model requested to be associated to this Provisioned Throughput. This value differs from the modelArn if updating hasn't completed."})  # fmt: skip
    foundation_model_arn: Optional[str] = field(default=None, metadata={"description": "The Amazon Resource Name (ARN) of the base model for which the Provisioned Throughput was created, or of the base model that the custom model for which the Provisioned Throughput was created was customized."})  # fmt: skip
    model_units: Optional[int] = field(default=None, metadata={"description": "The number of model units allocated to the Provisioned Throughput."})  # fmt: skip
    desired_model_units: Optional[int] = field(default=None, metadata={"description": "The number of model units that was requested to be allocated to the Provisioned Throughput."})  # fmt: skip
    status: Optional[str] = field(default=None, metadata={"description": "The status of the Provisioned Throughput."})  # fmt: skip
    commitment_duration: Optional[str] = field(default=None, metadata={"description": "The duration for which the Provisioned Throughput was committed."})  # fmt: skip
    commitment_expiration_time: Optional[datetime] = field(default=None, metadata={"description": "The timestamp for when the commitment term of the Provisioned Throughput expires."})  # fmt: skip
    creation_time: Optional[datetime] = field(default=None, metadata={"description": "The time that the Provisioned Throughput was created."})  # fmt: skip
    last_modified_time: Optional[datetime] = field(default=None, metadata={"description": "The time that the Provisioned Throughput was last modified."})  # fmt: skip

    def delete_resource(self, client: AwsClient, graph: Graph) -> bool:
        client.call(
            aws_service=service_name,
            action="delete-provisioned-model-throughput",
            result_name=None,
            provisionedModelId=self.safe_name,
        )
        return True

    @classmethod
    def called_mutator_apis(cls) -> List[AwsApiSpec]:
        return super().called_mutator_apis() + [AwsApiSpec(service_name, "delete-provisioned-model-throughput")]

    def connect_in_graph(self, builder: GraphBuilder, source: Json) -> None:
        if model_arn := self.model_arn:
            builder.add_edge(self, reverse=True, clazz=AwsBedrockCustomModel, id=model_arn)

    @classmethod
    def called_collect_apis(cls) -> List[AwsApiSpec]:
        return super().called_collect_apis() + [cls.api_spec]


@define(eq=False, slots=False)
class AwsBedrockGuardrailTopic:
    kind: ClassVar[str] = "aws_bedrock_guardrail_topic"
    mapping: ClassVar[Dict[str, Bender]] = {
        "name": S("name"),
        "definition": S("definition"),
        "examples": S("examples", default=[]),
        "type": S("type"),
    }
    name: Optional[str] = field(default=None, metadata={"description": "The name of the topic to deny."})  # fmt: skip
    definition: Optional[str] = field(default=None, metadata={"description": "A definition of the topic to deny."})  # fmt: skip
    examples: Optional[List[str]] = field(factory=list, metadata={"description": "A list of prompts, each of which is an example of a prompt that can be categorized as belonging to the topic."})  # fmt: skip
    type: Optional[str] = field(default=None, metadata={"description": "Specifies to deny the topic."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockGuardrailTopicPolicy:
    kind: ClassVar[str] = "aws_bedrock_guardrail_topic_policy"
    mapping: ClassVar[Dict[str, Bender]] = {
        "topics": S("topics", default=[]) >> ForallBend(AwsBedrockGuardrailTopic.mapping)
    }
    topics: Optional[List[AwsBedrockGuardrailTopic]] = field(factory=list, metadata={"description": "A list of policies related to topics that the guardrail should deny."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockGuardrailContentFilter:
    kind: ClassVar[str] = "aws_bedrock_guardrail_content_filter"
    mapping: ClassVar[Dict[str, Bender]] = {
        "type": S("type"),
        "input_strength": S("inputStrength"),
        "output_strength": S("outputStrength"),
    }
    type: Optional[str] = field(default=None, metadata={"description": "The harmful category that the content filter is applied to."})  # fmt: skip
    input_strength: Optional[str] = field(default=None, metadata={"description": "The strength of the content filter to apply to prompts. As you increase the filter strength, the likelihood of filtering harmful content increases and the probability of seeing harmful content in your application reduces."})  # fmt: skip
    output_strength: Optional[str] = field(default=None, metadata={"description": "The strength of the content filter to apply to model responses. As you increase the filter strength, the likelihood of filtering harmful content increases and the probability of seeing harmful content in your application reduces."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockGuardrailContentPolicy:
    kind: ClassVar[str] = "aws_bedrock_guardrail_content_policy"
    mapping: ClassVar[Dict[str, Bender]] = {
        "filters": S("filters", default=[]) >> ForallBend(AwsBedrockGuardrailContentFilter.mapping)
    }
    filters: Optional[List[AwsBedrockGuardrailContentFilter]] = field(factory=list, metadata={"description": "Contains the type of the content filter and how strongly it should apply to prompts and model responses."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockGuardrailWordPolicy:
    kind: ClassVar[str] = "aws_bedrock_guardrail_word_policy"
    mapping: ClassVar[Dict[str, Bender]] = {
        "words": S("words", default=[]) >> ForallBend(S("text")),
        "managed_word_lists": S("managedWordLists", default=[]) >> ForallBend(S("type")),
    }
    words: Optional[List[str]] = field(factory=list, metadata={"description": "A list of words configured for the guardrail."})  # fmt: skip
    managed_word_lists: Optional[List[str]] = field(factory=list, metadata={"description": "A list of managed words configured for the guardrail."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockGuardrailPiiEntity:
    kind: ClassVar[str] = "aws_bedrock_guardrail_pii_entity"
    mapping: ClassVar[Dict[str, Bender]] = {"type": S("type"), "action": S("action")}
    type: Optional[str] = field(default=None, metadata={"description": "The type of PII entity. For example, Social Security Number."})  # fmt: skip
    action: Optional[str] = field(default=None, metadata={"description": "The configured guardrail action when PII entity is detected."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockGuardrailRegex:
    kind: ClassVar[str] = "aws_bedrock_guardrail_regex"
    mapping: ClassVar[Dict[str, Bender]] = {
        "name": S("name"),
        "description": S("description"),
        "pattern": S("pattern"),
        "action": S("action"),
    }
    name: Optional[str] = field(default=None, metadata={"description": "The name of the regular expression for the guardrail."})  # fmt: skip
    description: Optional[str] = field(default=None, metadata={"description": "The description of the regular expression for the guardrail."})  # fmt: skip
    pattern: Optional[str] = field(default=None, metadata={"description": "The pattern of the regular expression configured for the guardrail."})  # fmt: skip
    action: Optional[str] = field(default=None, metadata={"description": "The action taken when a match to the regular expression is detected."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockGuardrailSensitiveInformationPolicy:
    kind: ClassVar[str] = "aws_bedrock_guardrail_sensitive_information_policy"
    mapping: ClassVar[Dict[str, Bender]] = {
        "pii_entities": S("piiEntities", default=[]) >> ForallBend(AwsBedrockGuardrailPiiEntity.mapping),
        "regexes": S("regexes", default=[]) >> ForallBend(AwsBedrockGuardrailRegex.mapping),
    }
    pii_entities: Optional[List[AwsBedrockGuardrailPiiEntity]] = field(factory=list, metadata={"description": "The list of PII entities configured for the guardrail."})  # fmt: skip
    regexes: Optional[List[AwsBedrockGuardrailRegex]] = field(factory=list, metadata={"description": "The list of regular expressions configured for the guardrail."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockGuardrailContextualGroundingFilter:
    kind: ClassVar[str] = "aws_bedrock_guardrail_contextual_grounding_filter"
    mapping: ClassVar[Dict[str, Bender]] = {"type": S("type"), "threshold": S("threshold")}
    type: Optional[str] = field(default=None, metadata={"description": "The filter type details for the guardrails contextual grounding filter."})  # fmt: skip
    threshold: Optional[float] = field(default=None, metadata={"description": "The threshold details for the guardrails contextual grounding filter."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockGuardrailContextualGroundingPolicy:
    kind: ClassVar[str] = "aws_bedrock_guardrail_contextual_grounding_policy"
    mapping: ClassVar[Dict[str, Bender]] = {
        "filters": S("filters", default=[]) >> ForallBend(AwsBedrockGuardrailContextualGroundingFilter.mapping)
    }
    filters: Optional[List[AwsBedrockGuardrailContextualGroundingFilter]] = field(factory=list, metadata={"description": "The filter details for the guardrails contextual grounding policy."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockGuardrail(BedrockTaggable, BaseAiResource, AwsResource):
    kind: ClassVar[str] = "aws_bedrock_guardrail"
    kind_display: ClassVar[str] = "AWS Bedrock Guardrail"
    kind_description: ClassVar[str] = (
        "AWS Bedrock Guardrail provides safety mechanisms and policies to ensure responsible use of machine learning models, "
        "helping to enforce compliance, security, and ethical standards."
    )
    api_spec: ClassVar[AwsApiSpec] = AwsApiSpec(
        "bedrock", "list-guardrails", "guardrails", expected_errors=["AccessDeniedException"]
    )
    aws_metadata: ClassVar[Dict[str, Any]] = {"provider_link_tpl": "https://{region_id}.console.aws.amazon.com/bedrock/home?region={region_id}#/guardrails/guardrail/{name}/{id}"}  # fmt: skip
    kind_service: ClassVar[Optional[str]] = service_name
    mapping: ClassVar[Dict[str, Bender]] = {
        "id": S("guardrailId"),
        "name": S("name"),
        "ctime": S("createdAt"),
        "mtime": S("updatedAt"),
        "arn": S("guardrailArn"),
        "description": S("description"),
        "guardrail_id": S("guardrailId"),
        "guardrail_arn": S("guardrailArn"),
        "version": S("version"),
        "status": S("status"),
        "topic_policy": S("topicPolicy") >> Bend(AwsBedrockGuardrailTopicPolicy.mapping),
        "content_policy": S("contentPolicy") >> Bend(AwsBedrockGuardrailContentPolicy.mapping),
        "word_policy": S("wordPolicy") >> Bend(AwsBedrockGuardrailWordPolicy.mapping),
        "sensitive_information_policy": S("sensitiveInformationPolicy")
        >> Bend(AwsBedrockGuardrailSensitiveInformationPolicy.mapping),
        "contextual_grounding_policy": S("contextualGroundingPolicy")
        >> Bend(AwsBedrockGuardrailContextualGroundingPolicy.mapping),
        "created_at": S("createdAt"),
        "updated_at": S("updatedAt"),
        "status_reasons": S("statusReasons", default=[]),
        "failure_recommendations": S("failureRecommendations", default=[]),
        "blocked_input_messaging": S("blockedInputMessaging"),
        "blocked_outputs_messaging": S("blockedOutputsMessaging"),
        "kms_key_arn": S("kmsKeyArn"),
    }
    description: Optional[str] = field(default=None, metadata={"description": "The description of the guardrail."})  # fmt: skip
    guardrail_id: Optional[str] = field(default=None, metadata={"description": "The unique identifier of the guardrail."})  # fmt: skip
    guardrail_arn: Optional[str] = field(default=None, metadata={"description": "The ARN of the guardrail."})  # fmt: skip
    version: Optional[str] = field(default=None, metadata={"description": "The version of the guardrail."})  # fmt: skip
    status: Optional[str] = field(default=None, metadata={"description": "The status of the guardrail."})  # fmt: skip
    topic_policy: Optional[AwsBedrockGuardrailTopicPolicy] = field(default=None, metadata={"description": "The topic policy that was configured for the guardrail."})  # fmt: skip
    content_policy: Optional[AwsBedrockGuardrailContentPolicy] = field(default=None, metadata={"description": "The content policy that was configured for the guardrail."})  # fmt: skip
    word_policy: Optional[AwsBedrockGuardrailWordPolicy] = field(default=None, metadata={"description": "The word policy that was configured for the guardrail."})  # fmt: skip
    sensitive_information_policy: Optional[AwsBedrockGuardrailSensitiveInformationPolicy] = field(default=None, metadata={"description": "The sensitive information policy that was configured for the guardrail."})  # fmt: skip
    contextual_grounding_policy: Optional[AwsBedrockGuardrailContextualGroundingPolicy] = field(default=None, metadata={"description": "The contextual grounding policy used in the guardrail."})  # fmt: skip
    created_at: Optional[datetime] = field(default=None, metadata={"description": "The date and time at which the guardrail was created."})  # fmt: skip
    updated_at: Optional[datetime] = field(default=None, metadata={"description": "The date and time at which the guardrail was updated."})  # fmt: skip
    status_reasons: Optional[List[str]] = field(factory=list, metadata={"description": "Appears if the status is FAILED. A list of reasons for why the guardrail failed to be created, updated, versioned, or deleted."})  # fmt: skip
    failure_recommendations: Optional[List[str]] = field(factory=list, metadata={"description": "Appears if the status of the guardrail is FAILED. A list of recommendations to carry out before retrying the request."})  # fmt: skip
    blocked_input_messaging: Optional[str] = field(default=None, metadata={"description": "The message that the guardrail returns when it blocks a prompt."})  # fmt: skip
    blocked_outputs_messaging: Optional[str] = field(default=None, metadata={"description": "The message that the guardrail returns when it blocks a model response."})  # fmt: skip
    kms_key_arn: Optional[str] = field(default=None, metadata={"description": "The ARN of the KMS key that encrypts the guardrail."})  # fmt: skip

    def delete_resource(self, client: AwsClient, graph: Graph) -> bool:
        client.call(
            aws_service=service_name,
            action="delete-guardrail",
            result_name=None,
            guardrailIdentifier=self.id or self.arn,
        )
        return True

    @classmethod
    def called_mutator_apis(cls) -> List[AwsApiSpec]:
        return super().called_mutator_apis() + [AwsApiSpec(service_name, "delete-guardrail")]

    @classmethod
    def called_collect_apis(cls) -> List[AwsApiSpec]:
        return super().called_collect_apis() + [cls.api_spec, AwsApiSpec(service_name, "get-guardrail")]

    @classmethod
    def collect(cls: Type[AwsResource], json: List[Json], builder: GraphBuilder) -> None:
        def add_tags(job: AwsResource) -> None:
            tags = builder.client.list(
                service_name,
                "list-tags-for-resource",
                "tags",
                expected_errors=["ResourceNotFoundException"],
                resourceARN=job.arn,
            )
            if tags:
                for tag in tags:
                    job.tags.update({tag.get("key"): tag.get("value")})

        for js in json:
            for result in builder.client.list(
                service_name,
                "get-guardrail",
                guardrailIdentifier=js["id"],
                guardrailVersion=js["version"],
            ):
                if instance := cls.from_api(result, builder):
                    builder.add_node(instance, js)
                    builder.submit_work(service_name, add_tags, instance)


@define(eq=False, slots=False)
class AwsBedrockVpcConfig:
    kind: ClassVar[str] = "aws_bedrock_vpc_config"
    mapping: ClassVar[Dict[str, Bender]] = {
        "subnet_ids": S("subnetIds", default=[]),
        "security_group_ids": S("securityGroupIds", default=[]),
    }
    subnet_ids: Optional[List[str]] = field(factory=list, metadata={"description": "VPC configuration subnets."})  # fmt: skip
    security_group_ids: Optional[List[str]] = field(factory=list, metadata={"description": "VPC configuration security group Ids."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockModelCustomizationJob(BedrockTaggable, BaseAiResource, AwsResource):
    kind: ClassVar[str] = "aws_bedrock_model_customization_job"
    kind_display: ClassVar[str] = "AWS Bedrock Model Customization Job"
    kind_description: ClassVar[str] = (
        "AWS Bedrock Model Customization Job is responsible for executing the processes involved in tailoring a machine learning model "
        "to specific datasets and tasks, optimizing the model for unique use cases."
    )
    api_spec: ClassVar[AwsApiSpec] = AwsApiSpec(
        "bedrock",
        "list-model-customization-jobs",
        "modelCustomizationJobSummaries",
        expected_errors=["ValidationException"],
    )
    kind_service: ClassVar[Optional[str]] = service_name
    aws_metadata: ClassVar[Dict[str, Any]] = {"provider_link_tpl": "https://{region_id}.console.aws.amazon.com/bedrock/home?region={region_id}#/custom-models/item/?arn={arn}"}  # fmt: skip
    mapping: ClassVar[Dict[str, Bender]] = {
        "id": S("jobArn"),
        "name": S("jobName"),
        "arn": S("jobArn"),
        "ctime": S("creationTime"),
        "mtime": S("lastModifiedTime"),
        "job_arn": S("jobArn"),
        "job_name": S("jobName"),
        "output_model_name": S("outputModelName"),
        "output_model_arn": S("outputModelArn"),
        "client_request_token": S("clientRequestToken"),
        "role_arn": S("roleArn"),
        "status": S("status"),
        "failure_message": S("failureMessage"),
        "creation_time": S("creationTime"),
        "last_modified_time": S("lastModifiedTime"),
        "end_time": S("endTime"),
        "base_model_arn": S("baseModelArn"),
        "hyper_parameters": S("hyperParameters"),
        "training_data_config": S("trainingDataConfig", "s3Uri"),
        "validation_data_config": S("validationDataConfig") >> Bend(AwsBedrockValidationDataConfig.mapping),
        "output_data_config": S("outputDataConfig", "s3Uri"),
        "customization_type": S("customizationType"),
        "output_model_kms_key_arn": S("outputModelKmsKeyArn"),
        "training_metrics": S("trainingMetrics", "trainingLoss"),
        "validation_metrics": S("validationMetrics", default=[]) >> ForallBend(S("validationLoss")),
        "vpc_config": S("vpcConfig") >> Bend(AwsBedrockVpcConfig.mapping),
    }
    job_arn: Optional[str] = field(default=None, metadata={"description": "The Amazon Resource Name (ARN) of the customization job."})  # fmt: skip
    job_name: Optional[str] = field(default=None, metadata={"description": "The name of the customization job."})  # fmt: skip
    output_model_name: Optional[str] = field(default=None, metadata={"description": "The name of the output model."})  # fmt: skip
    output_model_arn: Optional[str] = field(default=None, metadata={"description": "The Amazon Resource Name (ARN) of the output model."})  # fmt: skip
    client_request_token: Optional[str] = field(default=None, metadata={"description": "The token that you specified in the CreateCustomizationJob request."})  # fmt: skip
    role_arn: Optional[str] = field(default=None, metadata={"description": "The Amazon Resource Name (ARN) of the IAM role."})  # fmt: skip
    status: Optional[str] = field(default=None, metadata={"description": "The status of the job. A successful job transitions from in-progress to completed when the output model is ready to use. If the job failed, the failure message contains information about why the job failed."})  # fmt: skip
    failure_message: Optional[str] = field(default=None, metadata={"description": "Information about why the job failed."})  # fmt: skip
    creation_time: Optional[datetime] = field(default=None, metadata={"description": "Time that the resource was created."})  # fmt: skip
    last_modified_time: Optional[datetime] = field(default=None, metadata={"description": "Time that the resource was last modified."})  # fmt: skip
    end_time: Optional[datetime] = field(default=None, metadata={"description": "Time that the resource transitioned to terminal state."})  # fmt: skip
    base_model_arn: Optional[str] = field(default=None, metadata={"description": "Amazon Resource Name (ARN) of the base model."})  # fmt: skip
    hyper_parameters: Optional[Dict[str, str]] = field(default=None, metadata={"description": "The hyperparameter values for the job. For details on the format for different models, see Custom model hyperparameters."})  # fmt: skip
    training_data_config: Optional[str] = field(default=None, metadata={"description": "Contains information about the training dataset."})  # fmt: skip
    validation_data_config: Optional[AwsBedrockValidationDataConfig] = field(default=None, metadata={"description": "Contains information about the validation dataset."})  # fmt: skip
    output_data_config: Optional[str] = field(default=None, metadata={"description": "Output data configuration"})  # fmt: skip
    customization_type: Optional[str] = field(default=None, metadata={"description": "The type of model customization."})  # fmt: skip
    output_model_kms_key_arn: Optional[str] = field(default=None, metadata={"description": "The custom model is encrypted at rest using this key."})  # fmt: skip
    training_metrics: Optional[float] = field(default=None, metadata={"description": "Contains training metrics from the job creation."})  # fmt: skip
    validation_metrics: Optional[List[float]] = field(factory=list, metadata={"description": "The loss metric for each validator that you provided in the createjob request."})  # fmt: skip
    vpc_config: Optional[AwsBedrockVpcConfig] = field(default=None, metadata={"description": "VPC configuration for the custom model job."})  # fmt: skip

    @classmethod
    def called_collect_apis(cls) -> List[AwsApiSpec]:
        return super().called_collect_apis() + [cls.api_spec, AwsApiSpec(service_name, "get-model-customization-job")]

    @classmethod
    def collect(cls: Type[AwsResource], json: List[Json], builder: GraphBuilder) -> None:
        def add_tags(job: AwsResource) -> None:
            tags = builder.client.list(
                service_name,
                "list-tags-for-resource",
                "tags",
                expected_errors=["ResourceNotFoundException"],
                resourceARN=job.arn,
            )
            if tags:
                for tag in tags:
                    job.tags.update({tag.get("key"): tag.get("value")})

        for js in json:
            for result in builder.client.list(
                service_name,
                "get-model-customization-job",
                jobIdentifier=js["jobArn"],
            ):
                if instance := cls.from_api(result, builder):
                    builder.add_node(instance, js)
                    builder.submit_work(service_name, add_tags, instance)


@define(eq=False, slots=False)
class AwsBedrockEvaluationDataset:
    kind: ClassVar[str] = "aws_bedrock_evaluation_dataset"
    mapping: ClassVar[Dict[str, Bender]] = {"name": S("name"), "dataset_location": S("datasetLocation", "s3Uri")}
    name: Optional[str] = field(default=None, metadata={"description": "Used to specify supported built-in prompt datasets. Valid values are Builtin.Bold, Builtin.BoolQ, Builtin.NaturalQuestions, Builtin.Gigaword, Builtin.RealToxicityPrompts, Builtin.TriviaQa, Builtin.T-Rex, Builtin.WomensEcommerceClothingReviews and Builtin.Wikitext2."})  # fmt: skip
    dataset_location: Optional[str] = field(default=None, metadata={"description": "For custom prompt datasets, you must specify the location in Amazon S3 where the prompt dataset is saved."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockEvaluationDatasetMetricConfig:
    kind: ClassVar[str] = "aws_bedrock_evaluation_dataset_metric_config"
    mapping: ClassVar[Dict[str, Bender]] = {
        "task_type": S("taskType"),
        "dataset": S("dataset") >> Bend(AwsBedrockEvaluationDataset.mapping),
        "metric_names": S("metricNames", default=[]),
    }
    task_type: Optional[str] = field(default=None, metadata={"description": "The task type you want the model to carry out."})  # fmt: skip
    dataset: Optional[AwsBedrockEvaluationDataset] = field(default=None, metadata={"description": "Specifies the prompt dataset."})  # fmt: skip
    metric_names: Optional[List[str]] = field(factory=list, metadata={"description": "The names of the metrics used."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockAutomatedEvaluationConfig:
    kind: ClassVar[str] = "aws_bedrock_automated_evaluation_config"
    mapping: ClassVar[Dict[str, Bender]] = {
        "dataset_metric_configs": S("datasetMetricConfigs", default=[])
        >> ForallBend(AwsBedrockEvaluationDatasetMetricConfig.mapping)
    }
    dataset_metric_configs: Optional[List[AwsBedrockEvaluationDatasetMetricConfig]] = field(factory=list, metadata={"description": "Specifies the required elements for an automatic model evaluation job."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockHumanWorkflowConfig:
    kind: ClassVar[str] = "aws_bedrock_human_workflow_config"
    mapping: ClassVar[Dict[str, Bender]] = {
        "flow_definition_arn": S("flowDefinitionArn"),
        "instructions": S("instructions"),
    }
    flow_definition_arn: Optional[str] = field(default=None, metadata={"description": "The Amazon Resource Number (ARN) for the flow definition"})  # fmt: skip
    instructions: Optional[str] = field(default=None, metadata={"description": "Instructions for the flow definition"})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockHumanEvaluationCustomMetric:
    kind: ClassVar[str] = "aws_bedrock_human_evaluation_custom_metric"
    mapping: ClassVar[Dict[str, Bender]] = {
        "name": S("name"),
        "description": S("description"),
        "rating_method": S("ratingMethod"),
    }
    name: Optional[str] = field(default=None, metadata={"description": "The name of the metric. Your human evaluators will see this name in the evaluation UI."})  # fmt: skip
    description: Optional[str] = field(default=None, metadata={"description": "An optional description of the metric. Use this parameter to provide more details about the metric."})  # fmt: skip
    rating_method: Optional[str] = field(default=None, metadata={"description": "Choose how you want your human workers to evaluation your model. Valid values for rating methods are ThumbsUpDown, IndividualLikertScale,ComparisonLikertScale, ComparisonChoice, and ComparisonRank"})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockHumanEvaluationConfig:
    kind: ClassVar[str] = "aws_bedrock_human_evaluation_config"
    mapping: ClassVar[Dict[str, Bender]] = {
        "human_workflow_config": S("humanWorkflowConfig") >> Bend(AwsBedrockHumanWorkflowConfig.mapping),
        "custom_metrics": S("customMetrics", default=[]) >> ForallBend(AwsBedrockHumanEvaluationCustomMetric.mapping),
        "dataset_metric_configs": S("datasetMetricConfigs", default=[])
        >> ForallBend(AwsBedrockEvaluationDatasetMetricConfig.mapping),
    }
    human_workflow_config: Optional[AwsBedrockHumanWorkflowConfig] = field(default=None, metadata={"description": "The parameters of the human workflow."})  # fmt: skip
    custom_metrics: Optional[List[AwsBedrockHumanEvaluationCustomMetric]] = field(factory=list, metadata={"description": "A HumanEvaluationCustomMetric object. It contains the names the metrics, how the metrics are to be evaluated, an optional description."})  # fmt: skip
    dataset_metric_configs: Optional[List[AwsBedrockEvaluationDatasetMetricConfig]] = field(factory=list, metadata={"description": "Use to specify the metrics, task, and prompt dataset to be used in your model evaluation job."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockEvaluationConfig:
    kind: ClassVar[str] = "aws_bedrock_evaluation_config"
    mapping: ClassVar[Dict[str, Bender]] = {
        "automated": S("automated") >> Bend(AwsBedrockAutomatedEvaluationConfig.mapping),
        "human": S("human") >> Bend(AwsBedrockHumanEvaluationConfig.mapping),
    }
    automated: Optional[AwsBedrockAutomatedEvaluationConfig] = field(default=None, metadata={"description": "Used to specify an automated model evaluation job. See AutomatedEvaluationConfig to view the required parameters."})  # fmt: skip
    human: Optional[AwsBedrockHumanEvaluationConfig] = field(default=None, metadata={"description": "Used to specify a model evaluation job that uses human workers.See HumanEvaluationConfig to view the required parameters."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockEvaluationBedrockModel:
    kind: ClassVar[str] = "aws_bedrock_evaluation_bedrock_model"
    mapping: ClassVar[Dict[str, Bender]] = {
        "model_identifier": S("modelIdentifier"),
        "inference_params": S("inferenceParams"),
    }
    model_identifier: Optional[str] = field(default=None, metadata={"description": "The ARN of the Amazon Bedrock model specified."})  # fmt: skip
    inference_params: Optional[str] = field(default=None, metadata={"description": "Each Amazon Bedrock support different inference parameters that change how the model behaves during inference."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockEvaluationModelConfig:
    kind: ClassVar[str] = "aws_bedrock_evaluation_model_config"
    mapping: ClassVar[Dict[str, Bender]] = {
        "bedrock_model": S("bedrockModel") >> Bend(AwsBedrockEvaluationBedrockModel.mapping)
    }
    bedrock_model: Optional[AwsBedrockEvaluationBedrockModel] = field(default=None, metadata={"description": "Defines the Amazon Bedrock model and inference parameters you want used."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockEvaluationInferenceConfig:
    kind: ClassVar[str] = "aws_bedrock_evaluation_inference_config"
    mapping: ClassVar[Dict[str, Bender]] = {
        "models": S("models", default=[]) >> ForallBend(AwsBedrockEvaluationModelConfig.mapping)
    }
    models: Optional[List[AwsBedrockEvaluationModelConfig]] = field(factory=list, metadata={"description": "Used to specify the models."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockEvaluationJob(BedrockTaggable, BaseAiResource, AwsResource):
    kind: ClassVar[str] = "aws_bedrock_evaluation_job"
    kind_display: ClassVar[str] = "AWS Bedrock Evaluation Job"
    kind_description: ClassVar[str] = (
        "AWS Bedrock Evaluation Job assesses the performance of machine learning models, running test datasets and producing metrics "
        "that indicate the effectiveness of the model's predictions."
    )
    api_spec: ClassVar[AwsApiSpec] = AwsApiSpec(
        "bedrock", "list-evaluation-jobs", "jobSummaries", expected_errors=["AccessDeniedException"]
    )
    aws_metadata: ClassVar[Dict[str, Any]] = {}
    kind_service: ClassVar[Optional[str]] = service_name
    mapping: ClassVar[Dict[str, Bender]] = {
        "id": S("jobArn"),
        "name": S("jobName"),
        "arn": S("jobArn"),
        "ctime": S("creationTime"),
        "mtime": S("lastModifiedTime"),
        "job_name": S("jobName"),
        "status": S("status"),
        "job_arn": S("jobArn"),
        "job_description": S("jobDescription"),
        "role_arn": S("roleArn"),
        "customer_encryption_key_id": S("customerEncryptionKeyId"),
        "job_type": S("jobType"),
        "evaluation_config": S("evaluationConfig") >> Bend(AwsBedrockEvaluationConfig.mapping),
        "job_inference_config": S("inferenceConfig") >> Bend(AwsBedrockEvaluationInferenceConfig.mapping),
        "output_data_config": S("outputDataConfig", "s3Uri"),
        "creation_time": S("creationTime"),
        "last_modified_time": S("lastModifiedTime"),
        "failure_messages": S("failureMessages", default=[]),
    }
    job_name: Optional[str] = field(default=None, metadata={"description": "The name of the model evaluation job."})  # fmt: skip
    status: Optional[str] = field(default=None, metadata={"description": "The status of the model evaluation job."})  # fmt: skip
    job_arn: Optional[str] = field(default=None, metadata={"description": "The Amazon Resource Name (ARN) of the model evaluation job."})  # fmt: skip
    job_description: Optional[str] = field(default=None, metadata={"description": "The description of the model evaluation job."})  # fmt: skip
    role_arn: Optional[str] = field(default=None, metadata={"description": "The Amazon Resource Name (ARN) of the IAM service role used in the model evaluation job."})  # fmt: skip
    customer_encryption_key_id: Optional[str] = field(default=None, metadata={"description": "The Amazon Resource Name (ARN) of the customer managed key specified when the model evaluation job was created."})  # fmt: skip
    job_type: Optional[str] = field(default=None, metadata={"description": "The type of model evaluation job."})  # fmt: skip
    evaluation_config: Optional[AwsBedrockEvaluationConfig] = field(default=None, metadata={"description": "Contains details about the type of model evaluation job, the metrics used, the task type selected, the datasets used, and any custom metrics you defined."})  # fmt: skip
    job_inference_config: Optional[AwsBedrockEvaluationInferenceConfig] = field(default=None, metadata={"description": "Details about the models you specified in your model evaluation job."})  # fmt: skip
    output_data_config: Optional[str] = field(default=None, metadata={"description": "Amazon S3 location for where output data is saved."})  # fmt: skip
    creation_time: Optional[datetime] = field(default=None, metadata={"description": "When the model evaluation job was created."})  # fmt: skip
    last_modified_time: Optional[datetime] = field(default=None, metadata={"description": "When the model evaluation job was last modified."})  # fmt: skip
    failure_messages: Optional[List[str]] = field(factory=list, metadata={"description": "An array of strings the specify why the model evaluation job has failed."})  # fmt: skip

    @classmethod
    def called_collect_apis(cls) -> List[AwsApiSpec]:
        return super().called_collect_apis() + [cls.api_spec, AwsApiSpec(service_name, "get-evaluation-job")]

    @classmethod
    def collect(cls: Type[AwsResource], json: List[Json], builder: GraphBuilder) -> None:
        def add_tags(job: AwsResource) -> None:
            tags = builder.client.list(
                service_name,
                "list-tags-for-resource",
                "tags",
                expected_errors=["ResourceNotFoundException"],
                resourceARN=job.arn,
            )
            if tags:
                for tag in tags:
                    job.tags.update({tag.get("key"): tag.get("value")})

        for js in json:
            for result in builder.client.list(
                service_name,
                "get-evaluation-job",
                jobIdentifier=js["jobArn"],
            ):
                if instance := cls.from_api(result, builder):
                    builder.add_node(instance, js)
                    builder.submit_work(service_name, add_tags, instance)


@define(eq=False, slots=False)
class AwsBedrockGuardrailConfiguration:
    kind: ClassVar[str] = "aws_bedrock_guardrail_configuration"
    mapping: ClassVar[Dict[str, Bender]] = {
        "guardrail_identifier": S("guardrailIdentifier"),
        "guardrail_version": S("guardrailVersion"),
    }
    guardrail_identifier: Optional[str] = field(default=None, metadata={"description": "The unique identifier of the guardrail."})  # fmt: skip
    guardrail_version: Optional[str] = field(default=None, metadata={"description": "The version of the guardrail."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockMemoryConfiguration:
    kind: ClassVar[str] = "aws_bedrock_memory_configuration"
    mapping: ClassVar[Dict[str, Bender]] = {
        "enabled_memory_types": S("enabledMemoryTypes", default=[]),
        "storage_days": S("storageDays"),
    }
    enabled_memory_types: Optional[List[str]] = field(factory=list, metadata={"description": "The type of memory that is stored."})  # fmt: skip
    storage_days: Optional[int] = field(default=None, metadata={"description": "The number of days the agent is configured to retain the conversational context."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockInferenceConfiguration:
    kind: ClassVar[str] = "aws_bedrock_inference_configuration"
    mapping: ClassVar[Dict[str, Bender]] = {
        "maximum_length": S("maximumLength"),
        "stop_sequences": S("stopSequences", default=[]),
        "temperature": S("temperature"),
        "top_k": S("topK"),
        "top_p": S("topP"),
    }
    maximum_length: Optional[int] = field(default=None, metadata={"description": "The maximum number of tokens to allow in the generated response."})  # fmt: skip
    stop_sequences: Optional[List[str]] = field(factory=list, metadata={"description": "A list of stop sequences. A stop sequence is a sequence of characters that causes the model to stop generating the response."})  # fmt: skip
    temperature: Optional[float] = field(default=None, metadata={"description": "The likelihood of the model selecting higher-probability options while generating a response. A lower value makes the model more likely to choose higher-probability options, while a higher value makes the model more likely to choose lower-probability options."})  # fmt: skip
    top_k: Optional[int] = field(default=None, metadata={"description": "While generating a response, the model determines the probability of the following token at each point of generation. The value that you set for topK is the number of most-likely candidates from which the model chooses the next token in the sequence. For example, if you set topK to 50, the model selects the next token from among the top 50 most likely choices."})  # fmt: skip
    top_p: Optional[float] = field(default=None, metadata={"description": "While generating a response, the model determines the probability of the following token at each point of generation. The value that you set for Top P determines the number of most-likely candidates from which the model chooses the next token in the sequence. For example, if you set topP to 80, the model only selects the next token from the top 80% of the probability distribution of next tokens."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockPromptConfiguration:
    kind: ClassVar[str] = "aws_bedrock_prompt_configuration"
    mapping: ClassVar[Dict[str, Bender]] = {
        "base_prompt_template": S("basePromptTemplate"),
        "inference_configuration": S("inferenceConfiguration") >> Bend(AwsBedrockInferenceConfiguration.mapping),
        "parser_mode": S("parserMode"),
        "prompt_creation_mode": S("promptCreationMode"),
        "prompt_state": S("promptState"),
        "prompt_type": S("promptType"),
    }
    base_prompt_template: Optional[str] = field(default=None, metadata={"description": "Defines the prompt template with which to replace the default prompt template. You can use placeholder variables in the base prompt template to customize the prompt. For more information, see Prompt template placeholder variables. For more information, see Configure the prompt templates."})  # fmt: skip
    inference_configuration: Optional[AwsBedrockInferenceConfiguration] = field(default=None, metadata={"description": "Contains inference parameters to use when the agent invokes a foundation model in the part of the agent sequence defined by the promptType. For more information, see Inference parameters for foundation models."})  # fmt: skip
    parser_mode: Optional[str] = field(default=None, metadata={"description": "Specifies whether to override the default parser Lambda function when parsing the raw foundation model output in the part of the agent sequence defined by the promptType. If you set the field as OVERRIDEN, the overrideLambda field in the PromptOverrideConfiguration must be specified with the ARN of a Lambda function."})  # fmt: skip
    prompt_creation_mode: Optional[str] = field(default=None, metadata={"description": "Specifies whether to override the default prompt template for this promptType. Set this value to OVERRIDDEN to use the prompt that you provide in the basePromptTemplate. If you leave it as DEFAULT, the agent uses a default prompt template."})  # fmt: skip
    prompt_state: Optional[str] = field(default=None, metadata={"description": "Specifies whether to allow the agent to carry out the step specified in the promptType. If you set this value to DISABLED, the agent skips that step. The default state for each promptType is as follows.    PRE_PROCESSING – ENABLED     ORCHESTRATION – ENABLED     KNOWLEDGE_BASE_RESPONSE_GENERATION – ENABLED     POST_PROCESSING – DISABLED"})  # fmt: skip
    prompt_type: Optional[str] = field(default=None, metadata={"description": "The step in the agent sequence that this prompt configuration applies to."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockPromptOverrideConfiguration:
    kind: ClassVar[str] = "aws_bedrock_prompt_override_configuration"
    mapping: ClassVar[Dict[str, Bender]] = {
        "override_lambda": S("overrideLambda"),
        "prompt_configurations": S("promptConfigurations", default=[])
        >> ForallBend(AwsBedrockPromptConfiguration.mapping),
    }
    override_lambda: Optional[str] = field(default=None, metadata={"description": "The ARN of the Lambda function to use when parsing the raw foundation model output in parts of the agent sequence. If you specify this field, at least one of the promptConfigurations must contain a parserMode value that is set to OVERRIDDEN. For more information, see Parser Lambda function in Agents for Amazon Bedrock."})  # fmt: skip
    prompt_configurations: Optional[List[AwsBedrockPromptConfiguration]] = field(factory=list, metadata={"description": "Contains configurations to override a prompt template in one part of an agent sequence. For more information, see Advanced prompts."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockAgent(BedrockTaggable, BaseAiResource, AwsResource):
    kind: ClassVar[str] = "aws_bedrock_agent"
    kind_display: ClassVar[str] = "AWS Bedrock Agent"
    kind_description: ClassVar[str] = (
        "AWS Bedrock Agent is an intelligent service designed to facilitate communication with machine learning models, "
        "acting as a mediator between applications and model execution workflows."
    )
    reference_kinds: ClassVar[ModelReference] = {
        "successors": {
            "default": [AwsBedrockGuardrail.kind, "aws_bedrock_agent_version", "aws_bedrock_agent_knowledge_base"]
        },
    }
    aws_metadata: ClassVar[Dict[str, Any]] = {
        "provider_link_tpl": "https://{region_id}.console.aws.amazon.com/bedrock/home?region={region_id}#/agents/{id}"
    }
    kind_service: ClassVar[Optional[str]] = "bedrock-agent"
    api_spec: ClassVar[AwsApiSpec] = AwsApiSpec("bedrock-agent", "list-agents", "agentSummaries")
    mapping: ClassVar[Dict[str, Bender]] = {
        "id": S("agent", "agentId"),
        "name": S("agent", "agentName"),
        "ctime": S("agent", "createdAt"),
        "mtime": S("agent", "updatedAt"),
        "arn": S("agent", "agentArn"),
        "agent_arn": S("agent", "agentArn"),
        "agent_id": S("agent", "agentId"),
        "agent_name": S("agent", "agentName"),
        "agent_resource_role_arn": S("agent", "agentResourceRoleArn"),
        "agent_status": S("agent", "agentStatus"),
        "agent_version": S("agent", "agentVersion"),
        "client_token": S("agent", "clientToken"),
        "created_at": S("agent", "createdAt"),
        "customer_encryption_key_arn": S("agent", "customerEncryptionKeyArn"),
        "description": S("agent", "description"),
        "failure_reasons": S("agent", "failureReasons", default=[]),
        "foundation_model": S("agent", "foundationModel"),
        "guardrail_configuration": S("agent", "guardrailConfiguration")
        >> Bend(AwsBedrockGuardrailConfiguration.mapping),
        "idle_session_ttl_in_seconds": S("agent", "idleSessionTTLInSeconds"),
        "instruction": S("agent", "instruction"),
        "memory_configuration": S("agent", "memoryConfiguration") >> Bend(AwsBedrockMemoryConfiguration.mapping),
        "prepared_at": S("agent", "preparedAt"),
        "prompt_override_configuration": S("agent", "promptOverrideConfiguration")
        >> Bend(AwsBedrockPromptOverrideConfiguration.mapping),
        "agent_recommended_actions": S("agent", "recommendedActions", default=[]),
        "updated_at": S("agent", "updatedAt"),
    }
    agent_arn: Optional[str] = field(default=None, metadata={"description": "The Amazon Resource Name (ARN) of the agent."})  # fmt: skip
    agent_id: Optional[str] = field(default=None, metadata={"description": "The unique identifier of the agent."})  # fmt: skip
    agent_name: Optional[str] = field(default=None, metadata={"description": "The name of the agent."})  # fmt: skip
    agent_resource_role_arn: Optional[str] = field(default=None, metadata={"description": "The Amazon Resource Name (ARN) of the IAM role with permissions to invoke API operations on the agent."})  # fmt: skip
    agent_status: Optional[str] = field(default=None, metadata={"description": "The status of the agent and whether it is ready for use. The following statuses are possible:   CREATING – The agent is being created.   PREPARING – The agent is being prepared.   PREPARED – The agent is prepared and ready to be invoked.   NOT_PREPARED – The agent has been created but not yet prepared.   FAILED – The agent API operation failed.   UPDATING – The agent is being updated.   DELETING – The agent is being deleted."})  # fmt: skip
    agent_version: Optional[str] = field(default=None, metadata={"description": "The version of the agent."})  # fmt: skip
    client_token: Optional[str] = field(default=None, metadata={"description": "A unique, case-sensitive identifier to ensure that the API request completes no more than one time. If this token matches a previous request, Amazon Bedrock ignores the request, but does not return an error. For more information, see Ensuring idempotency."})  # fmt: skip
    created_at: Optional[datetime] = field(default=None, metadata={"description": "The time at which the agent was created."})  # fmt: skip
    customer_encryption_key_arn: Optional[str] = field(default=None, metadata={"description": "The Amazon Resource Name (ARN) of the KMS key that encrypts the agent."})  # fmt: skip
    description: Optional[str] = field(default=None, metadata={"description": "The description of the agent."})  # fmt: skip
    failure_reasons: Optional[List[str]] = field(factory=list, metadata={"description": "Contains reasons that the agent-related API that you invoked failed."})  # fmt: skip
    foundation_model: Optional[str] = field(default=None, metadata={"description": "The foundation model used for orchestration by the agent."})  # fmt: skip
    guardrail_configuration: Optional[AwsBedrockGuardrailConfiguration] = field(default=None, metadata={"description": "Details about the guardrail associated with the agent."})  # fmt: skip
    idle_session_ttl_in_seconds: Optional[int] = field(default=None, metadata={"description": "The number of seconds for which Amazon Bedrock keeps information about a user's conversation with the agent. A user interaction remains active for the amount of time specified. If no conversation occurs during this time, the session expires and Amazon Bedrock deletes any data provided before the timeout."})  # fmt: skip
    instruction: Optional[str] = field(default=None, metadata={"description": "Instructions that tell the agent what it should do and how it should interact with users."})  # fmt: skip
    memory_configuration: Optional[AwsBedrockMemoryConfiguration] = field(default=None, metadata={"description": "Contains memory configuration for the agent."})  # fmt: skip
    prepared_at: Optional[datetime] = field(default=None, metadata={"description": "The time at which the agent was last prepared."})  # fmt: skip
    prompt_override_configuration: Optional[AwsBedrockPromptOverrideConfiguration] = field(default=None, metadata={"description": "Contains configurations to override prompt templates in different parts of an agent sequence. For more information, see Advanced prompts."})  # fmt: skip
    agent_recommended_actions: Optional[List[str]] = field(factory=list, metadata={"description": "Contains recommended actions to take for the agent-related API that you invoked to succeed."})  # fmt: skip
    updated_at: Optional[datetime] = field(default=None, metadata={"description": "The time at which the agent was last updated."})  # fmt: skip

    def delete_resource(self, client: AwsClient, graph: Graph) -> bool:
        client.call(
            aws_service="bedrock-agent",
            action="delete-agent",
            result_name=None,
            agentId=self.id,
        )
        return True

    @classmethod
    def called_mutator_apis(cls) -> List[AwsApiSpec]:
        return super().called_mutator_apis() + [AwsApiSpec("bedrock-agent", "delete-agent")]

    def connect_in_graph(self, builder: GraphBuilder, source: Json) -> None:
        if (g_configuration := self.guardrail_configuration) and (g_id := g_configuration.guardrail_identifier):
            builder.add_edge(self, clazz=AwsBedrockGuardrail, id=g_id)

    @classmethod
    def called_collect_apis(cls) -> List[AwsApiSpec]:
        return super().called_collect_apis() + [cls.api_spec, AwsApiSpec("bedrock-agent", "get-agent")]

    @classmethod
    def service_name(cls) -> str:
        return "bedrock-agent"

    @classmethod
    def collect(cls: Type[AwsResource], json: List[Json], builder: GraphBuilder) -> None:
        def add_tags(agent: AwsResource) -> None:
            tags = builder.client.list(
                "bedrock-agent",
                "list-tags-for-resource",
                "tags",
                expected_errors=["ResourceNotFoundException"],
                resourceArn=agent.arn,
            )
            if tags:
                agent.tags.update(tags[0])

        def collect_agent_versions(agent: AwsBedrockAgent) -> None:
            if not agent.agent_version:
                return
            for result in builder.client.list(
                "bedrock-agent",
                "get-agent-version",
                agentId=agent.id,
                agentVersion=agent.agent_version,
            ):
                if instance := AwsBedrockAgentVersion.from_api(result, builder):
                    builder.add_node(instance, js)
                    builder.submit_work("bedrock-agent", add_tags, instance)

        def collect_knowledge_bases(agent: AwsBedrockAgent) -> None:
            if not agent.agent_version:
                return
            for result in builder.client.list(
                "bedrock-agent",
                "list-knowledge-bases",
                "agentKnowledgeBaseSummaries",
                agentId=agent.id,
                agentVersion=agent.agent_version,
            ):
                if instance := AwsBedrockAgentKnowledgeBase.from_api(result, builder):
                    builder.add_node(instance, js)
                    builder.submit_work("bedrock-agent", add_tags, instance)

        for js in json:
            for result in builder.client.list(
                "bedrock-agent",
                "get-agent",
                agentId=js["agentId"],
            ):
                if instance := cls.from_api(result, builder):
                    builder.add_node(instance, js)
                    builder.submit_work("bedrock-agent", add_tags, instance)
                    builder.submit_work("bedrock-agent", collect_agent_versions, instance)
                    builder.submit_work("bedrock-agent", collect_knowledge_bases, instance)


@define(eq=False, slots=False)
class AwsBedrockAgentVersion(BedrockTaggable, BaseAiResource, AwsResource):
    kind: ClassVar[str] = "aws_bedrock_agent_version"
    kind_display: ClassVar[str] = "AWS Bedrock Agent Version"
    kind_description: ClassVar[str] = (
        "AWS Bedrock Agent Version refers to a specific iteration of the Bedrock Agent, ensuring compatibility "
        "and enhancements across different versions of the agent for improved functionality."
    )
    kind_service: ClassVar[Optional[str]] = "bedrock-agent"
    aws_metadata: ClassVar[Dict[str, Any]] = {
        "provider_link_tpl": "https://{region_id}.console.aws.amazon.com/bedrock/home?region={region_id}#/agents/{id}/versions/{version}"
    }
    # Collected via AwsBedrockAgent()
    mapping: ClassVar[Dict[str, Bender]] = {
        "id": S("agentVersion", "agentId"),
        "name": S("agentVersion", "agentName"),
        "ctime": S("agentVersion", "createdAt"),
        "mtime": S("agentVersion", "updatedAt"),
        "arn": S("agentVersion", "agentArn"),
        "agent_arn": S("agentVersion", "agentArn"),
        "agent_id": S("agentVersion", "agentId"),
        "agent_name": S("agentVersion", "agentName"),
        "agent_resource_role_arn": S("agentVersion", "agentResourceRoleArn"),
        "agent_status": S("agentVersion", "agentStatus"),
        "created_at": S("agentVersion", "createdAt"),
        "customer_encryption_key_arn": S("agentVersion", "customerEncryptionKeyArn"),
        "description": S("agentVersion", "description"),
        "failure_reasons": S("agentVersion", "failureReasons", default=[]),
        "foundation_model": S("agentVersion", "foundationModel"),
        "guardrail_configuration": S("agentVersion", "guardrailConfiguration")
        >> Bend(AwsBedrockGuardrailConfiguration.mapping),
        "idle_session_ttl_in_seconds": S("agentVersion", "idleSessionTTLInSeconds"),
        "instruction": S("agentVersion", "instruction"),
        "memory_configuration": S("agentVersion", "memoryConfiguration") >> Bend(AwsBedrockMemoryConfiguration.mapping),
        "prompt_override_configuration": S("agentVersion", "promptOverrideConfiguration")
        >> Bend(AwsBedrockPromptOverrideConfiguration.mapping),
        "agent_recommended_actions": S("agentVersion", "recommendedActions", default=[]),
        "updated_at": S("agentVersion", "updatedAt"),
        "version": S("agentVersion", "version"),
    }
    agent_arn: Optional[str] = field(default=None, metadata={"description": "The Amazon Resource Name (ARN) of the agent that the version belongs to."})  # fmt: skip
    agent_id: Optional[str] = field(default=None, metadata={"description": "The unique identifier of the agent that the version belongs to."})  # fmt: skip
    agent_name: Optional[str] = field(default=None, metadata={"description": "The name of the agent that the version belongs to."})  # fmt: skip
    agent_resource_role_arn: Optional[str] = field(default=None, metadata={"description": "The Amazon Resource Name (ARN) of the IAM role with permissions to invoke API operations on the agent."})  # fmt: skip
    agent_status: Optional[str] = field(default=None, metadata={"description": "The status of the agent that the version belongs to."})  # fmt: skip
    created_at: Optional[datetime] = field(default=None, metadata={"description": "The time at which the version was created."})  # fmt: skip
    customer_encryption_key_arn: Optional[str] = field(default=None, metadata={"description": "The Amazon Resource Name (ARN) of the KMS key that encrypts the agent."})  # fmt: skip
    description: Optional[str] = field(default=None, metadata={"description": "The description of the version."})  # fmt: skip
    failure_reasons: Optional[List[str]] = field(factory=list, metadata={"description": "A list of reasons that the API operation on the version failed."})  # fmt: skip
    foundation_model: Optional[str] = field(default=None, metadata={"description": "The foundation model that the version invokes."})  # fmt: skip
    guardrail_configuration: Optional[AwsBedrockGuardrailConfiguration] = field(default=None, metadata={"description": "Details about the guardrail associated with the agent."})  # fmt: skip
    idle_session_ttl_in_seconds: Optional[int] = field(default=None, metadata={"description": "The number of seconds for which Amazon Bedrock keeps information about a user's conversation with the agent. A user interaction remains active for the amount of time specified. If no conversation occurs during this time, the session expires and Amazon Bedrock deletes any data provided before the timeout."})  # fmt: skip
    instruction: Optional[str] = field(default=None, metadata={"description": "The instructions provided to the agent."})  # fmt: skip
    memory_configuration: Optional[AwsBedrockMemoryConfiguration] = field(default=None, metadata={"description": "Contains details of the memory configuration on the version of the agent."})  # fmt: skip
    prompt_override_configuration: Optional[AwsBedrockPromptOverrideConfiguration] = field(default=None, metadata={"description": "Contains configurations to override prompt templates in different parts of an agent sequence. For more information, see Advanced prompts."})  # fmt: skip
    agent_recommended_actions: Optional[List[str]] = field(factory=list, metadata={"description": "A list of recommended actions to take for the failed API operation on the version to succeed."})  # fmt: skip
    updated_at: Optional[datetime] = field(default=None, metadata={"description": "The time at which the version was last updated."})  # fmt: skip
    version: Optional[str] = field(default=None, metadata={"description": "The version number."})  # fmt: skip

    def delete_resource(self, client: AwsClient, graph: Graph) -> bool:
        client.call(
            aws_service="bedrock-agent",
            action="delete-agent-version",
            result_name=None,
            agentId=self.agent_id,
            agentVersion=self.version,
        )
        return True

    @classmethod
    def called_mutator_apis(cls) -> List[AwsApiSpec]:
        return super().called_mutator_apis() + [AwsApiSpec("bedrock-agent", "delete-agent-version")]

    @classmethod
    def called_collect_apis(cls) -> List[AwsApiSpec]:
        return super().called_collect_apis() + [AwsApiSpec("bedrock-agent", "get-agent-version")]

    @classmethod
    def service_name(cls) -> str:
        return "bedrock-agent"


@define(eq=False, slots=False)
class AwsBedrockEmbeddingModelConfiguration:
    kind: ClassVar[str] = "aws_bedrock_embedding_model_configuration"
    mapping: ClassVar[Dict[str, Bender]] = {
        "bedrock_embedding_model_configuration": S("bedrockEmbeddingModelConfiguration", "dimensions")
    }
    bedrock_embedding_model_configuration: Optional[int] = field(default=None, metadata={"description": "The vector configuration details on the Bedrock embeddings model."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockVectorKnowledgeBaseConfiguration:
    kind: ClassVar[str] = "aws_bedrock_vector_knowledge_base_configuration"
    mapping: ClassVar[Dict[str, Bender]] = {
        "embedding_model_arn": S("embeddingModelArn"),
        "embedding_model_configuration": S("embeddingModelConfiguration")
        >> Bend(AwsBedrockEmbeddingModelConfiguration.mapping),
    }
    embedding_model_arn: Optional[str] = field(default=None, metadata={"description": "The Amazon Resource Name (ARN) of the model used to create vector embeddings for the knowledge base."})  # fmt: skip
    embedding_model_configuration: Optional[AwsBedrockEmbeddingModelConfiguration] = field(default=None, metadata={"description": "The embeddings model configuration details for the vector model used in Knowledge Base."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockKnowledgeBaseConfiguration:
    kind: ClassVar[str] = "aws_bedrock_knowledge_base_configuration"
    mapping: ClassVar[Dict[str, Bender]] = {
        "type": S("type"),
        "vector_knowledge_base_configuration": S("vectorKnowledgeBaseConfiguration")
        >> Bend(AwsBedrockVectorKnowledgeBaseConfiguration.mapping),
    }
    type: Optional[str] = field(default=None, metadata={"description": "The type of data that the data source is converted into for the knowledge base."})  # fmt: skip
    vector_knowledge_base_configuration: Optional[AwsBedrockVectorKnowledgeBaseConfiguration] = field(default=None, metadata={"description": "Contains details about the embeddings model that'sused to convert the data source."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockMongoDbAtlasFieldMapping:
    kind: ClassVar[str] = "aws_bedrock_mongo_db_atlas_field_mapping"
    mapping: ClassVar[Dict[str, Bender]] = {
        "metadata_field": S("metadataField"),
        "text_field": S("textField"),
        "vector_field": S("vectorField"),
    }
    metadata_field: Optional[str] = field(default=None, metadata={"description": "The name of the field in which Amazon Bedrock stores metadata about the vector store."})  # fmt: skip
    text_field: Optional[str] = field(default=None, metadata={"description": "The name of the field in which Amazon Bedrock stores the raw text from your data. The text is split according to the chunking strategy you choose."})  # fmt: skip
    vector_field: Optional[str] = field(default=None, metadata={"description": "The name of the field in which Amazon Bedrock stores the vector embeddings for your data sources."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockMongoDbAtlasConfiguration:
    kind: ClassVar[str] = "aws_bedrock_mongo_db_atlas_configuration"
    mapping: ClassVar[Dict[str, Bender]] = {
        "collection_name": S("collectionName"),
        "credentials_secret_arn": S("credentialsSecretArn"),
        "database_name": S("databaseName"),
        "endpoint": S("endpoint"),
        "endpoint_service_name": S("endpointServiceName"),
        "field_mapping": S("fieldMapping") >> Bend(AwsBedrockMongoDbAtlasFieldMapping.mapping),
        "vector_index_name": S("vectorIndexName"),
    }
    collection_name: Optional[str] = field(default=None, metadata={"description": "The collection name of the knowledge base in MongoDB Atlas."})  # fmt: skip
    credentials_secret_arn: Optional[str] = field(default=None, metadata={"description": "The Amazon Resource Name (ARN) of the secret that you created in Secrets Manager that contains user credentials for your MongoDB Atlas cluster."})  # fmt: skip
    database_name: Optional[str] = field(default=None, metadata={"description": "The database name in your MongoDB Atlas cluster for your knowledge base."})  # fmt: skip
    endpoint: Optional[str] = field(default=None, metadata={"description": "The endpoint URL of your MongoDB Atlas cluster for your knowledge base."})  # fmt: skip
    endpoint_service_name: Optional[str] = field(default=None, metadata={"description": "The name of the VPC endpoint service in your account that is connected to your MongoDB Atlas cluster."})  # fmt: skip
    field_mapping: Optional[AwsBedrockMongoDbAtlasFieldMapping] = field(default=None, metadata={"description": "Contains the names of the fields to which to map information about the vector store."})  # fmt: skip
    vector_index_name: Optional[str] = field(default=None, metadata={"description": "The name of the MongoDB Atlas vector search index."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockOpenSearchServerlessFieldMapping:
    kind: ClassVar[str] = "aws_bedrock_open_search_serverless_field_mapping"
    mapping: ClassVar[Dict[str, Bender]] = {
        "metadata_field": S("metadataField"),
        "text_field": S("textField"),
        "vector_field": S("vectorField"),
    }
    metadata_field: Optional[str] = field(default=None, metadata={"description": "The name of the field in which Amazon Bedrock stores metadata about the vector store."})  # fmt: skip
    text_field: Optional[str] = field(default=None, metadata={"description": "The name of the field in which Amazon Bedrock stores the raw text from your data. The text is split according to the chunking strategy you choose."})  # fmt: skip
    vector_field: Optional[str] = field(default=None, metadata={"description": "The name of the field in which Amazon Bedrock stores the vector embeddings for your data sources."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockOpenSearchServerlessConfiguration:
    kind: ClassVar[str] = "aws_bedrock_open_search_serverless_configuration"
    mapping: ClassVar[Dict[str, Bender]] = {
        "collection_arn": S("collectionArn"),
        "field_mapping": S("fieldMapping") >> Bend(AwsBedrockOpenSearchServerlessFieldMapping.mapping),
        "vector_index_name": S("vectorIndexName"),
    }
    collection_arn: Optional[str] = field(default=None, metadata={"description": "The Amazon Resource Name (ARN) of the OpenSearch Service vector store."})  # fmt: skip
    field_mapping: Optional[AwsBedrockOpenSearchServerlessFieldMapping] = field(default=None, metadata={"description": "Contains the names of the fields to which to map information about the vector store."})  # fmt: skip
    vector_index_name: Optional[str] = field(default=None, metadata={"description": "The name of the vector store."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockPineconeFieldMapping:
    kind: ClassVar[str] = "aws_bedrock_pinecone_field_mapping"
    mapping: ClassVar[Dict[str, Bender]] = {"metadata_field": S("metadataField"), "text_field": S("textField")}
    metadata_field: Optional[str] = field(default=None, metadata={"description": "The name of the field in which Amazon Bedrock stores metadata about the vector store."})  # fmt: skip
    text_field: Optional[str] = field(default=None, metadata={"description": "The name of the field in which Amazon Bedrock stores the raw text from your data. The text is split according to the chunking strategy you choose."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockPineconeConfiguration:
    kind: ClassVar[str] = "aws_bedrock_pinecone_configuration"
    mapping: ClassVar[Dict[str, Bender]] = {
        "connection_string": S("connectionString"),
        "credentials_secret_arn": S("credentialsSecretArn"),
        "field_mapping": S("fieldMapping") >> Bend(AwsBedrockPineconeFieldMapping.mapping),
        "namespace": S("namespace"),
    }
    connection_string: Optional[str] = field(default=None, metadata={"description": "The endpoint URL for your index management page."})  # fmt: skip
    credentials_secret_arn: Optional[str] = field(default=None, metadata={"description": "The Amazon Resource Name (ARN) of the secret that you created in Secrets Manager that is linked to your Pinecone API key."})  # fmt: skip
    field_mapping: Optional[AwsBedrockPineconeFieldMapping] = field(default=None, metadata={"description": "Contains the names of the fields to which to map information about the vector store."})  # fmt: skip
    namespace: Optional[str] = field(default=None, metadata={"description": "The namespace to be used to write new data to your database."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockRdsFieldMapping:
    kind: ClassVar[str] = "aws_bedrock_rds_field_mapping"
    mapping: ClassVar[Dict[str, Bender]] = {
        "metadata_field": S("metadataField"),
        "primary_key_field": S("primaryKeyField"),
        "text_field": S("textField"),
        "vector_field": S("vectorField"),
    }
    metadata_field: Optional[str] = field(default=None, metadata={"description": "The name of the field in which Amazon Bedrock stores metadata about the vector store."})  # fmt: skip
    primary_key_field: Optional[str] = field(default=None, metadata={"description": "The name of the field in which Amazon Bedrock stores the ID for each entry."})  # fmt: skip
    text_field: Optional[str] = field(default=None, metadata={"description": "The name of the field in which Amazon Bedrock stores the raw text from your data. The text is split according to the chunking strategy you choose."})  # fmt: skip
    vector_field: Optional[str] = field(default=None, metadata={"description": "The name of the field in which Amazon Bedrock stores the vector embeddings for your data sources."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockRdsConfiguration:
    kind: ClassVar[str] = "aws_bedrock_rds_configuration"
    mapping: ClassVar[Dict[str, Bender]] = {
        "credentials_secret_arn": S("credentialsSecretArn"),
        "database_name": S("databaseName"),
        "field_mapping": S("fieldMapping") >> Bend(AwsBedrockRdsFieldMapping.mapping),
        "resource_arn": S("resourceArn"),
        "table_name": S("tableName"),
    }
    credentials_secret_arn: Optional[str] = field(default=None, metadata={"description": "The Amazon Resource Name (ARN) of the secret that you created in Secrets Manager that is linked to your Amazon RDS database."})  # fmt: skip
    database_name: Optional[str] = field(default=None, metadata={"description": "The name of your Amazon RDS database."})  # fmt: skip
    field_mapping: Optional[AwsBedrockRdsFieldMapping] = field(default=None, metadata={"description": "Contains the names of the fields to which to map information about the vector store."})  # fmt: skip
    resource_arn: Optional[str] = field(default=None, metadata={"description": "The Amazon Resource Name (ARN) of the vector store."})  # fmt: skip
    table_name: Optional[str] = field(default=None, metadata={"description": "The name of the table in the database."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockRedisEnterpriseCloudFieldMapping:
    kind: ClassVar[str] = "aws_bedrock_redis_enterprise_cloud_field_mapping"
    mapping: ClassVar[Dict[str, Bender]] = {
        "metadata_field": S("metadataField"),
        "text_field": S("textField"),
        "vector_field": S("vectorField"),
    }
    metadata_field: Optional[str] = field(default=None, metadata={"description": "The name of the field in which Amazon Bedrock stores metadata about the vector store."})  # fmt: skip
    text_field: Optional[str] = field(default=None, metadata={"description": "The name of the field in which Amazon Bedrock stores the raw text from your data. The text is split according to the chunking strategy you choose."})  # fmt: skip
    vector_field: Optional[str] = field(default=None, metadata={"description": "The name of the field in which Amazon Bedrock stores the vector embeddings for your data sources."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockRedisEnterpriseCloudConfiguration:
    kind: ClassVar[str] = "aws_bedrock_redis_enterprise_cloud_configuration"
    mapping: ClassVar[Dict[str, Bender]] = {
        "credentials_secret_arn": S("credentialsSecretArn"),
        "endpoint": S("endpoint"),
        "field_mapping": S("fieldMapping") >> Bend(AwsBedrockRedisEnterpriseCloudFieldMapping.mapping),
        "vector_index_name": S("vectorIndexName"),
    }
    credentials_secret_arn: Optional[str] = field(default=None, metadata={"description": "The Amazon Resource Name (ARN) of the secret that you created in Secrets Manager that is linked to your Redis Enterprise Cloud database."})  # fmt: skip
    endpoint: Optional[str] = field(default=None, metadata={"description": "The endpoint URL of the Redis Enterprise Cloud database."})  # fmt: skip
    field_mapping: Optional[AwsBedrockRedisEnterpriseCloudFieldMapping] = field(default=None, metadata={"description": "Contains the names of the fields to which to map information about the vector store."})  # fmt: skip
    vector_index_name: Optional[str] = field(default=None, metadata={"description": "The name of the vector index."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockStorageConfiguration:
    kind: ClassVar[str] = "aws_bedrock_storage_configuration"
    mapping: ClassVar[Dict[str, Bender]] = {
        "mongo_db_atlas_configuration": S("mongoDbAtlasConfiguration")
        >> Bend(AwsBedrockMongoDbAtlasConfiguration.mapping),
        "opensearch_serverless_configuration": S("opensearchServerlessConfiguration")
        >> Bend(AwsBedrockOpenSearchServerlessConfiguration.mapping),
        "pinecone_configuration": S("pineconeConfiguration") >> Bend(AwsBedrockPineconeConfiguration.mapping),
        "rds_configuration": S("rdsConfiguration") >> Bend(AwsBedrockRdsConfiguration.mapping),
        "redis_enterprise_cloud_configuration": S("redisEnterpriseCloudConfiguration")
        >> Bend(AwsBedrockRedisEnterpriseCloudConfiguration.mapping),
        "type": S("type"),
    }
    mongo_db_atlas_configuration: Optional[AwsBedrockMongoDbAtlasConfiguration] = field(default=None, metadata={"description": "Contains the storage configuration of the knowledge base in MongoDB Atlas."})  # fmt: skip
    opensearch_serverless_configuration: Optional[AwsBedrockOpenSearchServerlessConfiguration] = field(default=None, metadata={"description": "Contains the storage configuration of the knowledge base in Amazon OpenSearch Service."})  # fmt: skip
    pinecone_configuration: Optional[AwsBedrockPineconeConfiguration] = field(default=None, metadata={"description": "Contains the storage configuration of the knowledge base in Pinecone."})  # fmt: skip
    rds_configuration: Optional[AwsBedrockRdsConfiguration] = field(default=None, metadata={"description": "Contains details about the storage configuration of the knowledge base in Amazon RDS. For more information, see Create a vector index in Amazon RDS."})  # fmt: skip
    redis_enterprise_cloud_configuration: Optional[AwsBedrockRedisEnterpriseCloudConfiguration] = field(default=None, metadata={"description": "Contains the storage configuration of the knowledge base in Redis Enterprise Cloud."})  # fmt: skip
    type: Optional[str] = field(default=None, metadata={"description": "The vector store service in which the knowledge base is stored."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockAgentKnowledgeBase(BedrockTaggable, BaseAiResource, AwsResource):
    kind: ClassVar[str] = "aws_bedrock_agent_knowledge_base"
    kind_display: ClassVar[str] = "AWS Bedrock Agent Knowledge Base"
    kind_description: ClassVar[str] = (
        "AWS Bedrock Agent Knowledge Base contains the knowledge resources that the Bedrock Agent relies on "
        "to provide accurate responses and perform tasks based on learned information."
    )
    kind_service: ClassVar[Optional[str]] = "bedrock-agent"
    aws_metadata: ClassVar[Dict[str, Any]] = {
        "provider_link_tpl": "https://{region_id}.console.aws.amazon.com/bedrock/home?region={region_id}#/knowledge-bases/knowledge-base/{name}/{id}/0"
    }
    # Collected via AwsBedrockAgent()
    mapping: ClassVar[Dict[str, Bender]] = {
        "id": S("knowledgeBaseId"),
        "name": S("name"),
        "arn": S("knowledgeBaseArn"),
        "ctime": S("createdAt"),
        "mtime": S("updatedAt"),
        "created_at": S("createdAt"),
        "description": S("description"),
        "failure_reasons": S("failureReasons", default=[]),
        "knowledge_base_arn": S("knowledgeBaseArn"),
        "knowledge_base_configuration": S("knowledgeBaseConfiguration")
        >> Bend(AwsBedrockKnowledgeBaseConfiguration.mapping),
        "knowledge_base_id": S("knowledgeBaseId"),
        "role_arn": S("roleArn"),
        "status": S("status"),
        "storage_configuration": S("storageConfiguration") >> Bend(AwsBedrockStorageConfiguration.mapping),
        "updated_at": S("updatedAt"),
    }
    created_at: Optional[datetime] = field(default=None, metadata={"description": "The time at which the knowledge base was created."})  # fmt: skip
    description: Optional[str] = field(default=None, metadata={"description": "The description of the knowledge base."})  # fmt: skip
    failure_reasons: Optional[List[str]] = field(factory=list, metadata={"description": "A list of reasons that the API operation on the knowledge base failed."})  # fmt: skip
    knowledge_base_arn: Optional[str] = field(default=None, metadata={"description": "The Amazon Resource Name (ARN) of the knowledge base."})  # fmt: skip
    knowledge_base_configuration: Optional[AwsBedrockKnowledgeBaseConfiguration] = field(default=None, metadata={"description": "Contains details about the embeddings configuration of the knowledge base."})  # fmt: skip
    knowledge_base_id: Optional[str] = field(default=None, metadata={"description": "The unique identifier of the knowledge base."})  # fmt: skip
    role_arn: Optional[str] = field(default=None, metadata={"description": "The Amazon Resource Name (ARN) of the IAM role with permissions to invoke API operations on the knowledge base."})  # fmt: skip
    status: Optional[str] = field(default=None, metadata={"description": "The status of the knowledge base. The following statuses are possible:   CREATING – The knowledge base is being created.   ACTIVE – The knowledge base is ready to be queried.   DELETING – The knowledge base is being deleted.   UPDATING – The knowledge base is being updated.   FAILED – The knowledge base API operation failed."})  # fmt: skip
    storage_configuration: Optional[AwsBedrockStorageConfiguration] = field(default=None, metadata={"description": "Contains details about the storage configuration of the knowledge base."})  # fmt: skip
    updated_at: Optional[datetime] = field(default=None, metadata={"description": "The time at which the knowledge base was last updated."})  # fmt: skip

    def delete_resource(self, client: AwsClient, graph: Graph) -> bool:
        client.call(
            aws_service="bedrock-agent", action="delete-knowledge-base", result_name=None, knowledgeBaseId=self.id
        )
        return True

    @classmethod
    def called_mutator_apis(cls) -> List[AwsApiSpec]:
        return super().called_mutator_apis() + [AwsApiSpec("bedrock-agent", "delete-knowledge-base")]

    @classmethod
    def called_collect_apis(cls) -> List[AwsApiSpec]:
        return super().called_collect_apis() + [
            AwsApiSpec("bedrock-agent", "list-knowledge-bases"),
        ]

    @classmethod
    def service_name(cls) -> str:
        return "bedrock-agent"


@define(eq=False, slots=False)
class AwsBedrockPromptModelInferenceConfiguration:
    kind: ClassVar[str] = "aws_bedrock_prompt_model_inference_configuration"
    mapping: ClassVar[Dict[str, Bender]] = {
        "max_tokens": S("maxTokens"),
        "stop_sequences": S("stopSequences", default=[]),
        "temperature": S("temperature"),
        "top_k": S("topK"),
        "top_p": S("topP"),
    }
    max_tokens: Optional[int] = field(default=None, metadata={"description": "The maximum number of tokens to return in the response."})  # fmt: skip
    stop_sequences: Optional[List[str]] = field(factory=list, metadata={"description": "A list of strings that define sequences after which the model will stop generating."})  # fmt: skip
    temperature: Optional[float] = field(default=None, metadata={"description": "Controls the randomness of the response. Choose a lower value for more predictable outputs and a higher value for more surprising outputs."})  # fmt: skip
    top_k: Optional[int] = field(default=None, metadata={"description": "The number of most-likely candidates that the model considers for the next token during generation."})  # fmt: skip
    top_p: Optional[float] = field(default=None, metadata={"description": "The percentage of most-likely candidates that the model considers for the next token."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockPromptInferenceConfiguration:
    kind: ClassVar[str] = "aws_bedrock_prompt_inference_configuration"
    mapping: ClassVar[Dict[str, Bender]] = {
        "text": S("text") >> Bend(AwsBedrockPromptModelInferenceConfiguration.mapping)
    }
    text: Optional[AwsBedrockPromptModelInferenceConfiguration] = field(default=None, metadata={"description": "Contains inference configurations for a text prompt."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockTextPromptTemplateConfiguration:
    kind: ClassVar[str] = "aws_bedrock_text_prompt_template_configuration"
    mapping: ClassVar[Dict[str, Bender]] = {
        "input_variables": S("inputVariables", default=[]) >> ForallBend(S("name")),
        "text": S("text"),
    }
    input_variables: Optional[List[str]] = field(factory=list, metadata={"description": "An array of the variables in the prompt template."})  # fmt: skip
    text: Optional[str] = field(default=None, metadata={"description": "The message for the prompt."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockPromptTemplateConfiguration:
    kind: ClassVar[str] = "aws_bedrock_prompt_template_configuration"
    mapping: ClassVar[Dict[str, Bender]] = {
        "text": S("text") >> Bend(AwsBedrockTextPromptTemplateConfiguration.mapping)
    }
    text: Optional[AwsBedrockTextPromptTemplateConfiguration] = field(default=None, metadata={"description": "Contains configurations for the text in a message for a prompt."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockPromptVariant:
    kind: ClassVar[str] = "aws_bedrock_prompt_variant"
    mapping: ClassVar[Dict[str, Bender]] = {
        "inference_configuration": S("inferenceConfiguration") >> Bend(AwsBedrockPromptInferenceConfiguration.mapping),
        "model_id": S("modelId"),
        "name": S("name"),
        "template_configuration": S("templateConfiguration") >> Bend(AwsBedrockPromptTemplateConfiguration.mapping),
        "template_type": S("templateType"),
    }
    inference_configuration: Optional[AwsBedrockPromptInferenceConfiguration] = field(default=None, metadata={"description": "Contains inference configurations for the prompt variant."})  # fmt: skip
    model_id: Optional[str] = field(default=None, metadata={"description": "The unique identifier of the model with which to run inference on the prompt."})  # fmt: skip
    name: Optional[str] = field(default=None, metadata={"description": "The name of the prompt variant."})  # fmt: skip
    template_configuration: Optional[AwsBedrockPromptTemplateConfiguration] = field(default=None, metadata={"description": "Contains configurations for the prompt template."})  # fmt: skip
    template_type: Optional[str] = field(default=None, metadata={"description": "The type of prompt template to use."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockAgentPrompt(BedrockTaggable, BaseAiResource, AwsResource):
    kind: ClassVar[str] = "aws_bedrock_agent_prompt"
    kind_display: ClassVar[str] = "AWS Bedrock Agent Prompt"
    kind_description: ClassVar[str] = (
        "AWS Bedrock Agent Prompt defines the input that the agent uses to generate responses or actions, "
        "guiding the interaction between users and machine learning models through structured prompts."
    )
    reference_kinds: ClassVar[ModelReference] = {
        "successors": {"default": [AwsBedrockCustomModel.kind]},
    }
    api_spec: ClassVar[AwsApiSpec] = AwsApiSpec(
        "bedrock-agent", "list-prompts", "promptSummaries", expected_errors=["AccessDeniedException"]
    )
    kind_service: ClassVar[Optional[str]] = "bedrock-agent"
    aws_metadata: ClassVar[Dict[str, Any]] = {"provider_link_tpl": "https://{region_id}.console.aws.amazon.com/bedrock/home?region={region_id}#/prompt-management/{id}"}  # fmt: skip
    mapping: ClassVar[Dict[str, Bender]] = {
        "id": S("id"),
        "name": S("name"),
        "ctime": S("createdAt"),
        "mtime": S("updatedAt"),
        "arn": S("arn"),
        "created_at": S("createdAt"),
        "customer_encryption_key_arn": S("customerEncryptionKeyArn"),
        "default_variant": S("defaultVariant"),
        "description": S("description"),
        "updated_at": S("updatedAt"),
        "prompt_variants": S("variants", default=[]) >> ForallBend(AwsBedrockPromptVariant.mapping),
        "version": S("version"),
    }
    created_at: Optional[datetime] = field(default=None, metadata={"description": "The time at which the prompt was created."})  # fmt: skip
    customer_encryption_key_arn: Optional[str] = field(default=None, metadata={"description": "The Amazon Resource Name (ARN) of the KMS key that the prompt is encrypted with."})  # fmt: skip
    default_variant: Optional[str] = field(default=None, metadata={"description": "The name of the default variant for the prompt. This value must match the name field in the relevant PromptVariant object."})  # fmt: skip
    description: Optional[str] = field(default=None, metadata={"description": "The descriptino of the prompt."})  # fmt: skip
    updated_at: Optional[datetime] = field(default=None, metadata={"description": "The time at which the prompt was last updated."})  # fmt: skip
    prompt_variants: Optional[List[AwsBedrockPromptVariant]] = field(factory=list, metadata={"description": "A list of objects, each containing details about a variant of the prompt."})  # fmt: skip
    version: Optional[str] = field(default=None, metadata={"description": "The version of the prompt."})  # fmt: skip

    def delete_resource(self, client: AwsClient, graph: Graph) -> bool:
        client.call(
            aws_service="bedrock-agent",
            action="delete-prompt",
            result_name=None,
            promptIdentifier=self.id,
        )
        return True

    @classmethod
    def called_mutator_apis(cls) -> List[AwsApiSpec]:
        return super().called_mutator_apis() + [AwsApiSpec("bedrock-agent", "delete-prompt")]

    @classmethod
    def called_collect_apis(cls) -> List[AwsApiSpec]:
        return super().called_collect_apis() + [cls.api_spec, AwsApiSpec("bedrock-agent", "get-prompt")]

    @classmethod
    def service_name(cls) -> str:
        return "bedrock-agent"

    def connect_in_graph(self, builder: GraphBuilder, source: Json) -> None:
        if variants := self.prompt_variants:
            for variant in variants:
                builder.add_edge(self, clazz=AwsBedrockCustomModel, id=variant.model_id)

    @classmethod
    def collect(cls: Type[AwsResource], json: List[Json], builder: GraphBuilder) -> None:
        def add_tags(prompt: AwsResource) -> None:
            tags = builder.client.list(
                "bedrock-agent",
                "list-tags-for-resource",
                "tags",
                expected_errors=["ResourceNotFoundException"],
                resourceArn=prompt.arn,
            )
            if tags:
                prompt.tags.update(tags[0])

        for js in json:
            for result in builder.client.list(
                "bedrock-agent",
                "get-prompt",
                promptIdentifier=js["id"],
                promptVersion=js["version"],
            ):
                if instance := cls.from_api(result, builder):
                    builder.add_node(instance, js)
                    builder.submit_work("bedrock-agent", add_tags, instance)


@define(eq=False, slots=False)
class AwsBedrockFlowDataConnectionConfiguration:
    kind: ClassVar[str] = "aws_bedrock_flow_data_connection_configuration"
    mapping: ClassVar[Dict[str, Bender]] = {"source_output": S("sourceOutput"), "target_input": S("targetInput")}
    source_output: Optional[str] = field(default=None, metadata={"description": "The name of the output in the source node that the connection begins from."})  # fmt: skip
    target_input: Optional[str] = field(default=None, metadata={"description": "The name of the input in the target node that the connection ends at."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockFlowConnectionConfiguration:
    kind: ClassVar[str] = "aws_bedrock_flow_connection_configuration"
    mapping: ClassVar[Dict[str, Bender]] = {
        "conditional": S("conditional", "condition"),
        "data": S("data") >> Bend(AwsBedrockFlowDataConnectionConfiguration.mapping),
    }
    conditional: Optional[str] = field(default=None, metadata={"description": "The configuration of a connection originating from a Condition node."})  # fmt: skip
    data: Optional[AwsBedrockFlowDataConnectionConfiguration] = field(default=None, metadata={"description": "The configuration of a connection originating from a node that isn't a Condition node."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockFlowConnection:
    kind: ClassVar[str] = "aws_bedrock_flow_connection"
    mapping: ClassVar[Dict[str, Bender]] = {
        "configuration": S("configuration") >> Bend(AwsBedrockFlowConnectionConfiguration.mapping),
        "name": S("name"),
        "source": S("source"),
        "target": S("target"),
        "type": S("type"),
    }
    configuration: Optional[AwsBedrockFlowConnectionConfiguration] = field(default=None, metadata={"description": "The configuration of the connection."})  # fmt: skip
    name: Optional[str] = field(default=None, metadata={"description": "A name for the connection that you can reference."})  # fmt: skip
    source: Optional[str] = field(default=None, metadata={"description": "The node that the connection starts at."})  # fmt: skip
    target: Optional[str] = field(default=None, metadata={"description": "The node that the connection ends at."})  # fmt: skip
    type: Optional[str] = field(default=None, metadata={"description": "Whether the source node that the connection begins from is a condition node (Conditional) or not (Data)."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockCollectorFlowNodeConfiguration:
    kind: ClassVar[str] = "aws_bedrock_collector_flow_node_configuration"
    mapping: ClassVar[Dict[str, Bender]] = {}


@define(eq=False, slots=False)
class AwsBedrockFlowCondition:
    kind: ClassVar[str] = "aws_bedrock_flow_condition"
    mapping: ClassVar[Dict[str, Bender]] = {"expression": S("expression"), "name": S("name")}
    expression: Optional[str] = field(default=None, metadata={"description": "Defines the condition. You must refer to at least one of the inputs in the condition. For more information, expand the Condition node section in Node types in prompt flows."})  # fmt: skip
    name: Optional[str] = field(default=None, metadata={"description": "A name for the condition that you can reference."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockConditionFlowNodeConfiguration:
    kind: ClassVar[str] = "aws_bedrock_condition_flow_node_configuration"
    mapping: ClassVar[Dict[str, Bender]] = {
        "conditions": S("conditions", default=[]) >> ForallBend(AwsBedrockFlowCondition.mapping)
    }
    conditions: Optional[List[AwsBedrockFlowCondition]] = field(factory=list, metadata={"description": "An array of conditions. Each member contains the name of a condition and an expression that defines the condition."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockInputFlowNodeConfiguration:
    kind: ClassVar[str] = "aws_bedrock_input_flow_node_configuration"
    mapping: ClassVar[Dict[str, Bender]] = {}


@define(eq=False, slots=False)
class AwsBedrockIteratorFlowNodeConfiguration:
    kind: ClassVar[str] = "aws_bedrock_iterator_flow_node_configuration"
    mapping: ClassVar[Dict[str, Bender]] = {}


@define(eq=False, slots=False)
class AwsBedrockKnowledgeBaseFlowNodeConfiguration:
    kind: ClassVar[str] = "aws_bedrock_knowledge_base_flow_node_configuration"
    mapping: ClassVar[Dict[str, Bender]] = {"knowledge_base_id": S("knowledgeBaseId"), "model_id": S("modelId")}
    knowledge_base_id: Optional[str] = field(default=None, metadata={"description": "The unique identifier of the knowledge base to query."})  # fmt: skip
    model_id: Optional[str] = field(default=None, metadata={"description": "The unique identifier of the model to use to generate a response from the query results. Omit this field if you want to return the retrieved results as an array."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockLexFlowNodeConfiguration:
    kind: ClassVar[str] = "aws_bedrock_lex_flow_node_configuration"
    mapping: ClassVar[Dict[str, Bender]] = {"bot_alias_arn": S("botAliasArn"), "locale_id": S("localeId")}
    bot_alias_arn: Optional[str] = field(default=None, metadata={"description": "The Amazon Resource Name (ARN) of the Amazon Lex bot alias to invoke."})  # fmt: skip
    locale_id: Optional[str] = field(default=None, metadata={"description": "The Region to invoke the Amazon Lex bot in."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockOutputFlowNodeConfiguration:
    kind: ClassVar[str] = "aws_bedrock_output_flow_node_configuration"
    mapping: ClassVar[Dict[str, Bender]] = {}


@define(eq=False, slots=False)
class AwsBedrockPromptFlowNodeInlineConfiguration:
    kind: ClassVar[str] = "aws_bedrock_prompt_flow_node_inline_configuration"
    mapping: ClassVar[Dict[str, Bender]] = {
        "inference_configuration": S("inferenceConfiguration") >> Bend(AwsBedrockPromptInferenceConfiguration.mapping),
        "model_id": S("modelId"),
        "template_configuration": S("templateConfiguration") >> Bend(AwsBedrockPromptTemplateConfiguration.mapping),
        "template_type": S("templateType"),
    }
    inference_configuration: Optional[AwsBedrockPromptInferenceConfiguration] = field(default=None, metadata={"description": "Contains inference configurations for the prompt."})  # fmt: skip
    model_id: Optional[str] = field(default=None, metadata={"description": "The unique identifier of the model to run inference with."})  # fmt: skip
    template_configuration: Optional[AwsBedrockPromptTemplateConfiguration] = field(default=None, metadata={"description": "Contains a prompt and variables in the prompt that can be replaced with values at runtime."})  # fmt: skip
    template_type: Optional[str] = field(default=None, metadata={"description": "The type of prompt template."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockPromptFlowNodeSourceConfiguration:
    kind: ClassVar[str] = "aws_bedrock_prompt_flow_node_source_configuration"
    mapping: ClassVar[Dict[str, Bender]] = {
        "inline": S("inline") >> Bend(AwsBedrockPromptFlowNodeInlineConfiguration.mapping),
        "resource": S("resource", "promptArn"),
    }
    inline: Optional[AwsBedrockPromptFlowNodeInlineConfiguration] = field(default=None, metadata={"description": "Contains configurations for a prompt that is defined inline"})  # fmt: skip
    resource: Optional[str] = field(default=None, metadata={"description": "Contains configurations for a prompt from Prompt management."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockPromptFlowNodeConfiguration:
    kind: ClassVar[str] = "aws_bedrock_prompt_flow_node_configuration"
    mapping: ClassVar[Dict[str, Bender]] = {
        "source_configuration": S("sourceConfiguration") >> Bend(AwsBedrockPromptFlowNodeSourceConfiguration.mapping)
    }
    source_configuration: Optional[AwsBedrockPromptFlowNodeSourceConfiguration] = field(default=None, metadata={"description": "Specifies whether the prompt is from Prompt management or defined inline."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockRetrievalFlowNodeServiceConfiguration:
    kind: ClassVar[str] = "aws_bedrock_retrieval_flow_node_service_configuration"
    mapping: ClassVar[Dict[str, Bender]] = {"s3": S("s3", "bucketName")}
    s3: Optional[str] = field(default=None, metadata={"description": "Contains configurations for the Amazon S3 location from which to retrieve data to return as the output from the node."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockRetrievalFlowNodeConfiguration:
    kind: ClassVar[str] = "aws_bedrock_retrieval_flow_node_configuration"
    mapping: ClassVar[Dict[str, Bender]] = {
        "service_configuration": S("serviceConfiguration")
        >> Bend(AwsBedrockRetrievalFlowNodeServiceConfiguration.mapping)
    }
    service_configuration: Optional[AwsBedrockRetrievalFlowNodeServiceConfiguration] = field(default=None, metadata={"description": "Contains configurations for the service to use for retrieving data to return as the output from the node."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockStorageFlowNodeServiceConfiguration:
    kind: ClassVar[str] = "aws_bedrock_storage_flow_node_service_configuration"
    mapping: ClassVar[Dict[str, Bender]] = {"s3": S("s3", "bucketName")}
    s3: Optional[str] = field(default=None, metadata={"description": "Contains configurations for the Amazon S3 location in which to store the input into the node."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockStorageFlowNodeConfiguration:
    kind: ClassVar[str] = "aws_bedrock_storage_flow_node_configuration"
    mapping: ClassVar[Dict[str, Bender]] = {
        "service_configuration": S("serviceConfiguration")
        >> Bend(AwsBedrockStorageFlowNodeServiceConfiguration.mapping)
    }
    service_configuration: Optional[AwsBedrockStorageFlowNodeServiceConfiguration] = field(default=None, metadata={"description": "Contains configurations for the service to use for storing the input into the node."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockFlowNodeConfiguration:
    kind: ClassVar[str] = "aws_bedrock_flow_node_configuration"
    mapping: ClassVar[Dict[str, Bender]] = {
        "agent": S("agent", "agentAliasArn"),
        "collector": S("collector") >> Bend(AwsBedrockCollectorFlowNodeConfiguration.mapping),
        "condition": S("condition") >> Bend(AwsBedrockConditionFlowNodeConfiguration.mapping),
        "input": S("input") >> Bend(AwsBedrockInputFlowNodeConfiguration.mapping),
        "iterator": S("iterator") >> Bend(AwsBedrockIteratorFlowNodeConfiguration.mapping),
        "knowledge_base": S("knowledgeBase") >> Bend(AwsBedrockKnowledgeBaseFlowNodeConfiguration.mapping),
        "lambda_function": S("lambdaFunction", "lambdaArn"),
        "lex": S("lex") >> Bend(AwsBedrockLexFlowNodeConfiguration.mapping),
        "output": S("output") >> Bend(AwsBedrockOutputFlowNodeConfiguration.mapping),
        "prompt": S("prompt") >> Bend(AwsBedrockPromptFlowNodeConfiguration.mapping),
        "retrieval": S("retrieval") >> Bend(AwsBedrockRetrievalFlowNodeConfiguration.mapping),
        "storage": S("storage") >> Bend(AwsBedrockStorageFlowNodeConfiguration.mapping),
    }
    agent: Optional[str] = field(default=None, metadata={"description": "Contains configurations for an agent node in your flow. Invokes an alias of an agent and returns the response."})  # fmt: skip
    collector: Optional[AwsBedrockCollectorFlowNodeConfiguration] = field(default=None, metadata={"description": "Contains configurations for a collector node in your flow. Collects an iteration of inputs and consolidates them into an array of outputs."})  # fmt: skip
    condition: Optional[AwsBedrockConditionFlowNodeConfiguration] = field(default=None, metadata={"description": "Contains configurations for a Condition node in your flow. Defines conditions that lead to different branches of the flow."})  # fmt: skip
    input: Optional[AwsBedrockInputFlowNodeConfiguration] = field(default=None, metadata={"description": "Contains configurations for an input flow node in your flow. The first node in the flow. inputs can't be specified for this node."})  # fmt: skip
    iterator: Optional[AwsBedrockIteratorFlowNodeConfiguration] = field(default=None, metadata={"description": "Contains configurations for an iterator node in your flow. Takes an input that is an array and iteratively sends each item of the array as an output to the following node. The size of the array is also returned in the output. The output flow node at the end of the flow iteration will return a response for each member of the array. To return only one response, you can include a collector node downstream from the iterator node."})  # fmt: skip
    knowledge_base: Optional[AwsBedrockKnowledgeBaseFlowNodeConfiguration] = field(default=None, metadata={"description": "Contains configurations for a knowledge base node in your flow. Queries a knowledge base and returns the retrieved results or generated response."})  # fmt: skip
    lambda_function: Optional[str] = field(default=None, metadata={"description": "Contains configurations for a Lambda function node in your flow. Invokes an Lambda function."})  # fmt: skip
    lex: Optional[AwsBedrockLexFlowNodeConfiguration] = field(default=None, metadata={"description": "Contains configurations for a Lex node in your flow. Invokes an Amazon Lex bot to identify the intent of the input and return the intent as the output."})  # fmt: skip
    output: Optional[AwsBedrockOutputFlowNodeConfiguration] = field(default=None, metadata={"description": "Contains configurations for an output flow node in your flow. The last node in the flow. outputs can't be specified for this node."})  # fmt: skip
    prompt: Optional[AwsBedrockPromptFlowNodeConfiguration] = field(default=None, metadata={"description": "Contains configurations for a prompt node in your flow. Runs a prompt and generates the model response as the output. You can use a prompt from Prompt management or you can configure one in this node."})  # fmt: skip
    retrieval: Optional[AwsBedrockRetrievalFlowNodeConfiguration] = field(default=None, metadata={"description": "Contains configurations for a Retrieval node in your flow. Retrieves data from an Amazon S3 location and returns it as the output."})  # fmt: skip
    storage: Optional[AwsBedrockStorageFlowNodeConfiguration] = field(default=None, metadata={"description": "Contains configurations for a Storage node in your flow. Stores an input in an Amazon S3 location."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockFlowNodeInput:
    kind: ClassVar[str] = "aws_bedrock_flow_node_input"
    mapping: ClassVar[Dict[str, Bender]] = {"expression": S("expression"), "name": S("name"), "type": S("type")}
    expression: Optional[str] = field(default=None, metadata={"description": "An expression that formats the input for the node. For an explanation of how to create expressions, see Expressions in Prompt flows in Amazon Bedrock."})  # fmt: skip
    name: Optional[str] = field(default=None, metadata={"description": "A name for the input that you can reference."})  # fmt: skip
    type: Optional[str] = field(default=None, metadata={"description": "The data type of the input. If the input doesn't match this type at runtime, a validation error will be thrown."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockFlowNodeOutput:
    kind: ClassVar[str] = "aws_bedrock_flow_node_output"
    mapping: ClassVar[Dict[str, Bender]] = {"name": S("name"), "type": S("type")}
    name: Optional[str] = field(default=None, metadata={"description": "A name for the output that you can reference."})  # fmt: skip
    type: Optional[str] = field(default=None, metadata={"description": "The data type of the output. If the output doesn't match this type at runtime, a validation error will be thrown."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockFlowNode:
    kind: ClassVar[str] = "aws_bedrock_flow_node"
    mapping: ClassVar[Dict[str, Bender]] = {
        "configuration": S("configuration") >> Bend(AwsBedrockFlowNodeConfiguration.mapping),
        "inputs": S("inputs", default=[]) >> ForallBend(AwsBedrockFlowNodeInput.mapping),
        "name": S("name"),
        "outputs": S("outputs", default=[]) >> ForallBend(AwsBedrockFlowNodeOutput.mapping),
        "type": S("type"),
    }
    configuration: Optional[AwsBedrockFlowNodeConfiguration] = field(default=None, metadata={"description": "Contains configurations for the node."})  # fmt: skip
    inputs: Optional[List[AwsBedrockFlowNodeInput]] = field(factory=list, metadata={"description": "An array of objects, each of which contains information about an input into the node."})  # fmt: skip
    name: Optional[str] = field(default=None, metadata={"description": "A name for the node."})  # fmt: skip
    outputs: Optional[List[AwsBedrockFlowNodeOutput]] = field(factory=list, metadata={"description": "A list of objects, each of which contains information about an output from the node."})  # fmt: skip
    type: Optional[str] = field(default=None, metadata={"description": "The type of node. This value must match the name of the key that you provide in the configuration you provide in the FlowNodeConfiguration field."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockFlowDefinition:
    kind: ClassVar[str] = "aws_bedrock_flow_definition"
    mapping: ClassVar[Dict[str, Bender]] = {
        "connections": S("connections", default=[]) >> ForallBend(AwsBedrockFlowConnection.mapping),
        "nodes": S("nodes", default=[]) >> ForallBend(AwsBedrockFlowNode.mapping),
    }
    connections: Optional[List[AwsBedrockFlowConnection]] = field(factory=list, metadata={"description": "An array of connection definitions in the flow."})  # fmt: skip
    nodes: Optional[List[AwsBedrockFlowNode]] = field(factory=list, metadata={"description": "An array of node definitions in the flow."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockFlowValidation:
    kind: ClassVar[str] = "aws_bedrock_flow_validation"
    mapping: ClassVar[Dict[str, Bender]] = {"message": S("message"), "severity": S("severity")}
    message: Optional[str] = field(default=None, metadata={"description": "A message describing the validation error."})  # fmt: skip
    severity: Optional[str] = field(default=None, metadata={"description": "The severity of the issue described in the message."})  # fmt: skip


@define(eq=False, slots=False)
class AwsBedrockAgentFlow(BedrockTaggable, BaseAiResource, AwsResource):
    kind: ClassVar[str] = "aws_bedrock_agent_flow"
    kind_display: ClassVar[str] = "AWS Bedrock Agent Flow"
    kind_description: ClassVar[str] = (
        "AWS Bedrock Agent Flow outlines the logical sequence of interactions between the agent and the model, "
        "defining the steps to be followed in executing tasks or answering queries."
    )
    reference_kinds: ClassVar[ModelReference] = {
        "successors": {"default": ["aws_bedrock_agent_flow_version"]},
    }
    api_spec: ClassVar[AwsApiSpec] = AwsApiSpec(
        "bedrock-agent", "list-flows", "flowSummaries", expected_errors=["AccessDeniedException"]
    )
    kind_service: ClassVar[Optional[str]] = "bedrock-agent"
    aws_metadata: ClassVar[Dict[str, Any]] = {"provider_link_tpl": "https://{region_id}.console.aws.amazon.com/bedrock/home?region={region_id}#/prompt-flows/{id}"}  # fmt: skip
    mapping: ClassVar[Dict[str, Bender]] = {
        "id": S("id"),
        "name": S("name"),
        "ctime": S("createdAt"),
        "mtime": S("updatedAt"),
        "arn": S("arn"),
        "created_at": S("createdAt"),
        "customer_encryption_key_arn": S("customerEncryptionKeyArn"),
        "definition": S("definition") >> Bend(AwsBedrockFlowDefinition.mapping),
        "description": S("description"),
        "execution_role_arn": S("executionRoleArn"),
        "status": S("status"),
        "updated_at": S("updatedAt"),
        "validations": S("validations", default=[]) >> ForallBend(AwsBedrockFlowValidation.mapping),
        "version": S("version"),
    }
    created_at: Optional[datetime] = field(default=None, metadata={"description": "The time at which the flow was created."})  # fmt: skip
    customer_encryption_key_arn: Optional[str] = field(default=None, metadata={"description": "The Amazon Resource Name (ARN) of the KMS key that the flow is encrypted with."})  # fmt: skip
    definition: Optional[AwsBedrockFlowDefinition] = field(default=None, metadata={"description": "The definition of the nodes and connections between the nodes in the flow."})  # fmt: skip
    description: Optional[str] = field(default=None, metadata={"description": "The description of the flow."})  # fmt: skip
    execution_role_arn: Optional[str] = field(default=None, metadata={"description": "The Amazon Resource Name (ARN) of the service role with permissions to create a flow. For more information, see Create a service row for flows in the Amazon Bedrock User Guide."})  # fmt: skip
    status: Optional[str] = field(default=None, metadata={"description": "The status of the flow. The following statuses are possible:   NotPrepared – The flow has been created or updated, but hasn't been prepared. If you just created the flow, you can't test it. If you updated the flow, the DRAFT version won't contain the latest changes for testing. Send a PrepareFlow request to package the latest changes into the DRAFT version.   Preparing – The flow is being prepared so that the DRAFT version contains the latest changes for testing.   Prepared – The flow is prepared and the DRAFT version contains the latest changes for testing.   Failed – The last API operation that you invoked on the flow failed. Send a GetFlow request and check the error message in the validations field."})  # fmt: skip
    updated_at: Optional[datetime] = field(default=None, metadata={"description": "The time at which the flow was last updated."})  # fmt: skip
    validations: Optional[List[AwsBedrockFlowValidation]] = field(factory=list, metadata={"description": "A list of validation error messages related to the last failed operation on the flow."})  # fmt: skip
    version: Optional[str] = field(default=None, metadata={"description": "The version of the flow for which information was retrieved."})  # fmt: skip

    def delete_resource(self, client: AwsClient, graph: Graph) -> bool:
        client.call(
            aws_service="bedrock-agent",
            action="delete-flow",
            result_name=None,
            flowIdentifier=self.id,
        )
        return True

    @classmethod
    def service_name(cls) -> str:
        return "bedrock-agent"

    @classmethod
    def called_mutator_apis(cls) -> List[AwsApiSpec]:
        return super().called_mutator_apis() + [AwsApiSpec("bedrock-agent", "delete-flow")]

    @classmethod
    def called_collect_apis(cls) -> List[AwsApiSpec]:
        return super().called_collect_apis() + [cls.api_spec, AwsApiSpec("bedrock-agent", "get-flow")]

    @classmethod
    def collect(cls: Type[AwsResource], json: List[Json], builder: GraphBuilder) -> None:
        def add_tags(flow: AwsResource) -> None:
            tags = builder.client.list(
                "bedrock-agent",
                "list-tags-for-resource",
                "tags",
                expected_errors=["ResourceNotFoundException"],
                resourceArn=flow.arn,
            )
            if tags:
                flow.tags.update(tags[0])

        def collect_flow_versions(flow: AwsBedrockAgentFlow) -> None:
            if not flow.version or flow.version == "DRAFT":
                return
            for result in builder.client.list(
                "bedrock-agent",
                "get-flow-version",
                flowIdentifier=flow.id,
                flowVersion=flow.version,
            ):
                if instance := AwsBedrockAgentFlowVersion.from_api(result, builder):
                    builder.add_node(instance, js)
                    builder.submit_work("bedrock-agent", add_tags, instance)

        for js in json:
            for result in builder.client.list(
                "bedrock-agent",
                "get-flow",
                flowIdentifier=js["id"],
            ):
                if instance := cls.from_api(result, builder):
                    builder.add_node(instance, js)
                    builder.submit_work("bedrock-agent", add_tags, instance)
                    builder.submit_work("bedrock-agent", collect_flow_versions, instance)


@define(eq=False, slots=False)
class AwsBedrockAgentFlowVersion(BedrockTaggable, BaseAiResource, AwsResource):
    kind: ClassVar[str] = "aws_bedrock_agent_flow_version"
    kind_display: ClassVar[str] = "AWS Bedrock Agent Flow Version"
    kind_description: ClassVar[str] = (
        "AWS Bedrock Agent Flow Version tracks the version history of agent workflows, ensuring compatibility and stability "
        "as workflows evolve and improve over time."
    )
    kind_service: ClassVar[Optional[str]] = "bedrock-agent"
    aws_metadata: ClassVar[Dict[str, Any]] = {"provider_link_tpl": "https://{region_id}.console.aws.amazon.com/bedrock/home?region={region_id}#/prompt-flows/{id}/versions/{version}"}  # fmt: skip
    # Collected via AwsBedrockAgentFlow()
    mapping: ClassVar[Dict[str, Bender]] = {
        "id": S("id"),
        "name": S("name"),
        "ctime": S("createdAt"),
        "arn": S("arn"),
        "created_at": S("createdAt"),
        "customer_encryption_key_arn": S("customerEncryptionKeyArn"),
        "definition": S("definition") >> Bend(AwsBedrockFlowDefinition.mapping),
        "description": S("description"),
        "execution_role_arn": S("executionRoleArn"),
        "status": S("status"),
        "version": S("version"),
    }
    created_at: Optional[datetime] = field(default=None, metadata={"description": "The time at which the flow was created."})  # fmt: skip
    customer_encryption_key_arn: Optional[str] = field(default=None, metadata={"description": "The Amazon Resource Name (ARN) of the KMS key that the version of the flow is encrypted with."})  # fmt: skip
    definition: Optional[AwsBedrockFlowDefinition] = field(default=None, metadata={"description": "The definition of the nodes and connections between nodes in the flow."})  # fmt: skip
    description: Optional[str] = field(default=None, metadata={"description": "The description of the flow."})  # fmt: skip
    execution_role_arn: Optional[str] = field(default=None, metadata={"description": "The Amazon Resource Name (ARN) of the service role with permissions to create a flow. For more information, see Create a service role for flows in Amazon Bedrock in the Amazon Bedrock User Guide."})  # fmt: skip
    status: Optional[str] = field(default=None, metadata={"description": "The status of the flow."})  # fmt: skip
    version: Optional[str] = field(default=None, metadata={"description": "The version of the flow for which information was retrieved."})  # fmt: skip

    def delete_resource(self, client: AwsClient, graph: Graph) -> bool:
        client.call(
            aws_service="bedrock-agent",
            action="delete-flow-version",
            result_name=None,
            flowIdentifier=self.id,
            flowVersion=self.version,
        )
        return True

    @classmethod
    def called_collect_apis(cls) -> List[AwsApiSpec]:
        return super().called_collect_apis() + [AwsApiSpec("bedrock-agent", "get-flow-version")]

    @classmethod
    def called_mutator_apis(cls) -> List[AwsApiSpec]:
        return super().called_mutator_apis() + [AwsApiSpec("bedrock-agent", "delete-flow-version")]

    @classmethod
    def service_name(cls) -> str:
        return "bedrock-agent"


resources: List[Type[AwsResource]] = [
    AwsBedrockCustomModel,
    AwsBedrockProvisionedModelThroughput,
    AwsBedrockGuardrail,
    AwsBedrockModelCustomizationJob,
    AwsBedrockEvaluationJob,
    AwsBedrockAgent,
    AwsBedrockAgentVersion,
    AwsBedrockAgentKnowledgeBase,
    AwsBedrockAgentPrompt,
    AwsBedrockAgentFlow,
    AwsBedrockAgentFlowVersion,
]
