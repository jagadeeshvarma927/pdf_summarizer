import time
from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from typing import List

from app.services.pdf_processor import extract_text_from_pdf
from app.services.llm_service import extract_company_info
from app.services.excel_service import generate_excel
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse
from fastapi.responses import Response
from app.logger import get_logger

generated_excel_data = None
app = FastAPI()
logger = get_logger("pdf_summarizer.main")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})



EXCEL_FILE_PATH = "generated_output.xlsx"



@app.post("/upload")
async def upload_pdfs(files: List[UploadFile] = File(...)):

    results = []

    MAX_PER_MINUTE = 10
    SLEEP_TIME = 60

    total_files = len(files)
    logger.info("Upload request received for %s file(s)", total_files)

    for i, file in enumerate(files):

        if not file.filename.lower().endswith(".pdf"):
            logger.info("Skipping non-PDF file: %s", file.filename)
            continue

        try:
            logger.info("Processing PDF: %s", file.filename)
            text = extract_text_from_pdf(file)

            if not text.strip():
                logger.warning("Empty PDF content for %s", file.filename)
                raise ValueError("Empty PDF content")
            
            llm_output = extract_company_info(text)
            logger.info("LLM processing completed for %s", file.filename)

            results.append({
                            "Filename": file.filename,
                            "Company Name": llm_output.get("company_name", "Not Found"),
                            "Summary": llm_output.get("summary", "No summary available"),
                            "Sentiment": llm_output.get("sentiment", "unknown")
                            })

        except Exception as e:
            logger.exception("Failed to process %s", file.filename)
            results.append({
                "Filename": file.filename,
                "Company Name": "Error",
                "Summary": str(e),
                "Sentiment": "unknown"
            })

        if (i + 1) % MAX_PER_MINUTE == 0:
            logger.info("Sleeping 60 seconds to respect rate limits")
            time.sleep(SLEEP_TIME)
    
    global generated_excel_data

    # Save Excel locally
    excel_file = generate_excel(results)
    generated_excel_data = excel_file.getvalue()
    logger.info("Excel file generated with %s result(s)", len(results))

    return JSONResponse({"status": "completed"})




@app.get("/download")
async def download_excel():

    global generated_excel_data

    if not generated_excel_data:
        return JSONResponse({"error": "No file generated yet"}, status_code=400)

    return Response(
        content=generated_excel_data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": "attachment; filename=company_news_summary.xlsx"
        }
    )


