import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings

def send_email_async_safe(recipient_email: str, subject: str, html_body: str) -> dict:
    if not recipient_email or "@" not in recipient_email:
        return {"sent": False, "reason": "No valid email provided"}
    if not settings.SMTP_APP_PASSWORD:
        print(f"📧 [SIMULATED EMAIL] To: {recipient_email} | Subject: {subject}")
        return {"sent": True, "simulated": True, "recipient": recipient_email}
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"Samagam Transport <{settings.SMTP_SENDER_EMAIL}>"
        msg["To"] = recipient_email
        msg.attach(MIMEText(html_body, "html"))
        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(settings.SMTP_SENDER_EMAIL, settings.SMTP_APP_PASSWORD)
            server.sendmail(settings.SMTP_SENDER_EMAIL, recipient_email, msg.as_string())
        return {"sent": True, "simulated": False, "recipient": recipient_email}
    except Exception as e:
        return {"sent": False, "reason": str(e)}

def build_saint_confirmation_html(saint_data: dict) -> str:
    return f"<h2>Samagam Boarding Pass SMG-{saint_data['id']:05d}</h2><p>Name: {saint_data['full_name']} | Ground: {saint_data['assigned_ground']} ({saint_data['assigned_tent']})</p>"
