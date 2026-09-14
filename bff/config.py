# bff/config.py
"""Env-driven BFF configuration. Plain os.environ reads, matching this
project's existing convention (main.py, scripts/provision_*.py) rather
than adding a new settings-library dependency.
"""
from __future__ import annotations

import os

REGION = os.environ.get("STACKS_AWS_REGION", "us-west-2")
ENVIRONMENT = os.environ.get("STACKS_ENVIRONMENT", "dev")
COGNITO_USER_POOL_ID = os.environ.get("STACKS_COGNITO_USER_POOL_ID", "")
COGNITO_APP_CLIENT_ID = os.environ.get("STACKS_COGNITO_APP_CLIENT_ID", "")
SESSION_COOKIE_NAME = "stacks_session"
AGENT_RUNTIME_ARN = os.environ.get("STACKS_AGENT_RUNTIME_ARN", "")
AGENTCORE_MEMORY_ID = os.environ.get("STACKS_AGENTCORE_MEMORY_ID", "")

# The one-click "Hackathon Judges" login path (bff/auth.py's
# judge_login route) signs in as this real, already-provisioned Cognito
# account entirely server-side -- the password is read from the server's
# own environment and never sent to or held by the browser, unlike a
# normal username/password login. No hardcoded default password: an
# unset STACKS_JUDGE_PASSWORD disables the route with a clear 503 rather
# than silently failing or (worse) shipping a real credential in source.
JUDGE_USERNAME = os.environ.get("STACKS_JUDGE_USERNAME", "test-branch-manager")
JUDGE_PASSWORD = os.environ.get("STACKS_JUDGE_PASSWORD", "")
