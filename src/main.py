"""
GK Digest Agent -- Main Orchestrator.

Runs the full pipeline: Scrape -> Summarize -> Format -> Email.
Designed to run daily via GitHub Actions or locally.

Usage:
    python src/main.py              # Full run (scrape + summarize + email)
    python src/main.py --dry-run    # Generate digest without sending email
    python src/main.py --scrape-only # Only test RSS scraping
"""

import sys
import os
import io
import argparse
import time

# Fix Windows console encoding for emoji output
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv

from src.scraper import load_feed_config, scrape_all_feeds
from src.summarizer import summarize_and_quiz_single_call
from src.formatter import format_digest, format_digest_html, get_email_subject
from src.emailer import send_digest_email


def run(dry_run: bool = False, scrape_only: bool = False):
    """
    Execute the full GK Digest pipeline.

    Args:
        dry_run: If True, generate digest but don't send email.
        scrape_only: If True, only scrape feeds and print results.
    """
    start_time = time.time()
    print("=" * 60)
    print("📋 GK DIGEST AGENT — Starting pipeline")
    print("=" * 60)

    # --- Step 1: Load configuration ---
    print("\n📁 Step 1: Loading feed configuration...")
    config = load_feed_config()
    topic_config = config.get('topics', {})
    print(f"   Loaded {len(topic_config)} topics")

    # --- Step 2: Scrape RSS feeds ---
    print("\n📡 Step 2: Scraping RSS feeds...")
    topic_articles = scrape_all_feeds(config)

    total_articles = sum(len(v) for v in topic_articles.values())
    print(f"\n   Total: {total_articles} articles across {len(topic_articles)} topics")

    if scrape_only:
        print("\n   Scrape-only mode — stopping here.")
        _print_scrape_summary(topic_articles, topic_config)
        return

    if total_articles == 0:
        print("\n   WARNING: No articles found. This might be a feed issue. Exiting.")
        return

    # --- Step 3 & 4: AI Summarization & Quiz ---
    print("\n🤖 Step 3 & 4: Generating Digest & Quiz with Gemini AI...")
    summaries, quiz = summarize_and_quiz_single_call(topic_articles, topic_config)

    active_topics = sum(1 for v in summaries.values() if v is not None)
    print(f"\n   {active_topics} topics with content, "
          f"{len(summaries) - active_topics} skipped")
    if quiz:
        print("   Quiz generated successfully!")

    # --- Step 5: Format digest ---
    print("\n📝 Step 5: Formatting digest...")
    digest_md = format_digest(summaries, topic_config, quiz)
    digest_html = format_digest_html(digest_md)
    subject = get_email_subject(summaries)

    print(f"   Subject: {subject}")
    print(f"   Digest length: {len(digest_md)} chars")

    # --- Step 6: Send email ---
    if dry_run:
        print("\n   Dry run mode — saving digest to files:\n")

        # Save markdown
        output_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'output_digest.md'
        )
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(digest_md)
        print(f"   Markdown saved to: {output_path}")

        # Save HTML
        html_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'output_digest.html'
        )
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(digest_html)
        print(f"   HTML saved to: {html_path}")

        # Print subject and preview
        print(f"\n{'=' * 60}")
        print(f"SUBJECT: {subject}")
        print(f"{'=' * 60}")
        # Print first 2000 chars of digest as preview
        print(digest_md[:2000])
        if len(digest_md) > 2000:
            print(f"\n... [{len(digest_md) - 2000} more chars, see output_digest.md]")
    else:
        print("\n📧 Step 6: Sending email...")
        send_digest_email(
            subject=subject,
            html_body=digest_html,
            text_body=digest_md,
        )

    # --- Done ---
    elapsed = time.time() - start_time
    print(f"\n{'=' * 60}")
    print(f"Pipeline complete in {elapsed:.1f} seconds")
    print(f"{'=' * 60}")


def _build_prelim_digest(summaries: dict, topic_config: dict) -> str:
    """Build a plain text digest for quiz generation input."""
    parts = []
    for topic_key, bullets in summaries.items():
        if bullets:
            name = topic_config.get(topic_key, {}).get('name', topic_key)
            parts.append(f"{name}:\n{bullets}")
    return '\n\n'.join(parts)


def _fallback_all_topics(topic_articles: dict, topic_config: dict) -> dict:
    """Create basic summaries from raw article titles when Gemini is unavailable."""
    from src.summarizer import _fallback_summarize
    summaries = {}
    for topic_key, articles in topic_articles.items():
        summaries[topic_key] = _fallback_summarize(articles[:4])
    return summaries


def _print_scrape_summary(topic_articles: dict, topic_config: dict):
    """Print a detailed summary of scraped articles."""
    for topic_key, articles in topic_articles.items():
        name = topic_config.get(topic_key, {}).get('name', topic_key)
        print(f"\n{'_' * 50}")
        print(f"  {name} ({len(articles)} articles)")
        for a in articles[:5]:
            pub = a.published.strftime('%H:%M') if a.published else '??:??'
            title_short = a.title[:80]
            print(f"   [{pub}] {title_short} ({a.source})")
        if len(articles) > 5:
            print(f"   ... and {len(articles) - 5} more")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='GK Digest Agent -- Daily Current Affairs for CDS & AFCAT'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Generate digest without sending email (saves to file)'
    )
    parser.add_argument(
        '--scrape-only',
        action='store_true',
        help='Only scrape RSS feeds and show results (no AI, no email)'
    )
    args = parser.parse_args()

    # Load .env file if it exists (for local development)
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
        print("Loaded .env file")

    run(dry_run=args.dry_run, scrape_only=args.scrape_only)


if __name__ == '__main__':
    main()
