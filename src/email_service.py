import smtplib
import smtplib
import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
from email.message import EmailMessage
from datetime import datetime

def send_api_key_email(recipient_email: str, api_key: str, valid_till_iso: str, brand_name: str):
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = os.getenv("SMTP_PORT", 587)
    smtp_user = os.getenv("SMTP_USERNAME")
    smtp_pass = os.getenv("SMTP_PASSWORD")

    # Format the date nicely
    try:
        expires_dt = datetime.fromisoformat(valid_till_iso)
        valid_till = expires_dt.strftime("%B %d, %Y")
    except Exception:
        valid_till = valid_till_iso

    url = f"https://mcpforgbl.duckdns.org/sse?token={api_key}"

    subject = f"Welcome to GBL - MCP: You now have access to {brand_name} Data! 🚀"
    body = f"""Hello! 👋

Great news—you are officially plugged in! You now have secure access to the {brand_name} data through the GBL - MCP Server. 

Your secure connection URL is ready:
{url}

Your access is valid until {valid_till}. 

Dive in and start exploring! If you need any help along the way, just give a shout to GBL - Tech.

Cheers,
The GBL Tech Team 🚀
"""

    if not smtp_server or not smtp_user or not smtp_pass:
        print("\n" + "="*40)
        print("MOCK EMAIL (No SMTP credentials configured)")
        print("="*40)
        print(f"To: {recipient_email}")
        print(f"Subject: {subject}")
        print(f"Body:\n{body}")
        print("="*40 + "\n")
        return

    msg = EmailMessage()
    msg.set_content(body)
    msg['Subject'] = subject
    msg['From'] = smtp_user
    msg['To'] = recipient_email

    try:
        with smtplib.SMTP(smtp_server, int(smtp_port)) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
            print(f"Email successfully sent to {recipient_email}")
    except Exception as e:
        print(f"Failed to send email to {recipient_email}: {e}")
