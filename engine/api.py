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

from .analysis.building_analysis import analyse_building
from .peb.building import BuildingInput, peb_building
from .peb.builtup_frame import BuiltUpSizes, default_sizes, sizes_dict
from .peb.loads_input import LoadsInput
from .peb.secondary import RoofSide, Sections, Wall
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


class RoofSideIn(BaseModel):
    spacing: float = 1250
    first: float = 0
    apex_gap: float = 200


class WallIn(BaseModel):
    spacing: float = 1250
    first: float = 1250
    top_gap: float = 300


class SectionsIn(BaseModel):
    purlin: str = "Z200x65x20x2.0"
    eave_strut: str = "C200x65x20x2.0"
    girt: str = "Z200x65x20x2.0"


class OpeningIn(BaseModel):
    wall: Literal["A", "B", "first", "last"]
    at: float
    width: float
    sill: float = 0
    height: float


class BuildingRequest(BaseModel):
    span: float
    eave_height: float
    roof_slope: float
    bay_spacing: float
    n_bays: int
    sizes: SizesIn | None = None
    roof_a: RoofSideIn = RoofSideIn()
    roof_b: RoofSideIn = RoofSideIn()
    wall_a: WallIn = WallIn()
    wall_b: WallIn = WallIn()
    gable: WallIn = WallIn()
    sections: SectionsIn = SectionsIn()
    end_first: Literal["frame", "rafter"] = "frame"
    end_last: Literal["frame", "rafter"] = "frame"
    braced_bays: list[int] | None = Field(None, description="1-based; default the first and the last bay")
    brace_type: Literal["rod", "angle"] = "rod"
    ridge_tie: Literal["rod", "strap"] = "rod"
    bolt: Literal["M12", "M16"] = "M12"
    fixed_lap: float | None = Field(None, description="mm each side of a frame; default 10 % of each bay")
    openings: list[OpeningIn] = []


@app.post("/peb/building")
def peb_building_api(req: BuildingRequest) -> dict:
    """The whole PEB building: main frames, purlins, girts, eave struts, sag rods, bracing, flange braces, end walls,
    openings and cleats (Phase 2). Geometry only, not designed."""
    try:
        return peb_building(_building_input(req))
    except (ValueError, BuiltUpError) as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


def _building_input(req: BuildingRequest) -> BuildingInput:
    return BuildingInput(
        span=req.span, eave_height=req.eave_height, roof_slope=req.roof_slope, bay_spacing=req.bay_spacing, n_bays=req.n_bays,
        sizes=BuiltUpSizes(**req.sizes.model_dump()) if req.sizes else None,
        roof_a=RoofSide(**req.roof_a.model_dump()), roof_b=RoofSide(**req.roof_b.model_dump()),
        wall_a=Wall(**req.wall_a.model_dump()), wall_b=Wall(**req.wall_b.model_dump()), gable=Wall(**req.gable.model_dump()),
        sections=Sections(**req.sections.model_dump()), end_first=req.end_first, end_last=req.end_last,
        braced_bays=tuple(req.braced_bays) if req.braced_bays is not None else None, brace_type=req.brace_type, ridge_tie=req.ridge_tie,
        bolt=req.bolt, fixed_lap=req.fixed_lap, openings=tuple(o.model_dump() for o in req.openings))


class LoadsIn(BaseModel):
    V: float | None = None
    exposure: Literal["B", "C", "D"] | None = None
    enclosure: Literal["enclosed", "partially_enclosed", "partially_open", "open"] = "enclosed"
    Kzt: float = 1.0
    risk: Literal["I", "II", "III", "IV"] = "II"
    roof_cladding: Literal["single", "sandwich"] = "single"
    roof_cladding_kpa: float | None = None
    wall_cladding: Literal["single", "sandwich"] = "single"
    wall_cladding_kpa: float | None = None
    collateral: float = 0.10
    Lo: float = 0.96
    base: Literal["pinned", "fixed"] = "pinned"
    lrfd: bool = True
    asd: bool = True


@app.post("/peb/loads/check")
def peb_loads_check(req: LoadsIn) -> dict:
    """The job's load inputs, checked, with what follows from them (Kd, GCpi, the sheeting values used)."""
    try:
        return LoadsInput(**req.model_dump()).summary()
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


class AnalysisRequest(BaseModel):
    building: BuildingRequest
    loads: LoadsIn
    p_delta: bool = True


@app.post("/peb/analysis")
def peb_analysis(req: AnalysisRequest) -> dict:
    """Phase 3: every frame line, the end walls and the longitudinal bracing for all load cases (unfactored) and the
    LRFD / ASD combinations. Run on demand, not stored. NOT FOR ISSUE: analysis only, members not designed."""
    try:
        return analyse_building(_building_input(req.building), LoadsInput(**req.loads.model_dump()), p_delta=req.p_delta)
    except (ValueError, BuiltUpError) as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


class DefaultsRequest(BaseModel):
    span: float


@app.post("/peb/frame/defaults")
def peb_frame_defaults(req: DefaultsRequest) -> dict:
    """The built-up placeholder sizes the span rules give (HANDOVER.md, Phase 1 decisions); the form shows them for editing."""
    return {"sizes": sizes_dict(default_sizes(req.span)), "designed": False}
