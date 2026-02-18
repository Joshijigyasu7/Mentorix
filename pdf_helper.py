from fpdf import FPDF
from io import BytesIO
import re

class PDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(0, 51, 102)
        self.cell(0, 10, self.title, ln=True, align="C")
        self.set_draw_color(0, 51, 102)
        self.line(10, self.get_y(), self.w - 10, self.get_y())
        self.ln(5)
    
    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

def create_pdf(title: str, content: str) -> BytesIO:
    """Create a formatted PDF and return as BytesIO (no file saved to disk)"""
    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.title = title.encode("latin-1", "ignore").decode("latin-1")
    pdf.add_page()
    pdf.set_left_margin(15)
    pdf.set_right_margin(15)

    # Replace common Unicode characters with ASCII equivalents
    unicode_replacements = {
        '\u2022': '-',  # bullet point
        '\u2013': '-',  # en dash
        '\u2014': '--', # em dash
        '\u2018': "'",  # left single quote
        '\u2019': "'",  # right single quote
        '\u201c': '"',  # left double quote
        '\u201d': '"',  # right double quote
        '\u2026': '...', # ellipsis
        '\u00b0': ' degrees', # degree symbol
        '\u00d7': 'x',  # multiplication sign
        '\u00f7': '/',  # division sign
        '\u2192': '->',  # right arrow
        '\u2190': '<-',  # left arrow
        '\u2264': '<=',  # less than or equal
        '\u2265': '>=',  # greater than or equal
        '\u2260': '!=',  # not equal
    }
    
    for unicode_char, ascii_char in unicode_replacements.items():
        content = content.replace(unicode_char, ascii_char)
    
    # Make text latin-1 safe (remove any remaining non-latin-1 characters)
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
        elif re.match(r"^(INSTRUCTIONS|QUESTIONS|ANSWER KEY|MARK DISTRIBUTION|BLOOM'?S?\s+TAXONOMY\s+DISTRIBUTION|QUESTION\s+PAPER|SECTION\s+\d+)\s*:?$", line, re.IGNORECASE):
            pdf.ln(2)
            pdf.set_font("Helvetica", "B", 12)
            pdf.set_text_color(0, 51, 102)
            pdf.multi_cell(0, 7, line.upper())
            pdf.ln(1)
            pdf.set_font("Helvetica", size=11)
            pdf.set_text_color(0, 0, 0)
        
        # Separator lines (=== or ---)
        elif re.match(r'^[=\-]{3,}$', line):
            pdf.ln(1)
            pdf.set_draw_color(0, 51, 102)
            pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
            pdf.ln(2)

        # Question/Answer lines (bold label with Bloom's level)
        elif re.match(r"^(Question\s*\d+|Answer\s*\d+)\b", line, re.IGNORECASE):
            pdf.ln(1)
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(0, 51, 102)
            pdf.multi_cell(0, 6, line)
            pdf.set_font("Helvetica", size=11)
            pdf.set_text_color(0, 0, 0)

        # Bold text (**text**)
        elif "**" in line:
            pdf.set_font("Helvetica", "B", 11)
            clean_line = line.replace("**", "")
            pdf.multi_cell(0, 6, clean_line)
            pdf.set_font("Helvetica", size=11)
        
        # Bullet points (-, *, •)
        elif line.startswith(("- ", "* ")):
            bullet_text = line[2:].strip()
            pdf.set_x(20)
            pdf.set_font("Helvetica", size=11)
            pdf.multi_cell(0, 6, f"- {bullet_text}")
        
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
            # Add small spacing after paragraphs
            if len(line) > 50:  # Only for longer paragraphs
                pdf.ln(1)
    
    # Return as BytesIO instead of saving to disk
    pdf_output = BytesIO()
    output_bytes = pdf.output(dest='S')
    
    # Handle both fpdf (returns str) and fpdf2 (returns bytes)
    if isinstance(output_bytes, str):
        pdf_output.write(output_bytes.encode('latin-1', 'ignore'))
    else:
        pdf_output.write(output_bytes)
    
    pdf_output.seek(0)
    return pdf_output
