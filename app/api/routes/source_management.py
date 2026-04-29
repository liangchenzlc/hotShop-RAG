from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import DataSource
from app.domain.schemas import (
    DataSourceCreate,
    DataSourceListResponse,
    DataSourceResponse,
    DataSourceUpdate,
)
from app.scheduler.collector import run_collection

router = APIRouter()


def _ds_to_response(ds: DataSource) -> DataSourceResponse:
    def fmt(dt):
        return dt.replace(microsecond=0).isoformat() + "Z" if dt else None
    return DataSourceResponse(
        id=ds.id,
        name=ds.name,
        source_type=ds.source_type,
        is_active=ds.is_active,
        config=ds.config or {},
        keywords=ds.keywords or [],
        schedule_cron=ds.schedule_cron,
        max_workers=ds.max_workers,
        last_run_at=fmt(ds.last_run_at),
        created_at=fmt(ds.created_at),
        updated_at=fmt(ds.updated_at),
    )


@router.post("", response_model=DataSourceResponse, status_code=201)
def create_source(payload: DataSourceCreate, db: Session = Depends(get_db)):
    existing = db.query(DataSource).filter(DataSource.name == payload.name).first()
    if existing:
        raise HTTPException(409, f"DataSource '{payload.name}' already exists")
    ds = DataSource(**payload.model_dump())
    db.add(ds)
    db.commit()
    db.refresh(ds)
    return _ds_to_response(ds)


@router.get("", response_model=DataSourceListResponse)
def list_sources(db: Session = Depends(get_db)):
    items = db.query(DataSource).order_by(DataSource.created_at.desc()).all()
    return DataSourceListResponse(
        total=len(items),
        items=[_ds_to_response(ds) for ds in items],
    )


@router.get("/{source_id}", response_model=DataSourceResponse)
def get_source(source_id: int, db: Session = Depends(get_db)):
    ds = db.query(DataSource).filter(DataSource.id == source_id).first()
    if not ds:
        raise HTTPException(404, "DataSource not found")
    return _ds_to_response(ds)


@router.patch("/{source_id}", response_model=DataSourceResponse)
def update_source(source_id: int, payload: DataSourceUpdate, db: Session = Depends(get_db)):
    ds = db.query(DataSource).filter(DataSource.id == source_id).first()
    if not ds:
        raise HTTPException(404, "DataSource not found")
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(ds, key, value)
    db.commit()
    db.refresh(ds)
    return _ds_to_response(ds)


@router.delete("/{source_id}", status_code=204)
def delete_source(source_id: int, db: Session = Depends(get_db)):
    ds = db.query(DataSource).filter(DataSource.id == source_id).first()
    if not ds:
        raise HTTPException(404, "DataSource not found")
    db.delete(ds)
    db.commit()


@router.post("/collect-all")
async def collect_all(db: Session = Depends(get_db)):
    """Manually trigger collection for all active sources."""
    sources = db.query(DataSource).filter(DataSource.is_active == True).all()
    results = []
    for src in sources:
        try:
            result = await run_collection(src)
            results.append({"name": src.name, "status": "ok", "detail": result})
        except Exception as exc:
            results.append({"name": src.name, "status": "failed", "detail": str(exc)})
    return {"results": results}


@router.post("/{source_id}/collect")
async def collect_source(source_id: int, db: Session = Depends(get_db)):
    """Manually trigger collection for a single source."""
    src = db.query(DataSource).filter(DataSource.id == source_id).first()
    if not src:
        raise HTTPException(404, "DataSource not found")
    result = await run_collection(src)
    return {"name": src.name, "status": "ok", "detail": result}
