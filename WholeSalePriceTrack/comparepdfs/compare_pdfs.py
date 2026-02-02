

import pdfplumber
import pandas as pd
import json
import sys
from datetime import datetime
from pathlib import Path


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
    """Create unique key for product matching"""
    return f"{product['brand']}||{product['product_name']}"


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
    
    return comparison_result


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python compare_pdfs.py <old_pdf> <new_pdf>")
        sys.exit(1)
    
    old_pdf = sys.argv[1]
    new_pdf = sys.argv[2]
    
    compare_pdfs(old_pdf, new_pdf)