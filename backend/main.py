"""
SmartRiver backend — Entry point.
Run with: python -m backend.main (from project root) or uvicorn backend.app.main:app --reload
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
