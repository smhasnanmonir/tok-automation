import pdfplumber
import sys
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT


def extract_sl_brand_name(input_pdf, output_pdf="extracted_sl_brand_name.pdf"):
    input_path = Path(input_pdf)
    if not input_path.exists():
        print(f"ERROR: Input PDF not found: {input_pdf}")
        sys.exit(1)

    rows = []
    serial_col = None
    brand_col = None
    product_col = None
    header_found = False

    try:
        with pdfplumber.open(input_pdf) as pdf:
            print(f"Processing {input_pdf}: {len(pdf.pages)} pages")
            for i, page in enumerate(pdf.pages, start=1):
                tables = page.extract_tables()
                if not tables:
                    continue
                for table in tables:
                    if not table or len(table) < 2:
                        continue
                    df_headers = table[0]
                    df_rows = table[1:]

                    # Detect columns if not found yet
                    if not header_found:
                        for idx, col in enumerate(df_headers):
                            col_lower = str(col).lower().strip() if col else ""
                            if col_lower in ("sl", "s/l", "s. l.", "serial", "no", "#", "sno", "s.no", "sl."):
                                serial_col = idx
                            elif col_lower in ("brand", "brand name", "brandname", "manufacturer"):
                                brand_col = idx
                            elif col_lower in ("product name", "product", "item", "productname", "item name", "name", "description"):
                                product_col = idx

                        if serial_col is None or product_col is None:
                            print(f"  Could not find SL / Product Name columns on page {i}, skipping")
                            continue
                        header_found = True

                    for row in df_rows:
                        sl = str(row[serial_col]).strip() if serial_col < len(row) and row[serial_col] else ""
                        brand = str(row[brand_col]).strip() if brand_col is not None and brand_col < len(row) and row[brand_col] else ""
                        name = str(row[product_col]).strip() if product_col < len(row) and row[product_col] else ""
                        if name and name.lower() not in ("nan", "none", ""):
                            rows.append((sl, brand, name))

                if (i % 5 == 0):
                    print(f"  Processed {i}/{len(pdf.pages)} pages")

        if not rows:
            print("ERROR: No data extracted from PDF")
            sys.exit(1)

        print(f"  Extracted {len(rows)} products")

    except Exception as e:
        print(f"ERROR: Could not process PDF: {e}")
        sys.exit(1)

    doc = SimpleDocTemplate(
        output_pdf,
        pagesize=A4,
        rightMargin=15,
        leftMargin=15,
        topMargin=15,
        bottomMargin=15
    )

    styles = getSampleStyleSheet()

    header_style = ParagraphStyle('Header', fontSize=7, textColor=colors.white, alignment=TA_CENTER, leading=9)
    cell_left = ParagraphStyle('Cell', fontSize=6, alignment=TA_LEFT, leading=8, wordWrap='CJK')
    cell_center = ParagraphStyle('CellCenter', fontSize=6, alignment=TA_CENTER, leading=8)

    table_data = [
        [
            Paragraph("<b>SL</b>", header_style),
            Paragraph("<b>Brand</b>", header_style),
            Paragraph("<b>Product Name</b>", header_style)
        ]
    ]

    for sl, brand, name in rows:
        table_data.append([
            Paragraph(sl, cell_center),
            Paragraph(brand, cell_left),
            Paragraph(name, cell_left)
        ])

    col_widths = [30, 90, 420]
    t = Table(table_data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 7),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 2),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#cbd5e1')),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
    ]))
    story = [t]

    doc.build(story)
    print(f"Extracted PDF saved to: {output_pdf}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_sl_name.py <input_pdf> [output_pdf]")
        print("  input_pdf   - Path to the source PDF")
        print("  output_pdf  - Output PDF path (default: extracted_sl_brand_name.pdf)")
        print("\nExample:")
        print('  python extract_sl_name.py "Bulk Wholesale Price-(01-06-2026).pdf"')
        print('  python extract_sl_name.py "input.pdf" "output.pdf"')
        sys.exit(1)

    input_pdf = sys.argv[1]
    output_pdf = sys.argv[2] if len(sys.argv) > 2 else "extracted_sl_brand_name.pdf"
    extract_sl_brand_name(input_pdf, output_pdf)
