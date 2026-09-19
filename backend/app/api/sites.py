"""Candidate site endpoints (PS-2 §34)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..geospatial.loader import get_store
from ..schemas.models import SiteCreate

router = APIRouter()


@router.get("/sites")
def list_sites():
    return {"sites": get_store().sites}


@router.post("/sites", status_code=201)
def create_site(req: SiteCreate):
    site = get_store().add_site(req.name, req.latitude, req.longitude, req.business_type)
    return site


@router.delete("/sites/{site_id}")
def delete_site(site_id: str):
    ok = get_store().delete_site(site_id)
    if not ok:
        raise HTTPException(404, "Site not found (or is a protected preset).")
    return {"deleted": site_id}
