"""
Digest Formatter for GK Digest Agent.

Formats AI-summarized bullets into the industry-proven digest structure
inspired by Morning Brew, TLDR, and 1440 Daily — optimized for CDS/AFCAT.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional


# Indian Standard Time offset
IST = timezone(timedelta(hours=5, minutes=30))

# Section order (Defence first — CDS is a defence exam)
SECTION_ORDER = [
    'defence',
    'polity',
    'economics',
    'science_tech',
    'geography',
    'environment',
    'history',
    'art_culture',
    'organisations',
    'awards',
    'sports',
    'current_affairs',
]


def _get_date_header() -> str:
    """Generate the date string in IST."""
    now = datetime.now(IST)
    day_name = now.strftime('%A')
    month_year = now.strftime('%B %Y')
    return f'{now.day} {month_year} ({day_name})'


def _get_date_header_short() -> str:
    """Short date for subject line."""
    now = datetime.now(IST)
    return f'{now.day} {now.strftime("%b %Y")}'


def _get_date_for_subject() -> str:
    """Date formatted for email subject line."""
    now = datetime.now(IST)
    return f'{now.day} {now.strftime("%b %Y")}'


def _extract_top3(summaries: dict, topic_config: dict) -> Optional[str]:
    """
    Extract the top 3 most important bullets across all topics for the hook.

    Priority: Defence > Polity > Economics > Science (matching CDS exam weight).
    Takes the first bullet from the highest-priority topics.
    """
    priority_order = ['defence', 'polity', 'economics', 'science_tech',
                      'current_affairs', 'sports', 'environment']
    top_bullets = []

    for topic_key in priority_order:
        if topic_key in summaries and summaries[topic_key]:
            lines = [l.strip() for l in summaries[topic_key].split('\n') if l.strip().startswith('- ')]
            if lines:
                # Take the first bullet and convert to numbered format
                bullet_text = lines[0][2:]  # Remove "- " prefix
                top_bullets.append(bullet_text)
                if len(top_bullets) >= 3:
                    break

    if not top_bullets:
        return None

    # Format as numbered list
    numbered = []
    for i, bullet in enumerate(top_bullets, 1):
        numbered.append(f"{i}. {bullet}")

    return '\n\n'.join(numbered)


def _extract_hook_for_subject(summaries: dict) -> str:
    """Extract a short hook phrase for the email subject line."""
    # Take from the first available topic (Defence first)
    for topic_key in ['defence', 'polity', 'economics', 'science_tech', 'current_affairs']:
        if topic_key in summaries and summaries[topic_key]:
            lines = [l.strip() for l in summaries[topic_key].split('\n') if l.strip().startswith('- ')]
            if lines:
                first_bullet = lines[0][2:]  # Remove "- "
                # Extract the bold term: **term** — ...
                if '**' in first_bullet:
                    start = first_bullet.index('**') + 2
                    end = first_bullet.index('**', start)
                    return first_bullet[start:end]
                # Fallback: first 5 words
                return ' '.join(first_bullet.split()[:5])
    return "Today's Updates"


def format_digest(
    summaries: dict[str, Optional[str]],
    topic_config: dict,
    quiz: Optional[str] = None,
) -> str:
    """
    Format the full digest in Markdown (works for email, Telegram, and newsletter).

    Args:
        summaries: Dict of topic_key -> bullet string (None = skipped).
        topic_config: The 'topics' section from feeds.yaml.
        quiz: Optional Quick Recall quiz string.

    Returns:
        Complete formatted digest as a Markdown string.
    """
    now = datetime.now(IST)
    date_full = now.strftime('%d %B %Y (%A)')
    sections = []

    # === HEADER ===
    header = f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 GK DIGEST — {date_full}
CDS & AFCAT Daily Current Affairs
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📖 12 topics • ⏱️ ~5 min read
"""
    sections.append(header)

    # === TOP 3 TODAY ===
    top3 = _extract_top3(summaries, topic_config)
    if top3:
        sections.append(f"\n🔥 TOP 3 TODAY\n\n{top3}\n")

    # === TOPIC SECTIONS ===
    section_num = 1
    for topic_key in SECTION_ORDER:
        if topic_key not in summaries or summaries[topic_key] is None:
            continue

        topic_data = topic_config.get(topic_key, {})
        emoji = topic_data.get('emoji', '📌')
        name = topic_data.get('name', topic_key)

        section_header = f"\n{emoji} {section_num}. {name.upper()}\n"
        sections.append(section_header)
        sections.append(summaries[topic_key])
        sections.append("")  # blank line

        section_num += 1

    # === QUICK RECALL QUIZ ===
    if quiz:
        quiz_section = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🧠 QUICK RECALL — Test Yourself

{_format_quiz(quiz)}
"""
        sections.append(quiz_section)

    # === FOOTER ===
    footer = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📎 Sources: PIB, The Hindu, Indian Express, Livemint,
   Down to Earth, LiveLaw, ISRO

💬 Feedback? Reply to this email — I read every reply.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GK Digest • Daily Current Affairs for CDS & AFCAT
Auto-generated on {now.strftime('%d %b %Y at %I:%M %p IST')}
"""
    sections.append(footer)

    return '\n'.join(sections)


def _format_quiz(quiz_raw: str) -> str:
    """Format the quiz into a clean numbered list."""
    lines = quiz_raw.strip().split('\n')
    formatted = []
    q_num = 0

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith('Q:') or line.startswith('Q '):
            q_num += 1
            question = line.split(':', 1)[-1].strip() if ':' in line else line[2:].strip()
            formatted.append(f"{q_num}. {question}")
        elif line.startswith('A:') or line.startswith('A '):
            answer = line.split(':', 1)[-1].strip() if ':' in line else line[2:].strip()
            formatted.append(f"   → {answer}")
            formatted.append("")  # blank line between Q&As

    return '\n'.join(formatted) if formatted else quiz_raw


def get_email_subject(summaries: dict) -> str:
    """Generate the email subject line with a hook."""
    now = datetime.now(IST)
    date_str = f'{now.day} {now.strftime("%b %Y")}'
    hook = _extract_hook_for_subject(summaries)
    return f"🎯 GK Digest – {date_str} | {hook}"


def format_digest_html(markdown_digest: str) -> str:
    """
    Convert the Markdown digest to a highly aesthetic HTML email card layout.
    Uses inline CSS with card design patterns for maximum email client compatibility.
    """
    import re
    
    html_lines = []
    in_section = False
    in_top3 = False
    in_quiz = False
    
    for line in markdown_digest.split('\n'):
        # Bold: **text** -> <strong>text</strong>
        line = re.sub(r'\*\*(.+?)\*\*', r'<strong style="color: #1F2937;">\1</strong>', line)
        
        # Markdown Link: [text](url) -> <a href="url" style="color: #4F46E5; text-decoration: none; font-weight: 600;">text</a>
        line = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2" style="color: #4f46e5; text-decoration: none; font-weight: 600;">\1</a>', line)
        
        # Section dividers
        if '━' in line:
            if in_section:
                html_lines.append('</div><!-- end card -->')
                in_section = False
            if in_top3:
                html_lines.append('</div><!-- end top3 card -->')
                in_top3 = False
            if in_quiz:
                html_lines.append('</div><!-- end quiz card -->')
                in_quiz = False
            continue

        # Header Block
        if '📋 GK DIGEST' in line:
            date_match = re.search(r'—\s*(.+)', line)
            date_val = date_match.group(1) if date_match else "Daily Update"
            header_html = f"""
            <div style="text-align: center; padding: 24px 0 16px 0; background: linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%); border-radius: 16px 16px 0 0; margin-bottom: 24px; color: #ffffff;">
                <span style="background: rgba(255, 255, 255, 0.2); padding: 4px 12px; border-radius: 20px; font-size: 11px; text-transform: uppercase; font-weight: bold; letter-spacing: 1px; font-family: 'Inter', -apple-system, sans-serif;">CDS & AFCAT Prep</span>
                <h1 style="margin: 12px 0 6px 0; font-size: 24px; font-family: 'Outfit', -apple-system, sans-serif; font-weight: 800; letter-spacing: -0.5px;">GK DAILY DIGEST</h1>
                <p style="margin: 0; font-size: 14px; opacity: 0.9; font-family: 'Inter', -apple-system, sans-serif;">{date_val}</p>
            </div>
            """
            html_lines.append(header_html)
            continue
            
        if '📖 12 topics' in line:
            # Metadata stats
            stats_html = f"""
            <div style="display: flex; justify-content: center; gap: 16px; margin: -12px 0 24px 0; padding: 0 12px; font-family: 'Inter', -apple-system, sans-serif; font-size: 12px; color: #6B7280; text-align: center;">
                <span style="background: #F3F4F6; padding: 6px 12px; border-radius: 8px; flex: 1;">⏱️ <strong>5 Min</strong> Read</span>
                <span style="background: #F3F4F6; padding: 6px 12px; border-radius: 8px; flex: 1;">📚 <strong>12 Topics</strong> Covered</span>
                <span style="background: #F3F4F6; padding: 6px 12px; border-radius: 8px; flex: 1;">🧠 <strong>Quiz</strong> Included</span>
            </div>
            """
            html_lines.append(stats_html)
            continue

        # Top 3 Highlights Section
        if '🔥 TOP 3 TODAY' in line:
            if in_section:
                html_lines.append('</div>')
                in_section = False
            in_top3 = True
            top3_header = """
            <div style="background: linear-gradient(135deg, #EEF2FF 0%, #E0E7FF 100%); border-left: 4px solid #4F46E5; border-radius: 12px; padding: 18px; margin-bottom: 24px; font-family: 'Inter', -apple-system, sans-serif;">
                <h2 style="margin: 0 0 12px 0; font-size: 15px; color: #4F46E5; font-family: 'Outfit', sans-serif; font-weight: 700; letter-spacing: 0.5px; display: flex; align-items: center; gap: 6px;">
                    🔥 TOP HIGHLIGHTS TODAY
                </h2>
            """
            html_lines.append(top3_header)
            continue

        # Quick Recall Quiz Section
        if '🧠 QUICK RECALL' in line:
            if in_section:
                html_lines.append('</div>')
                in_section = False
            if in_top3:
                html_lines.append('</div>')
                in_top3 = False
            in_quiz = True
            quiz_header = """
            <div style="background: #F9FAFB; border: 1px solid #E5E7EB; border-radius: 16px; padding: 20px; margin: 24px 0; font-family: 'Inter', -apple-system, sans-serif;">
                <h2 style="margin: 0 0 14px 0; font-size: 16px; color: #1F2937; font-family: 'Outfit', sans-serif; font-weight: 700; border-bottom: 2px solid #E5E7EB; padding-bottom: 8px; display: flex; align-items: center; gap: 8px;">
                    🧠 QUICK RECALL QUIZ
                </h2>
            """
            html_lines.append(quiz_header)
            continue

        # Emoji headers (Topic Sections)
        if line.strip() and any(line.strip().startswith(e) for e in ['🛡️', '🏛️', '💰', '🔬', '🌍', '🌿', '📜', '🎭', '🏢', '🏆', '⚽', '📌']):
            if in_section:
                html_lines.append('</div><!-- end previous card -->')
            in_section = True
            
            # Extract title
            title_text = line.strip()
            topic_card = f"""
            <div style="background: #ffffff; border: 1px solid #F3F4F6; border-radius: 12px; padding: 16px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.02); font-family: 'Inter', -apple-system, sans-serif;">
                <h3 style="margin: 0 0 12px 0; font-size: 14px; color: #4B5563; font-family: 'Outfit', sans-serif; font-weight: 700; letter-spacing: 0.2px; text-transform: uppercase;">
                    {title_text}
                </h3>
            """
            html_lines.append(topic_card)
            continue

        # Bullet points
        if line.strip().startswith('- '):
            bullet_content = line.strip()[2:]
            html_lines.append(
                f'<div style="font-size: 13px; color: #374151; line-height: 1.6; margin-bottom: 10px; display: flex; align-items: flex-start; gap: 8px;">'
                f'<span style="color: #6366F1; font-size: 16px; line-height: 12px;">•</span>'
                f'<span style="flex: 1;">{bullet_content}</span>'
                f'</div>'
            )
            continue

        # Numbered items (Inside Top 3 Card)
        if in_top3 and line.strip() and line.strip()[0].isdigit() and '. ' in line[:4]:
            item_content = line.strip()[2:]
            html_lines.append(
                f'<div style="background: #ffffff; border-radius: 8px; padding: 10px 12px; margin-bottom: 8px; border: 1px solid #E0E7FF; font-size: 13px; color: #374151; line-height: 1.5; box-shadow: 0 1px 2px rgba(0,0,0,0.01);">'
                f'{item_content}'
                f'</div>'
            )
            continue

        # Quiz Q&A formatting
        if in_quiz:
            if line.strip().startswith(('1.', '2.', '3.', '4.', '5.')):
                q_text = line.strip()
                html_lines.append(
                    f'<p style="margin: 12px 0 4px 0; font-size: 13.5px; font-weight: 600; color: #374151;">{q_text}</p>'
                )
                continue
            if '→' in line:
                a_text = line.strip()
                html_lines.append(
                    f'<p style="margin: 0 0 12px 14px; font-size: 13px; font-family: monospace; color: #4F46E5; background: #EEF2FF; padding: 4px 8px; border-radius: 4px; display: inline-block;">{a_text}</p>'
                )
                continue

        # Footer formatting
        if '📎 Sources' in line:
            if in_section:
                html_lines.append('</div>')
                in_section = False
            if in_quiz:
                html_lines.append('</div>')
                in_quiz = False
                
            footer_html = f"""
            <div style="text-align: center; padding: 24px 12px 8px 12px; border-top: 1px solid #E5E7EB; margin-top: 24px; font-family: 'Inter', -apple-system, sans-serif; font-size: 11px; color: #9CA3AF; line-height: 1.6;">
                <p style="margin: 0 0 8px 0; font-weight: 600; color: #6B7280;">📎 SOURCES: PIB, The Hindu, Indian Express, Livemint, LiveLaw, ISRO</p>
                <p style="margin: 0 0 4px 0;">This digest was auto-curated and summarized by your GK Digest Agent.</p>
                <p style="margin: 0;">Reply to this email with any feedback.</p>
            </div>
            """
            html_lines.append(footer_html)
            break

    body = '\n'.join(html_lines)

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@700;800&display=swap" rel="stylesheet">
</head>
<body style="margin: 0; padding: 16px; background-color: #F3F4F6;">
    <div style="max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.05); overflow: hidden;">
        <div style="padding: 16px;">
            {body}
        </div>
    </div>
</body>
</html>"""
