"""DynamoDB-backed PendingApprovalsSink. Satisfies
stacks.hitl.pending_approvals.PendingApprovalsSink exactly, mirroring
DynamoDBAuditLogSink's own structure (src/stacks/hooks/dynamodb_audit_log.py).
"""
from __future__ import annotations

import boto3
from boto3.dynamodb.conditions import Key

from stacks.hitl.pending_approvals import PendingApprovalRecord


class DynamoDBPendingApprovalsSink:
    def __init__(self, region: str, environment: str = "dev", boto_session: boto3.Session | None = None) -> None:
        session = boto_session or boto3.Session(region_name=region)
        resource = session.resource("dynamodb", region_name=region)
        self._table = resource.Table(f"Stacks-PendingApprovals-{environment}")

    def put(self, record: PendingApprovalRecord) -> None:
        self._table.put_item(Item=record.to_dict())

    def delete(self, library_id: str, case_id: str) -> None:
        self._table.delete_item(Key={"library_id": library_id, "case_id": case_id})

    def list_for_library(self, library_id: str) -> list[PendingApprovalRecord]:
        response = self._table.query(KeyConditionExpression=Key("library_id").eq(library_id))
        return [PendingApprovalRecord(**item) for item in response.get("Items", [])]
