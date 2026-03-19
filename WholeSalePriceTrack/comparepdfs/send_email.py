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
    
    # Hardcoded recipients
    recipients = ['monirhasnan@gmail.com', 'tj010901@gmail.com']
    
    if not smtp_username or not smtp_password:
        print('SMTP credentials not configured, skipping email')
        return False
    
    # Create email
    msg = MIMEMultipart('alternative')
    msg['From'] = smtp_username
    msg['To'] = ', '.join(recipients)
    msg['Subject'] = f'TOK Price Comparison: {old_pdf} vs {new_pdf}'
    
    # Calculate total products
    total_products = (summary.get('newly_added_count', 0) +
                      summary.get('price_increased_count', 0) +
                      summary.get('price_decreased_count', 0) +
                      summary.get('stock_out_count', 0) +
                      summary.get('unchanged_count', 0))
    
    # Plain text version
    plain_body = f"""TOK Wholesale Price Comparison Report

Comparison: {old_pdf} -> {new_pdf}

Summary:
- Newly Added: {summary.get('newly_added_count', 0)}
- Price Increased: {summary.get('price_increased_count', 0)}
- Price Decreased: {summary.get('price_decreased_count', 0)}
- Stock Out: {summary.get('stock_out_count', 0)}
- Unchanged: {summary.get('unchanged_count', 0)}

Total Products: {total_products}

PDF Report attached.
"""
    msg.attach(MIMEText(plain_body, 'plain'))
    
    # HTML version - professional and clean
    html_body = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f5f5f5;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f5f5f5; padding: 20px 0;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <!-- Header -->
                    <tr>
                        <td style="background-color: #1e40af; padding: 24px; text-align: center; border-radius: 8px 8px 0 0;">
                            <h1 style="margin: 0; color: #ffffff; font-size: 24px; font-weight: 600;">TOK Prices Tracker</h1>
                            <p style="margin: 8px 0 0 0; color: #bfdbfe; font-size: 14px;">Wholesale Price Comparison Report</p>
                        </td>
                    </tr>
                    
                    <!-- Comparison Info -->
                    <tr>
                        <td style="padding: 20px 24px; border-bottom: 1px solid #e5e7eb;">
                            <p style="margin: 0; color: #374151; font-size: 14px;">
                                <strong>Comparison:</strong> {old_pdf} → {new_pdf}
                            </p>
                        </td>
                    </tr>
                    
                    <!-- Summary Stats -->
                    <tr>
                        <td style="padding: 24px;">
                            <table width="100%" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td style="background-color: #dbeafe; padding: 16px; border-radius: 6px; text-align: center; width: 18%;">
                                        <p style="margin: 0; color: #6b7280; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px;">Newly Added</p>
                                        <p style="margin: 4px 0 0 0; color: #1e40af; font-size: 24px; font-weight: 700;">{summary.get('newly_added_count', 0)}</p>
                                    </td>
                                    <td style="width: 4%;"></td>
                                    <td style="background-color: #ffedd5; padding: 16px; border-radius: 6px; text-align: center; width: 18%;">
                                        <p style="margin: 0; color: #6b7280; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px;">Price Increased</p>
                                        <p style="margin: 4px 0 0 0; color: #c2410c; font-size: 24px; font-weight: 700;">{summary.get('price_increased_count', 0)}</p>
                                    </td>
                                    <td style="width: 4%;"></td>
                                    <td style="background-color: #dcfce7; padding: 16px; border-radius: 6px; text-align: center; width: 18%;">
                                        <p style="margin: 0; color: #6b7280; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px;">Price Decreased</p>
                                        <p style="margin: 4px 0 0 0; color: #166534; font-size: 24px; font-weight: 700;">{summary.get('price_decreased_count', 0)}</p>
                                    </td>
                                    <td style="width: 4%;"></td>
                                    <td style="background-color: #fee2e2; padding: 16px; border-radius: 6px; text-align: center; width: 18%;">
                                        <p style="margin: 0; color: #6b7280; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px;">Stock Out</p>
                                        <p style="margin: 4px 0 0 0; color: #991b1b; font-size: 24px; font-weight: 700;">{summary.get('stock_out_count', 0)}</p>
                                    </td>
                                    <td style="width: 4%;"></td>
                                    <td style="background-color: #f3f4f6; padding: 16px; border-radius: 6px; text-align: center; width: 18%;">
                                        <p style="margin: 0; color: #6b7280; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px;">Unchanged</p>
                                        <p style="margin: 4px 0 0 0; color: #374151; font-size: 24px; font-weight: 700;">{summary.get('unchanged_count', 0)}</p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Total Products -->
                    <tr>
                        <td style="padding: 0 24px 24px; text-align: center;">
                            <p style="margin: 0; color: #6b7280; font-size: 14px;">
                                Total Products: <strong style="color: #111827;">{total_products}</strong>
                            </p>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #f9fafb; padding: 16px; text-align: center; border-radius: 0 0 8px 8px;">
                            <p style="margin: 0; color: #9ca3af; font-size: 12px;">
                                PDF Report attached to this email
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""
    msg.attach(MIMEText(html_body, 'html'))
    
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
    
    # Send email to all recipients
    try:
        server = smtplib.SMTP(smtp_server, int(smtp_port))
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.sendmail(smtp_username, recipients, msg.as_string())
        server.quit()
        print(f'Email sent successfully to: {recipients}')
        return True
    except Exception as e:
        print(f'Failed to send email: {e}')
        return False


if __name__ == '__main__':
    send_email_with_attachment()