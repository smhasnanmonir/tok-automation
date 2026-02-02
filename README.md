# TOK Automation

Automated system for tracking and comparing wholesale price lists using GitHub Actions and Python. This tool automatically detects new PDF uploads, compares them with the previous version, and generates detailed reports on price changes, new products, and stock status.

## 🚀 Setup & Installation

### Step 1: Install Git LFS
Since PDF files can be large and binary, we use Git Large File Storage (LFS) to manage them efficiently.

**Ubuntu/Debian**
```bash
sudo apt install git-lfs
```

**CentOS/RHEL**
```bash
sudo yum install git-lfs
```

### Step 2: Prepare Your Repository
Initialize LFS and configure it to track PDF files.

```bash
git lfs install           # Enable LFS
git lfs track "*.pdf"     # Auto-handle all PDFs via LFS
git add .gitattributes    # Commit tracking rules FIRST
```

## ⚙️ How It Works

### 1. PDF Detection
The system is designed to automatically detect when a new PDF is uploaded to the `WholeSalePriceTrack/pdfs/` directory.
- It scans the directory for all `.pdf` files.
- **Sorting Logic:** Instead of relying on filesystem timestamps (which reset in CI environments), it uses **Git commit history**.
    - The file with the most recent commit timestamp is identified as the **New PDF**.
    - The file with the second most recent commit timestamp is identified as the **Old PDF**.

### 2. Comparison Process
A GitHub Actions workflow (`pdf-comparison.yml`) triggers automatically on every push to the PDF folder.
1.  **Extract Data:** The Python script (`compare_pdfs.py`) reads both PDFs using `pdfplumber`.
2.  **Analyze columns:** It intelligently identifies columns for Brand, Product Name, and Wholesale Prices.
3.  **Compare:** It matches products based on Brand and Name to calculate:
    - 📦 **Newly Added products**
    - 📈 **Price Increases**
    - 📉 **Price Decreases**
    - ❌ **Stock Outs** (Items present in the old PDF but missing in the new one)

### 3. Results & Notifications
- **JSON Report:** A detailed `comparison_result.json` is generated in the `results/` folder.
- **Workflow Summary:** A visual summary is posted directly to the GitHub Actions run summary.
- **Commit:** The results are automatically committed back to the repository.

## 📂 Project Structure

```
.
├── .github/workflows/
│   └── pdf-comparison.yml    # CI/CD Automation logic
├── WholeSalePriceTrack/
│   ├── comparepdfs/
│   │   └── compare_pdfs.py   # Python comparison logic
│   └── pdfs/                 # Store your Price list PDFs here
└── results/                  # Generated comparison outputs
```
