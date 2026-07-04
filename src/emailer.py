"""
Email Sender for GK Digest Agent.

Sends the formatted digest via Brevo API (free tier: 300 emails/day).
Fallback to printing the digest to stdout if email fails.
"""

import os
import requests


def send_digest_email(
    subject: str,
    html_body: str,
    text_body: str,
    to_email: str = None,
    from_email: str = None,
) -> bool:
    """
    Send the digest email via Brevo API.

    Args:
        subject: Email subject line.
        html_body: HTML version of the digest.
        text_body: Plain text version (fallback).
        to_email: Recipient email (defaults to EMAIL_TO env var).
        from_email: Sender email (defaults to EMAIL_FROM env var).

    Returns:
        True if sent successfully, False otherwise.
    """
    api_key = os.environ.get('BREVO_API_KEY', '')
    if not api_key:
        print("  ⚠️  BREVO_API_KEY not set. Printing digest to stdout instead.")
        print("\n" + "=" * 60)
        print(f"SUBJECT: {subject}")
        print("=" * 60)
        print(text_body)
        return False

    to_addr = to_email or os.environ.get('EMAIL_TO', '')
    from_addr = from_email or os.environ.get('EMAIL_FROM', '')

    if not to_addr or not from_addr:
        print("  ⚠️  EMAIL_TO or EMAIL_FROM not set. Cannot send email.")
        print("\n" + "=" * 60)
        print(f"SUBJECT: {subject}")
        print("=" * 60)
        print(text_body)
        return False

    # Split comma-separated emails for multiple recipients
    recipients = [{"email": email.strip()} for email in to_addr.split(',') if email.strip()]

    headers = {
        "api-key": api_key,
        "content-type": "application/json",
        "accept": "application/json"
    }

    payload = {
        "sender": {"name": "GK Digest", "email": from_addr},
        "to": recipients,
        "subject": subject,
        "htmlContent": html_body,
        "textContent": text_body
    }

    try:
        response = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            json=payload,
            headers=headers,
            timeout=10
        )
        if response.status_code in [200, 201, 202]:
            print(f"  ✅ Email sent successfully to {to_addr}")
            return True
        else:
            print(f"  ❌ Email failed (HTTP {response.status_code}): {response.text}")
            print("  📋 Falling back to stdout output:")
            print("\n" + "=" * 60)
            print(f"SUBJECT: {subject}")
            print("=" * 60)
            print(text_body)
            return False
    except Exception as e:
        print(f"  ❌ Error calling Brevo API: {e}")
        print("  📋 Falling back to stdout output:")
        print("\n" + "=" * 60)
        print(f"SUBJECT: {subject}")
        print("=" * 60)
        print(text_body)
        return False
