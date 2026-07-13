"""Unit checks for immutable S3 release-bucket provisioning."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
import sys

import pytest
from botocore.exceptions import ClientError

# Backend tests run with ``backend/`` as the import root, while the deployment
# provisioner intentionally lives at the repository root.
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from deploy import setup_aws  # noqa: E402


def _client_error(code: str) -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": code}}, "fixture")


@dataclass
class FakeS3:
    object_lock_enabled: bool = True
    calls: list[tuple[str, dict]] = field(default_factory=list)
    policy: dict | None = None

    def head_bucket(self, **kwargs):
        self.calls.append(("head_bucket", kwargs))

    def put_bucket_versioning(self, **kwargs):
        self.calls.append(("put_bucket_versioning", kwargs))

    def get_object_lock_configuration(self, **kwargs):
        self.calls.append(("get_object_lock_configuration", kwargs))
        if not self.object_lock_enabled:
            raise _client_error("ObjectLockConfigurationNotFoundError")
        return {"ObjectLockConfiguration": {"ObjectLockEnabled": "Enabled"}}

    def put_object_lock_configuration(self, **kwargs):
        self.calls.append(("put_object_lock_configuration", kwargs))

    def put_public_access_block(self, **kwargs):
        self.calls.append(("put_public_access_block", kwargs))

    def put_bucket_encryption(self, **kwargs):
        self.calls.append(("put_bucket_encryption", kwargs))

    def get_bucket_policy(self, **kwargs):
        self.calls.append(("get_bucket_policy", kwargs))
        if self.policy is None:
            raise _client_error("NoSuchBucketPolicy")
        return {"Policy": json.dumps(self.policy)}

    def put_bucket_policy(self, **kwargs):
        self.calls.append(("put_bucket_policy", kwargs))
        self.policy = json.loads(kwargs["Policy"])


@dataclass
class FakeSession:
    s3: FakeS3

    def client(self, service_name: str):
        assert service_name == "s3"
        return self.s3


@dataclass
class FakeWaiter:
    called_with: dict | None = None

    def wait(self, **kwargs):
        self.called_with = kwargs


@dataclass
class FakeEc2:
    run_kwargs: dict | None = None
    waiter: FakeWaiter = field(default_factory=FakeWaiter)

    def describe_instances(self, **kwargs):
        if "Filters" in kwargs:
            return {"Reservations": []}
        return {
            "Reservations": [
                {
                    "Instances": [
                        {
                            "InstanceId": "i-release-fixture",
                            "PublicIpAddress": "203.0.113.5",
                        }
                    ]
                }
            ]
        }

    def run_instances(self, **kwargs):
        self.run_kwargs = kwargs
        return {"Instances": [{"InstanceId": "i-release-fixture"}]}

    def get_waiter(self, name: str):
        assert name == "instance_running"
        return self.waiter


@dataclass
class FakeEc2Session:
    ec2: FakeEc2

    def client(self, service_name: str):
        assert service_name == "ec2"
        return self.ec2


@dataclass
class FakeExistingEc2:
    encrypted: bool

    def describe_instances(self, **kwargs):
        assert "Filters" in kwargs
        return {
            "Reservations": [
                {
                    "Instances": [
                        {
                            "InstanceId": "i-existing-fixture",
                            "PublicIpAddress": "203.0.113.6",
                            "BlockDeviceMappings": [{"Ebs": {"VolumeId": "vol-fixture"}}],
                        }
                    ]
                }
            ]
        }

    def describe_volumes(self, **kwargs):
        assert kwargs["VolumeIds"] == ["vol-fixture"]
        return {"Volumes": [{"VolumeId": "vol-fixture", "Encrypted": self.encrypted}]}


def test_ensure_bucket_requires_object_lock_and_preserves_policy(monkeypatch):
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("S3_BUCKET", "ordinary-provider-data")
    monkeypatch.setenv("DATA_RELEASE_BUCKET", "immutable-release-fixture")
    monkeypatch.setenv("DATA_RELEASE_PREFIX", "investor-platform-data")
    monkeypatch.setenv("S3_OBJECT_LOCK_RETENTION_DAYS", "30")
    s3 = FakeS3(policy={"Version": "2012-10-17", "Statement": [{"Sid": "KeepMe"}]})

    setup_aws.ensure_bucket(FakeSession(s3))

    call_map = {name: kwargs for name, kwargs in s3.calls}
    assert call_map["put_bucket_versioning"]["VersioningConfiguration"]["Status"] == "Enabled"
    assert call_map["put_object_lock_configuration"]["ObjectLockConfiguration"] == {
        "ObjectLockEnabled": "Enabled",
        "Rule": {"DefaultRetention": {"Mode": "COMPLIANCE", "Days": 30}},
    }
    assert s3.policy is not None
    assert {"Sid": "KeepMe"} in s3.policy["Statement"]
    deny = next(
        statement
        for statement in s3.policy["Statement"]
        if statement["Sid"] == "DenyDeleteImmutableInvestorReleaseObjects"
    )
    assert deny["Action"] == ["s3:DeleteObject", "s3:DeleteObjectVersion"]
    assert deny["Resource"] == [
        "arn:aws:s3:::immutable-release-fixture/investor-platform-data/*"
    ]


def test_ensure_bucket_rejects_existing_bucket_without_object_lock(monkeypatch):
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("S3_BUCKET", "legacy-release-fixture")
    s3 = FakeS3(object_lock_enabled=False)

    with pytest.raises(RuntimeError, match="created without Object Lock"):
        setup_aws.ensure_bucket(FakeSession(s3))


def test_ensure_instance_encrypts_the_root_volume(monkeypatch):
    monkeypatch.setenv("EC2_INSTANCE_NAME", "release-fixture")
    monkeypatch.setenv("EC2_AMI_ID", "ami-fixture")
    monkeypatch.setenv("EC2_KEY_NAME", "operator-key")
    monkeypatch.setenv("EBS_KMS_KEY_ID", "arn:aws:kms:us-east-1:123:key/fixture")
    ec2 = FakeEc2()

    instance_id, public_ip = setup_aws.ensure_instance(
        FakeEc2Session(ec2),
        "sg-fixture",
        "profile-fixture",
    )

    assert (instance_id, public_ip) == ("i-release-fixture", "203.0.113.5")
    assert ec2.run_kwargs is not None
    ebs = ec2.run_kwargs["BlockDeviceMappings"][0]["Ebs"]
    assert ebs["Encrypted"] is True
    assert ebs["KmsKeyId"] == "arn:aws:kms:us-east-1:123:key/fixture"


def test_ensure_instance_rejects_an_unencrypted_existing_host(monkeypatch):
    monkeypatch.setenv("EC2_INSTANCE_NAME", "release-fixture")
    with pytest.raises(RuntimeError, match="unencrypted EBS volumes"):
        setup_aws.ensure_instance(
            FakeEc2Session(FakeExistingEc2(encrypted=False)),  # type: ignore[arg-type]
            "sg-fixture",
            "profile-fixture",
        )
