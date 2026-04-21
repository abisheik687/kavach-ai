
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

<<<<<<< HEAD
# KAVACH-AI Day 12: Email Alerts
=======
# Multimodal Deepfake Detection System Using Advanced Machine Learning Techniques Day 12: Email Alerts
>>>>>>> 7df14d1 (UI enhanced)
# Notifies admins of high-priority detection events

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
<<<<<<< HEAD
SMTP_USER = os.getenv("SMTP_USER", "alert@kavach.ai")
=======
SMTP_USER = os.getenv("SMTP_USER", "alert@multimodal-deepfake-detection.ai")
>>>>>>> 7df14d1 (UI enhanced)
SMTP_PASS = os.getenv("SMTP_PASS", "mock_password")

class EmailAlerter:
    def __init__(self):
        self.enabled = os.getenv("ENABLE_EMAIL_ALERTS", "False").lower() == "true"

    def send_alert(self, recipient: str, subject: str, body: str, attachment_path: str = None):
        if not self.enabled:
            print(f"[MOCK EMAIL] To: {recipient} | Subject: {subject}")
            print(f"[MOCK BODY] {body}")
            return

        try:
            msg = MIMEMultipart()
            msg['From'] = SMTP_USER
            msg['To'] = recipient
<<<<<<< HEAD
            msg['Subject'] = f"[KAVACH-AI] {subject}"
=======
            msg['Subject'] = f"[Multimodal Deepfake Detection System Using Advanced Machine Learning Techniques] {subject}"
>>>>>>> 7df14d1 (UI enhanced)
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Attach PDF if provided
            if attachment_path and os.path.exists(attachment_path):
                from email.mime.application import MIMEApplication
                with open(attachment_path, "rb") as f:
                    attach = MIMEApplication(f.read(), _subtype="pdf")
                    attach.add_header('Content-Disposition', 'attachment', filename=os.path.basename(attachment_path))
                    msg.attach(attach)

            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            text = msg.as_string()
            server.sendmail(SMTP_USER, recipient, text)
            server.quit()
            print(f"Email sent to {recipient}")
            
        except Exception as e:
            print(f"Failed to send email: {e}")

# Global instance
alerter = EmailAlerter()
