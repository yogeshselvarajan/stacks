# scripts/upload_deployment_package.py
"""Uploads the built deployment package to the runtime-artifacts prefix
of Task 4's session-state bucket. Run after build_deployment_package.py:

    STACKS_SESSION_BUCKET=<Task 4's bucket_name output> \
      STACKS_AWS_REGION=us-west-2 python scripts/upload_deployment_package.py

Prints the values Task 7's dev.tfvars entries need.
"""
from __future__ import annotations

import os
from pathlib import Path

import boto3

REGION = os.environ.get("STACKS_AWS_REGION", "us-west-2")
BUCKET = os.environ["STACKS_SESSION_BUCKET"]
KEY = "runtime-artifacts/deployment_package.zip"
ZIP_PATH = Path(__file__).resolve().parent.parent / "build" / "deployment_package.zip"


def main() -> None:
    s3 = boto3.client("s3", region_name=REGION)
    s3.upload_file(str(ZIP_PATH), BUCKET, KEY)
    print(f"Uploaded to s3://{BUCKET}/{KEY}")
    print("Set these in infra/environments/dev.tfvars before Task 7's terraform apply:")
    print(f'  runtime_artifact_bucket = "{BUCKET}"')
    print(f'  runtime_artifact_key    = "{KEY}"')


if __name__ == "__main__":
    main()
