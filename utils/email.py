import os
import resend
from dotenv import load_dotenv

load_dotenv()

FROM_EMAIL = os.getenv("EMAIL_FROM", "noreply@verify.vt3.ai")
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://vt3.ai")
API_URL = os.getenv("API_URL", "https://api.vt3.ai")
LOGO_URL = f"{API_URL}/assets/vt3-light.png"


def send_verification_email(email: str, code: str) -> None:
    """Send a 6-digit verification code email via Resend."""
    resend.api_key = os.getenv("RESEND_API_KEY", "")

    verify_url = f"{FRONTEND_URL}/verify?email={email}&code={code}"

    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body style="margin:0;padding:0;background-color:#060606;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#060606;padding:40px 20px;">
    <tr>
      <td align="center">
        <table width="100%" style="max-width:480px;background-color:#0d0d0d;border:1px solid rgba(255,255,255,0.1);border-radius:16px;overflow:hidden;">

          <!-- Red top bar -->
          <tr>
            <td style="background-color:#C8232B;height:3px;"></td>
          </tr>

          <!-- Logo -->
          <tr>
            <td align="center" style="padding:32px 36px 0;">
              <img src="{LOGO_URL}" alt="VT3" width="80" style="display:block;height:auto;" />
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:28px 36px 40px;">
              <h1 style="margin:0 0 8px;font-size:22px;font-weight:700;color:#ffffff;text-align:center;">Verify your email</h1>
              <p style="margin:0 0 28px;font-size:14px;color:#94a3b8;line-height:1.6;text-align:center;">
                Enter the code below to confirm your email address and activate your account.
                This code expires in <strong style="color:#e2e8f0;">10 minutes</strong>.
              </p>

              <!-- Code box -->
              <div style="background-color:#111111;border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:24px;text-align:center;margin-bottom:24px;">
                <p style="margin:0 0 10px;font-size:11px;font-weight:600;letter-spacing:2px;text-transform:uppercase;color:#64748b;">Your verification code</p>
                <p style="margin:0;font-size:40px;font-weight:700;letter-spacing:12px;color:#ffffff;font-variant-numeric:tabular-nums;">{code}</p>
              </div>

              <!-- Verify button -->
              <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:16px;">
                <tr>
                  <td align="center">
                    <a href="{verify_url}"
                       style="display:inline-block;padding:14px 32px;background-color:#C8232B;color:#ffffff;text-decoration:none;border-radius:8px;font-size:14px;font-weight:600;letter-spacing:0.2px;">
                      Verify Email
                    </a>
                  </td>
                </tr>
              </table>

              <!-- Verify link -->
              <p style="margin:0 0 28px;font-size:12px;color:#475569;text-align:center;line-height:1.6;">
                Or copy this link:<br>
                <a href="{verify_url}" style="color:#3A8FE8;word-break:break-all;">{verify_url}</a>
              </p>

              <p style="margin:0;font-size:13px;color:#475569;line-height:1.6;text-align:center;">
                If you didn't create a VT3 account, you can safely ignore this email.
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding:20px 36px;border-top:1px solid rgba(255,255,255,0.06);">
              <p style="margin:0;font-size:12px;color:#334155;text-align:center;">
                &copy; 2026 VT3 &mdash; All rights reserved
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    resend.Emails.send({
        "from": FROM_EMAIL,
        "to": [email],
        "subject": f"{code} is your VT3 verification code",
        "html": html_content,
    })


def send_password_reset_email(email: str, reset_url: str) -> None:
    """Send a password reset link email via Resend."""
    resend.api_key = os.getenv("RESEND_API_KEY", "")

    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body style="margin:0;padding:0;background-color:#060606;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#060606;padding:40px 20px;">
    <tr>
      <td align="center">
        <table width="100%" style="max-width:480px;background-color:#0d0d0d;border:1px solid rgba(255,255,255,0.1);border-radius:16px;overflow:hidden;">

          <!-- Red top bar -->
          <tr>
            <td style="background-color:#C8232B;height:3px;"></td>
          </tr>

          <!-- Logo -->
          <tr>
            <td align="center" style="padding:32px 36px 0;">
              <img src="{LOGO_URL}" alt="VT3" width="80" style="display:block;height:auto;" />
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:28px 36px 40px;">
              <h1 style="margin:0 0 8px;font-size:22px;font-weight:700;color:#ffffff;text-align:center;">Reset your password</h1>
              <p style="margin:0 0 28px;font-size:14px;color:#94a3b8;line-height:1.6;text-align:center;">
                We received a request to reset your VT3 password. Click the button below to choose a new one.
                This link expires in <strong style="color:#e2e8f0;">1 hour</strong>.
              </p>

              <!-- Reset button -->
              <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;">
                <tr>
                  <td align="center">
                    <a href="{reset_url}"
                       style="display:inline-block;padding:14px 32px;background-color:#C8232B;color:#ffffff;text-decoration:none;border-radius:8px;font-size:14px;font-weight:600;letter-spacing:0.2px;">
                      Reset Password
                    </a>
                  </td>
                </tr>
              </table>

              <!-- Fallback link -->
              <p style="margin:0 0 28px;font-size:12px;color:#475569;text-align:center;line-height:1.6;">
                Or copy this link:<br>
                <a href="{reset_url}" style="color:#3A8FE8;word-break:break-all;">{reset_url}</a>
              </p>

              <p style="margin:0;font-size:13px;color:#475569;line-height:1.6;text-align:center;">
                If you didn't request a password reset, you can safely ignore this email. Your password won't change.
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding:20px 36px;border-top:1px solid rgba(255,255,255,0.06);">
              <p style="margin:0;font-size:12px;color:#334155;text-align:center;">
                &copy; 2026 VT3 &mdash; All rights reserved
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    resend.Emails.send({
        "from": FROM_EMAIL,
        "to": [email],
        "subject": "Reset your VT3 password",
        "html": html_content,
    })
