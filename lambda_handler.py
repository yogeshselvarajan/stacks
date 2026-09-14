# lambda_handler.py
"""AWS Lambda entrypoint for the BFF, exposed via a Lambda Function URL.
Wraps the same bff.main.app FastAPI instance the local uvicorn dev server
runs, via Mangum's ASGI adapter, so the deployed BFF is exactly the code
already tested against real AWS, not a reimplementation.
"""
from __future__ import annotations

from mangum import Mangum

from bff.main import app

handler = Mangum(app)
