import pathlib
import json
import os
import pytest

from serde.json import to_json, from_dict

from aws_ptrp.iam.iam_roles import IAMRole
from aws_ptrp import AwsPtrp
from aws_ptrp.services.s3.s3_service import S3Service, S3_SERVICE_NAME
from aws_ptrp.services.assume_role.assume_role_service import (
    AssumeRoleService,
    ROLE_TRUST_SERVICE_NAME,
)
from aws_ptrp.services.assume_role.assume_role_actions import AssumeRoleAction
from aws_ptrp.services.s3.s3_actions import S3Action
from aws_ptrp.services.s3.bucket import S3Bucket
from aws_ptrp.services import (
    register_service_action_type_by_name,
    register_service_action_by_name,
    register_service_resource_type_by_name,
    register_service_resource_by_name,
)

from authz_analyzer.datastores.aws.analyzer.exporter import AWSAuthzAnalyzerExporter
from authz_analyzer.writers.get_writers import get_writer
from authz_analyzer.writers.base_writers import OutputFormat
from authz_analyzer.utils.logger import get_logger


AWS_AUTHZ_ANALYZER_SATORI_DEV_JSON_FILE = pathlib.Path().joinpath(
    os.path.dirname(__file__), 'satori_dev_account_authz_analyzer.json'
)
AWS_AUTHZ_ANALYZER_SATORI_DEV_RESULT_JSON_FILE = pathlib.Path().joinpath(
    os.path.dirname(__file__), 'satori_dev_account_authz_analyzer_result.json'
)


@pytest.fixture
def register_services_for_deserialize_from_file():
    # add resolvers here action the type and the service
    register_service_action_by_name(S3_SERVICE_NAME, S3Action)
    register_service_resource_by_name(S3_SERVICE_NAME, S3Bucket)
    register_service_action_by_name(ROLE_TRUST_SERVICE_NAME, AssumeRoleAction)
    register_service_resource_by_name(ROLE_TRUST_SERVICE_NAME, IAMRole)
    register_service_action_type_by_name(S3_SERVICE_NAME, S3Service)
    register_service_resource_type_by_name(S3_SERVICE_NAME, S3Service)
    register_service_action_type_by_name(ROLE_TRUST_SERVICE_NAME, AssumeRoleService)
    register_service_resource_type_by_name(ROLE_TRUST_SERVICE_NAME, AssumeRoleService)


@pytest.mark.skipif(
    not os.environ.get("AUTHZ_SATORI_DEV_ACCOUNT_TEST"),
    reason="not really a test, just pull latest satori dev account config and write it to file",
)
def test_aws_authz_analyzer_with_s3_write_satori_dev_account():
    aws_account_id = '105246067165'
    assume_role_name = 'LalonFromStage'
    authz_analyzer = AwsPtrp.load_from_role(get_logger(False), aws_account_id, assume_role_name, set([S3Service()]))

    authz_analyzer_json = to_json(authz_analyzer)
    with open(AWS_AUTHZ_ANALYZER_SATORI_DEV_JSON_FILE, "w", encoding="utf-8") as outfile:
        outfile.write(authz_analyzer_json)


@pytest.mark.skipif(
    not os.environ.get("AUTHZ_SATORI_DEV_ACCOUNT_TEST"),
    reason="not really a test, just pull latest satori dev account config and write it to file",
)
def test_aws_authz_analyzer_load_satori_dev_json_file(
    # pylint: disable=unused-argument,redefined-outer-name
    register_services_for_deserialize_from_file,
):
    with open(AWS_AUTHZ_ANALYZER_SATORI_DEV_JSON_FILE, "r", encoding="utf-8") as file:
        authz_analyzer_json_from_file = json.load(file)
        authz_analyzer = from_dict(AwsPtrp, authz_analyzer_json_from_file)
        authz_analyzer_json_from_serde = json.loads(to_json(authz_analyzer))

        assert authz_analyzer_json_from_file == authz_analyzer_json_from_serde


@pytest.mark.skipif(
    not os.environ.get("AUTHZ_SATORI_DEV_ACCOUNT_TEST"),
    reason="not really a test, just pull latest satori dev account config and write it to file",
)
def test_aws_authz_analyzer_resolve_permissions_satori_dev_json_file(
    register_services_for_deserialize_from_file,
):  # pylint: disable=unused-argument,redefined-outer-name
    with open(AWS_AUTHZ_ANALYZER_SATORI_DEV_JSON_FILE, "r", encoding="utf-8") as file:
        authz_analyzer_json_from_file = json.load(file)
        authz_analyzer: AwsPtrp = from_dict(AwsPtrp, authz_analyzer_json_from_file)
        writer = get_writer(AWS_AUTHZ_ANALYZER_SATORI_DEV_RESULT_JSON_FILE, OutputFormat.MULTI_JSON)
        exporter = AWSAuthzAnalyzerExporter(writer)
        authz_analyzer.resolve_permissions(get_logger(False), exporter.export_entry_from_ptrp_line)
