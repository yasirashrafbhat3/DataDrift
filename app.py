from __future__ import annotations

import csv
import io
import os
from typing import Any, Dict, List

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse, PlainTextResponse

from pipeline import (
    analyze_csv_text,
    apply_approved_changes,
    build_sample_csv,
    export_rows_as_csv,
)

app = FastAPI(title="DataDrift", version="1.0.0")
app.state.last_analysis = None
app.state.last_cleaned_rows = []

HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>DataDrift</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      margin: 0;
      background: #0f172a;
      color: #e2e8f0;
    }
    .wrap { max-width: 1200px; margin: 0 auto; padding: 24px; }
    .card {
      background: #111827;
      border: 1px solid #334155;
      border-radius: 14px;
      padding: 20px;
      margin-top: 18px;
      box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    }
    h1, h2, h3 { margin-top: 0; }
    .actions { display: flex; gap: 10px; flex-wrap: wrap; }
    button {
      background: #38bdf8;
      color: #082f49;
      border: none;
      border-radius: 10px;
      padding: 10px 16px;
      font-weight: 700;
      cursor: pointer;
    }
    button.secondary { background: #1d4ed8; color: white; }
    button.danger { background: #ef4444; color: white; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px,1fr)); gap: 16px; }
    .metric {
      background: #0b1220;
      border: 1px solid #334155;
      border-radius: 12px;
      padding: 16px;
    }
    .label { color: #94a3b8; font-size: 12px; text-transform: uppercase; }
    .value { font-size: 28px; font-weight: bold; margin-top: 8px; }
    .issue, .suggestion, .anomaly {
      background: #0b1220;
      border: 1px solid #374151;
      border-radius: 10px;
      padding: 12px;
      margin-top: 10px;
    }
    table { width: 100%; border-collapse: collapse; margin-top: 10px; }
    th, td { padding: 10px; text-align: left; border-bottom: 1px solid #334155; }
    .muted { color: #94a3b8; }
    input[type="file"] { display: none; }
    .upload-zone {
      border: 2px dashed #38bdf8;
      border-radius: 12px;
      padding: 24px;
      text-align: center;
      background: rgba(56, 189, 248, 0.06);
      cursor: pointer;
    }
  </style>
</head>
<body>
  <div class="wrap">
    <h1>DataDrift</h1>
    <p class="muted">AI-powered e-commerce data intelligence for upload, review, cleanup, and export.</p>

    <div class="card">
      <div class="actions">
        <button id="uploadBtn">Upload CSV</button>
        <button class="secondary" id="sampleBtn">Load sample data</button>
        <button class="secondary" id="approveBtn">Approve safe fixes</button>
        <button class="danger" id="exportBtn">Export cleaned CSV</button>
      </div>
      <input id="fileInput" type="file" accept=".csv,text/csv" />
    </div>

    <div class="card">
      <div class="grid">
        <div class="metric"><div class="label">Orders</div><div class="value" id="ordersMetric">0</div></div>
        <div class="metric"><div class="label">Revenue</div><div class="value" id="revenueMetric">$0.00</div></div>
        <div class="metric"><div class="label">Avg Order</div><div class="value" id="avgOrderMetric">$0.00</div></div>
        <div class="metric"><div class="label">Quality</div><div class="value" id="qualityMetric">0%</div></div>
      </div>
    </div>

    <div class="card">
      <h2>Upload & review</h2>
      <div class="upload-zone" id="dropzone">Drop CSV here or click to browse</div>
      <p id="fileName" class="muted">No file selected.</p>
    </div>

    <div class="card">
      <h2>Issues</h2>
      <div id="issues"></div>
    </div>

    <div class="card">
      <h2>Safe cleaning suggestions</h2>
      <div id="suggestions"></div>
    </div>

    <div class="card">
      <h2>Business analytics</h2>
      <div class="grid" id="analyticsGrid"></div>
    </div>

    <div class="card">
      <h2>Anomalies</h2>
      <div id="anomalies"></div>
    </div>

    <div class="card">
      <h2>Preview</h2>
      <table>
        <thead id="previewHead"></thead>
        <tbody id="previewBody"></tbody>
      </table>
    </div>
  </div>

  <script>
    const state = { analysis: null, cleanedRows: [] };

    function formatMoney(v) {
      return '$' + Number(v || 0).toFixed(2);
    }

    function setText(id, value) {
      document.getElementById(id).textContent = value;
    }

    function renderIssues(issues = []) {
      const el = document.getElementById('issues');
      if (!issues.length) {
        el.innerHTML = '<div class="muted">No issues found.</div>';
        return;
      }
      el.innerHTML = issues.map(issue => `
        <div class="issue">
          <strong>${issue.field}</strong><br>
          ${issue.message}<br>
          <span class="muted">Row ${issue.row_index}, level: ${issue.level}</span>
        </div>
      `).join('');
    }

    function renderSuggestions(suggestions = []) {
      const el = document.getElementById('suggestions');
      if (!suggestions.length) {
        el.innerHTML = '<div class="muted">No safe suggestions available.</div>';
        return;
      }
      el.innerHTML = suggestions.map(item => `
        <div class="suggestion">
          <strong>${item.field}</strong><br>
          ${item.reason}<br>
          <span class="muted">${item.original_value || 'empty'} → ${item.suggested_value}</span>
        </div>
      `).join('');
    }

    function renderAnalytics(analytics = {}) {
      const grid = document.getElementById('analyticsGrid');
      const cards = [
        ['Orders', analytics.total_orders || 0],
        ['Revenue', formatMoney(analytics.total_revenue || 0)],
        ['Avg Order', formatMoney(analytics.average_order_value || 0)],
        ['Top Category', analytics.top_category || 'N/A'],
        ['Top Product', analytics.top_product || 'N/A'],
        ['Unique Customers', analytics.unique_customers || 0]
      ];
      grid.innerHTML = cards.map(([label, value]) => `
        <div class="metric"><div class="label">${label}</div><div class="value" style="font-size:20px;">${value}</div></div>
      `).join('');
    }

    function renderAnomalies(anomalies = []) {
      const el = document.getElementById('anomalies');
      if (!anomalies.length) {
        el.innerHTML = '<div class="muted">No anomalies detected.</div>';
        return;
      }
      el.innerHTML = anomalies.map(item => `
        <div class="anomaly">
          <strong>${item.type}</strong><br>
          ${item.message}<br>
          <span class="muted">Field: ${item.field}, Row: ${item.row_index}</span>
        </div>
      `).join('');
    }

    function renderPreview(rows = []) {
      const head = document.getElementById('previewHead');
      const body = document.getElementById('previewBody');
      if (!rows.length) {
        head.innerHTML = '';
        body.innerHTML = '<tr><td class="muted">No rows to show.</td></tr>';
        return;
      }
      const keys = Object.keys(rows[0]).slice(0, 8);
      head.innerHTML = '<tr>' + keys.map(k => '<th>' + k + '</th>').join('') + '</tr>';
      body.innerHTML = rows.slice(0, 8).map(row => '<tr>' + keys.map(key => '<td>' + (row[key] ?? '') + '</td>').join('') + '</tr>').join('');
    }

    function updateDashboard(analysis) {
      state.analysis = analysis;
      setText('ordersMetric', analysis.row_count || 0);
      setText('revenueMetric', formatMoney(analysis.analytics?.total_revenue || 0));
      setText('avgOrderMetric', formatMoney(analysis.analytics?.average_order_value || 0));
      setText('qualityMetric', (analysis.quality_score || 0) + '%');
      renderIssues(analysis.issues || []);
      renderSuggestions(analysis.suggestions || []);
      renderAnalytics(analysis.analytics || {});
      renderAnomalies(analysis.anomalies || []);
      renderPreview(analysis.rows || []);
      setText('fileName', analysis.file_name || 'No file selected.');
    }

    async function upload(file) {
      if (!file) return;
      const formData = new FormData();
      formData.append('file', file);
      const response = await fetch('/api/upload', { method: 'POST', body: formData });
      const data = await response.json();
      if (!response.ok) {
        alert(data.detail || 'Upload failed');
        return;
      }
      updateDashboard(data.analysis);
      state.cleanedRows = data.analysis.rows || [];
    }

    document.getElementById('uploadBtn').addEventListener('click', () => document.getElementById('fileInput').click());
    document.getElementById('dropzone').addEventListener('click', () => document.getElementById('fileInput').click());
    document.getElementById('fileInput').addEventListener('change', (event) => upload(event.target.files[0]));

    document.getElementById('sampleBtn').addEventListener('click', async () => {
      const response = await fetch('/api/sample-dataset');
      const csvText = await response.text();
      const blob = new Blob([csvText], { type: 'text/csv' });
      const file = new File([blob], 'sample_data.csv', { type: 'text/csv' });
      upload(file);
    });

    document.getElementById('approveBtn').addEventListener('click', async () => {
      if (!state.analysis) {
        alert('Please upload data first.');
        return;
      }
      const approved = (state.analysis.suggestions || []).filter(item => item.safe).map(item => ({
        row_index: item.row_index,
        field: item.field,
        suggested_value: item.suggested_value
      }));
      if (!approved.length) {
        alert('There are no safe fixes to approve.');
        return;
      }
      const response = await fetch('/api/approve-cleaning', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approved_changes: approved })
      });
      const data = await response.json();
      if (!response.ok) {
        alert(data.detail || 'Approval failed');
        return;
      }
      state.cleanedRows = data.cleaned_rows || [];
      renderPreview(state.cleanedRows);
      alert('Approved fixes applied.');
    });

    document.getElementById('exportBtn').addEventListener('click', async () => {
      if (!state.cleanedRows.length) {
        alert('No cleaned rows to export.');
        return;
      }
      const response = await fetch('/api/export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rows: state.cleanedRows, file_name: 'cleaned_data.csv' })
      });
      const csvText = await response.text();
      const blob = new Blob([csvText], { type: 'text/csv' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'cleaned_data.csv';
      a.click();
    });
  </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return HTML_PAGE


@app.get("/health")
def health_check() -> Dict[str, Any]:
    return {"status": "ok", "service": "DataDrift", "ai_enabled": bool(os.getenv("OPENAI_API_KEY"))}


@app.get("/api/sample-dataset")
def sample_dataset() -> PlainTextResponse:
    csv_text = build_sample_csv()
    return PlainTextResponse(csv_text, media_type="text/csv")


@app.post("/api/upload")
async def upload_csv(file: UploadFile = File(...)) -> Dict[str, Any]:
    if not file.filename:
        return {"detail": "No file selected."}

    content = await file.read()
    text = content.decode("utf-8-sig")
    analysis = analyze_csv_text(text, file.filename)
    app.state.last_analysis = analysis
    app.state.last_cleaned_rows = analysis.get("rows", [])
    return {"analysis": analysis}


@app.post("/api/approve-cleaning")
async def approve_cleaning(payload: Dict[str, Any]) -> Dict[str, Any]:
    rows = app.state.last_analysis.get("rows", []) if app.state.last_analysis else []
    approved_changes = payload.get("approved_changes", [])
    if not rows:
        return {"detail": "No data loaded."}
    cleaned_rows = apply_approved_changes(rows, approved_changes)
    app.state.last_cleaned_rows = cleaned_rows
    return {"cleaned_rows": cleaned_rows}


@app.post("/api/export")
async def export_csv(payload: Dict[str, Any]) -> PlainTextResponse:
    rows = payload.get("rows", [])
    if not rows:
        return PlainTextResponse("", media_type="text/csv")
    csv_text = export_rows_as_csv(rows)
    return PlainTextResponse(csv_text, media_type="text/csv")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
