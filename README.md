# DataDrift

DataDrift is a simple e-commerce data quality dashboard built with a Python FastAPI backend and a single `index.html` frontend.

## Overview

The app lets a user:
- upload a CSV file containing e-commerce order data,
- review schema issues, missing values, duplicates, invalid totals, and date problems,
- approve safe cleaning suggestions,
- view business metrics and anomaly alerts,
- export the cleaned CSV for downstream use.

The project is intentionally lightweight and beginner-friendly.

## Project structure

```text
DataDrift/
├── index.html
├── README.md
└── backend/
    ├── main.py
    ├── pipeline.py
    └── requirements.txt
```

## Setup on Mac / VS Code

1. Open Terminal in VS Code.
2. Change into the project folder:

```bash
cd DataDrift
```

3. Create a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

4. Install dependencies:

```bash
pip install --upgrade pip
pip install -r backend/requirements.txt
```

## Run the app

Start the backend from the project root:

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Then open the app in your browser:

```text
http://localhost:8000/
```

## Optional AI configuration

AI features are optional and server-side only. If you later want to enable AI-assisted recommendations, add an environment variable on the server side:

```bash
export OPENAI_API_KEY="your-key-here"
```

The app still works normally without this key.

## Sample dataset

A sample CSV is available from the app UI through the "Load sample dataset" button. It also includes values with quoted commas, such as `"Premium, Wireless Mouse"`, to test CSV parsing correctly.

## Notes

- The app never silently deletes or changes original dataset rows.
- Cleaning suggestions are proposed and only applied when the user approves them.
- The backend validates actual uploaded data instead of hardcoded metrics.
