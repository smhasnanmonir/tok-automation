# TOK Price Tracker - Deployment Guide

This guide explains how to deploy the TOK Wholesale Price Tracker system.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Project Structure](#project-structure)
3. [Local Development Setup](#local-development-setup)
4. [Generating Comparisons](#generating-comparisons)
5. [Deploying Frontend with Wrangler](#deploying-frontend-with-wrangler)
6. [GitHub Actions (Automatic)](#github-actions-automatic)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before deploying, ensure you have:

- **Node.js** 18+ installed
- **Python** 3.11+ installed
- **Cloudflare account** (for Pages deployment)
- **Git** installed
- **Wrangler CLI** installed (optional, for manual deployment)

### Install Wrangler CLI

```bash
npm install -g wrangler
```

---

## Project Structure

```
tok-automation/
├── .github/
│   └── workflows/
│       └── pdf-comparison.yml    # GitHub Actions automation
├── WholeSalePriceTrack/
│   ├── comparepdfs/
│   │   └── compare_pdfs.py       # Python comparison script
│   └── pdfs/
│       └── *.pdf                  # Wholesale price PDFs
├── frontend/
│   ├── index.html                 # Dashboard HTML
│   ├── index.js                   # Dashboard JavaScript
│   ├── index.css                  # Dashboard Styles
│   └── wrangler.jsonc             # Cloudflare Pages config
├── results/
│   ├── comparison_result.json    # Latest comparison
│   ├── available_weeks.json       # List of available PDFs
│   └── comparisons/               # All comparison files
│       └── *.json
└── DEPLOYMENT_GUIDE.md           # This file
```

---

## Local Development Setup

### Step 1: Clone the Repository

```bash
git clone https://github.com/smhasnanmonir/tok-automation.git
cd tok-automation
```

### Step 2: Install Python Dependencies

```bash
pip install pdfplumber pandas
```

### Step 3: List Available PDFs

```bash
python WholeSalePriceTrack/comparepdfs/compare_pdfs.py list
```

Expected output:

```
Available PDFs (sorted by date, newest first):
============================================================
1. Wholesale Price ( 07-03-2026 ).pdf (07-03-2026)
2. Wholesale Price ( 28-02-2026 ).pdf (28-02-2026)
3. Wholesale Price ( 21-02-2026 ) (1).pdf (21-02-2026)
4. Wholesale Price ( 15-02-2026 ).pdf (15-02-2026)
```

---

## Generating Comparisons

### Option 1: Compare Two Specific PDFs

```bash
python WholeSalePriceTrack/comparepdfs/compare_pdfs.py compare <old_pdf> <new_pdf>
```

Example:

```bash
python WholeSalePriceTrack/comparepdfs/compare_pdfs.py compare \
  "WholeSalePriceTrack/pdfs/Wholesale Price ( 15-02-2026 ).pdf" \
  "WholeSalePriceTrack/pdfs/Wholesale Price ( 21-02-2026 ) (1).pdf"
```

### Option 2: Generate All Comparisons

This creates comparison files for ALL possible week pairs (useful for the frontend):

```bash
python WholeSalePriceTrack/comparepdfs/compare_pdfs.py generate-all
```

This generates:

- 6 comparison files in `results/comparisons/`
- An index file at `results/comparisons/index.json`

### Option 3: Update Available Weeks

```bash
python WholeSalePriceTrack/comparepdfs/compare_pdfs.py generate-weeks
```

This updates `results/available_weeks.json` for the frontend dropdown.

---

## Deploying Frontend with Wrangler

### Method 1: Using Wrangler CLI (Recommended)

#### Step 1: Login to Cloudflare

```bash
cd frontend
npx wrangler login
```

This will open a browser window for OAuth authentication.

#### Step 2: Deploy

```bash
npx wrangler pages deploy . --project-name=automation
```

Or with auto-commit warning silenced:

```bash
npx wrangler pages deploy . --project-name=automation --commit-dirty=true
```

#### Step 3: Access Your Site

- **Cloudflare Pages URL**: `https://<project-name>.pages.dev`
- **Custom Domain**: `auto.tokbd.com` (if configured)

### Method 2: Using GitHub Integration

1. Go to [Cloudflare Dashboard](https://dash.cloudflare.com)
2. Navigate to **Pages** > **Connect to Git**
3. Select your GitHub repository
4. Configure:
   - **Production branch**: `main`
   - **Build command**: (leave empty)
   - **Build output directory**: `frontend`
5. Click **Save and Deploy**

### Important: Exclude Large Files

The `wrangler.jsonc` file should exclude large PDF files:

```jsonc
{
  "name": "automation",
  "compatibility_date": "2026-02-08",
  "pages_build_output_dir": "./",
  "exclude": [
    "WholeSalePriceTrack/**",
    "results/**",
    ".github/**",
    "*.md",
    "*.py",
    "*.yml",
    "*.jsonc",
  ],
}
```

> **Note**: Cloudflare Pages has a 25 MiB file size limit. The PDF files are ~130 MiB each, so they must be excluded.

---

## GitHub Actions (Automatic)

The project includes GitHub Actions workflow that runs automatically when you push new PDFs.

### How It Works

1. **Trigger**: Push new PDF files to `WholeSalePriceTrack/pdfs/`
2. **Workflow**: Runs `.github/workflows/pdf-comparison.yml`
3. **Steps**:
   - Installs Python dependencies
   - Finds the 2 most recent PDFs
   - Runs comparison
   - Generates all comparisons
   - Commits results back to repository

### Manual Trigger

You can also run the workflow manually:

1. Go to your repository on GitHub
2. Click **Actions** tab
3. Select **PDF Comparison Automation**
4. Click **Run workflow**

---

## Troubleshooting

### Error: "Pages only supports files up to 25 MiB"

**Cause**: Large PDF files are being included in deployment.

**Solution**: Ensure `wrangler.jsonc` has the `exclude` configuration shown above.

### Error: "Failed to fetch auth token"

**Cause**: Wrangler not logged in.

**Solution**: Run `npx wrangler login` and authenticate in your browser.

### Error: "Unknown command"

**Cause**: Missing the `compare` command.

**Solution**: Use `python compare_pdfs.py compare <old> <new>` not just `<old> <new>`

### Frontend Shows "Week data unavailable"

**Cause**: `available_weeks.json` not generated.

**Solution**: Run:

```bash
python WholeSalePriceTrack/comparepdfs/compare_pdfs.py generate-weeks
```

### Cannot Select Different Weeks

**Cause**: Comparison files not generated.

**Solution**: Run:

```bash
python WholeSalePriceTrack/comparepdfs/compare_pdfs.py generate-all
```

---

## Quick Reference Commands

| Command                                                 | Description                   |
| ------------------------------------------------------- | ----------------------------- |
| `python compare_pdfs.py list`                           | List all PDFs                 |
| `python compare_pdfs.py compare <old> <new>`            | Compare two PDFs              |
| `python compare_pdfs.py generate-weeks`                 | Update week list for frontend |
| `python compare_pdfs.py generate-all`                   | Generate all comparisons      |
| `npx wrangler login`                                    | Login to Cloudflare           |
| `npx wrangler pages deploy . --project-name=automation` | Deploy frontend               |

---

## Adding New PDFs

1. Add PDF to `WholeSalePriceTrack/pdfs/`
2. Follow naming convention: `Wholesale Price ( DD-MM-YYYY ).pdf`
3. Run generate-all: `python compare_pdfs.py generate-all`
4. Deploy frontend: `npx wrangler pages deploy frontend/ --project-name=automation`

---

## Support

For issues:

1. Check GitHub Actions logs for errors
2. Verify PDF format matches: `Wholesale Price ( DD-MM-YYYY ).pdf`
3. Ensure PDF has proper table structure with Brand and Product Name columns
