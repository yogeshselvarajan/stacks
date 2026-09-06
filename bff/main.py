# bff/main.py
from fastapi import FastAPI

from bff.auth import router as auth_router
from bff.routes.approvals import router as approvals_router
from bff.routes.reads import router as reads_router

app = FastAPI(title="Stacks BFF")
app.include_router(auth_router)
app.include_router(reads_router)
app.include_router(approvals_router)
