from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def api_root():
    return {"message": "API v1"}
