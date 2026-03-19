# TOK Wholesale Price Tracker - Project Documentation

## 📋 Overview

**TOK Wholesale Price Tracker** is an automated system for tracking and comparing wholesale price lists from multiple PDF files. The system automatically detects new PDF uploads, compares them with previous versions, and generates detailed reports on price changes, new products, and stock status.

---

## 🎯 Purpose

The main goal of this project is to **automate pricing analysis** for wholesale products. Instead of manually comparing large PDF price lists (often containing 800+ products across 50+ pages), the system:

1. **Automatically detects** when new price PDFs are uploaded
2. **Extracts product data** from PDF tables
3. **Compares prices** between two time periods
4. **Generates reports** showing:
   - New products added
   - Price increases
   - Price decreases
   - Stock outs (products no longer available)
5. **Provides a web dashboard** to visualize all changes

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     TOK Price Tracker System                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │   PDF Files  │───▶│   Python     │───▶│   Results    │       │
│  │  (Source)    │    │   Script     │    │   (JSON)     │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│         │                   │                   │               │
│         ▼                   ▼                   ▼               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │  Wholesale   │    │  compare_    │    │  comparison  │       │
│  │  Price PDFs  │    │  pdfs.py     │    │  _result.json│       │
│  │              │    │              │    │              │       │
│  │ • 28-02-2026 │    │ • pdfplumber │    │ • newly_added│       │
│  │ • 07-03-2026 │    │ • pandas     │    │ • price_inc  │       │
│  └──────────────┘    └──────────────┘    │ • price_dec  │       │
│                                          │ • stock_out  │       │
│                                          └──────────────┘       │
│                                                 │               │
│                                                 ▼               │
│                                          ┌──────────────┐       │
│                                          │   Frontend   │       │
│                                          │   Dashboard  │       │
│                                          └──────────────┘       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📂 Project Structure

```
tok-automation/
├── .github/
│   └── workflows/
│       └── pdf-comparison.yml    # GitHub Actions automation
│
├── WholeSalePriceTrack/
│   ├── comparepdfs/
│   │   ├── compare_pdfs.py        # Core Python comparison script
│   │   └── send_email.py          # Email notification script
│   │
│   └── pdfs/
│       ├── Wholesale Price ( 28-02-2026 ).pdf
│       └── Wholesale Price ( 07-03-2026 ).pdf
│
├── frontend/
│   ├── index.html                # Dashboard HTML
│   ├── index.js                  # Dashboard JavaScript
│   ├── index.css                 # Dashboard Styles
│   └── wrangler.jsonc             # Cloudflare Pages config
│
├── results/
│   ├── comparison_result.json         # Latest comparison data
│   ├── comparison_result_report.pdf   # Auto-generated PDF report
│   ├── comparison_result_summary.txt
│   └── available_weeks.json           # List of available PDFs
│
├── GITHUB_SETUP.md               # GitHub secrets configuration
└── README.md                      # Original README
```

---

## 🔧 Components

### 1. Python Backend (`compare_pdfs.py`)

The core script that handles PDF processing and comparison.

#### Key Functions:

| Function                                                                                 | Purpose                                                                   |
| ---------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| [`extract_date_from_filename()`](WholeSalePriceTrack/comparepdfs/compare_pdfs.py:11)     | Extracts date from PDF filename like `Wholesale Price ( 28-02-2026 ).pdf` |
| [`get_all_pdfs()`](WholeSalePriceTrack/comparepdfs/compare_pdfs.py:24)                   | Gets all PDF files sorted by date (newest first)                          |
| [`extract_products_from_pdf()`](WholeSalePriceTrack/comparepdfs/compare_pdfs.py:45)      | Extracts product data from PDF tables using pdfplumber                    |
| [`safe_price_convert()`](WholeSalePriceTrack/comparepdfs/compare_pdfs.py:115)            | Safely converts price strings to floats                                   |
| [`compare_pdfs()`](WholeSalePriceTrack/comparepdfs/compare_pdfs.py:128)                  | Main comparison function                                                  |
| [`generate_available_weeks_json()`](WholeSalePriceTrack/comparepdfs/compare_pdfs.py:261) | Generates list of available PDFs for frontend                             |

#### Usage:

```bash
# List all available PDFs
python WholeSalePriceTrack/comparepdfs/compare_pdfs.py list

# Compare two specific PDFs
python WholeSalePriceTrack/comparepdfs/compare_pdfs.py compare <old_pdf> <new_pdf>

# Generate available weeks JSON
python WholeSalePriceTrack/comparepdfs/compare_pdfs.py generate-weeks
```

#### Output JSON Structure:

```json
{
  "metadata": {
    "old_pdf": "path/to/old.pdf",
    "new_pdf": "path/to/new.pdf",
    "comparison_date": "2026-03-19T12:00:00",
    "old_pdf_total_products": 861,
    "new_pdf_total_products": 841,
    "summary": {
      "newly_added_count": 25,
      "price_increased_count": 1,
      "price_decreased_count": 1,
      "stock_out_count": 46,
      "unchanged_count": 803
    }
  },
  "newly_added_products": [...],
  "price_increased_products": [...],
  "price_decreased_products": [...],
  "stock_out_products": [...]
}
```

---

### 2. GitHub Actions Workflow (`.github/workflows/pdf-comparison.yml`)

Automates the entire process when new PDFs are pushed.

#### Workflow Triggers:

| Trigger             | Description                                                    |
| ------------------- | -------------------------------------------------------------- |
| `push`              | Runs when PDF files in `WholeSalePriceTrack/pdfs/` are changed |
| `workflow_dispatch` | Allows manual trigger from GitHub UI                           |

#### Workflow Steps:

1. **Checkout** - Clones repository with full history (for date tracking)
2. **Setup Python** - Uses Python 3.11
3. **Install Dependencies** - Installs `pdfplumber`, `pandas`, `pypdf`, `reportlab`
4. **Find PDFs** - Identifies the 2 most recent PDFs using Git commit dates
5. **Run Comparison** - Executes the Python comparison script (generates JSON + PDF)
6. **Commit Results** - Saves comparison results to `results/` folder
7. **Push Changes** - Pushes results back to repository
8. **Send Email** - Sends HTML email with PDF attachment to stakeholders
9. **Create Summary** - Posts summary to GitHub Actions run

---

### 3. Email Notification System (`send_email.py`)

The system automatically sends professional HTML emails when new price comparisons are generated.

#### How It Works:

1. **Trigger**: After the comparison is complete and results are saved
2. **Read Data**: The script reads `comparison_result.json` to get summary statistics
3. **Create Email**: Generates both plain text and HTML versions
4. **Send**: Uses Python's `smtplib` to send via Gmail SMTP

#### Key Functions:

| Function                                                                           | Purpose                                                 |
| ---------------------------------------------------------------------------------- | ------------------------------------------------------- |
| [`send_email_with_attachment()`](WholeSalePriceTrack/comparepdfs/send_email.py:14) | Main function that reads data, creates email, and sends |

#### Email Features:

- **Professional HTML Template**: Clean, modern design with TOK branding
- **Summary Statistics**: Shows counts for all categories (New, Increased, Decreased, Stock Out, Unchanged)
- **Color-Coded Cards**: Light background colors for each category
- **PDF Attachment**: Automatically attaches the generated PDF report
- **Multi-Recipient**: Sends to multiple stakeholders

#### Recipients (Hardcoded):

```python
recipients = ['tokbdshop@gmail.com', 'monirhasnan@gmail.com']
```

#### Email Template Design:

```
┌─────────────────────────────────────────────┐
│  TOK Prices Tracker                        │
│  Wholesale Price Comparison Report         │
├─────────────────────────────────────────────┤
│  Comparison: Old PDF → New PDF              │
├─────────────────────────────────────────────┤
│  ┌─────────┐ ┌─────────┐ ┌─────────┐       │
│  │ Newly   │ │ Price   │ │ Price   │       │
│  │ Added   │ │Increased│ │Decreased│       │
│  │   25    │ │    5    │ │    1    │       │
│  └─────────┘ └─────────┘ └─────────┘       │
│  ┌─────────┐ ┌─────────┐                   │
│  │ Stock   │ │Unchanged│                   │
│  │  Out    │ │  803    │                   │
│  │   41    │ │         │                   │
│  └─────────┘ └─────────┘                   │
├─────────────────────────────────────────────┤
│  Total Products: 875                       │
│  PDF Report attached to this email          │
└─────────────────────────────────────────────┘
```

#### GitHub Secrets Required:

| Secret Name     | Value            | Description                |
| --------------- | ---------------- | -------------------------- |
| `SMTP_SERVER`   | `smtp.gmail.com` | SMTP server                |
| `SMTP_PORT`     | `587`            | SMTP port (TLS)            |
| `SMTP_USERNAME` | your email       | Gmail address              |
| `SMTP_PASSWORD` | app password     | 16-char Gmail App Password |

#### Workflow Integration:

The email is sent as the last step in the GitHub Actions workflow:

```yaml
- name: Send Email Notification
  if: success()
  run: python WholeSalePriceTrack/comparepdfs/send_email.py
  env:
    SMTP_SERVER: ${{ secrets.SMTP_SERVER }}
    SMTP_PORT: ${{ secrets.SMTP_PORT }}
    SMTP_USERNAME: ${{ secrets.SMTP_USERNAME }}
    SMTP_PASSWORD: ${{ secrets.SMTP_PASSWORD }}
```

---

### 4. Frontend Dashboard (`frontend/`)

A modern web interface to view comparison results.

#### Features:

- **Week Selection**: Choose which two weeks to compare
- **Statistics Dashboard**: Shows counts of new, increased, decreased, and stock-out products
- **Product Cards**: Detailed view of each product with price information
- **Search**: Filter products by brand or name
- **Download**: Export comparison data as JSON
- **Responsive Design**: Works on desktop and mobile

#### Data Sources:

The frontend fetches data from:

- `comparison_result.json` - Latest comparison results
- `available_weeks.json` - List of available PDF weeks

#### Key UI Elements:

| Element        | Description                                                     |
| -------------- | --------------------------------------------------------------- |
| Header         | Shows TOK logo and last updated time                            |
| Week Selectors | Dropdowns to select old and new PDF weeks                       |
| Stats Grid     | 4 cards showing: New, Price Increase, Price Decrease, Stock Out |
| Product Grids  | Cards displaying individual product details                     |
| Search Bar     | Real-time filtering of products                                 |

---

## 📊 How It Works

### Step 1: PDF Upload

1. New wholesale price PDF is added to `WholeSalePriceTrack/pdfs/`
2. Filename format: `Wholesale Price ( DD-MM-YYYY ).pdf`
3. Git LFS handles large PDF files efficiently

### Step 2: Automated Detection

1. GitHub Actions triggers on push to PDF folder
2. Workflow finds the 2 most recent PDFs using Git commit history
3. Determines which is "old" and which is "new"

### Step 3: Data Extraction

1. Python script opens each PDF using pdfplumber
2. Extracts tables from all pages
3. Identifies columns: Brand, Product Name, Normal Price, Wholesale Price
4. Creates product list with prices

### Step 4: Comparison

1. Matches products by Brand + Product Name
2. Compares wholesale prices between old and new
3. Categorizes each product:
   - **Newly Added**: In new PDF but not in old
   - **Price Increased**: Price went up
   - **Price Decreased**: Price went down
   - **Stock Out**: In old PDF but not in new
   - **Unchanged**: No price change

### Step 5: Results Generation

1. Creates `comparison_result.json` with all details
2. Creates `comparison_result_report.pdf` with formatted PDF report
3. Creates `available_weeks.json` listing all PDFs
4. Commits and pushes to repository

### Step 6: Email Notification

1. Reads the comparison summary from `comparison_result.json`
2. Creates a professional HTML email with:
   - TOK branding header
   - Summary statistics in color-coded cards
   - Total product count
3. Attaches the PDF report
4. Sends to multiple recipients via Gmail SMTP

### Step 7: Dashboard Update

1. Frontend fetches latest JSON from GitHub
2. Displays results in interactive dashboard
3. Users can search, filter, and download data

---

## 🛠️ Technology Stack

| Layer           | Technology       | Purpose                       |
| --------------- | ---------------- | ----------------------------- |
| Backend         | Python 3.11+     | PDF processing and comparison |
| PDF Parsing     | pdfplumber       | Extract tables from PDFs      |
| PDF Generation  | ReportLab        | Generate PDF reports          |
| Data Processing | pandas           | Data manipulation             |
| Email           | Python smtplib   | Send email notifications      |
| Automation      | GitHub Actions   | CI/CD pipeline                |
| Frontend        | HTML/CSS/JS      | Web dashboard                 |
| Hosting         | Cloudflare Pages | Free static hosting           |
| Storage         | Git LFS          | Large file storage for PDFs   |

---

## 📈 Example Output

### Comparison Summary:

```
Old PDF: Wholesale Price ( 28-02-2026 ).pdf (861 products)
New PDF: Wholesale Price ( 07-03-2026 ).pdf (841 products)

Newly Added: 25 products
Price Increased: 1 products
Price Decreased: 1 products
Stock Out: 46 products
Unchanged: 803 products
```

### Product Card Example:

```json
{
  "brand": "SAMSUNG",
  "product_name": "Galaxy A16 8GB",
  "old_wholesale_price": "24,500",
  "old_wholesale_price_for_you": "22,500",
  "new_wholesale_price": "25,000",
  "new_wholesale_price_for_you": "23,000",
  "price_difference": 500,
  "percentage_change": 2.22
}
```

---

## 🚀 Getting Started

### Prerequisites:

- Python 3.11+
- Git with LFS configured
- GitHub account (for automation)

### Local Development:

```bash
# Clone repository
git clone https://github.com/smhasnanmonir/tok-automation.git
cd tok-automation

# Install Python dependencies
pip install pdfplumber pandas reportlab

# List available PDFs
python WholeSalePriceTrack/comparepdfs/compare_pdfs.py list

# Compare two PDFs
python WholeSalePriceTrack/comparepdfs/compare_pdfs.py compare \
  "WholeSalePriceTrack/pdfs/Wholesale Price ( 28-02-2026 ).pdf" \
  "WholeSalePriceTrack/pdfs/Wholesale Price ( 07-03-2026 ).pdf"

# Generate available weeks
python WholeSalePriceTrack/comparepdfs/compare_pdfs.py generate-weeks
```

### Deployment:

1. Push PDF files to the repository
2. GitHub Actions automatically runs the comparison
3. Results appear in `results/` folder
4. Dashboard updates automatically at: `https://tok-automation.pages.dev`

---

## 🔒 Security Notes

- The system only processes PDF files in the designated folder
- No external API calls required (all processing is local)
- Results are stored in the repository (version controlled)
- Frontend is read-only (no data modification)

---

## 📝 License

This project is for internal use by TOK (tokbd.shop).

---

## 👤 Author

Developed for TOK Bangladesh - Your Trusted Online Shopping Destination

---

## 🆘 Support

For issues or questions:

1. Check the GitHub Actions logs for error details
2. Verify PDF format matches: `Wholesale Price ( DD-MM-YYYY ).pdf`
3. Ensure PDF has proper table structure with Brand and Product Name columns
4. For email issues: Verify GitHub Secrets are configured (see [GITHUB_SETUP.md](GITHUB_SETUP.md))
5. For Gmail auth errors: Use App Password, not regular password
