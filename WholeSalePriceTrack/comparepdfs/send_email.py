#!/usr/bin/env python3
"""
Send comparison report via email using SMTP
"""
import smtplib
import os
import json
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders


def send_email_with_attachment():
    """Send email with PDF attachment"""
    
    # Read comparison results
    try:
        with open('results/comparison_result.json', 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("No comparison result found, skipping email")
        return False
    
    summary = data.get('metadata', {}).get('summary', {})
    old_pdf = data.get('metadata', {}).get('old_pdf', '').split('/')[-1].replace('.pdf', '')
    new_pdf = data.get('metadata', {}).get('new_pdf', '').split('/')[-1].replace('.pdf', '')
    
    # Get SMTP config from environment
    smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = os.getenv('SMTP_PORT', '587')
    smtp_username = os.getenv('SMTP_USERNAME', '')
    smtp_password = os.getenv('SMTP_PASSWORD', '')
    recipient = os.getenv('RECIPIENT', 'tokbdshop@gmail.com')
    
    if not smtp_username or not smtp_password:
        print('SMTP credentials not configured, skipping email')
        return False
    
    # Create email
    msg = MIMEMultipart()
    msg['From'] = smtp_username
    msg['To'] = recipient
    msg['Subject'] = f'TOK Price Comparison: {old_pdf} vs {new_pdf}'
    
    body = f"""TOK Wholesale Price Comparison Report

Comparison: {old_pdf} -> {new_pdf}

Summary:
- Newly Added: {summary.get('newly_added_count', 0)}
- Price Increased: {summary.get('price_increased_count', 0)}
- Price Decreased: {summary.get('price_decreased_count', 0)}
- Stock Out: {summary.get('stock_out_count', 0)}
- Unchanged: {summary.get('unchanged_count', 0)}

Total Products: {summary.get('newly_added_count', 0) + summary.get('price_increased_count', 0) + summary.get('price_decreased_count', 0) + summary.get('stock_out_count', 0) + summary.get('unchanged_count', 0)}

PDF Report attached.
"""
    msg.attach(MIMEText(body, 'plain'))
    
    # Attach PDF if exists
    pdf_path = 'results/comparison_result_report.pdf'
    if os.path.exists(pdf_path):
        with open(pdf_path, 'rb') as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', 'attachment; filename=comparison_report.pdf')
            msg.attach(part)
    else:
        print(f"PDF not found at {pdf_path}, sending email without attachment")
    
    # Send email
    try:
        server = smtplib.SMTP(smtp_server, int(smtp_port))
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.sendmail(smtp_username, recipient, msg.as_string())
        server.quit()
        print('Email sent successfully!')
        return True
    except Exception as e:
        print(f'Failed to send email: {e}')
        return False


if __name__ == '__main__':
    send_email_with_attachment()