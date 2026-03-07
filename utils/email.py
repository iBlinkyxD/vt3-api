import os
from dotenv import load_dotenv

from fastapi_mail import FastMail, MessageSchema, ConnectionConfig

conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_FROM"),
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False
)

async def send_verification_email(email: str, code: str):

    message = MessageSchema(
        subject="Verify your account",
        recipients=[email],
        body=f"Your verification code is: {code}",
        subtype="plain"
    )

    fm = FastMail(conf)
    await fm.send_message(message)