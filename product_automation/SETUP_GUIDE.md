# TOK Product Automation - Setup Guide

This guide will help you set up and run the product automation system.

## Overview

This automation system:
1. Reads product data from an Excel file (name, price, optional fields)
2. Searches Google Images for product photos
3. Downloads the images
4. Generates product details using AI (OpenRouter API)
5. Posts the complete product data to your TOK backend

## Prerequisites

1. **Python 3.11+** installed
2. **Backend running** at `http://localhost:8787` (or your configured URL)
3. **Admin JWT token** from your TOK admin panel
4. **OpenRouter API key** from https://openrouter.ai/keys

## Step 1: Install Dependencies

```bash
cd tok-automation/product_automation
pip install -r requirements.txt
```

## Step 2: Configure Environment

1. Copy the example environment file:
```bash
copy .env.example .env
```

2. Edit `.env` with your configuration:
   - `API_BASE_URL`: Your backend URL (e.g., `http://localhost:8787`)
   - `ADMIN_TOKEN`: Copy from admin panel cookies
   - `OPENROUTER_API_KEY`: Your OpenRouter API key
   - `EXCEL_FILE`: Path to your Excel file

### Getting the Admin Token

1. Log in to your admin panel (e.g., `admin.tokbd.com`)
2. Open browser DevTools (F12) → Application → Cookies
3. Find the cookie named `adminAccessToken`
4. Copy its value
5. Paste it into `.env` as `ADMIN_TOKEN`

### Getting OpenRouter API Key

1. Go to https://openrouter.ai/
2. Sign up / Log in
3. Go to API Keys section
4. Create a new key
5. Copy the key and set it in `.env`

## Step 3: Prepare Excel File

Create an Excel file with the following columns:

| Column | Required | Description |
|--------|----------|-------------|
| name | Yes | Product name (3+ chars) |
| price | Yes | Selling price (numeric) |
| brand | No | Brand name |
| category | No | Product category |
| origin_price | No | Original/MRP price |
| skin_type | No | Skin type (optional) |
| skin_concern | No | Skin concern (optional) |
| origin_country | No | Country (default: korea) |

**Example Excel structure:**

| name | price | brand | category |
|------|-------|-------|----------|
| Sunflower Seed Oil Serum | 45000 | L'Occitane | Skincare |
| Vitamin C Brightening Cream | 35000 | The Ordinary | Skincare |

Save as `products.xlsx` and set `EXCEL_FILE=products.xlsx` in `.env`.

## Step 4: Run the Automation

### Basic usage:

```bash
python product_automation.py
```

### Example output:

```
============================================================
TOK Product Automation
============================================================
Started at: 2026-05-20T11:30:00+06:00

📊 Found 5 product(s) to process

============================================================
Processing: Sunflower Seed Oil Serum
============================================================

🔍 Searching Google Images for: Sunflower Seed Oil Serum
  Found 1 image(s)
  ✓ Downloaded: 20260520_113000_product_serum.jpg

🤖 Generating product details with AI...
  ✓ AI data generated successfully

📤 Posting product to backend...
  ✓ Product posted successfully
    Status: Product Posted!

...

============================================================
Processing Complete
============================================================
Total products: 5
Successful: 5
Failed: 0
```

## Step 5: Configuration Options

Edit values in `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `HEADLESS` | `true` | Run browser without GUI (faster) |
| `PRODUCT_DELAY` | `2` | Seconds between products |
| `SKIP_IMAGES` | `false` | Skip image search/download |
| `SKIP_AI` | `false` | Skip AI generation, use Excel data |
| `OPENROUTER_MODEL` | `deepseek/deepseek-v3.2` | AI model to use |

## Step 6: Troubleshooting

### Common Issues

1. **Token Error**: Run `python product_automation.py` to display the error. Check your `ADMIN_TOKEN` is correct.

2. **AI API Error**: Check your `OPENROUTER_API_KEY` is valid. You can test it at https://openrouter.ai/

3. **Excel File Not Found**: Check the `EXCEL_FILE` path in `.env`. Use absolute paths:
   ```
   EXCEL_FILE=D:\Code\Web Projects\TOK\tok-automation\products.xlsx
   ```

4. **Network Error**: Ensure your backend is running and accessible.

## Directory Structure

```
tok-automation/product_automation/
├── .env.example          # Example configuration
├── .env                  # Your configuration (create this)
├── requirements.txt      # Python dependencies
├── config.py             # Configuration loader
├── excel_reader.py       # Excel file reader
├── google_image_search.py # Google image search & download
├── ai_service.py         # AI integration
├── product_automation.py # Main script
└── downloads/            # Downloaded images (auto-created)
```

## Next Steps

- Add more optional columns to your Excel file for better data
- Adjust AI model in `.env` for better results
- Set `PRODUCT_DELAY` higher if you have API rate limits
