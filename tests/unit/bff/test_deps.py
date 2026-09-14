# tests/unit/bff/test_deps.py
"""I2 (final review fix round): get_agent_runtime_client() must fail
fast and clearly when STACKS_AGENT_RUNTIME_ARN is not configured, rather
than constructing a BedrockAgentCoreRuntimeClient against an empty ARN
and letting the first real invocation surface a confusing AWS API error.

No real AWS config is imported here -- the module-level config value is
monkeypatched directly on bff.deps (the name already imported into that
module's namespace), and the module-level client cache is reset first so
this test is independent of whatever earlier tests in the same process
may have already cached there.
"""
import pytest

from bff import deps


def test_get_agent_runtime_client_raises_a_clear_error_when_arn_is_not_configured(monkeypatch):
    monkeypatch.setattr(deps, "AGENT_RUNTIME_ARN", "")
    monkeypatch.setattr(deps, "_agent_runtime_client", None)

    with pytest.raises(RuntimeError, match="STACKS_AGENT_RUNTIME_ARN is not configured"):
        deps.get_agent_runtime_client()
