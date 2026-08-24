"""Shared types for the Stacks tool belt.

Mirrors docs/architecture/tool_architecture.md section 2 exactly. Do not
add a field here that is not in that spec without updating the doc first.
"""
from __future__ import annotations

import enum
from datetime import datetime

from pydantic import BaseModel

LibraryId = str
BookingId = str
PatronId = str
DepartmentId = str
ILLRequestId = str
CirculationRecordId = str
HoldingId = str
CaseId = str
MemoryNamespace = str


class SensitivityFlag(str, enum.Enum):
    MINOR_ACCOUNT = "MINOR_ACCOUNT"
    HARDSHIP_PATTERN = "HARDSHIP_PATTERN"
    RARE_OR_SPECIAL_COLLECTIONS = "RARE_OR_SPECIAL_COLLECTIONS"
    POLICY_EXCEPTION_REQUIRED = "POLICY_EXCEPTION_REQUIRED"


class PolicyClauseRef(BaseModel):
    policy_name: str
    clause_id: str
    clause_text: str


class AuditActor(str, enum.Enum):
    AGENT = "AGENT"
    HUMAN = "HUMAN"


class ApprovalToken(BaseModel):
    token: str
    approver_role: str
    related_action_id: str


class RequesterSubstitutionPattern(BaseModel):
    request_frequency: int
    subject_areas: list[str]
    has_accepted_substitution_without_escalation: bool
    last_updated: datetime


class HardshipHistoryFact(BaseModel):
    flagged_at: datetime


class MemoryWriteInput(BaseModel):
    memory_namespace: MemoryNamespace
    strategy: str
    source_action_id: str
    extracted_fields: dict
    timestamp: datetime


def memory_namespace_for_patron(library_id: LibraryId, patron_id: PatronId) -> MemoryNamespace:
    """Build the library-id-qualified Memory namespace key.

    Deliberately library_id-qualified so a bare patron_id can never
    collide across two libraries in a multi-library deployment
    (tool_architecture.md section 2). Not used by Plan 1's tools directly
    (Memory is not wired yet) but defined here now so a later plan does
    not need to touch this file to add the read/write call sites.
    """
    return f"{library_id}:{patron_id}"
