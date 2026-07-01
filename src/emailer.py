"""
Email Sender for GK Digest Agent.

Sends the formatted digest via Resend (free tier: 100 emails/day).
Fallback to printing the digest to stdout if email fails.
"""

import os
import resend


def send_digest_email(
    subject: str,
    html_body: str,
    text_body: str,
    to_email: str = None,
    from_email: str = None,
) -> bool:
    """
    Send the digest email via Resend API.

    Args:
        subject: Email subject line.
        html_body: HTML version of the digest.
        text_body: Plain text version (fallback).
        to_email: Recipient email (defaults to EMAIL_TO env var).
        from_email: Sender email (defaults to EMAIL_FROM env var).

    Returns:
        True if sent successfully, False otherwise.
    """
    api_key = os.environ.get('RESEND_API_KEY', '')
    if not api_key:
        print("  ⚠️  RESEND_API_KEY not set. Printing digest to stdout instead.")
        print("\n" + "=" * 60)
        print(f"SUBJECT: {subject}")
        print("=" * 60)
        print(text_body)
        return False

    to_addr = to_email or os.environ.get('EMAIL_TO', '')
    from_addr = from_email or os.environ.get('EMAIL_FROM', 'onboarding@resend.dev')

    if not to_addr:
        print("  ⚠️  EMAIL_TO not set. Cannot send email.")
        print("\n" + "=" * 60)
        print(f"SUBJECT: {subject}")
        print("=" * 60)
        print(text_body)
        return False

    resend.api_key = api_key

    try:
        # Split comma-separated emails
        recipients = [email.strip() for email in to_addr.split(',') if email.strip()]
        
        params = {
            "from": f"GK Digest <{from_addr}>",
            "to": recipients,
            "subject": subject,
            "html": html_body,
            "text": text_body,
        }

        result = resend.Emails.send(params)
        print(f"  ✅ Email sent successfully to {to_addr}")
        print(f"     Message ID: {result.get('id', 'N/A')}")
        return True

    except Exception as e:
        print(f"  ❌ Email failed: {e}")
        print("  📋 Falling back to stdout output:\n")
        print(text_body)
        return False


if __name__ == '__main__':
    """Quick test: send a test email."""
    from dotenv import load_dotenv
    load_dotenv()

    success = send_digest_email(
        subject="🎯 GK Digest – Test Email",
        html_body="<h1>Test</h1><p>This is a test email from GK Digest Agent.</p>",
        text_body="Test: This is a test email from GK Digest Agent.",
    )
    print(f"\nTest result: {'Success' if success else 'Failed'}")
