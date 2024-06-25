import datetime
import time
import logging
from bs4 import BeautifulSoup
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

class MyFPDF(FPDF, HTMLMixin):
    pass

def generate_pdf_report(thread_id, report_content, company_name):
    # Convert Markdown to HTML
        html_content = markdown2.markdown(report_content)

        # Generate PDF with ReportLab
        pdf_path = f"files/report_{thread_id}.pdf"
        doc = SimpleDocTemplate(pdf_path, pagesize=A4)
        elements = []

        # Define styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Title'],
            fontSize=24,
            leading=28,
            spaceAfter=20
        )
        heading1_style = ParagraphStyle(
            'Heading1',
            parent=styles['Heading1'],
            fontSize=18,
            leading=22,
            spaceAfter=20,
            fontName='Helvetica-Bold'
        )
        body_style = ParagraphStyle(
            'BodyText',
            parent=styles['BodyText'],
            fontSize=12,
            leading=14,
            spaceAfter=12
        )

        # Create a title page
        elements.append(Paragraph("Title of the Report", title_style))
        elements.append(Spacer(1, 0.5 * inch))
        elements.append(Paragraph("Author Name", body_style))
        elements.append(Paragraph("Date", body_style))
        elements.append(PageBreak())

        # Process the HTML content and convert it to ReportLab's flowables
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html_content, 'html.parser')
        for element in soup.children:
            if element.name == 'h1':
                elements.append(Paragraph(element.get_text(), heading1_style))
                elements.append(Spacer(1, 0.2 * inch))
            elif element.name == 'p':
                elements.append(Paragraph(element.get_text(), body_style))
                elements.append(Spacer(1, 0.1 * inch))
            elif element.name == 'h2':
                elements.append(Paragraph(element.get_text(), heading1_style))
                elements.append(Spacer(1, 0.2 * inch))
            # Add more conditions here if you have other HTML tags to process

        # Build the PDF
        doc.build(elements)
        return pdf_path

def extract_company_name(content):
    match = re.search(r'\b[A-Z]{3,}\b', content)
    return match.group(0) if match else "Company"

def generate_report_logic(thread_id):
    try:
        # Add message to generate report
        addMessageToThread(thread_id, "Create a comprehensive and detailed analytical report based on the provided startup pitch deck. Follow the default report format provided earlier.")

        # Run the assistant to generate the report
        run_id = runAssistant(thread_id)

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

        # Extract company name from the report content
        company_name = extract_company_name(report_content)

        # Generate PDF report
        pdf_path = generate_pdf_report(thread_id, report_content, company_name)
        
        return pdf_path
    except Exception as e:
        logging.error(f"Error generating report: {str(e)}")
        raise Exception(f"Error generating report: {str(e)}")

