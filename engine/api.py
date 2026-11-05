# Manafe3 engine. Copyright (c) 2026 Ahmed Ali. All rights reserved.
"""The engine's HTTP API (FastAPI). Run: `python manafe3.py` (or `uv run uvicorn engine.api:app --port 8765`).

    GET  /health      engine, PyNite, bimsteelauto (and anastruct) versions; which per-machine paths are set
    POST /peb/frame   {span, eave_height, roof_slope, bay_spacing, n_bays} -> a portal frame as members (mm)
    POST /section/builtup  {segments: [...], x?: [...]} -> A, Ix, Iy, Zx, Sx_top/bot along a built-up member
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import __version__, settings
from .peb.frame import FrameInput, portal_frame
from .sections.builtup import BuiltUpError, BuiltUpMember

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


class SegmentIn(BaseModel):
    length: float
    hw_start: float = Field(..., description="web plate depth at the segment start, mm")
    hw_end: float = Field(..., description="web plate depth at the segment end, mm")
    tw: float
    bf_top: float
    tf_top: float
    bf_bot: float
    tf_bot: float
    grade: str = "S355"
    straight: str = "top"


class BuiltUpRequest(BaseModel):
    segments: list[SegmentIn]
    x: list[float] | None = Field(None, description="stations along the member, mm; default: ends, splices, quarters")


@app.post("/section/builtup")
def section_builtup(req: BuiltUpRequest) -> dict:
    """Section properties of a built-up member along its length (bimsteelauto's WeldedI at each station)."""
    try:
        m = BuiltUpMember.from_dicts([s.model_dump() for s in req.segments])
        xs = req.x if req.x is not None else m.stations()
        rows = [m.properties_at(x) for x in xs]
    except BuiltUpError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return {
        "units": {"length": "mm", "A": "mm2", "I": "mm4", "S": "mm3", "Z": "mm3", "mass": "kg"},
        "length": m.length, "splices": m.splices, "mass_axis": m.mass_axis(), "stations": rows,
        "source": "bimsteelauto.sections.WeldedI (closed form); cross-checked against sectionproperties in the tests",
    }


@app.post("/peb/frame")
def peb_frame(req: FrameRequest) -> dict:
    try:
        return portal_frame(FrameInput(**req.model_dump()))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
