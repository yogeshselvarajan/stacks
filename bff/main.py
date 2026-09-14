# bff/main.py
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from bff.auth import router as auth_router
from bff.routes.approvals import router as approvals_router
from bff.routes.cases import router as cases_router
from bff.routes.reads import router as reads_router

app = FastAPI(title="Stacks BFF")

# The BFF and the Next.js app run on different origins during local
# development (different ports on localhost). The production deployment
# (Task 20) sits behind a shared domain, so this is a dev-only concern,
# but without it the browser's CORS preflight (OPTIONS) on every request
# fails before the real request is ever sent, since Starlette has no
# built-in OPTIONS handler and returns 405 for it by default.
_dev_origin = os.environ.get("STACKS_FRONTEND_ORIGIN", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[_dev_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(reads_router)
app.include_router(approvals_router)
app.include_router(cases_router)
