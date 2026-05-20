# TOK Product Automation - TUI with Auto-Login

## ✅ System Complete

The automation system is **fully configured** and ready to use with:

### Production Integration
- ✅ Backend API: `https://backend.tokbd.com`
- ✅ Admin API: `https://admin.tokbd.com`
- ✅ Image Upload: Via backend API (same as tok-admin backend)

### Features
1. **Auto-Login**: Sends OTP to `monirhasnan@gmail.com`
2. **Google Images Search**: Downloads product photos using Playwright
3. **AI Generation**: Creates product details with OpenRouter
4. **Product Posting**: Sends complete product data to backend
5. **Visual Progress**: Interactive TUI with progress bars

## 🚀 Quick Start

### 1. Setup `.env`
```powershell
copy .env.example .env
```

Edit `.env`:
```env
# Production URLs (already configured)
API_BASE_URL=https://backend.tokbd.com
ADMIN_API_BASE_URL=https://admin.tokbd.com

# OTP Email
EMAIL_FOR_OTP=monirhasnan@gmail.com

# OpenRouter API Key (required)
OPENROUTER_API_KEY=YOUR_OPENROUTER_API_KEY

# Excel file
EXCEL_FILE=products.xlsx
```

### 2. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 3. Prepare Excel File
Create `products.xlsx` in the same directory with columns:

| name | price | brand | category |
|------|-------|-------|----------|
| Sunflower Seed Oil Serum | 45000 | L'Occitane | Skincare |
| Vitamin C Brightening Cream | 35000 | The Ordinary | Skincare |

### 4. Run Automation
```powershell
.\run_tui_automation.ps1
```

## 📋 TUI Workflow

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
[+] OTP sent! Check your email.

Enter OTP from email: 123456
[+] Login successful!

============================================================
  Running Automation
============================================================
  [====================] 3/5

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

## 🎯 What Happens

1. **Login**: OTP sent to email → You enter OTP → Auto-login
2. **Excel Reading**: Reads product data from your Excel file
3. **Image Search**: Google Images → Downloads first relevant image
4. **AI Generation**: Creates descriptions, ingredients, benefits
5. **Backend Post**: Sends complete product data to TOK backend

## 📊 Excel Columns

| Column | Required | Description |
|--------|----------|-------------|
| `name` | ✅ | Product name (3+ chars) |
| `price` | ✅ | Selling price |
| `brand` | ⭕ | Brand name |
| `category` | ⭕ | Product category |
| `origin_price` | ⭕ | Original/MRP price |
| `skin_type` | ⭕ | Skin type |
| `skin_concern` | ⭕ | Skin concern |
| `origin_country` | ⭕ | Country (default: korea) |

## ⚙️ Configuration Options

Edit `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `EMAIL_FOR_OTP` | `monirhasnan@gmail.com` | OTP email |
| `SKIP_IMAGES` | `false` | Skip image search |
| `SKIP_AI` | `false` | Skip AI generation |
| `PRODUCT_DELAY` | `2` | Seconds between products |
| `HEADLESS` | `true` | Use headless browser |

## 🛠️ Files

```
tok-automation/product_automation/
├── .env.example
├── .env
├── requirements.txt
├── excel_reader.py
├── google_image_search.py
├── ai_service.py
├── product_automation.py    # CLI version
├── tui_automation.py        # TUI with auto-login ⭐
├── run_automation.ps1       # CLI runner
├── run_tui_automation.ps1   # TUI runner ⭐
└── README_TUI.md
```

## 📞 Next Steps

1. Create `products.xlsx` with your product data
2. Get `OPENROUTER_API_KEY` from https://openrouter.ai/keys
3. Run `.\run_tui_automation.ps1`
4. Check email for OTP, enter it when prompted
5. Products will be automatically created in your backend!
