# Manafe3 engine. Copyright (c) 2026 Ahmed Ali. All rights reserved.
"""The engine's HTTP API (FastAPI). Run: `python manafe3.py` (or `uv run uvicorn engine.api:app --port 8765`).

    GET  /health      engine, PyNite, bimsteelauto (and anastruct) versions; which per-machine paths are set
    POST /peb/frame   {span, eave_height, roof_slope, bay_spacing, n_bays} -> a portal frame as members (mm)
    POST /section/builtup  {segments: [...], x?: [...]} -> A, Ix, Iy, Zx, Sx_top/bot along a built-up member
    POST /peb/frame/defaults  {span} -> the built-up placeholder sizes from the span rules
    /peb/frame takes section "builtup" (default, Phase 1) or "hot_rolled" (Phase 0), and optional sizes
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import __version__, settings
from typing import Literal

from .peb.builtup_frame import BuiltUpSizes, default_sizes, sizes_dict
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


class SizesIn(BaseModel):
    hw_knee: float
    hw_base: float
    hw_rafter: float
    haunch_length: float
    bf: float
    tf: float
    grade: str = "S355"


class FrameRequest(BaseModel):
    span: float = Field(..., description="mm, column line A to B")
    eave_height: float = Field(..., description="mm")
    roof_slope: float = Field(..., description="rise/run, 0.1 = 1:10")
    bay_spacing: float = Field(..., description="mm")
    n_bays: int = Field(..., description="number of bays; frames = n_bays + 1")
    section: Literal["builtup", "hot_rolled"] = "builtup"
    sizes: SizesIn | None = Field(None, description="built-up sizes, mm; default: the span rules (POST /peb/frame/defaults)")


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
        d = req.model_dump()
        sizes = BuiltUpSizes(**d.pop("sizes")) if req.sizes else None
        d.pop("sizes", None)
        return portal_frame(FrameInput(**d, sizes=sizes))
    except (ValueError, BuiltUpError) as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


class DefaultsRequest(BaseModel):
    span: float


@app.post("/peb/frame/defaults")
def peb_frame_defaults(req: DefaultsRequest) -> dict:
    """The built-up placeholder sizes the span rules give (HANDOVER.md, Phase 1 decisions); the form shows them for editing."""
    return {"sizes": sizes_dict(default_sizes(req.span)), "designed": False}
