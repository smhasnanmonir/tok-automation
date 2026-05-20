# TOK Product Automation - Complete System with TUI

## 🎯 Overview

This automation system runs on **production URLs** and includes an interactive TUI (Text User Interface) that:

1. **Automatically sends OTP request** to `monirhasnan@gmail.com`
2. **You enter the OTP manually** from your email
3. **Logs in automatically** to the admin panel
4. **Reads Excel file** with product data
5. **Searches Google Images** using Playwright
6. **Downloads product photos**
7. **Generates product details with AI** (OpenRouter)
8. **Posts products** to the backend

## 📂 File Structure

```
tok-automation/product_automation/
├── .env.example                  # Environment configuration
├── .env                          # Your configuration (create this)
├── requirements.txt              # Python dependencies
├── __init__.py                   # Package init
├── config.py                     # Configuration loader
├── excel_reader.py               # Excel file reader
├── google_image_search.py        # Google Images search
├── ai_service.py                 # OpenRouter AI integration
├── product_automation.py         # CLI automation script
├── tui_automation.py             # TUI with auto-login ⭐
├── run_automation.ps1            # PowerShell runner (CLI)
├── run_tui_automation.ps1        # PowerShell runner (TUI) ⭐
└── SETUP_GUIDE.md                # Setup instructions
```

## 🚀 Quick Start

### Step 1: Setup Environment

1. **Copy config template:**
   ```powershell
   copy .env.example .env
   ```

2. **Edit `.env`** with your settings:
   ```powershell
   notepad .env
   ```

   Important settings:
   ```
   # Production URLs
   API_BASE_URL=https://backend.tokbd.com

   # Email for OTP (where OTP is sent)
   EMAIL_FOR_OTP=monirhasnan@gmail.com

   # OpenRouter API key
   OPENROUTER_API_KEY=sk-or-v1-...

   # Excel file
   EXCEL_FILE=products.xlsx
   ```

3. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

### Step 2: Prepare Excel File

Create `products.xlsx` with these columns:

| Column | Required | Description |
|--------|----------|-------------|
| `name` | ✅ | Product name (min 3 chars) |
| `price` | ✅ | Selling price (numeric) |
| `brand` | ⭕ | Brand name (optional) |
| `category` | ⭕ | Product category (optional) |
| `origin_price` | ⭕ | Original/MRP price (optional) |
| `skin_type` | ⭕ | Skin type (optional) |
| `skin_concern` | ⭕ | Skin concern (optional) |
| `origin_country` | ⭕ | Country (default: korea) |

**Example:**
```
name,price,brand,category
Sunflower Seed Oil Serum,45000,L'Occitane,Skincare
Vitamin C Brightening Cream,35000,The Ordinary,Skincare
```

### Step 3: Run the TUI (Recommended)

```powershell
.\run_tui_automation.ps1
```

**What happens:**
1. OTP request sent to `monirhasnan@gmail.com`
2. Check your email inbox for OTP code
3. Enter OTP when prompted
4. Browse/select Excel file
5. Automation runs with progress display
6. Results summary shown

## 🎮 TUI Interaction Flow

```
============================================================
  TOK Product Automation - TUI Version
============================================================

Configuration:
  - Email: monirhasnan@gmail.com
  - Excel File: (browse to select)
  - Skip Images: false
  - Skip AI: false

============================================================
  Admin Login
============================================================
[+] Sending OTP request to: monirhasnan@gmail.com
[+] OTP sent! Check your email inbox.

  ⏳ Waiting for OTP email...

Enter OTP from email: 123456
[+] Login successful!

============================================================
  Select Excel File
============================================================
Available Excel files:
  [1] products.xlsx (D:\...\products.xlsx)

Select file (or enter path): 1

============================================================
  Processing Products
============================================================
[+] Found 5 products

============================================================
  Running Automation
============================================================
  [====================] 4/5

  Processing: Sunflower Seed Oil Serum
  🔍 Searching Google Images...
  Found 1 image(s)
  ✓ Downloaded: product_serum.jpg
  🤖 Generating AI data...
  ✓ AI data generated
  📤 Posting to backend...
  ✓ Posted successfully

============================================================
  Processing Complete
============================================================
  Total: 5
  Success: 5
  Failed: 0
```

## 🔐 Getting OTP Email

1. **Send request:**
   - TUI automatically sends OTP to `EMAIL_FOR_OTP` in `.env`
   - Default: `monirhasnan@gmail.com`

2. **Check email:**
   - Open Gmail (or your email provider)
   - Look for email from `admin.tokbd.com`
   - Find 6-digit OTP code

3. **Enter OTP:**
   - Type the 6-digit code when prompted
   - Press Enter

## ⚙️ Configuration Options

Edit `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `EMAIL_FOR_OTP` | `monirhasnan@gmail.com` | Email to receive OTP |
| `API_BASE_URL` | `https://backend.tokbd.com` | Backend URL |
| `OPENROUTER_API_KEY` | `sk-or-v1-...` | OpenRouter API key |
| `EXCEL_FILE` | `products.xlsx` | Excel file path |
| `HEADLESS` | `true` | Use headless browser |
| `PRODUCT_DELAY` | `2` | Seconds between products |
| `SKIP_IMAGES` | `false` | Skip image search |
| `SKIP_AI` | `false` | Skip AI generation |
| `OPENROUTER_MODEL` | `deepseek/deepseek-v3.2` | AI model |

## 🤖 AI Models (OpenRouter)

| Model | Speed | Quality | Use Case |
|-------|-------|---------|----------|
| `deepseek/deepseek-v3.2` | Medium | High | Best balance ⭐ |
| `x-ai/grok-4.1-fast` | Fast | High | Quick generation |
| `qwen/qwen3.5-flash-02-23` | Fast | High | Good quality |
| `google/gemma-4-26b-a4b-it` | Medium | High | Technical content |

## 📊 Excel Columns Explained

**Required:**
- `name`: Product name (must be 3+ characters)
- `price`: Selling price (stored as text in DB)

**Optional:**
- `brand`: Brand name
- `category`: Product category
- `origin_price`: Original/MRP price
- `skin_type`: Skin type (Acne, Combination, Dry, etc.)
- `skin_concern`: Skin concern (Aging, Brightening, etc.)
- `origin_country`: Country of origin (default: korea)

## 🛠️ Troubleshooting

### Issue: OTP not received

**Solution:**
1. Check spam/junk folder in email
2. Verify `EMAIL_FOR_OTP` in `.env`
3. Wait 2-3 minutes between OTP requests

### Issue: Login failed

**Solution:**
1. Check OTP is 6 digits
2. Verify email matches `EMAIL_FOR_OTP`
3. Check backend is running

### Issue: Excel file not found

**Solution:**
1. Ensure `products.xlsx` is in the same folder as `.env`
2. Or set full path in `.env`:
   ```
   EXCEL_FILE=D:\Code\Web Projects\TOK\products.xlsx
   ```

### Issue: AI API error

**Solution:**
1. Check `OPENROUTER_API_KEY` is valid
2. Visit https://openrouter.ai/keys to verify
3. Try a different model in `OPENROUTER_MODEL`

### Issue: Images not downloading

**Solution:**
1. Reduce `PRODUCT_DELAY` if rate limited
2. Set `SKIP_IMAGES=true` to skip
3. Check firewall/antivirus blocking

## 📝 Commands Reference

### PowerShell (Recommended)
```powershell
# TUI version (with auto-login)
.\run_tui_automation.ps1

# CLI version (manual login)
.\run_automation.ps1
```

### Direct Python
```bash
# TUI mode
python tui_automation.py

# CLI mode
python product_automation.py
```

## 🎯 Production URLs

- **Backend API:** `https://backend.tokbd.com`
- **Admin API:** `https://admin.tokbd.com`
- **Product Listing:** `https://tokbd.com/products`

## ✅ Checklist

Before running:
- [ ] `.env` file created and configured
- [ ] `OPENROUTER_API_KEY` set
- [ ] `EMAIL_FOR_OTP` set (default: monirhasnan@gmail.com)
- [ ] `products.xlsx` in the directory
- [ ] Python dependencies installed
- [ ] Email inbox checked for OTP

## 📞 Support

For issues:
1. Check `.env` configuration
2. Verify Excel file format
3. Check backend API is accessible
4. Review OpenRouter API key validity
