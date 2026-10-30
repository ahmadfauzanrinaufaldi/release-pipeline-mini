import os

from fastapi import FastAPI

app = FastAPI(title="release-pipeline-mini")

# Versi diisi saat build (lihat Dockerfile, ARG APP_VERSION) atau lewat env.
VERSION = os.getenv("APP_VERSION", "dev")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/version")
def version() -> dict:
    return {"version": VERSION}
