import pdfplumber
import pandas as pd
import json
import sys
import os
from datetime import datetime
from pathlib import Path
import re
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


# Patterns to remove from product names for comparison
PRODUCT_NAME_CLEANUP_PATTERNS = [
    r'\(Promotion Running\)',
    r'\(Promotion\)',
    r'\(promotion running\)',
    r'\(promotion\)',
    r'\s*-\s*Promotion Running',
    r'\s*-\s*Promotion',
    r'\s*-\s*promotion running',
    r'\s*-\s*promotion',
]


def cleanup_product_name(product_name):
    """Remove promotional text from product name for consistent comparison"""
    cleaned = product_name
    for pattern in PRODUCT_NAME_CLEANUP_PATTERNS:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def extract_date_from_filename(filename):
    """Extract date from PDF filename like 'Wholesale Price ( 28-02-2026 ).pdf'"""
    # Look for date pattern in parentheses
    match = re.search(r'\(\s*(\d{2}-\d{2}-\d{4})\s*\)', filename)
    if match:
        date_str = match.group(1)
        try:
            return datetime.strptime(date_str, '%d-%m-%Y')
        except:
            pass
    return None


def get_all_pdfs(pdf_dir='WholeSalePriceTrack/pdfs'):
    """Get all PDF files sorted by date (newest first)"""
    pdf_dir = Path(pdf_dir)
    if not pdf_dir.exists():
        return []

    pdfs = []
    for pdf_file in pdf_dir.glob('*.pdf'):
        date = extract_date_from_filename(pdf_file.name)
        pdfs.append({
            'path': str(pdf_file),
            'name': pdf_file.name,
            'date': date,
            'date_str': date.strftime('%d-%m-%Y') if date else pdf_file.name
        })

    # Sort by date (newest first)
    pdfs.sort(key=lambda x: x['date'] if x['date'] else datetime.min, reverse=True)
    return pdfs


def extract_products_from_pdf(pdf_path):
    """Extract products from PDF"""
    all_products = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            print(f"Processing {pdf_path}: {len(pdf.pages)} pages")

            for i, page in enumerate(pdf.pages, start=1):
                tables = page.extract_tables()

                if tables:
                    for table in tables:
                        if not table or len(table) < 2:
                            continue

                        df = pd.DataFrame(table[1:], columns=table[0])

                        # Find columns
                        brand_col = None
                        product_col = None
                        normal_price_col = None
                        wholesale_price_col = None

                        for col in df.columns:
                            col_lower = str(col).lower()
                            if 'brand' in col_lower:
                                brand_col = col
                            elif 'product' in col_lower and 'name' in col_lower:
                                product_col = col
                            elif 'normal' in col_lower and 'wholesale' in col_lower:
                                normal_price_col = col
                            elif 'wholesale' in col_lower and 'you' in col_lower:
                                wholesale_price_col = col

                        # Extract products
                        if brand_col and product_col:
                            for _, row in df.iterrows():
                                brand = str(row.get(brand_col, '')).strip()
                                product_name = str(row.get(product_col, '')).strip()

                                if brand and product_name and brand != 'nan' and product_name != 'nan':
                                    normal_price = str(row.get(normal_price_col, '')).strip() if normal_price_col else ''
                                    wholesale_price = str(row.get(wholesale_price_col, '')).strip() if wholesale_price_col else ''

                                    product = {
                                        "brand": brand,
                                        "product_name": product_name,
                                        "wholesale_price": normal_price,
                                        "wholesale_price_for_you": wholesale_price,
                                        "page": i
                                    }
                                    all_products.append(product)

                if (i % 10 == 0):
                    print(f"  Processed {i}/{len(pdf.pages)} pages")

        print(f"  Extracted {len(all_products)} products")
        return all_products

    except Exception as e:
        print(f"ERROR: Could not process {pdf_path}: {e}")
        return []


def create_product_key(product):
    """Create unique key for product matching
    Uses cleaned product name to handle promotional variants"""
    cleaned_name = cleanup_product_name(product['product_name'])
    return f"{product['brand']}||{cleaned_name}"


def safe_price_convert(price_str):
    """Safely convert price string to float"""
    if not price_str or price_str == 'nan' or price_str == '':
        return 0.0

    cleaned = ''.join(c for c in price_str if c.isdigit() or c == '.')

    try:
        return float(cleaned) if cleaned else 0.0
    except:
        return 0.0


def compare_pdfs(old_pdf_path, new_pdf_path, output_json='results/comparison_result.json'):
    """Compare two PDFs and generate comparison report"""

    print("="*80)
    print("PDF COMPARISON")
    print("="*80)

    # Extract products
    print("\n[1/3] Extracting products from OLD PDF...")
    old_products = extract_products_from_pdf(old_pdf_path)

    print("\n[2/3] Extracting products from NEW PDF...")
    new_products = extract_products_from_pdf(new_pdf_path)

    if not old_products or not new_products:
        print("\nERROR: Could not extract products from one or both PDFs")
        sys.exit(1)

    # Create dictionaries for lookup
    old_dict = {create_product_key(p): p for p in old_products}
    new_dict = {create_product_key(p): p for p in new_products}

    # Initialize results
    newly_added = []
    price_increased = []
    price_decreased = []
    stock_out = []
    unchanged = []

    print("\n[3/3] Comparing products...")

    # Compare products
    for key, new_product in new_dict.items():
        if key not in old_dict:
            newly_added.append(new_product)
        else:
            old_product = old_dict[key]

            old_price = safe_price_convert(old_product['wholesale_price_for_you'])
            new_price = safe_price_convert(new_product['wholesale_price_for_you'])

            if new_price > old_price and old_price > 0:
                price_increased.append({
                    "brand": new_product['brand'],
                    "product_name": new_product['product_name'],
                    "old_wholesale_price": old_product['wholesale_price'],
                    "old_wholesale_price_for_you": old_product['wholesale_price_for_you'],
                    "new_wholesale_price": new_product['wholesale_price'],
                    "new_wholesale_price_for_you": new_product['wholesale_price_for_you'],
                    "price_difference": new_price - old_price,
                    "percentage_change": round(((new_price - old_price) / old_price * 100), 2) if old_price > 0 else 0
                })
            elif new_price < old_price and new_price > 0:
                price_decreased.append({
                    "brand": new_product['brand'],
                    "product_name": new_product['product_name'],
                    "old_wholesale_price": old_product['wholesale_price'],
                    "old_wholesale_price_for_you": old_product['wholesale_price_for_you'],
                    "new_wholesale_price": new_product['wholesale_price'],
                    "new_wholesale_price_for_you": new_product['wholesale_price_for_you'],
                    "price_difference": old_price - new_price,
                    "percentage_change": round(((old_price - new_price) / old_price * 100), 2) if old_price > 0 else 0
                })
            else:
                unchanged.append(new_product)

    # Find stock out products
    for key, old_product in old_dict.items():
        if key not in new_dict:
            stock_out.append(old_product)

    # Create comparison result
    comparison_result = {
        "metadata": {
            "old_pdf": str(old_pdf_path),
            "new_pdf": str(new_pdf_path),
            "comparison_date": datetime.now().isoformat(),
            "old_pdf_total_products": len(old_products),
            "new_pdf_total_products": len(new_products),
            "summary": {
                "newly_added_count": len(newly_added),
                "price_increased_count": len(price_increased),
                "price_decreased_count": len(price_decreased),
                "stock_out_count": len(stock_out),
                "unchanged_count": len(unchanged)
            }
        },
        "newly_added_products": newly_added,
        "price_increased_products": price_increased,
        "price_decreased_products": price_decreased,
        "stock_out_products": stock_out
    }

    # Create results directory
    Path(output_json).parent.mkdir(parents=True, exist_ok=True)

    # Save to JSON
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(comparison_result, f, indent=2, ensure_ascii=False)

    # Print summary
    print("\n" + "="*80)
    print("COMPARISON SUMMARY")
    print("="*80)
    print(f"Old PDF: {old_pdf_path} ({len(old_products)} products)")
    print(f"New PDF: {new_pdf_path} ({len(new_products)} products)")
    print(f"\nNewly Added: {len(newly_added)} products")
    print(f"Price Increased: {len(price_increased)} products")
    print(f"Price Decreased: {len(price_decreased)} products")
    print(f"Stock Out: {len(stock_out)} products")
    print(f"Unchanged: {len(unchanged)} products")
    print(f"\nComparison saved to: {output_json}")
    print("="*80)

    # Create text summary
    summary_path = output_json.replace('.json', '_summary.txt')
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write("PDF COMPARISON SUMMARY\n")
        f.write("="*80 + "\n\n")
        f.write(f"Old PDF: {old_pdf_path} ({len(old_products)} products)\n")
        f.write(f"New PDF: {new_pdf_path} ({len(new_products)} products)\n")
        f.write(f"Comparison Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"Newly Added: {len(newly_added)} products\n")
        f.write(f"Price Increased: {len(price_increased)} products\n")
        f.write(f"Price Decreased: {len(price_decreased)} products\n")
        f.write(f"Stock Out: {len(stock_out)} products\n")
        f.write(f"Unchanged: {len(unchanged)} products\n")

    print(f"Summary saved to: {summary_path}")

    # Generate PDF report
    pdf_path = output_json.replace('.json', '_report.pdf')
    generate_pdf_report(comparison_result, pdf_path)

    return comparison_result


def create_cell(text, max_len=40):
    """Create a paragraph cell that wraps text properly"""
    if not text:
        return Paragraph("", getSampleStyleSheet()['Normal'])
    # Use word wrap by creating paragraph
    return Paragraph(text[:max_len] if len(text) <= max_len else text[:max_len-3]+'...',
                    ParagraphStyle('cell', fontSize=8, wordWrap='CJK'))

def generate_pdf_report(comparison_result, output_pdf='results/comparison_report.pdf'):
    """Generate a PDF report matching the website design"""
    
    # Create the PDF document - landscape for more space
    from reportlab.lib.pagesizes import landscape
    doc = SimpleDocTemplate(
        output_pdf,
        pagesize=landscape(A4),
        rightMargin=15,
        leftMargin=15,
        topMargin=15,
        bottomMargin=15
    )
    
    # Get styles
    styles = getSampleStyleSheet()
    
    # Custom styles matching website design
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#2563eb'),
        spaceAfter=8,
        alignment=TA_CENTER
    )
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Heading2'],
        fontSize=10,
        textColor=colors.HexColor('#64748b'),
        spaceAfter=10,
        alignment=TA_CENTER
    )
    
    section_style = ParagraphStyle(
        'Section',
        parent=styles['Heading2'],
        fontSize=11,
        textColor=colors.HexColor('#0f172a'),
        spaceBefore=12,
        spaceAfter=6,
        alignment=TA_CENTER
    )
    
    warning_style = ParagraphStyle(
        'Warning',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#dc2626'),
        spaceBefore=5,
        spaceAfter=5,
        alignment=TA_CENTER
    )
    
    # Build the story (content)
    story = []
    
    # Title
    story.append(Paragraph("TOK Prices Tracker", title_style))
    story.append(Paragraph("Wholesale Price Comparison Report", subtitle_style))
    
    # Warning text at the top
    story.append(Paragraph("⚠️ THIS PDF IS AUTOMATICALLY GENERATED BY TOK SYSTEM", warning_style))
    
    # Metadata
    metadata = comparison_result.get('metadata', {})
    old_pdf = metadata.get('old_pdf', '').split('/')[-1].replace('.pdf', '')
    new_pdf = metadata.get('new_pdf', '').split('/')[-1].replace('.pdf', '')
    comparison_date = metadata.get('comparison_date', '')[:10]
    
    metadata_style = ParagraphStyle('Metadata', parent=styles['Normal'], fontSize=9, alignment=TA_CENTER)
    story.append(Paragraph(f"Date: {comparison_date} | Old: {old_pdf} | New: {new_pdf}", metadata_style))
    story.append(Spacer(1, 8))
    
    # Summary stats - matching website's stats-grid
    summary = metadata.get('summary', {})
    
    # Summary table - compact
    summary_data = [
        ['Newly Added', 'Price Increased', 'Price Decreased', 'Stock Out', 'Unchanged'],
        [
            str(summary.get('newly_added_count', 0)),
            str(summary.get('price_increased_count', 0)),
            str(summary.get('price_decreased_count', 0)),
            str(summary.get('stock_out_count', 0)),
            str(summary.get('unchanged_count', 0))
        ]
    ]
    
    summary_table = Table(summary_data, colWidths=[90, 90, 90, 90, 90])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('BACKGROUND', (0, 1), (-1, 1), colors.white),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, 1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 10))
    
    # Helper function to create product tables with all products
    def create_product_table(products, title, header_color, text_color, show_price_change=True):
        if not products:
            return []
        
        sections = []
        # Center-aligned section title
        centered_title = ParagraphStyle('SectionCentered', parent=section_style, alignment=TA_CENTER)
        sections.append(Paragraph(f"{title} ({len(products)})", centered_title))
        
        # Determine columns based on whether to show price change
        if show_price_change:
            # Column widths with Change column
            col_widths = [60, 250, 60, 60, 60]
            headers = [
                Paragraph('<b>Brand</b>', styles['Normal']),
                Paragraph('<b>Product Name</b>', styles['Normal']),
                Paragraph('<b>Old Price</b>', styles['Normal']),
                Paragraph('<b>New Price</b>', styles['Normal']),
                Paragraph('<b>Change</b>', styles['Normal'])
            ]
        else:
            # Column widths without Change column (for NEWLY ADDED and STOCK OUT)
            col_widths = [60, 350, 100]
            headers = [
                Paragraph('<b>Brand</b>', styles['Normal']),
                Paragraph('<b>Product Name</b>', styles['Normal']),
                Paragraph('<b>Price</b>', styles['Normal'])
            ]
        
        # Split into pages if too many products
        rows_per_page = 30
        total_rows = len(products)
        
        for start in range(0, total_rows, rows_per_page):
            end = min(start + rows_per_page, total_rows)
            page_products = products[start:end]
            
            # Build table data with proper cell wrapping
            table_data = [headers]
            
            for p in page_products:
                brand = p.get('brand', '')[:15] if p.get('brand') else ''
                product = p.get('product_name', '')[:50] if p.get('product_name') else ''
                
                # Use Paragraph for text wrapping
                brand_cell = Paragraph(brand, ParagraphStyle('b', fontSize=7))
                product_cell = Paragraph(product, ParagraphStyle('p', fontSize=7))
                
                if show_price_change:
                    # Show price change columns (for PRICE INCREASED and PRICE DECREASED)
                    if 'old_wholesale_price_for_you' in p:
                        old_p = str(p.get('old_wholesale_price_for_you', '0'))
                        new_p = str(p.get('new_wholesale_price_for_you', '0'))
                        diff = p.get('price_difference', 0)
                        pct = p.get('percentage_change', 0)
                        sign = '+' if diff > 0 else ''
                        change = f"{sign}{diff} ({pct}%)"
                        table_data.append([
                            brand_cell,
                            product_cell,
                            Paragraph(old_p, ParagraphStyle('n', fontSize=7)),
                            Paragraph(new_p, ParagraphStyle('n', fontSize=7)),
                            Paragraph(change, ParagraphStyle('c', fontSize=7))
                        ])
                else:
                    # No price change columns (for NEWLY ADDED and STOCK OUT)
                    price = str(p.get('wholesale_price_for_you', 'N/A'))
                    table_data.append([
                        brand_cell,
                        product_cell,
                        Paragraph(price, ParagraphStyle('n', fontSize=7))
                    ])
            
            if len(table_data) > 1:
                # Create table with fixed column widths
                t = Table(table_data, colWidths=col_widths)
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), header_color),
                    ('TEXTCOLOR', (0, 0), (-1, 0), text_color),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 7),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
                    ('TOPPADDING', (0, 0), (-1, -1), 3),
                    ('BOTTOMPADDING', (0, 1), (-1, -1), 3),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                    ('LEFTPADDING', (0, 0), (-1, -1), 3),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                ]))
                sections.append(t)
            
            if end < total_rows:
                sections.append(PageBreak())
        
        return sections
    
    # Newly Added Products - ALL products (no price change columns)
    newly_added = comparison_result.get('newly_added_products', [])
    if newly_added:
        story.extend(create_product_table(
            newly_added,
            "NEWLY ADDED PRODUCTS",
            colors.HexColor('#dbeafe'),  # Light blue background
            colors.HexColor('#1e40af'),   # Dark blue text
            show_price_change=False
        ))
        story.append(PageBreak())
    
    # Price Increased - ALL products (with price change columns)
    price_increased = comparison_result.get('price_increased_products', [])
    if price_increased:
        story.extend(create_product_table(
            price_increased,
            "PRICE INCREASED",
            colors.HexColor('#ffedd5'),  # Light orange background
            colors.HexColor('#c2410c'),  # Dark orange text
            show_price_change=True
        ))
        story.append(PageBreak())
    
    # Price Decreased - ALL products (with price change columns)
    price_decreased = comparison_result.get('price_decreased_products', [])
    if price_decreased:
        story.extend(create_product_table(
            price_decreased,
            "PRICE DECREASED",
            colors.HexColor('#dcfce7'),  # Light green background
            colors.HexColor('#166534'),  # Dark green text
            show_price_change=True
        ))
        story.append(PageBreak())
    
    # Stock Out - ALL products (no price change columns)
    stock_out = comparison_result.get('stock_out_products', [])
    if stock_out:
        story.extend(create_product_table(
            stock_out,
            "STOCK OUT",
            colors.HexColor('#fee2e2'),  # Light red background
            colors.HexColor('#991b1b'),  # Dark red text
            show_price_change=False
        ))
    
    # Footer
    story.append(Spacer(1, 15))
    story.append(Paragraph("Generated automatically by TOK Automation System",
                           ParagraphStyle('Footer', parent=styles['Normal'],
                                         fontSize=6, textColor=colors.grey, alignment=TA_CENTER)))
    
    # Build PDF
    doc.build(story)
    print(f"PDF report saved to: {output_pdf}")
    return output_pdf


def generate_available_weeks_json(pdf_dir='WholeSalePriceTrack/pdfs', output_file='results/available_weeks.json'):
    """Generate a JSON file with all available weeks for the frontend"""
    pdfs = get_all_pdfs(pdf_dir)

    weeks_data = {
        "weeks": [
            {
                "filename": pdf['name'],
                "path": pdf['path'],
                "date": pdf['date_str'],
                "display_name": f"Week of {pdf['date_str']}" if pdf['date'] else pdf['name']
            }
            for pdf in pdfs
        ],
        "generated_at": datetime.now().isoformat()
    }

    # Create results directory
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(weeks_data, f, indent=2, ensure_ascii=False)

    print(f"Available weeks saved to: {output_file}")
    return weeks_data


def generate_all_comparisons(pdf_dir='WholeSalePriceTrack/pdfs', output_dir='results/comparisons'):
    """Generate comparison JSON for all possible week pairs"""
    pdfs = get_all_pdfs(pdf_dir)
    
    if len(pdfs) < 2:
        print("Need at least 2 PDFs to generate comparisons")
        return
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    comparisons = []
    
    # Generate comparisons for all pairs (newer vs older)
    for i, new_pdf in enumerate(pdfs):
        for j, old_pdf in enumerate(pdfs):
            if i < j:  # new_pdf is newer than old_pdf
                # Create a safe filename
                safe_name = f"{new_pdf['date_str']}_vs_{old_pdf['date_str']}.json"
                output_file = output_path / safe_name
                
                print(f"\nGenerating: {new_pdf['date_str']} vs {old_pdf['date_str']}")
                
                # Run comparison
                result = compare_pdfs(old_pdf['path'], new_pdf['path'], str(output_file))
                
                comparisons.append({
                    "new_date": new_pdf['date_str'],
                    "old_date": old_pdf['date_str'],
                    "filename": safe_name,
                    "path": str(output_file)
                })
    
    # Save index of all comparisons
    index_file = output_path / 'index.json'
    index_data = {
        "comparisons": comparisons,
        "generated_at": datetime.now().isoformat()
    }
    
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(index_data, f, indent=2, ensure_ascii=False)
    
    print(f"\nGenerated {len(comparisons)} comparisons")
    print(f"Index saved to: {index_file}")
    
    return index_data


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python compare_pdfs.py compare <old_pdf> <new_pdf>  - Compare two specific PDFs")
        print("  python compare_pdfs.py list                          - List all available PDFs")
        print("  python compare_pdfs.py generate-weeks                - Generate available_weeks.json")
        print("  python compare_pdfs.py generate-all                  - Generate all comparison files")
        print("  python compare_pdfs.py pdf [json_file]               - Generate PDF report from JSON")
        sys.exit(1)

    command = sys.argv[1]

    if command == "compare":
        if len(sys.argv) != 4:
            print("Usage: python compare_pdfs.py compare <old_pdf> <new_pdf>")
            sys.exit(1)
        old_pdf = sys.argv[2]
        new_pdf = sys.argv[3]
        compare_pdfs(old_pdf, new_pdf)

    elif command == "list":
        pdfs = get_all_pdfs()
        print("\nAvailable PDFs (sorted by date, newest first):")
        print("="*60)
        for i, pdf in enumerate(pdfs, 1):
            print(f"{i}. {pdf['name']} ({pdf['date_str']})")
        print()

    elif command == "generate-weeks":
        generate_available_weeks_json()

    elif command == "generate-all":
        generate_all_comparisons()

    elif command == "pdf":
        # Generate PDF from existing comparison result
        json_file = sys.argv[2] if len(sys.argv) > 2 else 'results/comparison_result.json'
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        pdf_file = json_file.replace('.json', '_report.pdf')
        generate_pdf_report(data, pdf_file)

    else:
        print(f"Unknown command: {command}")
        print("Use: compare, list, generate-weeks, generate-all, or pdf")
        sys.exit(1)
