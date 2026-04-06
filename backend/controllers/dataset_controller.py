"""
Dataset controller — Upload and list datasets. Store in repository for pipeline flow.
Admin: upload. Any user: list.

Upload scans CSV for station_code column, maps codes → river_name via RIVER_NAME_BY_STATION_CODE
(see backend.services.river_mapping), and attaches metadata to the stored dataset row for traceability.
"""
from pathlib import Path
import csv
import logging

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query, BackgroundTasks

from backend.auth.dependencies import require_admin

router = APIRouter()
logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[2]


def _csv_row_count(path: Path) -> int:
    """Fast row count without loading full file into pandas."""
    try:
        with path.open("r", encoding="utf-8", newline="") as f:
            n = sum(1 for _ in csv.reader(f))
        return max(0, n - 1)
    except Exception:
        return 0


def _scan_filesystem_datasets() -> list[dict]:
    """
    Discover CSV datasets from datasets/ and datasets/by_river.
    Excludes uploads/ because those are tracked in uploaded_datasets table.
    """
    datasets_dir = ROOT / "datasets"
    if not datasets_dir.exists():
        return []

    paths: list[Path] = []
    # Top-level curated datasets
    paths.extend([p for p in datasets_dir.glob("*.csv") if p.is_file()])
    # River-split datasets
    by_river = datasets_dir / "by_river"
    if by_river.exists():
        paths.extend([p for p in by_river.rglob("*.csv") if p.is_file()])

    seen = set()
    out: list[dict] = []
    for p in sorted(paths, key=lambda x: x.stat().st_mtime, reverse=True):
        rp = str(p.resolve())
        if rp in seen:
            continue
        seen.add(rp)
        try:
            rel = str(p.relative_to(ROOT))
        except ValueError:
            rel = str(p)
        out.append({
            "id": f"fs:{rel}",
            "name": p.name,
            "file_path": rel,
            "file_size_bytes": int(p.stat().st_size),
            "row_count": _csv_row_count(p),
            "uploaded_by": None,
            "created_at": None,
            "river_name": p.stem if p.stem.lower().startswith("sungai ") else None,
            "station_codes_seen": [],
            "river_validation_warnings": [],
            "source": "filesystem",
        })
    return out


@router.get("/")
def list_datasets():
    """List dataset metadata from both uploads and filesystem CSVs."""
    from backend.db.repository import list_uploaded_datasets
    uploaded = list_uploaded_datasets(limit=2000)
    for it in uploaded:
        it["source"] = "uploaded"
    fs_items = _scan_filesystem_datasets()
    uploaded_paths = {str((x.get("file_path") or "")).replace("\\", "/").lower() for x in uploaded}
    merged = list(uploaded)
    for fs in fs_items:
        p = str((fs.get("file_path") or "")).replace("\\", "/").lower()
        if p in uploaded_paths:
            continue
        merged.append(fs)
    items = merged
    return {"items": items, "total": len(items)}


@router.post("/upload")
async def upload_dataset(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: dict = Depends(require_admin),
):
    """Upload CSV; save to disk; register in SQLite; ingest into dashboard readings; queue ML training."""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="CSV file required")
    content = await file.read()
    import pandas as pd

    from backend.db.repository import delete_dataset, find_uploaded_dataset_id_by_filename, save_dataset
    from backend.services.river_mapping import dataset_upload_metadata_from_csv

    meta = dataset_upload_metadata_from_csv(content)
    if meta.get("reject"):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "upload_rejected",
                "message": meta.get("reject_detail"),
                "warnings": meta.get("warnings", []),
            },
        )

    # Same filename → replace previous registration and its readings (no duplicate datasets / rows).
    existing_id = find_uploaded_dataset_id_by_filename(file.filename)
    if existing_id is not None:
        try:
            delete_dataset(int(existing_id))
            logger.info("Replaced prior upload id=%s name=%s", existing_id, file.filename)
        except ValueError:
            pass

    path = ROOT / "datasets" / "uploads" / file.filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)

    try:
        rel = path.relative_to(ROOT)
        file_path = str(rel)
    except ValueError:
        file_path = str(path)

    try:
        row_count = int(len(pd.read_csv(path)))
    except Exception:
        row_count = 0

    row = save_dataset(
        name=file.filename,
        file_path=file_path,
        file_size=len(content),
        row_count=row_count,
        uploaded_by=current_user["id"],
        river_name=meta.get("river_name"),
        station_codes_seen=meta.get("station_codes_seen") or [],
        river_validation_warnings=meta.get("warnings") or [],
    )
    dataset_id = int(row["id"])

    from backend.services.upload_ingest import ingest_upload_csv_path, schedule_background_train_upload

    ingest_result = ingest_upload_csv_path(path, dataset_id, run_anomaly_forecast=True)
    if not ingest_result.get("ok"):
        logger.error("Upload ingest failed id=%s err=%s", dataset_id, ingest_result.get("error"))
        try:
            delete_dataset(dataset_id)
        except Exception:
            pass
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass
        raise HTTPException(
            status_code=422,
            detail=f"Could not load WQI readings: {ingest_result.get('error', 'unknown')}",
        )

    background_tasks.add_task(schedule_background_train_upload, file.filename)

    logger.info(
        "Dataset uploaded+ingested id=%s name=%s rows=%s readings=%s user_id=%s",
        dataset_id,
        file.filename,
        row_count,
        ingest_result.get("readings_stored"),
        current_user.get("id"),
    )
    return {
        "dataset_id": dataset_id,
        "filename": file.filename,
        "size": len(content),
        "river_name": row.get("river_name"),
        "station_codes_seen": row.get("station_codes_seen"),
        "warnings": meta.get("warnings", []),
        "row_count": row_count,
        "ingested": True,
        "readings_stored": ingest_result.get("readings_stored"),
        "rows_processed": ingest_result.get("rows_processed"),
        "training_queued": True,
        "message": "Upload saved, WQI readings loaded into the dashboard, and model training queued in the background.",
    }


@router.delete("/{dataset_id}")
def remove_dataset(
    dataset_id: int,
    _admin: dict = Depends(require_admin),
):
    """
    Delete one dataset record.
    Also removes in-memory readings linked to this dataset_id.
    """
    from backend.db.repository import delete_dataset
    try:
        result = delete_dataset(int(dataset_id))
    except ValueError:
        raise HTTPException(status_code=404, detail="Dataset not found")
    logger.info(
        "Dataset deleted id=%s removed_readings=%s",
        int(dataset_id),
        result.get("removed_readings", 0),
    )
    from backend.services.dataset_refresh import refresh_forecast_after_readings_change

    refresh_forecast_after_readings_change()
    file_path = (result.get("dataset") or {}).get("file_path")

    # Best effort cleanup for uploaded CSV files under datasets/uploads.
    if file_path:
        try:
            p = Path(file_path)
            if not p.is_absolute():
                p = ROOT / p
            if p.exists() and p.is_file():
                uploads_root = ROOT / "datasets" / "uploads"
                if uploads_root in p.resolve().parents:
                    p.unlink(missing_ok=True)
        except Exception:
            pass

    return {
        "success": True,
        "deleted_dataset_id": int(dataset_id),
        "removed_readings": result.get("removed_readings", 0),
    }


@router.delete("/filesystem/remove")
def remove_filesystem_dataset(
    file_path: str = Query(..., description="Relative path under project root, e.g. datasets/by_river/..."),
    _admin: dict = Depends(require_admin),
):
    """
    Delete a CSV dataset file from filesystem listing.
    Safety: only allows deletion under datasets/ (no parent traversal).
    """
    rel = (file_path or "").strip().replace("\\", "/")
    if not rel:
        raise HTTPException(status_code=400, detail="file_path required")
    if ".." in rel:
        raise HTTPException(status_code=400, detail="Invalid file_path")
    p = Path(rel)
    if p.is_absolute():
        raise HTTPException(status_code=400, detail="file_path must be relative")
    full = (ROOT / p).resolve()
    datasets_root = (ROOT / "datasets").resolve()
    if datasets_root not in full.parents and full != datasets_root:
        raise HTTPException(status_code=400, detail="Deletion allowed only under datasets/")
    if not full.exists() or not full.is_file():
        raise HTTPException(status_code=404, detail="Dataset file not found")
    if full.suffix.lower() != ".csv":
        raise HTTPException(status_code=400, detail="Only CSV files can be deleted")

    try:
        full.unlink(missing_ok=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {e}")

    stem = full.stem.strip()
    rel_l = rel.lower()
    from backend.db.repository import remove_readings_by_river_label
    from backend.services.dataset_loader import reload_default_readings_from_disk

    removed_river_rows = 0
    if "/by_river/" in rel_l or stem.lower().startswith("sungai "):
        removed_river_rows = remove_readings_by_river_label(stem)
        from backend.db.repository import _store
        refresh = {
            "mode": "removed_river",
            "river": stem,
            "removed_readings": removed_river_rows,
            "readings_remaining": len(_store["readings"]),
        }
    else:
        refresh = reload_default_readings_from_disk()
        refresh["mode"] = "reloaded_from_disk"

    from backend.services.dataset_refresh import refresh_forecast_after_readings_change

    refresh_forecast_after_readings_change()
    logger.info("Filesystem dataset removed path=%s refresh=%s", rel, refresh.get("mode"))

    return {
        "success": True,
        "deleted_file_path": rel,
        "removed_readings_by_river": removed_river_rows,
        "dashboard_refresh": refresh,
    }
