# bff/main.py
from fastapi import FastAPI

from bff.auth import router as auth_router

app = FastAPI(title="Stacks BFF")
app.include_router(auth_router)
