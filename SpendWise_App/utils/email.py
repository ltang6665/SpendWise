import hashlib
import hmac
import smtplib
import secrets
import string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, timezone
from ..config import settings


def generate_verification_code(length: int = 6) -> str:
    """Generate a random 6-digit verification code"""
    return ''.join(secrets.choice(string.digits) for _ in range(length))

def generate_reset_code(length: int = 6) -> str:
    """Generate a random 6-character alphanumeric reset token"""
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def hash_one_time_code(code: str, purpose: str) -> str:
    """Return a keyed digest so short-lived codes are not recoverable from a DB dump."""
    message = f"{purpose}:{code}".encode("utf-8")
    digest = hmac.new(settings.SECRET_KEY.encode("utf-8"), message, hashlib.sha256).hexdigest()
    return f"hmac-sha256-v1:{digest}"

def verify_one_time_code(code: str, stored_digest: str | None, purpose: str) -> bool:
    if not stored_digest:
        return False
    return hmac.compare_digest(hash_one_time_code(code, purpose), stored_digest)

def send_email(to_email: str, subject: str, html_content: str) -> bool:
    """Internal function to send email via SMTP"""
    try:
        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.SENDER_NAME} <{settings.SENDER_EMAIL}>"
        msg["To"] = to_email
        
        # Attach HTML content
        msg.attach(MIMEText(html_content, "html"))
        
        # Connect to SMTP server and send
        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SENDER_EMAIL, settings.SENDER_PASSWORD)
            server.send_message(msg)
        
        print(f"Email sent successfully to {to_email}")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

def get_verification_code_expiry() -> datetime:
    """Get expiry time for verification code (10 minutes from now)"""
    return datetime.now(timezone.utc) + timedelta(minutes=10)

def get_reset_token_expiry() -> datetime:
    """Get expiry time for reset token (1 hour from now)"""
    return datetime.now(timezone.utc) + timedelta(hours=1)

def send_verification_email(email: str, verification_code: str) -> bool:
    try:
        subject = "Verify Your SpendWise Email"
        html_content = f"""
        <html>
            <body style="font-family: 'Inter', Arial, sans-serif; background-color: #F4F5F8; padding: 40px 20px; margin: 0;">
                <div style="max-width: 500px; margin: 0 auto; background-color: #FFFFFF; padding: 40px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #E6E9F0;">
                    <h2 style="color: #5C55D9; margin-top: 0; margin-bottom: 24px; font-size: 24px;">Welcome to SpendWise!</h2>
                    <p style="color: #1F2430; font-size: 16px; line-height: 1.5; margin-bottom: 24px;">
                        Thank you for registering. Please verify your email address to get started.
                    </p>
                    <div style="background-color: #E6E9F0; padding: 24px; border-radius: 12px; text-align: center; margin-bottom: 24px;">
                        <p style="color: #1F2430; margin-top: 0; margin-bottom: 8px; font-size: 14px; font-weight: 500;">Your verification code is:</p>
                        <p style="color: #5C55D9; font-size: 36px; font-weight: bold; letter-spacing: 6px; margin: 0;">
                            {verification_code}
                        </p>
                    </div>
                    <p style="color: #1F2430; font-size: 14px; margin-bottom: 12px;">
                        This code will expire in <strong>10 minutes</strong>.
                    </p>
                    <p style="color: #8A94A6; font-size: 12px; margin: 0;">
                        If you didn't register for SpendWise, please ignore this email.
                    </p>
                </div>
            </body>
        </html>
        """
        return send_email(email, subject, html_content)
    except Exception as e:
        print(f"Error sending verification email: {e}")
        return False


def send_password_reset_email(email: str, reset_code: str) -> bool:
    try:
        subject = "Reset Your SpendWise Password"
        html_content = f"""
        <html>
            <body style="font-family: 'Inter', Arial, sans-serif; background-color: #F4F5F8; padding: 40px 20px; margin: 0;">
                <div style="max-width: 500px; margin: 0 auto; background-color: #FFFFFF; padding: 40px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #E6E9F0;">
                    <h2 style="color: #5C55D9; margin-top: 0; margin-bottom: 24px; font-size: 24px;">Password Reset Request</h2>
                    <p style="color: #1F2430; font-size: 16px; line-height: 1.5; margin-bottom: 24px;">
                        We received a request to reset your password. Use the code below to reset it.
                    </p>
                    <div style="background-color: #E6E9F0; padding: 24px; border-radius: 12px; text-align: center; margin-bottom: 24px;">
                        <p style="color: #1F2430; margin-top: 0; margin-bottom: 8px; font-size: 14px; font-weight: 500;">Your reset code is:</p>
                        <p style="color: #5C55D9; font-size: 32px; font-weight: bold; letter-spacing: 6px; margin: 0; font-family: monospace;">
                            {reset_code}
                        </p>
                    </div>
                    <p style="color: #1F2430; font-size: 14px; margin-bottom: 12px;">
                        This code will expire in <strong>1 hour</strong>.
                    </p>
                    <p style="color: #8A94A6; font-size: 12px; margin: 0;">
                        If you didn't request a password reset, please ignore this email and your password will remain unchanged.
                    </p>
                </div>
            </body>
        </html>
        """
        return send_email(email, subject, html_content)
    except Exception as e:
        print(f"Error sending password reset email: {e}")
        return False


def send_email_change_verification(email: str, verification_code: str) -> bool:
    try:
        subject = "Confirm Your New SpendWise Email"
        html_content = f"""
        <html>
            <body style="font-family: 'Inter', Arial, sans-serif; background-color: #F4F5F8; padding: 40px 20px; margin: 0;">
                <div style="max-width: 500px; margin: 0 auto; background-color: #FFFFFF; padding: 40px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #E6E9F0;">
                    <h2 style="color: #5C55D9; margin-top: 0; margin-bottom: 24px; font-size: 24px;">Email Change Request</h2>
                    <p style="color: #1F2430; font-size: 16px; line-height: 1.5; margin-bottom: 24px;">
                        You requested to change your SpendWise account email to this address.
                    </p>
                    <div style="background-color: #E6E9F0; padding: 24px; border-radius: 12px; text-align: center; margin-bottom: 24px;">
                        <p style="color: #1F2430; margin-top: 0; margin-bottom: 8px; font-size: 14px; font-weight: 500;">Your confirmation code is:</p>
                        <p style="color: #5C55D9; font-size: 36px; font-weight: bold; letter-spacing: 6px; margin: 0;">
                            {verification_code}
                        </p>
                    </div>
                    <p style="color: #1F2430; font-size: 14px; margin-bottom: 12px;">
                        This code will expire in <strong>10 minutes</strong>.
                    </p>
                    <p style="color: #8A94A6; font-size: 12px; margin: 0;">
                        If you did not request this change, please secure your account immediately.
                    </p>
                </div>
            </body>
        </html>
        """
        return send_email(email, subject, html_content)
    except Exception as e:
        print(f"Error sending email change verification: {e}")
        return False

def send_password_changed_notification(email: str, lock_token: str) -> bool:
    try:
        subject = "Your SpendWise Password Was Changed"
        # The link points directly to your backend FastAPI server
        lock_url = f"{settings.BACKEND_URL}/users/lock-account/{lock_token}"
        
        html_content = f"""
        <html>
            <body style="font-family: 'Inter', Arial, sans-serif; background-color: #F4F5F8; padding: 40px 20px; margin: 0;">
                <div style="max-width: 500px; margin: 0 auto; background-color: #FFFFFF; padding: 40px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #E6E9F0;">
                    <h2 style="color: #5C55D9; margin-top: 0; margin-bottom: 24px; font-size: 24px;">Password Changed Successfully</h2>
                    <p style="color: #1F2430; font-size: 16px; line-height: 1.5; margin-bottom: 24px;">
                        This is a quick security notification to confirm that the password for your SpendWise account was just changed.
                    </p>
                    <p style="color: #1F2430; font-size: 14px; margin-bottom: 24px;">
                        If you made this change in your settings, you don't need to do anything else!
                    </p>
                    
                    <div style="background-color: #FCE8E8; padding: 20px; border-radius: 12px; border-left: 4px solid #D93D42;">
                        <p style="color: #D93D42; font-size: 14px; margin-top: 0; margin-bottom: 12px;">
                            <strong>Didn't make this change?</strong>
                        </p>
                        <p style="color: #D93D42; font-size: 14px; margin-bottom: 20px;">
                            If you did not authorize this, please secure your account immediately by clicking the button below. This will instantly freeze your account.
                        </p>
                        <a href="{lock_url}" style="display: inline-block; background-color: #D93D42; color: #FFFFFF; text-decoration: none; padding: 12px 24px; border-radius: 6px; font-weight: bold; font-size: 14px;">
                            Lock My Account Instantly
                        </a>
                    </div>
                </div>
            </body>
        </html>
        """
        return send_email(email, subject, html_content)
    except Exception as e:
        print(f"Error sending password change notification: {e}")
        return False
