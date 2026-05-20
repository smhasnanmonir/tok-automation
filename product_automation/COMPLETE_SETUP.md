# TOK Product Automation - Complete Setup Guide

## 🎯 Overview

This automation system runs **entirely on production** and:
1. ✅ Auto-login via OTP to `monirhasnan@gmail.com`
2. ✅ Google Images search (Playwright)
3. ✅ Download images
4. ✅ Upload to R2 (TokBD storage) - **same as tok-admin frontend**
5. ✅ Generate AI product details (OpenRouter)
6. ✅ Post products to backend

## 📂 Directory Structure

```
tok-automation/product_automation/
├── .env.example                    # Configure this first!
├── .env                            # (Create from .env.example)
├── requirements.txt                # Python dependencies
├── excel_reader.py                 # Reads Excel files
├── google_image_search.py          # Google Images + Playwright
├── ai_service.py                   # OpenRouter AI
├── product_automation.py           # CLI version
├── tui_automation.py               # TUI with auto-login ⭐
├── run_tui_automation.ps1          # Run TUI script ⭐
├── run_automation.ps1              # Run CLI script
└── README.md                       # Documentation
```

## 🚀 Quick Start

### Step 1: Setup Environment (Once)

```powershell
cd D:\Code\Web Projects\TOK\tok-automation\product_automation
copy .env.example .env
notepad .env
```

Edit `.env`:
```env
# Production URLs (already set)
API_BASE_URL=https://backend.tokbd.com
ADMIN_API_BASE_URL=https://admin.tokbd.com

# Email to receive OTP
EMAIL_FOR_OTP=monirhasnan@gmail.com

# OpenRouter API Key (REQUIRED)
OPENROUTER_API_KEY=YOUR_OPENROUTER_API_KEY

# Excel file path
EXCEL_FILE=products.xlsx

# Optional: Skip AI or Images if needed
SKIP_AI=false
SKIP_IMAGES=false
PRODUCT_DELAY=2
```

### Step 2: Install Dependencies

```powershell
pip install -r requirements.txt
```

### Step 3: Create Excel File

Create `products.xlsx` in the same directory with these columns:

| Column | Required | Example |
|--------|----------|---------|
| `name` | ✅ | Sunflower Seed Oil Serum |
| `price` | ✅ | 45000 |
| `brand` | ⭕ | L'Occitane |
| `category` | ⭕ | Skincare |
| `origin_price` | ⭕ | 55000 |
| `skin_type` | ⭕ | All |
| `skin_concern` | ⭕ | All |
| `origin_country` | ⭕ | korea |

**Example Excel:**
```
name,price,brand,category,origin_price,skin_type,skin_concern,origin_country
Sunflower Seed Oil Serum,45000,L'Occitane,Skincare,55000,All,All,korea
Vitamin C Brightening Cream,35000,The Ordinary,Skincare,40000,All,Aging,korea
```

### Step 4: Run Automation

```powershell
.\run_tui_automation.ps1
```

## 🎮 TUI Workflow

```
============================================================
  TOK Product Automation - TUI Version
============================================================

Configuration:
  - Email: monirhasnan@gmail.com
  - Excel: products.xlsx

============================================================
  Admin Login
============================================================
[+] Sending OTP to: monirhasnan@gmail.com
[+] OTP sent! Check your email inbox.

  ⏳ Waiting for OTP email...

Enter OTP from email: 123456
[+] Login successful!

============================================================
  Running Automation
============================================================
  [====================] 3/5

  Processing: Sunflower Seed Oil Serum
  🔍 Searching Google Images...
  Found 1 image(s)
  ✓ Downloaded and uploaded: product_serum.jpg
  🤖 Generating AI data...
  ✓ AI data generated successfully
  📤 Posting to backend...
  ✓ Posted successfully

============================================================
  Processing Complete
============================================================
  Total: 5
  Success: 5
  Failed: 0
```

## 🔐 Getting OTP

1. **OTP is sent** to `EMAIL_FOR_OTP` in `.env` (default: `monirhasnan@gmail.com`)
2. **Check email inbox** (and spam folder)
3. **Find 6-digit code** from `admin.tokbd.com`
4. **Enter OTP** when prompted

## 📊 Features Explained

### 1. Auto-Login
- Sends OTP request to backend
- You enter OTP from email
- System logs in automatically

### 2. Google Images Search
- Uses Playwright to search Google Images
- Downloads first relevant image
- **Uploads to R2** (same as tok-admin frontend)

### 3. AI Generation
- Uses OpenRouter API
- Generates SEO-optimized descriptions
- Creates ingredients, how-to-use, benefits

### 4. Product Posting
- Posts to `https://backend.tokbd.com/api/products/post`
- Uses JWT token for authentication
- Includes uploaded image URL

## ⚙️ Configuration Options

Edit `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `EMAIL_FOR_OTP` | `monirhasnan@gmail.com` | Email to receive OTP |
| `SKIP_IMAGES` | `false` | Skip Google image search |
| `SKIP_AI` | `false` | Skip AI generation |
| `PRODUCT_DELAY` | `2` | Seconds between products |
| `HEADLESS` | `true` | Use headless browser |
| `OPENROUTER_MODEL` | `deepseek/deepseek-v3.2` | AI model |

## 🤖 AI Models

| Model | Speed | Quality | Use Case |
|-------|-------|---------|----------|
| `deepseek/deepseek-v3.2` | Medium | High | Best balance ⭐ |
| `x-ai/grok-4.1-fast` | Fast | High | Quick generation |
| `qwen/qwen3.5-flash-02-23` | Fast | High | Good quality |
| `google/gemma-4-26b-a4b-it` | Medium | High | Technical content |

## 🔧 Troubleshooting

### OTP not received?
- Check spam/junk folder
- Wait 2-3 minutes between requests
- Verify email in `.env`

### Login failed?
- Check OTP is 6 digits
- Verify email matches `EMAIL_FOR_OTP`

### Images not uploading?
- Check `OPENROUTER_API_KEY`
- Reduce `PRODUCT_DELAY` if rate limited
- Set `SKIP_IMAGES=true` to bypass

### Excel file not found?
- Ensure `products.xlsx` is in the same folder as `.env`
- Or set full path in `.env`:
  ```
  EXCEL_FILE=D:\Code\Web Projects\TOK\products.xlsx
  ```

## 📝 Commands

```powershell
# TUI version (auto-login)
.\run_tui_automation.ps1

# CLI version (manual login)
.\run_automation.ps1

# Direct Python
python tui_automation.py
python product_automation.py
```

## ✅ Checklist

Before running:
- [ ] `.env` configured with `OPENROUTER_API_KEY`
- [ ] `EMAIL_FOR_OTP` set
- [ ] `products.xlsx` in the directory
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Email inbox ready for OTP

## 🎯 What Happens

1. **Login**: OTP sent → You enter → Auto-login complete
2. **Excel**: Reads product data
3. **Images**: Google search → Download → Upload to R2
4. **AI**: Generates descriptions, ingredients, benefits
5. **Backend**: Posts complete product with uploaded image

## 📞 Production URLs

- **Backend API**: `https://backend.tokbd.com`
- **Admin API**: `https://admin.tokbd.com`
- **Product Listing**: `https://tokbd.com/products`

All operations run on production - no local server needed!
