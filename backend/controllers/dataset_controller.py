"""
Dataset controller — Upload and list datasets. Store in repository for pipeline flow.
"""
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Depends

router = APIRouter()
ROOT = Path(__file__).resolve().parents[3]


@router.get("/")
def list_datasets():
    """List all datasets (metadata)."""
    from backend.db.repository import _store
    items = _store["datasets"]
    return {"items": items, "total": len(items)}


@router.post("/upload")
async def upload_dataset(file: UploadFile = File(...)):
    """Upload CSV; save to datasets/uploads and register in DB. Returns dataset_id for preprocessing."""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        return {"error": "CSV file required"}
    content = await file.read()
    path = ROOT / "datasets" / "uploads" / file.filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    from backend.db.repository import save_dataset
    try:
        rel = path.relative_to(ROOT)
        file_path = str(rel)
    except ValueError:
        file_path = str(path)
    row = save_dataset(
        name=file.filename,
        file_path=file_path,
        file_size_bytes=len(content),
        row_count=0,
        uploaded_by=1,
    )
    return {
        "dataset_id": row["id"],
        "filename": file.filename,
        "size": len(content),
        "message": "Upload saved. Run POST /api/v1/preprocessing/run with this file or dataset_id.",
    }
