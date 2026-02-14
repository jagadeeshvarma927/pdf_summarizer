from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from typing import List

from app.services.pdf_processor import extract_text_from_pdf
from app.services.llm_service import extract_company_info
from app.services.excel_service import generate_excel
from fastapi.responses import StreamingResponse

app = FastAPI()

# Mount static folder
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})



@app.post("/upload")
async def upload_pdfs(files: List[UploadFile] = File(...)):
    results = []

    for file in files:
        print(f"Processing: {file.filename}")

        text = extract_text_from_pdf(file)
        llm_output = extract_company_info(text)

        results.append({
            "Filename": file.filename,
            "Company Name": llm_output["company_name"],
            "Summary": llm_output["summary"]
        })

    # Generate Excel file
    excel_file = generate_excel(results)

    return StreamingResponse(
        excel_file,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": "attachment; filename=company_news_summary.xlsx"
        }
    )

    results = []

    for file in files:
        print(f"Processing: {file.filename}")

        text = extract_text_from_pdf(file)
        print(f"Extracted {len(text)} characters")

        llm_output = extract_company_info(text)

        results.append({
            "filename": file.filename,
            "company_name": llm_output["company_name"],
            "summary": llm_output["summary"]
        })

    return {
        "message": "PDFs processed successfully 🚀",
        "results": results
    }