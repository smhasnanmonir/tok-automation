# GitHub Environment Setup Guide

This guide explains how to configure the GitHub repository secrets required for the TOK Automation workflow, particularly for email notifications.

## Required Secrets

The workflow requires the following GitHub Secrets to be configured:

| Secret Name     | Value              | Description                |
| --------------- | ------------------ | -------------------------- |
| `SMTP_SERVER`   | `smtp.gmail.com`   | SMTP server for Gmail      |
| `SMTP_PORT`     | `587`              | SMTP port (TLS)            |
| `SMTP_USERNAME` | Your Gmail address | e.g., `yourname@gmail.com` |
| `SMTP_PASSWORD` | Gmail App Password | 16-character app password  |

**Note:** Email recipients are hardcoded in the script to:

- `tokbdshop@gmail.com`
- `monirhasnan@gmail.com`

## Step-by-Step Setup

### Step 1: Navigate to Repository Settings

1. Go to your GitHub repository
2. Click on **Settings** tab
3. In the left sidebar, click on **Secrets and variables**
4. Click on **Actions**

### Step 2: Add New Secrets

For each secret listed above:

1. Click the **New repository secret** button
2. Enter the secret name in the **Name** field
3. Enter the secret value in the **Secret** field
4. Click **Add secret**

### Step 3: Configure Gmail for SMTP

Since Gmail requires App Passwords (not regular passwords) for third-party apps:

1. Go to your Google Account: https://myaccount.google.com
2. Click on **Security** in the left sidebar
3. Enable **2-Step Verification** if not already enabled
4. Go to https://myaccount.google.com/apppasswords
5. Select **Mail** as the app
6. Select **Other (Custom name)** and enter "TOK Automation"
7. Click **Generate**
8. Copy the 16-character password shown
9. Use this as the `SMTP_PASSWORD` secret value

### Step 4: Verify Configuration

After adding all secrets:

1. Go to the **Actions** tab in your repository
2. Select the **PDF Comparison Automation** workflow
3. Click **Run workflow**
4. Click **Run workflow** button
5. Watch the workflow execution to confirm email is sent successfully

## Troubleshooting

### Email Not Sent

If the workflow runs but no email is received:

1. Check workflow logs for error messages
2. Verify all secrets are correctly configured
3. Ensure Gmail App Password is correct (16 characters)
4. Check spam/junk folder

### Common Errors

- **"SMTP credentials not configured"**: Missing `SMTP_USERNAME` or `SMTP_PASSWORD` secrets
- **"Authentication failed"**: Wrong Gmail App Password
- **"535 5.7.8"**: Need to use App Password, not regular password

## Security Notes

- Never commit secrets to the repository
- Secrets are encrypted and only available during workflow runs
- Rotate App Passwords periodically
- Use a dedicated email address for automation if preferred
