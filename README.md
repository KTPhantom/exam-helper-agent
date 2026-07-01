# 📋 GK Digest Agent

**Automated daily GK digest for CDS & AFCAT exam preparation — at zero cost.**

Scrapes Indian news RSS feeds, summarizes them with Google Gemini AI, and emails
you a skimmable 5-minute digest every morning at 7:00 AM IST.

## Architecture

```
RSS Feeds (PIB, Hindu, IE) → Gemini AI (summarize) → Email (Resend)
         ↑                                                ↑
    GitHub Actions (daily cron, free)              You (inbox)
```

## Quick Start (Personal Use)

### 1. Get Free API Keys (5 minutes)

| Service | Free Tier | Get Key |
|---|---|---|
| **Google Gemini** | 1,500 req/day | [aistudio.google.com](https://aistudio.google.com) |
| **Resend** | 100 emails/day | [resend.com](https://resend.com) |

### 2. Local Setup

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/gk-digest-agent.git
cd gk-digest-agent

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Configure secrets
copy .env.example .env
# Edit .env with your API keys and email
```

### 3. Test Locally

```bash
# Test RSS scraping only (no AI, no email)
python src/main.py --scrape-only

# Generate digest without sending email (saves to output_digest.md)
python src/main.py --dry-run

# Full run: scrape + summarize + email
python src/main.py
```

### 4. Deploy to GitHub Actions (Free, Automated)

1. Push this repo to GitHub (public repo = free unlimited Actions)
2. Go to **Settings → Secrets and variables → Actions**
3. Add these repository secrets:

| Secret Name | Value |
|---|---|
| `GEMINI_API_KEY` | Your Gemini API key |
| `RESEND_API_KEY` | Your Resend API key |
| `EMAIL_TO` | Your email address |
| `EMAIL_FROM` | `onboarding@resend.dev` (or your verified Resend domain) |

4. Go to **Actions** tab → **Daily GK Digest** → **Run workflow** to test
5. The cron will now run automatically every day at 7:00 AM IST

> **Note:** GitHub may disable cron jobs if the repo has no commits for 60 days.
> Push a small commit periodically, or manually trigger the workflow.

## Project Structure

```
gk-digest-agent/
├── .github/workflows/
│   └── daily-digest.yml    # GitHub Actions cron
├── src/
│   ├── main.py             # Pipeline orchestrator
│   ├── scraper.py          # RSS feed scraper
│   ├── summarizer.py       # Gemini AI summarizer
│   ├── formatter.py        # Digest formatter (MD + HTML)
│   └── emailer.py          # Resend email sender
├── config/
│   └── feeds.yaml          # RSS feed URLs by topic
├── requirements.txt
├── .env.example
└── README.md
```

## Digest Format

The digest follows an industry-proven structure (Morning Brew + TLDR + 1440 Daily):

1. **🔥 Top 3 Today** — The 3 most important items at a glance
2. **🛡️ Defence** (first, because CDS is a defence exam)
3. **12 topic sections** — 2-4 bullets each, same order daily
4. **🧠 Quick Recall Quiz** — 5 questions to test yourself
5. **📎 Footer** — Sources, share links

## Cost Breakdown

| Component | Service | Monthly Cost |
|---|---|---|
| Scheduling | GitHub Actions | $0 |
| News Data | RSS Feeds | $0 |
| AI Summarization | Gemini Flash (free tier) | $0 |
| Email Delivery | Resend (free tier) | $0 |
| **Total** | | **$0** |

## Future Expansion

When ready for public deployment, add:
- **Telegram channel** (`src/telegram_bot.py`) — unlimited free subscribers
- **Buttondown newsletter** (`src/newsletter.py`) — web archive + email subscribers
- **Static website** (GitHub Pages) — SEO + AdSense monetization

## License

MIT
