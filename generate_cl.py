from fpdf import FPDF
import os

pdf = FPDF()
pdf.add_page()

# Set fonts
pdf.set_font("Helvetica", style="B", size=14)

# Header
pdf.cell(0, 10, "Shiva Keerth", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Helvetica", size=11)
pdf.cell(0, 5, "Software Engineer | Python, FastAPI, Docker, AWS", new_x="LMARGIN", new_y="NEXT")
pdf.cell(0, 5, "Email: gantishivakeerth@gmail.com | Location: Ahmedabad / Gujarat", new_x="LMARGIN", new_y="NEXT")
pdf.ln(10)

# Date & Addressing
from datetime import datetime
pdf.cell(0, 5, datetime.today().strftime("%B %d, %Y"), new_x="LMARGIN", new_y="NEXT")
pdf.ln(5)

pdf.set_font("Helvetica", style="B", size=11)
pdf.cell(0, 5, "Hiring Manager", new_x="LMARGIN", new_y="NEXT")
pdf.cell(0, 5, "Kaseya", new_x="LMARGIN", new_y="NEXT")
pdf.ln(10)

pdf.set_font("Helvetica", size=11)
pdf.cell(0, 5, "Dear Hiring Manager,", new_x="LMARGIN", new_y="NEXT")
pdf.ln(5)

# Body Paragraphs - Removed em-dash and used ASCII safe characters
body = (
    "I am writing to express my strong interest in the Software Engineer I position at Kaseya. "
    "With a solid foundation in backend development and cloud-based architecture, I am eager to bring my "
    "technical skills in Python, FastAPI, Docker, and AWS to your engineering team.\n\n"
    
    "In my recent projects, I have specialized in building robust, scalable APIs and deploying applications. "
    "For instance, I developed an Enterprise Knowledge Graph platform and a Dual-Domain processing platform where I "
    "engineered backend services utilizing Python and FastAPI. I initially containerized and deployed these systems "
    "on AWS EC2 using Docker before migrating the interfaces to Streamlit Community Cloud for optimized accessibility. "
    "This hands-on experience has given me a deep understanding of cloud environments, deployment flexibility, and writing "
    "clean, maintainable code - skills that align perfectly with Kaseya's focus on building high-performance IT "
    "operations software.\n\n"
    
    "While my background includes significant experience with AI integrations, my core strength lies in backend "
    "engineering, systems architecture, and developing efficient REST APIs. I am highly adaptable, thrive in "
    "fast-paced environments, and am committed to continuous learning. I am excited about the opportunity to "
    "contribute to Kaseya's mission of empowering IT professionals with unified, automated software solutions.\n\n"
    
    "Thank you for your time and consideration. I look forward to the possibility of discussing how my backend "
    "engineering skills can add value to your team."
)

pdf.multi_cell(0, 6, body)
pdf.ln(10)

pdf.cell(0, 5, "Sincerely,", new_x="LMARGIN", new_y="NEXT")
pdf.ln(8)

pdf.set_font("Helvetica", style="B", size=11)
pdf.cell(0, 5, "Shiva Keerth", new_x="LMARGIN", new_y="NEXT")

# Save to Downloads
output_path = r"C:\Users\ganti\Downloads\Shiva_Keerth_Cover_Letter_Kaseya.pdf"
pdf.output(output_path)
print(f"PDF saved to {output_path}")
