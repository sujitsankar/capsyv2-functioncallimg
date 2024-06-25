from fastapi import FastAPI
from app.routes import router as assistant_router

app = FastAPI()

app.include_router(assistant_router, prefix="/assistant")
