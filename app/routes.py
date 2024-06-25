from fastapi import APIRouter, UploadFile, File, Form, HTTPException
import shutil
import os
import logging
import time

import datetime
import time
import logging
from bs4 import BeautifulSoup
from fastapi.responses import JSONResponse
from fpdf import FPDF, HTMLMixin
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem, PageBreak
from reportlab.lib import colors
import markdown2
from assistant.assistant import *


from fpdf import FPDF, HTMLMixin
from assistant.assistant import *
#from assistant.report_generator import generate_report_logic

router = APIRouter()

logging.basicConfig(level=logging.INFO)

@router.post("/upload_file")
async def upload_file(file: UploadFile = File(...)):
    start_time = time.time()
    file_location = f"files/{file.filename}"
    try:
        # Save the uploaded file
        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)

        # Ensure the file is closed before proceeding
        file_object.close()

        # Open the file again for uploading to OpenAI
        file_id = saveFileOpenAI(file_location)
        end_time = time.time()
        logging.info(f"Time taken to upload file: {end_time - start_time} seconds")
        return {"file_id": file_id}
    except Exception as e:
        logging.error(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")
    finally:
        if os.path.exists(file_location):
            try:
                os.remove(file_location)
            except Exception as e:
                logging.error(f"Error removing file: {str(e)}")

@router.post("/create_vector_store")
async def create_vector_store(file_ids: str = Form(...), name: str = Form(...)):
    start_time = time.time()
    try:
        file_ids_list = file_ids.split(",")
        vector_store_id = createVectorStore(file_ids_list, name)
        end_time = time.time()
        logging.info(f"Time taken to create vector store: {end_time - start_time} seconds")
        return {"vector_store_id": vector_store_id}
    except Exception as e:
        logging.error(f"Error creating vector store: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating vector store: {str(e)}")

@router.post("/start_thread")
async def start_thread(prompt: str = Form(...), vector_id: str = Form(...)):
    start_time = time.time()
    try:
        thread_id = startAssistantThread(prompt, vector_id)
        end_time = time.time()
        logging.info(f"Time taken to start thread: {end_time - start_time} seconds")
        return {"thread_id": thread_id}
    except Exception as e:
        logging.error(f"Error starting thread: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error starting thread: {str(e)}")

@router.post("/run_assistant")
async def run_assistant(thread_id: str = Form(...)):
    start_time = time.time()
    try:
        run_id = runAssistant(thread_id)
        end_time = time.time()
        logging.info(f"Time taken to run assistant: {end_time - start_time} seconds")
        return {"run_id": run_id}
    except Exception as e:
        if "already has an active run" in str(e):
            logging.error(f"Error running assistant: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Thread {thread_id} already has an active run.")
        raise HTTPException(status_code=500, detail=f"Error running assistant: {str(e)}")

@router.get("/check_run_status")
async def check_run_status(thread_id: str, run_id: str):
    start_time = time.time()
    try:
        status = checkRunStatus(thread_id, run_id)
        end_time = time.time()
        logging.info(f"Time taken to check run status: {end_time - start_time} seconds")
        return {"status": status}
    except Exception as e:
        logging.error(f"Error checking run status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error checking run status: {str(e)}")

@router.get("/retrieve_thread")
async def retrieve_thread(thread_id: str):
    start_time = time.time()
    try:
        messages = retrieveThread(thread_id)
        end_time = time.time()
        logging.info(f"Time taken to retrieve thread: {end_time - start_time} seconds")
        return {"messages": messages}
    except Exception as e:
        logging.error(f"Error retrieving thread: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving thread: {str(e)}")

@router.post("/add_message_to_thread")
async def add_message_to_thread(thread_id: str = Form(...), prompt: str = Form(...)):
    start_time = time.time()
    try:
        addMessageToThread(thread_id, prompt)
        end_time = time.time()
        logging.info(f"Time taken to add message to thread: {end_time - start_time} seconds")
        return {"message": "Message added successfully"}
    except Exception as e:
        logging.error(f"Error adding message to thread: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error adding message to thread: {str(e)}")


class MyFPDF(FPDF, HTMLMixin):
    pass

@router.post("/generate_report")
async def generate_report(thread_id: str = Form(...)):
    addMessageToThread(thread_id, "Create a comprehensive and detailed analytical report based on the provided startup pitch deck. Respond in the JSON format. Use the generate_report function to create the report")
    report_json = run_report_assistant(thread_id)
    print(report_json)
    return JSONResponse(content=report_json)

"""     addMessageToThread(thread_id, "Create a comprehensive and detailed analytical report based on the provided startup pitch deck. Use the generate_report function to create the report")

        # Run the assistant to generate the report
        run_id = run_report_assistant(thread_id)

        # Wait until the assistant has completed generating the report
        status = 'running'
        while status != 'completed':
            time.sleep(20)
            status = checkRunStatus(thread_id, run_id)

        # Retrieve all messages in the thread to find the final report
        messages = retrieveThread(thread_id)

        # Find the latest assistant response with the report content
        report_content = ""
        for message in reversed(messages):  # Loop from the end to get the latest message first
            if message['role'] == 'assistant':
                report_content = message['content']
                break

        if not report_content:
            raise Exception("No report content found in the assistant's responses.")
        
        # Generate PDF with Unicode support
       
        # Convert Markdown to HTML
        html_content = markdown2.markdown(report_content)

        print(html_content)

        # Extract company name from the HTML content
        # Extract company name from the HTML content
        soup = BeautifulSoup(html_content, 'html.parser')
        ul_element = soup.find('ul')
        if ul_element:
            first_li_element = ul_element.find('li')
            if first_li_element:
                startup_name = first_li_element.get_text().split(':')[-1].strip()
            else:
                raise Exception("No list item found in the unordered list.")
        else:
            raise Exception("No unordered list found in the report content.")

        # Register Calibri fonts
        pdfmetrics.registerFont(TTFont('Calibri', 'C:/Windows/Fonts/calibri.ttf'))
        pdfmetrics.registerFont(TTFont('Calibri-Bold', 'C:/Windows/Fonts/calibrib.ttf'))
        pdfmetrics.registerFont(TTFont('Calibri-Italic', 'C:/Windows/Fonts/calibrii.ttf'))
        pdfmetrics.registerFont(TTFont('Calibri-BoldItalic', 'C:/Windows/Fonts/calibriz.ttf'))

        # Generate PDF with ReportLab
        pdf_path = f"files/report_{thread_id}.pdf"
        doc = SimpleDocTemplate(pdf_path, pagesize=A4)
        elements = []

        # Define styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Title'],
            fontName='Calibri',
            fontSize=24,
            leading=28,
            spaceAfter=20
        )
        heading1_style = ParagraphStyle(
            'Heading1',
            parent=styles['Heading1'],
            fontName='Calibri-Bold',
            fontSize=18,
            leading=22,
            spaceAfter=14,
            spaceBefore=14,
        )
        heading2_style = ParagraphStyle(
            'Heading2',
            parent=styles['Heading2'],
            fontName='Calibri-Bold',
            fontSize=16,
            leading=20,
            spaceAfter=12,
            spaceBefore=12,
        )
        heading3_style = ParagraphStyle(
            'Heading3',
            parent=styles['Heading3'],
            fontName='Calibri-Bold',
            fontSize=14,
            leading=18,
            spaceAfter=10,
            spaceBefore=10,
        )
        body_style = ParagraphStyle(
            'BodyText',
            parent=styles['BodyText'],
            fontName='Calibri',
            fontSize=12,
            leading=14,
            spaceAfter=10,
            spaceBefore=6
        )
        bullet_style = ParagraphStyle(
            'Bullet',
            parent=styles['BodyText'],
            fontName='Calibri',
            fontSize=12,
            leading=14,
            leftIndent=20,
            spaceAfter=10,
            spaceBefore=6
        )

        # Create a title page
        elements.append(Paragraph(f"{startup_name} Report", title_style))
        elements.append(Spacer(1, 0.5 * inch))
        elements.append(Paragraph("CapsyAI", body_style))
        elements.append(Paragraph(datetime.date.today().strftime("%Y-%m-%d"), body_style))
        elements.append(PageBreak())

        # Process the HTML content and convert it to ReportLab's flowables
        soup = BeautifulSoup(html_content, 'html.parser')
        for element in soup.descendants:
            if element.name == 'h1':
                elements.append(Paragraph(element.get_text(), heading1_style))
                elements.append(Spacer(1, 0.2 * inch))
            elif element.name == 'h2':
                elements.append(Paragraph(element.get_text(), heading2_style))
                elements.append(Spacer(1, 0.15 * inch))
            elif element.name == 'h3':
                elements.append(Paragraph(element.get_text(), heading3_style))
                elements.append(Spacer(1, 0.1 * inch))
            elif element.name == 'p':
                elements.append(Paragraph(element.get_text(), body_style))
                elements.append(Spacer(1, 0.1 * inch))
            elif element.name == 'ul':
                bullet_points = []
                for li in element.find_all('li'):
                    bullet_points.append(ListItem(Paragraph(li.get_text(), bullet_style)))
                elements.append(ListFlowable(bullet_points, bulletType='bullet', start='circle'))
                elements.append(Spacer(1, 0.1 * inch))
            elif element.name == 'ol':
                numbered_points = []
                for li in element.find_all('li'):
                    numbered_points.append(ListItem(Paragraph(li.get_text(), body_style)))
                elements.append(ListFlowable(numbered_points, bulletType='1'))
                elements.append(Spacer(1, 0.1 * inch))
            elif element.name == 'br':
                elements.append(Spacer(1, 0.1 * inch))

        # Build the PDF
        doc.build(elements)

        end_time = time.time()
        logging.info(f"Time taken to generate report: {end_time - start_time} seconds")
        return {"pdf_path": pdf_path}
    except Exception as e:
        logging.error(f"Error generating report: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating report: {str(e)}")
"""
''' pdf = MyFPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, report_content.encode('latin-1', 'replace').decode('latin-1'))
        
        pdf_path = f"files/report_{thread_id}.pdf"
        pdf.output(pdf_path)
        
        end_time = time.time()
        logging.info(f"Time taken to generate report: {end_time - start_time} seconds")
        return {"pdf_path": pdf_path}
    except Exception as e:
        logging.error(f"Error generating report: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating report: {str(e)}")
'''