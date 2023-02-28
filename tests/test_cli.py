from typing import Callable, List
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from authz_analyzer import cli
from authz_analyzer.datastores.aws.analyzer import AwsAssumeRoleInput


@patch('authz_analyzer.cli.run_snowflake', MagicMock())
def test_snowflake():
    invoke(
        cli.snowflake,
        [
            '--username',
            'user',
            '--password',
            'password',
            '--account',
            'account',
            '--host',
            'host',
            '--warehouse',
            'warehouse',
        ],
    )


@pytest.mark.parametrize('additional_args', [[], ['--key-file', 'key_file_path']], ids=['basic', 'key-file'])
@patch('authz_analyzer.cli.run_bigquery', MagicMock())
def test_bigquery(additional_args: List[str]):
    args = ['--project', 'proj1']
    args.extend(additional_args)
    invoke(cli.bigquery, args)


def test_valid_aws_account_params():
    assert AwsAssumeRoleInput(
        role_arn='arn:aws:iam::105246067165:role/SatoriScanner', external_id=None
    ) == cli.valid_aws_account_params(None, None, 'role_arn: arn:aws:iam::105246067165:role/SatoriScanner  ')
    assert AwsAssumeRoleInput(
        role_arn='arn:aws:iam::105246067165:role/SatoriScanner', external_id='1234'
    ) == cli.valid_aws_account_params(
        None, None, 'role_arn: arn:aws:iam::105246067165:role/SatoriScanner,  external_id: 1234'
    )
    assert AwsAssumeRoleInput(
        role_arn='arn:aws:iam::105246067165:role/__+---==SatoriScanner',
        external_id='sdfdsfknsdal43+-@',
    ) == cli.valid_aws_account_params(
        None,
        None,
        '    role_arn:arn:aws:iam::105246067165:role/__+---==SatoriScanner,external_id: sdfdsfknsdal43+-@',
    )
    with pytest.raises(Exception):
        cli.valid_aws_account_params(  # role_name includes '?'
            None,
            None,
            ' role_arn:arn:aws:ia???m::105246067165:role/__+---==SatoriScanner,external_id: sdfdsfknsdal43+-@',
        )
    with pytest.raises(Exception):
        cli.valid_aws_account_params(  # missing ','
            None,
            None,
            'role_arn:arn:aws:iam::105246067165:role/__+---==SatoriScanner external_id: sdfdsfknsdal43+-@',
        )


@pytest.mark.parametrize(
    'additional_args',
    [
        [],
        [
            '--additional-account-params',
            'role_arn: arn:aws:iam::105246067165:role/SatoriScanner,  external_id: 1234',
        ],
    ],
    ids=['no-args', 'additional_account'],
)
@patch('authz_analyzer.cli.run_aws_s3', MagicMock())
def test_aws_s3(additional_args: List[str]):
    args = [
        '--target-account-params',
        'role_arn: arn:aws:iam::982269985744:role/SatoriScanner,  external_id: 4321',
    ]
    args.extend(additional_args)
    invoke(cli.aws_s3, args)


@pytest.mark.parametrize(
    'additional_args', [[], ['--port', 12345], ['--dbname', 'db123']], ids=['no-args', 'port', 'different dbname']
)
@patch('authz_analyzer.cli.run_postgres', MagicMock())
def test_postgres(additional_args: List[str]):
    args = ['--username', 'user1', '--password', 'password', '--host', 'host1']
    args.extend(additional_args)
    invoke(cli.postgres, args)


@pytest.mark.parametrize(
    'additional_args', [[], ['--port', 12345], ['--dbname', 'db123']], ids=['no-args', 'port', 'different dbname']
)
@patch('authz_analyzer.cli.run_redshift', MagicMock())
def test_redshift(additional_args: List[str]):
    args = ['--username', 'user1', '--password', 'password', '--host', 'host1']
    args.extend(additional_args)
    invoke(cli.redshift, args)


@pytest.mark.parametrize(
    'additional_args', [[], ['--port', 12345], ['--ssl', False]], ids=['no-args', 'port', 'disable ssl']
)
@patch('authz_analyzer.cli.run_mongodb', MagicMock())
def test_mongodb(additional_args: List[str]):
    args = ['--username', 'user1', '--password', 'password', '--host', 'host1']
    args.extend(additional_args)
    invoke(cli.mongodb, args)


@patch('authz_analyzer.cli.run_mongodb_atlas', MagicMock())
def test_atlas():
    args = [
        '--public_key',
        'key',
        '--private_key',
        'private-key',
        '--username',
        'user1',
        '--password',
        'password',
        '--project',
        'project1',
        '--cluster',
        'cluster1',
    ]
    invoke(cli.atlas, args)


def invoke(command: Callable[[List[str]], None], args: List[str]):
    runner = CliRunner()
    result = runner.invoke(command, args, obj=generate_obj())  # type: ignore
    assert result.exit_code == 0, result.output


def generate_obj():
    return {"OUT": "MOCK_PATH", "FORMAT": "CSV", "DEBUG": False, "LOGGER": MagicMock()}
