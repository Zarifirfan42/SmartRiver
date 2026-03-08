"""
Dataset service: save file, parse CSV, store metadata.
"""
from pathlib import Path
from typing import Optional
import pandas as pd


class DatasetService:
    """Handle dataset upload and metadata."""

    def __init__(self, upload_dir: Optional[Path] = None):
        self.upload_dir = upload_dir or Path("datasets/uploads")

    def save_upload(self, content: bytes, filename: str) -> Path:
        """Save uploaded file and return path."""
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        path = self.upload_dir / filename
        path.write_bytes(content)
        return path

    def load_csv(self, path: Path) -> pd.DataFrame:
        """Load CSV as DataFrame."""
        return pd.read_csv(path)
