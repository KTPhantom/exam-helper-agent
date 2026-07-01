"""
RSS Feed Scraper for GK Digest Agent.

Fetches articles from configured RSS feeds, filters by recency (last 24 hours),
and groups them by exam topic using keyword matching.
"""

import feedparser
import yaml
import os
import re
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from typing import Optional
import time
import struct
import calendar


@dataclass
class Article:
    """Represents a single news article from an RSS feed."""
    title: str
    summary: str
    link: str
    source: str
    published: Optional[datetime] = None
    topic_key: Optional[str] = None


def _parse_published_date(entry: dict) -> Optional[datetime]:
    """Extract and parse the publication date from an RSS entry."""
    date_fields = ['published_parsed', 'updated_parsed']
    for field_name in date_fields:
        parsed = entry.get(field_name)
        if parsed:
            try:
                timestamp = calendar.timegm(parsed)
                return datetime.fromtimestamp(timestamp, tz=timezone.utc)
            except (ValueError, OverflowError, OSError):
                continue
    # Fallback: try parsing date strings directly
    for field_name in ['published', 'updated']:
        date_str = entry.get(field_name, '')
        if date_str:
            for fmt in [
                '%a, %d %b %Y %H:%M:%S %z',
                '%Y-%m-%dT%H:%M:%S%z',
                '%a, %d %b %Y %H:%M:%S GMT',
            ]:
                try:
                    return datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
    return None


def _clean_html(text: str) -> str:
    """Strip HTML tags from text."""
    clean = re.sub(r'<[^>]+>', '', text)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean


def load_feed_config(config_path: str = None) -> dict:
    """Load the RSS feed configuration from YAML."""
    if config_path is None:
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'config', 'feeds.yaml'
        )
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def fetch_feed(url: str, source: str, max_retries: int = 2) -> list[Article]:
    """Fetch and parse a single RSS feed URL."""
    articles = []
    for attempt in range(max_retries + 1):
        try:
            feed = feedparser.parse(url)
            if feed.bozo and not feed.entries:
                if attempt < max_retries:
                    time.sleep(2 ** attempt)
                    continue
                print(f"  ⚠️  Feed error for {source} ({url}): {feed.bozo_exception}")
                return []
            break
        except Exception as e:
            if attempt < max_retries:
                time.sleep(2 ** attempt)
                continue
            print(f"  ❌ Failed to fetch {source}: {e}")
            return []

    for entry in feed.entries:
        title = _clean_html(entry.get('title', ''))
        summary = _clean_html(
            entry.get('summary', entry.get('description', ''))
        )
        link = entry.get('link', '')
        published = _parse_published_date(entry)

        if title:
            articles.append(Article(
                title=title,
                summary=summary[:500],  # Truncate long summaries
                link=link,
                source=source,
                published=published,
            ))

    return articles


def _matches_topic(article: Article, keywords: list[str]) -> bool:
    """Check if an article matches a topic's keywords."""
    if not keywords:
        return False
    text = f"{article.title} {article.summary}".lower()
    return any(kw.lower() in text for kw in keywords)


def scrape_all_feeds(config: dict, hours_lookback: int = 36) -> dict[str, list[Article]]:
    """
    Scrape all configured RSS feeds and group articles by topic.

    Args:
        config: The parsed feeds.yaml configuration.
        hours_lookback: How many hours back to include articles (default: 36
                        to account for timezone differences and late publishing).

    Returns:
        Dict mapping topic_key -> list of relevant Articles.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_lookback)
    topics = config.get('topics', {})

    # Step 1: Fetch all unique feeds (avoid fetching the same URL twice)
    url_to_source: dict[str, str] = {}
    for topic_key, topic_data in topics.items():
        for feed_info in topic_data.get('feeds', []):
            url = feed_info['url']
            if url not in url_to_source:
                url_to_source[url] = feed_info['source']

    print(f"📡 Fetching {len(url_to_source)} RSS feeds...")
    all_articles: list[Article] = []
    for url, source in url_to_source.items():
        print(f"  → {source}...", end=" ")
        fetched = fetch_feed(url, source)
        # Filter by recency
        recent = []
        for a in fetched:
            if a.published is None or a.published >= cutoff:
                recent.append(a)
        print(f"{len(recent)} recent articles")
        all_articles.extend(recent)

    # Step 2: Deduplicate by title similarity
    seen_titles = set()
    unique_articles = []
    for article in all_articles:
        # Normalize title for dedup
        normalized = re.sub(r'[^a-z0-9\s]', '', article.title.lower())
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        if normalized not in seen_titles:
            seen_titles.add(normalized)
            unique_articles.append(article)

    print(f"📰 {len(unique_articles)} unique articles after dedup")

    # Step 3: Classify articles into topics by keyword matching
    topic_articles: dict[str, list[Article]] = {}
    assigned = set()

    # Sort topics by order for priority-based assignment
    sorted_topics = sorted(
        topics.items(),
        key=lambda x: x[1].get('order', 99)
    )

    for topic_key, topic_data in sorted_topics:
        keywords = topic_data.get('keywords', [])
        topic_articles[topic_key] = []

        for i, article in enumerate(unique_articles):
            if i in assigned:
                continue
            if _matches_topic(article, keywords):
                article.topic_key = topic_key
                topic_articles[topic_key].append(article)
                assigned.add(i)

    # Step 4: Unassigned articles go to current_affairs (catch-all)
    if 'current_affairs' in topic_articles:
        for i, article in enumerate(unique_articles):
            if i not in assigned:
                article.topic_key = 'current_affairs'
                topic_articles['current_affairs'].append(article)

    # Print summary
    for topic_key, articles in topic_articles.items():
        topic_name = topics[topic_key]['name']
        print(f"  📂 {topic_name}: {len(articles)} articles")

    return topic_articles


if __name__ == '__main__':
    """Quick test: run the scraper standalone."""
    config = load_feed_config()
    results = scrape_all_feeds(config)
    print("\n--- Scraping Complete ---")
    for topic_key, articles in results.items():
        print(f"\n{'='*50}")
        print(f"Topic: {topic_key} ({len(articles)} articles)")
        for a in articles[:3]:
            print(f"  • {a.title} ({a.source})")
