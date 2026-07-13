#!/usr/bin/env python3
"""Provision and bootstrap the least-privilege AWS release host.

This utility deliberately separates infrastructure creation from host bootstrap:
AWS APIs create only storage, an instance role, a security group, and an EC2
instance. SSH bootstrap performs the initial checked-out source, GHCR login,
and Let's Encrypt certificate issuance without placing registry credentials in
EC2 user data.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import ClientError


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} must be set")
    return value


def optional(name: str) -> str | None:
    value = os.environ.get(name, "").strip()
    return value or None


def aws_region() -> str:
    return required("AWS_REGION")


def instance_name() -> str:
    return required("EC2_INSTANCE_NAME")


def security_group_name() -> str:
    return required("EC2_SG_NAME")


def bucket_name() -> str:
    # Release artifacts may live in a distinct bucket from ordinary provider
    # data. Prefer the explicit release bucket so Object Lock and the EC2 read
    # role protect the same location stage_data_release.sh publishes to.
    return optional("DATA_RELEASE_BUCKET") or required("S3_BUCKET")


def release_prefix() -> str:
    prefix = os.environ.get("DATA_RELEASE_PREFIX", "investor-platform-data").strip("/")
    if not prefix:
        raise RuntimeError("DATA_RELEASE_PREFIX must not be empty")
    return prefix


def object_lock_retention_days() -> int:
    value = int(os.environ.get("S3_OBJECT_LOCK_RETENTION_DAYS", "365"))
    if value < 1:
        raise RuntimeError("S3_OBJECT_LOCK_RETENTION_DAYS must be at least one day")
    return value


def session() -> boto3.Session:
    # Let boto3 use the standard AWS credential chain (OIDC, profile, or an
    # instance role). Never force long-lived access keys into this script.
    return boto3.Session(region_name=aws_region())


def _client_error_code(error: ClientError) -> str:
    return str(error.response.get("Error", {}).get("Code", ""))


def ensure_bucket(aws: boto3.Session) -> None:
    """Create a private, versioned, Object-Locked release bucket if necessary."""
    s3 = aws.client("s3")
    name = bucket_name()
    try:
        s3.head_bucket(Bucket=name)
    except ClientError as error:
        if _client_error_code(error) not in {"404", "NoSuchBucket"}:
            raise
        # Object Lock can only be enabled while a bucket is created. Require it
        # from the start rather than claiming ordinary S3 versioning is an
        # immutable release store.
        kwargs: dict[str, Any] = {"Bucket": name, "ObjectLockEnabledForBucket": True}
        if aws_region() != "us-east-1":
            kwargs["CreateBucketConfiguration"] = {"LocationConstraint": aws_region()}
        s3.create_bucket(**kwargs)

    s3.put_bucket_versioning(
        Bucket=name,
        VersioningConfiguration={"Status": "Enabled"},
    )
    try:
        lock_configuration = s3.get_object_lock_configuration(Bucket=name)
    except ClientError as error:
        if _client_error_code(error) != "ObjectLockConfigurationNotFoundError":
            raise
        raise RuntimeError(
            f"Bucket {name} was created without Object Lock. Create a new "
            "Object-Lock-enabled release bucket and set S3_BUCKET to it; "
            "Object Lock cannot be enabled on an existing bucket."
        ) from error
    if lock_configuration.get("ObjectLockConfiguration", {}).get("ObjectLockEnabled") != "Enabled":
        raise RuntimeError(f"Bucket {name} does not have Object Lock enabled")
    s3.put_object_lock_configuration(
        Bucket=name,
        ObjectLockConfiguration={
            "ObjectLockEnabled": "Enabled",
            "Rule": {
                "DefaultRetention": {
                    "Mode": "COMPLIANCE",
                    "Days": object_lock_retention_days(),
                }
            },
        },
    )
    s3.put_public_access_block(
        Bucket=name,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True,
        },
    )
    s3.put_bucket_encryption(
        Bucket=name,
        ServerSideEncryptionConfiguration={
            "Rules": [
                {
                    "ApplyServerSideEncryptionByDefault": {
                        "SSEAlgorithm": "AES256",
                    }
                }
            ]
        },
    )
    # A retained version cannot be deleted, but an ordinary delete marker
    # could still hide it from a normal GetObject. Deny delete operations for
    # release prefixes so a deployed URI never silently resolves to a marker.
    release_deny_statement = {
        "Sid": "DenyDeleteImmutableInvestorReleaseObjects",
        "Effect": "Deny",
        "Principal": "*",
        "Action": ["s3:DeleteObject", "s3:DeleteObjectVersion"],
        "Resource": [f"arn:aws:s3:::{name}/{release_prefix()}/*"],
    }
    try:
        bucket_policy = json.loads(s3.get_bucket_policy(Bucket=name)["Policy"])
    except ClientError as error:
        if _client_error_code(error) != "NoSuchBucketPolicy":
            raise
        bucket_policy = {"Version": "2012-10-17", "Statement": []}
    statements = bucket_policy.setdefault("Statement", [])
    if not isinstance(statements, list):
        raise RuntimeError(f"Bucket {name} has an invalid policy Statement")
    bucket_policy["Statement"] = [
        statement
        for statement in statements
        if statement.get("Sid") != release_deny_statement["Sid"]
    ]
    bucket_policy["Statement"].append(release_deny_statement)
    s3.put_bucket_policy(Bucket=name, Policy=json.dumps(bucket_policy))
    print(f"Ensured private, versioned, Object-Locked data bucket: {name}")


def ensure_instance_profile(aws: boto3.Session) -> str:
    """Create an EC2 role restricted to this release bucket/prefix."""
    iam = aws.client("iam")
    role_name = f"{instance_name()}-release-role"
    profile_name = f"{instance_name()}-release-profile"
    prefix = release_prefix()
    assume_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "ec2.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }
        ],
    }
    try:
        iam.get_role(RoleName=role_name)
    except iam.exceptions.NoSuchEntityException:
        iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(assume_policy),
            Description="Read-only immutable investor-platform data releases",
        )

    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "ListOnlyReleasePrefix",
                "Effect": "Allow",
                "Action": ["s3:ListBucket"],
                "Resource": [f"arn:aws:s3:::{bucket_name()}"],
                "Condition": {"StringLike": {"s3:prefix": [f"{prefix}/*"]}},
            },
            {
                "Sid": "ReadOnlyReleaseObjects",
                "Effect": "Allow",
                "Action": ["s3:GetObject", "s3:GetObjectVersion"],
                "Resource": [f"arn:aws:s3:::{bucket_name()}/{prefix}/*"],
            },
        ],
    }
    iam.put_role_policy(
        RoleName=role_name,
        PolicyName="read-immutable-investor-release",
        PolicyDocument=json.dumps(policy),
    )

    try:
        iam.get_instance_profile(InstanceProfileName=profile_name)
    except iam.exceptions.NoSuchEntityException:
        iam.create_instance_profile(InstanceProfileName=profile_name)
        # IAM can take a moment to make a newly created profile attachable.
        time.sleep(2)
        iam.add_role_to_instance_profile(InstanceProfileName=profile_name, RoleName=role_name)

    print(f"Ensured least-privilege EC2 instance profile: {profile_name}")
    return profile_name


def _default_vpc(ec2: Any) -> str:
    configured = optional("VPC_ID")
    if configured:
        return configured
    vpcs = ec2.describe_vpcs(Filters=[{"Name": "is-default", "Values": ["true"]}])["Vpcs"]
    if not vpcs:
        raise RuntimeError("VPC_ID must be set when the account has no default VPC")
    return str(vpcs[0]["VpcId"])


def _ingress_matches(permission: dict[str, Any], port: int, cidr: str) -> bool:
    return (
        permission.get("IpProtocol") == "tcp"
        and permission.get("FromPort") == port
        and permission.get("ToPort") == port
        and any(range_.get("CidrIp") == cidr for range_ in permission.get("IpRanges", []))
    )


def _is_unexpected_public_ingress(permission: dict[str, Any], ssh_cidr: str) -> bool:
    public_ranges = {entry.get("CidrIp") for entry in permission.get("IpRanges", [])}
    if not public_ranges:
        return False
    if permission.get("IpProtocol") == "-1":
        return True
    if permission.get("IpProtocol") != "tcp":
        return "0.0.0.0/0" in public_ranges
    from_port = int(permission.get("FromPort", -1))
    to_port = int(permission.get("ToPort", -1))
    for cidr in public_ranges:
        allowed = (
            cidr == "0.0.0.0/0"
            and from_port == to_port
            and from_port in {80, 443}
        ) or (cidr == ssh_cidr and from_port == to_port == 22)
        if not allowed:
            return True
    return False


def ensure_security_group(aws: boto3.Session) -> str:
    """Permit only HTTPS/HTTP publicly and SSH from an operator CIDR."""
    ec2 = aws.client("ec2")
    name = security_group_name()
    vpc_id = _default_vpc(ec2)
    ssh_cidr = required("ALLOWED_SSH_CIDR")

    try:
        group = ec2.describe_security_groups(
            Filters=[
                {"Name": "group-name", "Values": [name]},
                {"Name": "vpc-id", "Values": [vpc_id]},
            ]
        )["SecurityGroups"][0]
    except IndexError:
        created = ec2.create_security_group(
            GroupName=name,
            Description="Investor platform: public TLS gateway only; no backend ingress",
            VpcId=vpc_id,
        )
        group = ec2.describe_security_groups(GroupIds=[created["GroupId"]])["SecurityGroups"][0]

    group_id = str(group["GroupId"])
    desired = (
        (22, ssh_cidr, "SSH from approved operator network"),
        (80, "0.0.0.0/0", "HTTP for ACME challenge and HTTPS redirect"),
        (443, "0.0.0.0/0", "HTTPS gateway"),
    )
    current = group.get("IpPermissions", [])
    for port, cidr, description in desired:
        if any(_ingress_matches(permission, port, cidr) for permission in current):
            continue
        try:
            ec2.authorize_security_group_ingress(
                GroupId=group_id,
                IpPermissions=[
                    {
                        "IpProtocol": "tcp",
                        "FromPort": port,
                        "ToPort": port,
                        "IpRanges": [{"CidrIp": cidr, "Description": description}],
                    }
                ],
            )
        except ClientError as error:
            if _client_error_code(error) != "InvalidPermission.Duplicate":
                raise

    refreshed = ec2.describe_security_groups(GroupIds=[group_id])["SecurityGroups"][0]
    unexpected = [
        permission
        for permission in refreshed.get("IpPermissions", [])
        if _is_unexpected_public_ingress(permission, ssh_cidr)
    ]
    if unexpected:
        raise RuntimeError(
            "Security group has unexpected public ingress. Remove it before deploying: "
            + json.dumps(unexpected)
        )
    print(f"Ensured least-privilege security group: {group_id}")
    return group_id


def _user_data() -> str:
    return """#!/usr/bin/env bash
set -Eeuo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates curl git awscli certbot docker.io docker-compose-plugin postgresql-client
usermod -aG docker ubuntu
install -d -o ubuntu -g ubuntu \
  /opt/rd-alpha /opt/rd-alpha-data /opt/rd-alpha-backups \
  /opt/rd-alpha-certs /opt/rd-alpha-certbot-webroot
"""


def _running_instance(ec2: Any) -> dict[str, Any] | None:
    response = ec2.describe_instances(
        Filters=[
            {"Name": "tag:Name", "Values": [instance_name()]},
            {"Name": "instance-state-name", "Values": ["pending", "running"]},
        ]
    )
    for reservation in response["Reservations"]:
        if reservation["Instances"]:
            return reservation["Instances"][0]
    return None


def ensure_instance(aws: boto3.Session, group_id: str, profile_name: str) -> tuple[str, str]:
    """Launch a host that can read only immutable release data."""
    ec2 = aws.client("ec2")
    existing = _running_instance(ec2)
    if existing:
        volume_ids = [
            str(mapping["Ebs"]["VolumeId"])
            for mapping in existing.get("BlockDeviceMappings", [])
            if mapping.get("Ebs", {}).get("VolumeId")
        ]
        if volume_ids:
            volumes = ec2.describe_volumes(VolumeIds=volume_ids)["Volumes"]
            unencrypted = [str(volume["VolumeId"]) for volume in volumes if not volume.get("Encrypted")]
            if unencrypted:
                raise RuntimeError(
                    "Existing release host has unencrypted EBS volumes; migrate it before deployment: "
                    + ", ".join(unencrypted)
                )
        instance_id = str(existing["InstanceId"])
        public_ip = str(existing.get("PublicIpAddress") or "")
        if not public_ip:
            ec2.get_waiter("instance_running").wait(InstanceIds=[instance_id])
            existing = ec2.describe_instances(InstanceIds=[instance_id])["Reservations"][0]["Instances"][0]
            public_ip = str(existing["PublicIpAddress"])
        return instance_id, public_ip

    image_id = required("EC2_AMI_ID")
    key_name = required("EC2_KEY_NAME")
    instance_type = os.environ.get("EC2_INSTANCE_TYPE", "t3.large")
    root_volume: dict[str, Any] = {
        "VolumeSize": 100,
        "VolumeType": "gp3",
        "DeleteOnTermination": True,
        "Encrypted": True,
    }
    if kms_key_id := optional("EBS_KMS_KEY_ID"):
        root_volume["KmsKeyId"] = kms_key_id
    response = ec2.run_instances(
        ImageId=image_id,
        InstanceType=instance_type,
        KeyName=key_name,
        SecurityGroupIds=[group_id],
        IamInstanceProfile={"Name": profile_name},
        MinCount=1,
        MaxCount=1,
        UserData=_user_data(),
        MetadataOptions={
            "HttpTokens": "required",
            "HttpEndpoint": "enabled",
            "HttpPutResponseHopLimit": 1,
        },
        BlockDeviceMappings=[
            {
                "DeviceName": "/dev/sda1",
                "Ebs": root_volume,
            }
        ],
        TagSpecifications=[
            {
                "ResourceType": "instance",
                "Tags": [{"Key": "Name", "Value": instance_name()}],
            }
        ],
    )
    instance_id = str(response["Instances"][0]["InstanceId"])
    ec2.get_waiter("instance_running").wait(InstanceIds=[instance_id])
    instance = ec2.describe_instances(InstanceIds=[instance_id])["Reservations"][0]["Instances"][0]
    return instance_id, str(instance["PublicIpAddress"])


def configure_dns(aws: boto3.Session, public_ip: str) -> None:
    """Point the required DNS hostname at the created instance."""
    hostname = required("PUBLIC_HOSTNAME").rstrip(".")
    zone_id = required("ROUTE53_HOSTED_ZONE_ID")
    route53 = aws.client("route53")
    route53.change_resource_record_sets(
        HostedZoneId=zone_id,
        ChangeBatch={
            "Comment": "Investor platform release host",
            "Changes": [
                {
                    "Action": "UPSERT",
                    "ResourceRecordSet": {
                        "Name": hostname,
                        "Type": "A",
                        "TTL": 60,
                        "ResourceRecords": [{"Value": public_ip}],
                    },
                }
            ],
        },
    )
    print(f"Pointed {hostname} at {public_ip}; wait for DNS propagation before TLS bootstrap.")


def _ssh_command(host: str, remote_command: str) -> list[str]:
    key_path = Path(required("BOOTSTRAP_SSH_KEY")).expanduser()
    if not key_path.is_file():
        raise RuntimeError(f"BOOTSTRAP_SSH_KEY does not exist: {key_path}")
    return [
        "ssh",
        "-o",
        "StrictHostKeyChecking=accept-new",
        "-i",
        str(key_path),
        f"{os.environ.get('BOOTSTRAP_SSH_USER', 'ubuntu')}@{host}",
        remote_command,
    ]


def _run_ssh(host: str, remote_command: str, *, input_text: str | None = None) -> None:
    subprocess.run(
        _ssh_command(host, remote_command),
        input=input_text,
        text=True,
        check=True,
    )


def bootstrap_host(host: str) -> None:
    """Perform checkout, registry login, and certificate setup over SSH."""
    repository_url = required("REPOSITORY_URL")
    repository_ref = required("REPOSITORY_REF")
    deploy_path = required("DEPLOY_PATH")
    certs_dir = required("CERTS_DIR")
    certbot_webroot = required("CERTBOT_WEBROOT")
    hostname = required("PUBLIC_HOSTNAME").rstrip(".")
    email = required("LETSENCRYPT_EMAIL")
    quoted = shlex.quote
    checkout = f"""
set -Eeuo pipefail
sudo install -d -o "$(id -un)" -g "$(id -gn)" {quoted(deploy_path)}
if [[ -d {quoted(deploy_path)}/.git ]]; then
  git -C {quoted(deploy_path)} fetch --prune origin
else
  git clone {quoted(repository_url)} {quoted(deploy_path)}
fi
git -C {quoted(deploy_path)} checkout --detach {quoted(repository_ref)}
sudo install -d -o "$(id -un)" -g "$(id -gn)" {quoted(certs_dir)} {quoted(certbot_webroot)}
"""
    _run_ssh(host, checkout)

    registry_user = required("GHCR_USERNAME")
    registry_token = required("GHCR_READ_TOKEN")
    _run_ssh(
        host,
        f"set -Eeuo pipefail; docker login ghcr.io --username {quoted(registry_user)} --password-stdin",
        input_text=f"{registry_token}\n",
    )

    tls = f"""
set -Eeuo pipefail
sudo certbot certonly --standalone --non-interactive --agree-tos \
  --email {quoted(email)} --keep-until-expiring -d {quoted(hostname)}
sudo install -d -o "$(id -un)" -g "$(id -gn)" {quoted(certs_dir)}
sudo cp /etc/letsencrypt/live/{quoted(hostname)}/fullchain.pem {quoted(certs_dir)}/fullchain.pem
sudo cp /etc/letsencrypt/live/{quoted(hostname)}/privkey.pem {quoted(certs_dir)}/privkey.pem
sudo chown "$(id -un):$(id -gn)" {quoted(certs_dir)}/fullchain.pem {quoted(certs_dir)}/privkey.pem
sudo chmod 0644 {quoted(certs_dir)}/fullchain.pem
sudo chmod 0600 {quoted(certs_dir)}/privkey.pem
"""
    _run_ssh(host, tls)
    renewal = f"""
set -Eeuo pipefail
sudo tee /usr/local/sbin/rd-alpha-renew-tls >/dev/null <<'EOF'
#!/usr/bin/env bash
set -Eeuo pipefail

DEPLOY_PATH={quoted(deploy_path)}
CERTS_DIR={quoted(certs_dir)}
LETSENCRYPT_HOSTNAME={quoted(hostname)}
COMPOSE_FILE="${{DEPLOY_PATH}}/deploy/docker-compose.yml"
ENV_FILE="${{DEPLOY_PATH}}/deploy/.env"

compose() {{
  docker compose --env-file "${{ENV_FILE}}" -f "${{COMPOSE_FILE}}" "$@"
}}

frontend_stopped=false
if [[ -f "${{ENV_FILE}}" && -f "${{COMPOSE_FILE}}" ]]; then
  compose stop frontend || true
  frontend_stopped=true
fi
restart_frontend() {{
  if [[ "${{frontend_stopped}}" == true ]]; then
    compose up -d frontend || true
  fi
}}
trap restart_frontend EXIT

certbot renew --standalone --non-interactive
install -d -m 0755 "${{CERTS_DIR}}"
install -m 0644 "/etc/letsencrypt/live/${{LETSENCRYPT_HOSTNAME}}/fullchain.pem" "${{CERTS_DIR}}/fullchain.pem"
install -m 0600 "/etc/letsencrypt/live/${{LETSENCRYPT_HOSTNAME}}/privkey.pem" "${{CERTS_DIR}}/privkey.pem"
if [[ "${{frontend_stopped}}" == true ]]; then
  compose up -d frontend
  frontend_stopped=false
fi
EOF
sudo chmod 0750 /usr/local/sbin/rd-alpha-renew-tls
sudo tee /etc/systemd/system/rd-alpha-tls-renew.service >/dev/null <<'EOF'
[Unit]
Description=Renew and install investor platform TLS certificate

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/rd-alpha-renew-tls
EOF
sudo tee /etc/systemd/system/rd-alpha-tls-renew.timer >/dev/null <<'EOF'
[Unit]
Description=Daily investor platform TLS renewal check

[Timer]
OnCalendar=*-*-* 03:17:00 UTC
RandomizedDelaySec=30m
Persistent=true

[Install]
WantedBy=timers.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now rd-alpha-tls-renew.timer
"""
    _run_ssh(host, renewal)
    print(f"Bootstrapped checkout, GHCR login, and TLS certificate on {host}")


def stage_data(universe_version: str) -> None:
    root = Path(__file__).resolve().parent.parent
    subprocess.run(
        [str(root / "scripts" / "stage_data_release.sh"), "--universe-version", universe_version],
        cwd=root,
        check=True,
        env=os.environ.copy(),
    )


def destroy(aws: boto3.Session) -> None:
    """Destroy only explicitly named resources after a deliberate confirmation."""
    ec2 = aws.client("ec2")
    instance = _running_instance(ec2)
    if instance:
        ec2.terminate_instances(InstanceIds=[instance["InstanceId"]])
        print(f"Terminating instance {instance['InstanceId']}")
    print(
        "Instance termination requested. Bucket, IAM role, and security group are retained "
        "to prevent accidental loss of immutable releases."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Provision immutable investor-platform infrastructure")
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--create", action="store_true", help="Create bucket, role, security group, and EC2")
    actions.add_argument("--configure-dns", action="store_true", help="Upsert PUBLIC_HOSTNAME DNS record")
    actions.add_argument("--bootstrap", action="store_true", help="SSH bootstrap checkout, GHCR login, and TLS")
    actions.add_argument("--stage-data", action="store_true", help="Stage one sealed immutable data artifact")
    actions.add_argument("--destroy", action="store_true", help="Terminate the named EC2 host only")
    parser.add_argument("--host", help="Public EC2 host/IP for --bootstrap or --configure-dns")
    parser.add_argument("--universe-version", help="Required with --stage-data")
    parser.add_argument("--confirm-destroy", action="store_true")
    args = parser.parse_args()

    if args.stage_data:
        if not args.universe_version:
            raise SystemExit("--universe-version is required with --stage-data")
        stage_data(args.universe_version)
        return

    aws = session()
    if args.create:
        ensure_bucket(aws)
        profile_name = ensure_instance_profile(aws)
        group_id = ensure_security_group(aws)
        instance_id, public_ip = ensure_instance(aws, group_id, profile_name)
        print(json.dumps({"instance_id": instance_id, "public_ip": public_ip}, sort_keys=True))
        if optional("PUBLIC_HOSTNAME") and optional("ROUTE53_HOSTED_ZONE_ID"):
            configure_dns(aws, public_ip)
        return

    if args.configure_dns:
        if not args.host:
            raise SystemExit("--host is required with --configure-dns")
        configure_dns(aws, args.host)
        return

    if args.bootstrap:
        if not args.host:
            raise SystemExit("--host is required with --bootstrap")
        bootstrap_host(args.host)
        return

    if not args.confirm_destroy:
        raise SystemExit("--destroy requires --confirm-destroy")
    destroy(aws)


if __name__ == "__main__":
    try:
        main()
    except (ClientError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"infrastructure setup failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
