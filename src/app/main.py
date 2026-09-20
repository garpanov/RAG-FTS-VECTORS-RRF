from fastapi import FastAPI

from app.routers import router as documents_router

app = FastAPI(title="Document ingestion service")
app.include_router(documents_router)
