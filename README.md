# PDF Summarizer

A small FastAPI app that extracts text from uploaded PDFs, summarizes company information using an LLM service, and returns results as an Excel file.

## Features
- Upload one or more PDF files via the web UI
- Extract text from PDFs (`app/services/pdf_processor.py`)
- Summarize and extract company information (`app/services/llm_service.py`)
- Export results to Excel (`app/services/excel_service.py`)

## Requirements
- Python 3.9+
- Install dependencies:

```bash
pip install -r requirements.txt
```

## Run (development)
Start the FastAPI server with Uvicorn from the repository root:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Then open your browser at http://localhost:8000 and use the upload form.

## Project structure
- `app/` — application package and services
	- `app/main.py` — FastAPI application entrypoint
	- `app/services/` — PDF extraction, LLM, and Excel helpers
- `requirements.txt` — Python dependencies

## Notes
- `app/main.py` exposes the upload endpoint at `/upload` and serves a simple UI at `/`.
- The app returns a streaming Excel file containing filename, company name, and summary for each uploaded PDF.

## Contributing
Send issues or PRs. Keep changes focused and add small tests where helpful.

