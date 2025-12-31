#!/usr/bin/env python3
"""
PATH: deploy/setup_aws.py
PURPOSE:
  - One-click AWS infrastructure provisioning (S3 bucket + EC2 instance)
  - Uploads local data to S3
  - Configures security groups and SSH access

ROLE IN ARCHITECTURE:
  - Infrastructure provisioning layer

USAGE:
  python deploy/setup_aws.py --create    # Create all resources
  python deploy/setup_aws.py --upload    # Upload data to S3
  python deploy/setup_aws.py --destroy   # Tear down resources
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

# Configuration - Override via environment variables
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
S3_BUCKET_NAME = os.environ.get("S3_BUCKET", "your-bucket-name")
EC2_INSTANCE_TYPE = os.environ.get("EC2_INSTANCE_TYPE", "c5.xlarge")
EC2_AMI_ID = os.environ.get("EC2_AMI_ID", "ami-0c7217cdde317cfec")  # Ubuntu 22.04 LTS
EC2_KEY_NAME = os.environ.get("EC2_KEY_NAME", "your-key-pair")
SECURITY_GROUP_NAME = os.environ.get("EC2_SG_NAME", "rd-alpha-sg")
INSTANCE_NAME = os.environ.get("EC2_INSTANCE_NAME", "rd-alpha-server")

# AWS Credentials from environment variables (required)
AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "")


def get_boto_session():
    """Create boto3 session with credentials."""
    return boto3.Session(
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        region_name=AWS_REGION,
    )


def create_s3_bucket(session):
    """Create S3 bucket with versioning enabled."""
    s3 = session.client("s3")
    
    try:
        if AWS_REGION == "us-east-1":
            s3.create_bucket(Bucket=S3_BUCKET_NAME)
        else:
            s3.create_bucket(
                Bucket=S3_BUCKET_NAME,
                CreateBucketConfiguration={"LocationConstraint": AWS_REGION},
            )
        print(f"✓ Created S3 bucket: {S3_BUCKET_NAME}")
    except ClientError as e:
        if e.response["Error"]["Code"] == "BucketAlreadyOwnedByYou":
            print(f"✓ S3 bucket already exists: {S3_BUCKET_NAME}")
        else:
            raise
    
    # Enable versioning
    s3.put_bucket_versioning(
        Bucket=S3_BUCKET_NAME,
        VersioningConfiguration={"Status": "Enabled"},
    )
    print("✓ Enabled S3 versioning")
    
    return S3_BUCKET_NAME


def create_security_group(session):
    """Create security group with required ports."""
    ec2 = session.client("ec2")
    
    # Get default VPC
    vpcs = ec2.describe_vpcs(Filters=[{"Name": "is-default", "Values": ["true"]}])
    vpc_id = vpcs["Vpcs"][0]["VpcId"] if vpcs["Vpcs"] else None
    
    try:
        response = ec2.create_security_group(
            GroupName=SECURITY_GROUP_NAME,
            Description="Security group for FSE R&D Alpha server",
            VpcId=vpc_id,
        )
        sg_id = response["GroupId"]
        print(f"✓ Created security group: {sg_id}")
    except ClientError as e:
        if e.response["Error"]["Code"] == "InvalidGroup.Duplicate":
            sgs = ec2.describe_security_groups(GroupNames=[SECURITY_GROUP_NAME])
            sg_id = sgs["SecurityGroups"][0]["GroupId"]
            print(f"✓ Security group already exists: {sg_id}")
            return sg_id
        raise
        
        # Add ingress rules
    rules = [
        {"port": 22, "desc": "SSH"},
        {"port": 80, "desc": "HTTP"},
        {"port": 443, "desc": "HTTPS"},
        {"port": 8000, "desc": "FastAPI"},
    ]
    
    for rule in rules:
        try:
            ec2.authorize_security_group_ingress(
                GroupId=sg_id,
                IpPermissions=[{
                        "IpProtocol": "tcp",
                        "FromPort": rule["port"],
                        "ToPort": rule["port"],
                    "IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": rule["desc"]}],
                }],
            )
            print(f"  ✓ Added rule: {rule['desc']} (port {rule['port']})")
        except ClientError as e:
            if "InvalidPermission.Duplicate" in str(e):
                pass
            else:
                raise
    
        return sg_id
        

def create_key_pair(session):
    """Create EC2 key pair and save to file."""
    ec2 = session.client("ec2")
    key_path = Path.home() / ".ssh" / f"{EC2_KEY_NAME}.pem"
    
    try:
        response = ec2.create_key_pair(KeyName=EC2_KEY_NAME)
        key_path.parent.mkdir(parents=True, exist_ok=True)
        key_path.write_text(response["KeyMaterial"])
        key_path.chmod(0o400)
        print(f"✓ Created key pair: {key_path}")
    except ClientError as e:
        if e.response["Error"]["Code"] == "InvalidKeyPair.Duplicate":
            print(f"✓ Key pair already exists: {EC2_KEY_NAME}")
            if not key_path.exists():
                print(f"  ⚠ Warning: Key file not found at {key_path}")
        else:
            raise
    
    return EC2_KEY_NAME


def create_ec2_instance(session, sg_id, key_name):
    """Launch EC2 instance with user data script."""
    ec2 = session.client("ec2")
    
    # Check for existing instance
    instances = ec2.describe_instances(
        Filters=[
            {"Name": "tag:Name", "Values": [INSTANCE_NAME]},
            {"Name": "instance-state-name", "Values": ["running", "pending"]},
        ]
    )
    
    for reservation in instances["Reservations"]:
        for instance in reservation["Instances"]:
            instance_id = instance["InstanceId"]
            public_ip = instance.get("PublicIpAddress", "pending...")
            print(f"✓ Instance already exists: {instance_id} ({public_ip})")
            return instance_id, public_ip
    
    # User data script to install dependencies
    user_data = """#!/bin/bash
set -e

# Update system
apt-get update && apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
usermod -aG docker ubuntu

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Install Python 3.11
add-apt-repository ppa:deadsnakes/ppa -y
apt-get install -y python3.11 python3.11-venv python3-pip

# Install Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs

# Install PostgreSQL client tools
apt-get install -y postgresql-client

# Clone repository
cd /home/ubuntu
git clone https://github.com/vastdreams/rd-alpha-research.git || true

echo "✓ Setup complete" > /home/ubuntu/setup_done.txt
"""

    response = ec2.run_instances(
        ImageId=EC2_AMI_ID,
        InstanceType=EC2_INSTANCE_TYPE,
        KeyName=key_name,
        SecurityGroupIds=[sg_id],
        MinCount=1,
        MaxCount=1,
        BlockDeviceMappings=[{
                "DeviceName": "/dev/sda1",
                "Ebs": {
                    "VolumeSize": 100,
                    "VolumeType": "gp3",
                    "DeleteOnTermination": True,
                },
        }],
        UserData=user_data,
        TagSpecifications=[{
                "ResourceType": "instance",
            "Tags": [{"Key": "Name", "Value": INSTANCE_NAME}],
        }],
    )
    
    instance_id = response["Instances"][0]["InstanceId"]
    print(f"✓ Launched EC2 instance: {instance_id}")
    
    # Wait for instance to be running
    print("  Waiting for instance to start...")
    waiter = ec2.get_waiter("instance_running")
    waiter.wait(InstanceIds=[instance_id])
    
    # Get public IP
    instance = ec2.describe_instances(InstanceIds=[instance_id])
    public_ip = instance["Reservations"][0]["Instances"][0].get("PublicIpAddress")
    print(f"✓ Instance running at: {public_ip}")
    
    return instance_id, public_ip


def upload_data_to_s3(session):
    """Upload local data to S3 bucket."""
    s3 = session.client("s3")
    data_dir = Path(__file__).parent.parent / "data"
    
    folders_to_upload = ["raw/annual_reports", "raw/xbrl", "reference"]
    
    for folder in folders_to_upload:
        folder_path = data_dir / folder
        if not folder_path.exists():
            print(f"  ⚠ Skipping {folder} (not found)")
            continue
        
        files = list(folder_path.rglob("*"))
        files = [f for f in files if f.is_file()]
        print(f"  Uploading {len(files)} files from {folder}...")
        
        for file_path in files:
            relative_path = file_path.relative_to(data_dir)
            s3_key = str(relative_path)
            try:
                s3.upload_file(str(file_path), S3_BUCKET_NAME, s3_key)
            except Exception as e:
                print(f"    ⚠ Failed to upload {file_path}: {e}")
        
        print(f"  ✓ Uploaded {folder}")
    
    print("✓ Data upload complete")


def destroy_resources(session):
    """Tear down all AWS resources."""
    ec2 = session.client("ec2")
    s3 = session.resource("s3")
    
    # Terminate EC2 instances
    instances = ec2.describe_instances(
        Filters=[{"Name": "tag:Name", "Values": [INSTANCE_NAME]}]
    )
    for reservation in instances["Reservations"]:
        for instance in reservation["Instances"]:
            if instance["State"]["Name"] not in ["terminated", "shutting-down"]:
                ec2.terminate_instances(InstanceIds=[instance["InstanceId"]])
                print(f"✓ Terminated instance: {instance['InstanceId']}")
    
    # Delete S3 bucket contents and bucket
    try:
        bucket = s3.Bucket(S3_BUCKET_NAME)
        bucket.object_versions.delete()
        bucket.delete()
        print(f"✓ Deleted S3 bucket: {S3_BUCKET_NAME}")
    except Exception as e:
        print(f"  ⚠ Could not delete S3 bucket: {e}")
    
    # Delete security group (wait for instance to terminate)
    time.sleep(30)
    try:
        ec2.delete_security_group(GroupName=SECURITY_GROUP_NAME)
        print(f"✓ Deleted security group: {SECURITY_GROUP_NAME}")
    except Exception as e:
        print(f"  ⚠ Could not delete security group: {e}")
    
    # Delete key pair
    try:
        ec2.delete_key_pair(KeyName=EC2_KEY_NAME)
        key_path = Path.home() / ".ssh" / f"{EC2_KEY_NAME}.pem"
        if key_path.exists():
            key_path.unlink()
        print(f"✓ Deleted key pair: {EC2_KEY_NAME}")
    except Exception as e:
        print(f"  ⚠ Could not delete key pair: {e}")


def print_connection_info(public_ip):
    """Print SSH and access instructions."""
    key_path = Path.home() / ".ssh" / f"{EC2_KEY_NAME}.pem"
    print("\n" + "=" * 60)
    print("CONNECTION INFO")
    print("=" * 60)
    print(f"SSH:     ssh -i {key_path} ubuntu@{public_ip}")
    print(f"API:     http://{public_ip}:8000")
    print(f"Frontend: http://{public_ip}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="AWS Infrastructure Setup")
    parser.add_argument("--create", action="store_true", help="Create all resources")
    parser.add_argument("--upload", action="store_true", help="Upload data to S3")
    parser.add_argument("--destroy", action="store_true", help="Destroy all resources")
    args = parser.parse_args()
    
    session = get_boto_session()

    if args.destroy:
        print("Destroying AWS resources...")
        destroy_resources(session)
        return
    
    if args.create:
        print("Creating AWS infrastructure...")
        create_s3_bucket(session)
        sg_id = create_security_group(session)
        key_name = create_key_pair(session)
        instance_id, public_ip = create_ec2_instance(session, sg_id, key_name)
        print_connection_info(public_ip)

    if args.upload:
        print("Uploading data to S3...")
        upload_data_to_s3(session)

    if not any([args.create, args.upload, args.destroy]):
        parser.print_help()


if __name__ == "__main__":
    main()
