import os
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from config import FRONTEND_URL

conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_FROM"),
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
)

async def send_verification_email(email: str, code: str):

    verify_link = f"{FRONTEND_URL}/verify?email={email}&code={code}"

    html_content = f"""
    <html>
        <body>
            <h2>Verify Your Account</h2>

            <p>Your verification code is:</p>

            <h1 style="letter-spacing:4px;">{code}</h1>

            <p>Or click the button below to verify instantly:</p>

            <a href="{verify_link}"
               style="
               display:inline-block;
               padding:12px 20px;
               background-color:#2563eb;
               color:white;
               text-decoration:none;
               border-radius:6px;">
               Verify Account
            </a>

            <p style="margin-top:20px;">
                If the button doesn't work, copy this link:
            </p>

            <p>{verify_link}</p>

        </body>
    </html>
    """

    message = MessageSchema(
        subject="Verify your account",
        recipients=[email],
        body=html_content,
        subtype="html"
    )

    fm = FastMail(conf)
    await fm.send_message(message)