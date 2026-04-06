"""
Preprocessing controller — Run data pipeline and store results.
Admin only: trigger processing.

Implementation delegates to backend.services.upload_ingest (same path as automatic upload ingest).
"""
from pathlib import Path
from typing import Optional
import logging

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query

from backend.auth.dependencies import require_admin

router = APIRouter()
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]


@router.post("/run")
async def run_preprocessing(
    file: Optional[UploadFile] = File(None),
    dataset_id: Optional[int] = Query(None),
    current_user: dict = Depends(require_admin),
):
    """
    Run preprocessing on uploaded CSV or existing dataset.
    Saves WQI readings to storage for dashboard and ML.
    """
    has_file = file is not None and bool(getattr(file, "filename", None))
    if not has_file and dataset_id is None:
        raise HTTPException(status_code=400, detail="Provide file or dataset_id")
    try:
        if has_file:
            content = await file.read()
            path = ROOT / "datasets" / "uploads" / file.filename
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            input_path = path
        else:
            from backend.db.repository import _store

            ds = next((d for d in _store["datasets"] if d["id"] == dataset_id), None)
            if not ds:
                raise HTTPException(status_code=404, detail="Dataset not found")
            input_path = Path(ds["file_path"])
            if not input_path.is_absolute():
                input_path = ROOT / input_path
        if not Path(input_path).exists():
            raise HTTPException(status_code=404, detail="File not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if dataset_id is None and has_file:
        from backend.db.repository import _store

        fn = file.filename
        for drec in reversed(_store.get("datasets", [])):
            fp = (drec.get("file_path") or "").replace("\\", "/")
            if (drec.get("name") or "") == fn or fp.endswith(fn):
                dataset_id = int(drec["id"])
                break
    if dataset_id is None:
        dataset_id = 1

    from backend.services.upload_ingest import ingest_upload_csv_path

    res = ingest_upload_csv_path(Path(input_path), int(dataset_id), run_anomaly_forecast=True)
    if not res.get("ok"):
        raise HTTPException(status_code=422, detail=res.get("error", "Ingest failed"))

    logger.info(
        "Preprocessing complete dataset_id=%s rows=%s readings=%s user_id=%s",
        dataset_id,
        res.get("rows_processed"),
        res.get("readings_stored"),
        current_user.get("id"),
    )
    return {
        "message": "Preprocessing complete",
        "rows_processed": res.get("rows_processed", 0),
        "readings_stored": res.get("readings_stored", 0),
        "dataset_id": dataset_id,
    }
