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
