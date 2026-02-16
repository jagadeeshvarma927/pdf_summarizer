# from fastapi import FastAPI, Request, UploadFile, File
# from fastapi.responses import HTMLResponse
# from fastapi.templating import Jinja2Templates
# from fastapi.staticfiles import StaticFiles
# from typing import List

# from app.services.pdf_processor import extract_text_from_pdf
# from app.services.llm_service import extract_company_info
# from app.services.excel_service import generate_excel
# from fastapi.responses import StreamingResponse

# app = FastAPI()

# # Mount static folder
# app.mount("/static", StaticFiles(directory="app/static"), name="static")

# # Setup templates
# templates = Jinja2Templates(directory="app/templates")


# @app.get("/", response_class=HTMLResponse)
# async def home(request: Request):
#     return templates.TemplateResponse("index.html", {"request": request})



# @app.post("/upload")
# async def upload_pdfs(files: List[UploadFile] = File(...)):
#     results = []

#     for file in files:
#         print(f"Processing: {file.filename}")

#         text = extract_text_from_pdf(file)
#         llm_output = extract_company_info(text)

#         results.append({
#             "Filename": file.filename,
#             "Company Name": llm_output["company_name"],
#             "Summary": llm_output["summary"]
#         })

#     # Generate Excel file
#     excel_file = generate_excel(results)

#     return StreamingResponse(
#         excel_file,
#         media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#         headers={
#             "Content-Disposition": "attachment; filename=company_news_summary.xlsx"
#         }
#     )

#     results = []

#     for file in files:
#         print(f"Processing: {file.filename}")

#         text = extract_text_from_pdf(file)
#         print(f"Extracted {len(text)} characters")

#         llm_output = extract_company_info(text)

#         results.append({
#             "filename": file.filename,
#             "company_name": llm_output["company_name"],
#             "summary": llm_output["summary"]
#         })

#     return {
#         "message": "PDFs processed successfully 🚀",
#         "results": results
#     }



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

generated_excel_data = None
app = FastAPI()

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

    for i, file in enumerate(files):

        if not file.filename.lower().endswith(".pdf"):
            continue

        try:
            text = extract_text_from_pdf(file)

            if not text.strip():
                raise ValueError("Empty PDF content")
            
            llm_output = extract_company_info(text)

            results.append({
                "Filename": file.filename,
                "Company Name": llm_output["company_name"],
                "Summary": llm_output["summary"]
            })

        except Exception as e:
            results.append({
                "Filename": file.filename,
                "Company Name": "Error",
                "Summary": str(e)
            })

        if (i + 1) % MAX_PER_MINUTE == 0:
            print("Sleeping 60 seconds to respect rate limits...")
            time.sleep(SLEEP_TIME)
    
    global generated_excel_data

    # Save Excel locally
    excel_file = generate_excel(results)

    generated_excel_data = excel_file.getvalue()

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


# @app.post("/upload")
# async def upload_pdfs(files: List[UploadFile] = File(...)):

#     results = []

#     MAX_PER_MINUTE = 10
#     SLEEP_TIME = 60  # seconds

#     try:
#         total_files = len(files)

#         for i, file in enumerate(files):

#             print(f"Processing {i+1}/{total_files}: {file.filename}")

#             # Extract PDF text
#             text = extract_text_from_pdf(file)

#             if not text.strip():
#                 raise ValueError("Empty PDF content")

#             # Call LLM
#             llm_output = extract_company_info(text)

#             results.append({
#                 "Filename": file.filename,
#                 "Company Name": llm_output["company_name"],
#                 "Summary": llm_output["summary"]
#             })

#             # Rate limit control
#             if (i + 1) % MAX_PER_MINUTE == 0:
#                 print("Sleeping 60 seconds to respect rate limits...")
#                 time.sleep(SLEEP_TIME)

#     except Exception as e:
#         print("Processing stopped due to error:", str(e))
#         print("Returning partial results...")

#     # Generate Excel (even if partial)
#     excel_file = generate_excel(results)

#     return StreamingResponse(
#         excel_file,
#         media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#         headers={
#             "Content-Disposition": "attachment; filename=company_news_summary.xlsx"
#         }
#     )
