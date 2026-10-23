from __future__ import annotations

import os
from typing import Any, Dict, List

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from backend.pipeline import (
    analyze_csv_text,
    apply_approved_changes,
    build_sample_csv,
    export_rows_as_csv,
)

app = FastAPI(title="DataDrift", version="1.0.0")
app.state.last_analysis = None
app.state.last_cleaned_rows = []


@app.get("/health")
def health_check() -> Dict[str, Any]:
    return {
        "status": "ok",
        "service": "DataDrift API",
        "ai_enabled": bool(os.getenv("OPENAI_API_KEY")),
        "message": "DataDrift is running."
    }


@app.get("/")
def serve_frontend() -> FileResponse:
    return FileResponse("index.html")


@app.get("/api/sample-dataset")
def sample_dataset() -> PlainTextResponse:
    csv_text = build_sample_csv()
    return PlainTextResponse(
        csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=sample_ecommerce_data.csv"},
    )


@app.post("/api/upload")
async def upload_csv(file: UploadFile = File(...)) -> Dict[str, Any]:
    if not file.filename:
        return JSONResponse(status_code=400, content={"detail": "No file selected."})

    try:
        content = await file.read()
        text = content.decode("utf-8-sig")
        analysis = analyze_csv_text(text, file.filename)
        app.state.last_analysis = analysis
        app.state.last_cleaned_rows = analysis.get("rows", [])
        return {"status": "success", "analysis": analysis}
    except UnicodeDecodeError:
        return JSONResponse(status_code=400, content={"detail": "File is not valid UTF-8 text."})
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.post("/api/validate")
async def validate_csv(file: UploadFile = File(...)) -> Dict[str, Any]:
    return await upload_csv(file)


@app.get("/api/analytics")
def get_analytics() -> Dict[str, Any]:
    if app.state.last_analysis is None:
        return {"status": "empty", "analytics": {} }
    return {"status": "success", "analytics": app.state.last_analysis.get("analytics", {}) }


@app.post("/api/approve-cleaning")
async def approve_cleaning(payload: Dict[str, Any]) -> Dict[str, Any]:
    rows = app.state.last_analysis.get("rows", []) if app.state.last_analysis else []
    approved_changes = payload.get("approved_changes", [])
    if not rows:
        return JSONResponse(status_code=400, content={"detail": "No dataset is currently loaded."})

    approved_rows = apply_approved_changes(rows, approved_changes)
    app.state.last_cleaned_rows = approved_rows
    export_csv = export_rows_as_csv(approved_rows)

    analysis = app.state.last_analysis or {}
    analytics = analysis.get("analytics", {})
    if analytics:
        analytics["approved_clean_rows"] = len(approved_rows)

    return {
        "status": "success",
        "cleaned_rows": approved_rows,
        "csv": export_csv,
        "analytics": analytics,
    }


@app.post("/api/export")
async def export_csv(payload: Dict[str, Any]) -> PlainTextResponse:
    rows = payload.get("rows", [])
    file_name = payload.get("file_name", "cleaned_data.csv")
    if not rows:
        return JSONResponse(status_code=400, content={"detail": "No cleaned rows were supplied for export."})

    csv_text = export_rows_as_csv(rows)
    return PlainTextResponse(
        csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={file_name}"},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
