"""DynamoDB-backed AuditLogSink, satisfying the same append() signature
as the in-memory AuditLogSink (src/stacks/hooks/audit_log.py) so
AuditLogHook works unmodified when wired to this sink instead. Uses a
per-library atomic counter item (DynamoDB's standard atomic-counter
pattern, one update_item ADD call) to preserve exact insertion order
across process restarts. The in-memory sink's itertools.count() only
guaranteed order within one process's lifetime, which a real deployment
(a fresh AgentCore Runtime invocation per call) does not have. The
counter lives at sequence=0 for each library_id and is never itself a
real audit record. Every real record's sequence is >= 1.
"""
from __future__ import annotations

import boto3
from boto3.dynamodb.conditions import Key

from stacks.hooks.audit_log import AuditLogRecord
from stacks.types import AuditActor


class DynamoDBAuditLogSink:
    def __init__(self, region: str, environment: str = "dev", boto_session: boto3.Session | None = None) -> None:
        session = boto_session or boto3.Session(region_name=region)
        resource = session.resource("dynamodb", region_name=region)
        self._table = resource.Table(f"Stacks-AuditLog-{environment}")

    def append(self, record: AuditLogRecord) -> None:
        counter_response = self._table.update_item(
            Key={"library_id": record.library_id, "sequence": 0},
            UpdateExpression="ADD next_sequence :incr",
            ExpressionAttributeValues={":incr": 1},
            ReturnValues="UPDATED_NEW",
        )
        record.sequence = int(counter_response["Attributes"]["next_sequence"])
        item = record.to_dict()
        if item.get("actor") is not None:
            item["actor"] = item["actor"].value
        self._table.put_item(Item=item)

    def all(self, library_id: str) -> list[AuditLogRecord]:
        """Requires library_id (unlike the in-memory sink's argument-less
        all(), which was already scoped to one session's own sink) since
        this sink is shared real infrastructure. An unscoped scan would
        be both a cross-tenant leak risk and an unbounded-cost query.
        AuditLogHook never calls this method, only append(), so this
        signature difference does not affect existing Hook wiring."""
        response = self._table.query(
            KeyConditionExpression=Key("library_id").eq(library_id) & Key("sequence").gt(0),
        )
        records = []
        for item in response.get("Items", []):
            item = dict(item)
            item.pop("next_sequence", None)
            if item.get("actor") is not None:
                item["actor"] = AuditActor(item["actor"])
            records.append(AuditLogRecord(**item))
        return records
