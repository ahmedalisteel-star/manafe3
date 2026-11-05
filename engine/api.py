# Manafe3 engine. Copyright (c) 2026 Ahmed Ali. All rights reserved.
"""The engine's HTTP API (FastAPI). Run: `python manafe3.py` (or `uv run uvicorn engine.api:app --port 8765`).

    GET  /health      engine, PyNite, bimsteelauto (and anastruct) versions; which per-machine paths are set
    POST /peb/frame   {span, eave_height, roof_slope, bay_spacing, n_bays} -> a portal frame as members (mm)
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import __version__, settings
from .peb.frame import FrameInput, portal_frame

app = FastAPI(title="Manafe3 engine", version=__version__)

# The browser app is served from port 8000 (another origin); it may call the engine, nothing else may.
_WEB = settings.get("MANAFE3_WEB_PORT", "8000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[f"http://localhost:{_WEB}", f"http://127.0.0.1:{_WEB}"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


def _version(dist: str) -> str | None:
    try:
        return version(dist)
    except PackageNotFoundError:
        return None


@app.get("/health")
def health() -> dict:
    peb = settings.get_path("BIMSTEELAUTO_PEB_PATH")
    return {
        "status": "ok",
        "engine": __version__,
        "pynite": _version("PyNiteFEA"),
        "bimsteelauto": _version("bimsteelauto"),
        "anastruct": _version("anastruct"),
        "private_peb": {"configured": peb is not None, "found": bool(peb and peb.is_dir())},
    }


class FrameRequest(BaseModel):
    span: float = Field(..., description="mm, column line A to B")
    eave_height: float = Field(..., description="mm")
    roof_slope: float = Field(..., description="rise/run, 0.1 = 1:10")
    bay_spacing: float = Field(..., description="mm")
    n_bays: int = Field(..., description="number of bays; frames = n_bays + 1")


@app.post("/peb/frame")
def peb_frame(req: FrameRequest) -> dict:
    try:
        return portal_frame(FrameInput(**req.model_dump()))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
