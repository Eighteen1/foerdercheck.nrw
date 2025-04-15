import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

load_dotenv()

class EmailService:
    def __init__(self):
        self.smtp_server = os.getenv('SMTP_SERVER')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_username = os.getenv('SMTP_USERNAME')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.from_email = os.getenv('FROM_EMAIL')
        self.frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')

    def send_email(self, to_email: str, subject: str, body: str) -> bool:
        try:
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = to_email
            msg['Subject'] = subject

            msg.attach(MIMEText(body, 'html'))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)

            return True
        except Exception as e:
            print(f"Error sending email: {e}")
            return False

    def send_verification_email(self, email: str, token: str) -> bool:
        verification_url = f"{self.frontend_url}/verify/{token}"
        subject = "Bestätigen Sie Ihre E-Mail-Adresse"
        body = f"""
        <html>
            <body>
                <h2>Willkommen bei Fördercheck.NRW</h2>
                <p>Bitte bestätigen Sie Ihre E-Mail-Adresse, indem Sie auf den folgenden Link klicken:</p>
                <p><a href="{verification_url}">E-Mail-Adresse bestätigen</a></p>
                <p>Dieser Link ist 30 Minuten gültig.</p>
                <p>Falls Sie diese E-Mail nicht erwartet haben, können Sie sie ignorieren.</p>
            </body>
        </html>
        """
        return self.send_email(email, subject, body)

    def send_login_link(self, email: str, token: str) -> bool:
        login_url = f"{self.frontend_url}/login?token={token}"
        subject = "Ihr Login-Link für Fördercheck.NRW"
        body = f"""
        <html>
            <body>
                <h2>Login für Fördercheck.NRW</h2>
                <p>Klicken Sie auf den folgenden Link, um sich anzumelden:</p>
                <p><a href="{login_url}">Jetzt anmelden</a></p>
                <p>Dieser Link ist 30 Minuten gültig.</p>
                <p>Falls Sie diese E-Mail nicht erwartet haben, können Sie sie ignorieren.</p>
            </body>
        </html>
        """
        return self.send_email(email, subject, body) 