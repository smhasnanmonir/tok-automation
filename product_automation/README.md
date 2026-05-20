# TOK Product Automation - Complete System

## Summary

I have created a complete Python automation system at `tok-automation/product_automation/` that:

1. **Reads product data from Excel** - Supports columns: name, price, brand, category, origin_price, skin_type, skin_concern, origin_country
2. **Searches Google Images using Playwright** - Downloads product photos from search results
3. **Generates product details with AI** - Uses OpenRouter API to create descriptions, ingredients, how-to-use, benefits
4. **Posts products to backend** - Sends complete data via POST /api/products/post with admin authentication

## Files Created

```
tok-automation/product_automation/
├── .env.example              # Environment configuration template
├── .env                      # (Create from .env.example)
├── requirements.txt          # Python dependencies
├── __init__.py               # Package initialization
├── config.py                 # Configuration loader
├── excel_reader.py           # Excel file reader
├── google_image_search.py    # Google Images search & Playwright download
├── ai_service.py             # OpenRouter AI integration
├── product_automation.py     # Main automation script
├── run_automation.ps1        # PowerShell runner script
└── SETUP_GUIDE.md            # Complete setup instructions
```

## Quick Start

1. **Copy and configure environment:**
   ```bash
   copy .env.example .env
   # Edit .env with your settings
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run automation:**
   ```bash
   python product_automation.py
   ```

## Configuration Required

- `API_BASE_URL`: Backend URL (e.g., `http://localhost:8787`)
- `ADMIN_TOKEN`: JWT token from admin panel cookies
- `OPENROUTER_API_KEY`: Key from https://openrouter.ai/keys
- `EXCEL_FILE`: Path to products.xlsx

## Excel Format

Required columns:
- `name`: Product name (min 3 characters)
- `price`: Selling price (numeric)

Optional columns:
- `brand`, `category`, `origin_price`, `skin_type`, `skin_concern`, `origin_country`

## Features

- **Google Image Search**: Downloads first relevant image from Google Images
- **AI Generation**: Creates SEO-optimized product descriptions
- **Admin Auth**: Uses JWT tokens for secure backend access
- **Error Handling**: Gracefully handles failures and continues
- **Configurable**: Skip AI, skip images, adjust delays
- **Detailed Logging**: Shows progress for each product

## Supported AI Models (OpenRouter)

- `deepseek/deepseek-v3.2` - Best quality/cost balance
- `x-ai/grok-4.1-fast` - Fast responses
- `qwen/qwen3.5-flash-02-23` - Good quality, fast
- `google/gemma-4-26b-a4b-it` - Good for technical content

## Backend API Integration

- Endpoint: `POST /api/products/post`
- Authentication: Bearer token in header
- Required fields: name, slug, brand, brand_slug, price, img, card_photo, productDetails
- Response: Product ID and confirmation message

## Next Steps

1. Create your Excel file with product data
2. Configure .env with your tokens and API key
3. Run the automation script
4. Products will be posted to your backend automatically
