# bff/deps.py
"""FastAPI dependencies: cookie extraction and JWT verification. The
verifier itself is swappable (a plain function returning a
CognitoClaimsVerifier instance), so tests override get_current_claims
directly via FastAPI's dependency_overrides rather than mocking JWKS
network calls.
"""
from __future__ import annotations

from fastapi import Cookie, HTTPException

from stacks.data.dynamodb_repository import DynamoDBLibraryDataRepository
from stacks.data.repository import LibraryDataRepository
from stacks.hitl.dynamodb_pending_approvals import DynamoDBPendingApprovalsSink
from stacks.hitl.pending_approvals import PendingApprovalsSink
from stacks.hooks.audit_log import AuditLogSink
from stacks.hooks.dynamodb_audit_log import DynamoDBAuditLogSink
from stacks.identity.claims import InvalidClaimsError, StaffIdentityClaims
from stacks.identity.cognito_verifier import CognitoClaimsVerifier
from stacks.memory.agentcore_store import AgentCoreMemoryStore
from stacks.memory.store import MemoryStore

from bff.clients.agent_runtime import AgentRuntimeClient, BedrockAgentCoreRuntimeClient
from bff.config import (
    AGENT_RUNTIME_ARN,
    AGENTCORE_MEMORY_ID,
    COGNITO_APP_CLIENT_ID,
    COGNITO_USER_POOL_ID,
    ENVIRONMENT,
    REGION,
    SESSION_COOKIE_NAME,
)

_verifier: CognitoClaimsVerifier | None = None
_repo: LibraryDataRepository | None = None
_pending_approvals_sink: PendingApprovalsSink | None = None
_audit_sink: AuditLogSink | None = None
_agent_runtime_client: AgentRuntimeClient | None = None
_memory: MemoryStore | None = None
_memory_initialized = False


def _get_verifier() -> CognitoClaimsVerifier:
    global _verifier
    if _verifier is None:
        _verifier = CognitoClaimsVerifier(user_pool_id=COGNITO_USER_POOL_ID, region=REGION, app_client_id=COGNITO_APP_CLIENT_ID)
    return _verifier


def get_current_claims(stacks_session: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME)) -> StaffIdentityClaims:
    if stacks_session is None:
        raise HTTPException(status_code=401, detail="not authenticated")
    try:
        return _get_verifier().verify(stacks_session)
    except InvalidClaimsError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


def get_repo() -> LibraryDataRepository:
    global _repo
    if _repo is None:
        _repo = DynamoDBLibraryDataRepository(region=REGION, environment=ENVIRONMENT)
    return _repo


def get_memory() -> MemoryStore | None:
    """Real AgentCore Memory when STACKS_AGENTCORE_MEMORY_ID is configured,
    None otherwise (fail-open: read endpoints show no recallSummary rather
    than erroring, matching main.py's own memory-optional convention).
    """
    global _memory, _memory_initialized
    if not _memory_initialized:
        _memory = AgentCoreMemoryStore(memory_id=AGENTCORE_MEMORY_ID, region=REGION) if AGENTCORE_MEMORY_ID else None
        _memory_initialized = True
    return _memory


def get_pending_approvals_sink() -> PendingApprovalsSink:
    global _pending_approvals_sink
    if _pending_approvals_sink is None:
        _pending_approvals_sink = DynamoDBPendingApprovalsSink(region=REGION, environment=ENVIRONMENT)
    return _pending_approvals_sink


def get_audit_sink() -> AuditLogSink:
    global _audit_sink
    if _audit_sink is None:
        _audit_sink = DynamoDBAuditLogSink(region=REGION, environment=ENVIRONMENT)
    return _audit_sink


def get_agent_runtime_client() -> AgentRuntimeClient:
    global _agent_runtime_client
    if _agent_runtime_client is None:
        _agent_runtime_client = BedrockAgentCoreRuntimeClient(region=REGION, agent_runtime_arn=AGENT_RUNTIME_ARN)
    return _agent_runtime_client
