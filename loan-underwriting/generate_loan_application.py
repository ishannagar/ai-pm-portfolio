"""
generate_loan_application.py

Generates realistic Indian home loan application PDFs using ReportLab.
Outputs two sample applications under applications/.
"""

# Standard library: resolve output paths next to this script.
import os
from pathlib import Path

# ReportLab imports for PDF layout, tables, and styling.
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


# Output directory for generated PDFs (created automatically if missing).
OUTPUT_DIR = Path(__file__).resolve().parent / "applications"


def format_inr_indian(amount) -> str:
    """
    Format a whole-number rupee amount in Indian grouping (lakhs/crores style).
    Example: 185000 -> ₹1,85,000
    """
    n = int(amount)
    s = str(abs(n))
    if len(s) <= 3:
        return "₹" + s
    # Last three digits (hundreds, tens, ones).
    last = s[-3:]
    rest = s[:-3]
    parts = []
    # Remaining digits are grouped in pairs from the right.
    while len(rest) > 2:
        parts.insert(0, rest[-2:])
        rest = rest[:-2]
    if rest:
        parts.insert(0, rest)
    parts.append(last)
    sign = "-" if n < 0 else ""
    return sign + "₹" + ",".join(parts)


def section_title(text: str, styles) -> Paragraph:
    """Build a bold section heading paragraph for the form."""
    return Paragraph(f"<b>{text}</b>", styles["SectionHeading"])


def build_bank_header(styles) -> list:
    """Return flowables for the bank branding at the top of the first page."""
    elements = []
    # Main bank product line.
    elements.append(Paragraph("<b>FirstBank Home Loans</b>", styles["BankTitle"]))
    elements.append(Paragraph("Home Loan Application Form", styles["FormSubtitle"]))
    elements.append(Spacer(1, 0.4 * cm))
    elements.append(
        Paragraph(
            "<i>Please fill all sections in block letters. Amounts in Indian Rupees (INR).</i>",
            styles["SmallNote"],
        )
    )
    elements.append(Spacer(1, 0.5 * cm))
    return elements


def table_for_section(rows: list, col_widths: list) -> Table:
    """
    Create a two-column table (Field | Value) with light grid and header styling.
    First row of rows should be the column headers.
    """
    tbl = Table(rows, colWidths=col_widths, hAlign="LEFT")
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a5276")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return tbl


def build_application_pdf(output_path: Path, data: dict) -> None:
    """
    Assemble the full loan application PDF from structured section data.
    data keys: personal, employment, financial, loan, assets_liabilities (each list of [field, value]).
    """
    # Ensure parent directory exists before writing.
    output_path.parent.mkdir(parents=True, exist_ok=True)

    styles = getSampleStyleSheet()
    # Custom paragraph styles for hierarchy and readability.
    styles.add(
        ParagraphStyle(
            name="BankTitle",
            parent=styles["Heading1"],
            fontSize=18,
            textColor=colors.HexColor("#1a5276"),
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="FormSubtitle",
            parent=styles["Normal"],
            fontSize=11,
            textColor=colors.HexColor("#2c3e50"),
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SmallNote",
            parent=styles["Normal"],
            fontSize=8,
            textColor=colors.grey,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SectionHeading",
            parent=styles["Heading2"],
            fontSize=11,
            textColor=colors.HexColor("#1a5276"),
            spaceBefore=14,
            spaceAfter=8,
        )
    )

    # A4 document with comfortable margins for a formal form.
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm,
    )
    story = []

    # Bank header block.
    story.extend(build_bank_header(styles))

    # Application reference and applicant summary line (optional metadata row).
    story.append(
        Paragraph(
            f"<b>Application type:</b> {data.get('application_type', 'Standard')} &nbsp;&nbsp; "
            f"<b>Date:</b> {data.get('application_date', '____________')}",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 0.3 * cm))

    # Standard two-column width for Field | Value (fits A4 with margins).
    col_widths = [5.2 * cm, 12.3 * cm]

    # --- Personal Details ---
    story.append(section_title("Personal Details", styles))
    personal_rows = [["Field", "Details"]] + data["personal"]
    story.append(table_for_section(personal_rows, col_widths))
    story.append(Spacer(1, 0.2 * cm))

    # --- Employment Details ---
    story.append(section_title("Employment Details", styles))
    employment_rows = [["Field", "Details"]] + data["employment"]
    story.append(table_for_section(employment_rows, col_widths))
    story.append(Spacer(1, 0.2 * cm))

    # --- Financial Details ---
    story.append(section_title("Financial Details", styles))
    financial_rows = [["Field", "Details"]] + data["financial"]
    story.append(table_for_section(financial_rows, col_widths))
    story.append(Spacer(1, 0.2 * cm))

    # --- Loan Details ---
    story.append(section_title("Loan Details", styles))
    loan_rows = [["Field", "Details"]] + data["loan"]
    story.append(table_for_section(loan_rows, col_widths))
    story.append(Spacer(1, 0.2 * cm))

    # --- Assets & Liabilities ---
    story.append(section_title("Assets & Liabilities", styles))
    al_rows = [["Field", "Details"]] + data["assets_liabilities"]
    story.append(table_for_section(al_rows, col_widths))
    story.append(Spacer(1, 0.4 * cm))

    # Declaration footer (typical on bank forms).
    story.append(
        Paragraph(
            "<b>Declaration:</b> I declare that the information provided is true and complete "
            "to the best of my knowledge. I authorize FirstBank to verify credit, employment, "
            "and property details.",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 0.8 * cm))
    story.append(Paragraph("_" * 40 + " &nbsp;&nbsp;&nbsp; Date: ____________", styles["Normal"]))

    doc.build(story)


def main() -> None:
    """Create applications/ folder and write both sample PDFs."""

    # Create output folder automatically if it does not exist.
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # --- GOOD application: Rahul Sharma ---
    rahul = {
        "application_type": "Salaried – Standard",
        "application_date": "24-Mar-2025",
        "personal": [
            ["Full name", "Rahul Sharma"],
            ["Age", "35 years"],
            ["Residential address", "Flat 402, Green Valley Apartments, Whitefield, Bengaluru – 560066"],
            ["PAN", "ABCDE1234F"],
            ["Aadhaar (last 4 digits)", "XXXX-XXXX-9012"],
            ["Mobile", "+91 98765 43210"],
            ["Email", "rahul.sharma@email.com"],
        ],
        "employment": [
            ["Employer name", "Tata Consultancy Services Limited (TCS)"],
            ["Designation", "Software Engineer"],
            ["Employment type", "Permanent / Full-time"],
            ["Total experience (current role)", "8 years at TCS"],
            ["Office address", "TCS Campus, Electronic City, Bengaluru"],
        ],
        "financial": [
            ["Monthly income (declared)", format_inr_indian(185000)],
            ["Average monthly income (bank statement)", format_inr_indian(185000)],
            ["Existing EMIs (all loans)", format_inr_indian(15000) + " per month"],
            ["Credit score (CIBIL / bureau)", "780"],
            ["Other fixed obligations", "Nil"],
        ],
        "loan": [
            ["Loan amount requested", format_inr_indian(8000000)],
            ["Purpose", "Purchase of residential property (self-occupied)"],
            ["Property value (as per valuation)", format_inr_indian(12000000)],
            ["LTV (Loan-to-Value) – indicative", "66.7% (subject to bank policy)"],
            ["Tenure requested", "20 years (240 months)"],
            ["Interest type", "Floating – linked to repo rate"],
        ],
        "assets_liabilities": [
            ["Fixed Deposits", format_inr_indian(1000000) + " (₹10 Lakh)"],
            ["Listed equity / mutual funds", format_inr_indian(500000) + " (₹5 Lakh)"],
            ["Vehicle", "Car – estimated value " + format_inr_indian(800000) + " (₹8 Lakh)"],
            ["Outstanding home / personal loans", "As per EMI schedule – EMIs " + format_inr_indian(15000) + "/month"],
            ["Credit card outstanding", "Nil (paid in full)"],
        ],
    }

    # --- RISKY application: Priya Patel ---
    priya = {
        "application_type": "Self-employed / Freelancer",
        "application_date": "24-Mar-2025",
        "personal": [
            ["Full name", "Priya Patel"],
            ["Age", "28 years"],
            ["Residential address", "203, Sunrise Residency, Satellite, Ahmedabad – 380015"],
            ["PAN", "FGHIJ5678K"],
            ["Aadhaar (last 4 digits)", "XXXX-XXXX-3456"],
            ["Mobile", "+91 91234 56789"],
            ["Email", "priya.patel.freelance@email.com"],
        ],
        "employment": [
            ["Occupation", "Freelancer (creative / digital services)"],
            ["Employer name", "Self-employed – multiple clients (variable)"],
            ["Employment type", "Contract / project-based"],
            ["Years in current line", "2 years (self-employed)"],
            ["Income pattern", "Irregular – depends on project invoicing"],
        ],
        "financial": [
            ["Monthly income (declared)", format_inr_indian(65000) + " (irregular month-to-month)"],
            ["Average last 6 months (stated)", format_inr_indian(52000) + " – high variance"],
            ["Existing EMIs (all loans)", format_inr_indian(28000) + " per month"],
            ["Credit score (CIBIL / bureau)", "620"],
            ["Other fixed obligations", "Personal loan + credit card minimums (as per statement)"],
        ],
        "loan": [
            ["Loan amount requested", format_inr_indian(7500000)],
            ["Purpose", "Purchase of under-construction apartment"],
            ["Property value (as per agreement)", format_inr_indian(8500000)],
            ["LTV (Loan-to-Value) – indicative", "88.2% (subject to bank policy – elevated)"],
            ["Tenure requested", "25 years (300 months)"],
            ["Interest type", "Floating – subject to risk-based pricing"],
        ],
        "assets_liabilities": [
            ["Bank savings / current balance", format_inr_indian(200000) + " (₹2 Lakh only)"],
            ["Investments (FD / MF / equity)", "Minimal – not substantiated with statements"],
            ["Vehicle / other assets", "None declared"],
            ["Outstanding loans", "EMIs totaling " + format_inr_indian(28000) + "/month"],
            ["Guarantees / contingent liabilities", "None declared"],
        ],
    }

    # Write both PDFs to applications/.
    path_rahul = OUTPUT_DIR / "rahul_sharma_loan.pdf"
    path_priya = OUTPUT_DIR / "priya_patel_loan.pdf"
    build_application_pdf(path_rahul, rahul)
    build_application_pdf(path_priya, priya)

    print("Created:")
    print(f"  {path_rahul}")
    print(f"  {path_priya}")


if __name__ == "__main__":
    main()
