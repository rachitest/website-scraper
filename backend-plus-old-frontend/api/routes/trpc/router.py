from fastapi import APIRouter
from python_trpc import TRPCRouter
from typing import Dict

router = APIRouter()
trpc = TRPCRouter()

@trpc.query()
def hello(name: str) -> Dict[str, str]:
    """Sample tRPC query."""
    return {"message": f"Hello, {name}!"}

router.include_router(trpc.router, prefix="/trpc")
