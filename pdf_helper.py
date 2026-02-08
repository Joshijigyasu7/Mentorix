from fpdf import FPDF
from io import BytesIO
import re

class PDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(0, 51, 102)
        self.cell(0, 12, self.title, ln=True, align="C")
        self.ln(8)
    
    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

def create_pdf(title: str, content: str) -> BytesIO:
    """Create a formatted PDF and return as BytesIO (no file saved to disk)"""
    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.title = title
    pdf.add_page()
    pdf.set_left_margin(15)
    pdf.set_right_margin(15)

    # Make text latin-1 safe
    safe_content = content.encode("latin-1", "ignore").decode("latin-1")
    
    lines = safe_content.split("\n")
    
    for line in lines:
        raw_line = line
        line = line.strip()
        
        if not line:
            pdf.ln(4)
            continue
        
        # Main headings (##)
        if line.startswith("## "):
            pdf.ln(3)
            pdf.set_font("Helvetica", "B", 14)
            pdf.set_text_color(0, 51, 102)
            pdf.multi_cell(0, 8, line[3:].strip())
            pdf.ln(2)
            pdf.set_font("Helvetica", size=11)
            pdf.set_text_color(0, 0, 0)
        
        # Subheadings (###)
        elif line.startswith("### "):
            pdf.ln(2)
            pdf.set_font("Helvetica", "B", 12)
            pdf.set_text_color(51, 51, 51)
            pdf.multi_cell(0, 7, line[4:].strip())
            pdf.ln(1)
            pdf.set_font("Helvetica", size=11)
            pdf.set_text_color(0, 0, 0)
        
        # Section labels / keywords
        elif re.match(r"^(INSTRUCTIONS|QUESTIONS|ANSWER KEY|MARK DISTRIBUTION|SECTION\s+\d+)\s*:?$", line, re.IGNORECASE):
            pdf.ln(2)
            pdf.set_font("Helvetica", "B", 12)
            pdf.set_text_color(0, 51, 102)
            pdf.multi_cell(0, 7, line.upper())
            pdf.ln(1)
            pdf.set_font("Helvetica", size=11)
            pdf.set_text_color(0, 0, 0)

        # Question/Answer lines (bold label)
        elif re.match(r"^(Question\s*\d+|Answer\s*\d+)\b", line, re.IGNORECASE):
            pdf.set_font("Helvetica", "B", 11)
            pdf.multi_cell(0, 6, line)
            pdf.set_font("Helvetica", size=11)

        # Bold text (**text**)
        elif "**" in line:
            pdf.set_font("Helvetica", "B", 11)
            clean_line = line.replace("**", "")
            pdf.multi_cell(0, 6, clean_line)
            pdf.set_font("Helvetica", size=11)
        
        # Bullet points (-, *, •)
        elif line.startswith(("- ", "* ", "• ")):
            bullet_text = line[2:].strip()
            pdf.set_x(20)
            pdf.set_font("Helvetica", size=11)
            pdf.multi_cell(0, 6, f"  {bullet_text}")
        
        # Numbered lists (e.g., 1. or 1))
        elif re.match(r'^\d+[\.)]', line):
            pdf.set_x(20)
            pdf.set_font("Helvetica", size=11)
            pdf.multi_cell(0, 6, line)
        
        # Regular paragraphs
        else:
            pdf.set_font("Helvetica", size=11)
            pdf.set_text_color(0, 0, 0)
            pdf.multi_cell(0, 6, line)
    
    # Return as BytesIO instead of saving to disk
    pdf_output = BytesIO()
    pdf_output.write(pdf.output(dest='S').encode('latin-1'))
    pdf_output.seek(0)
    return pdf_output
