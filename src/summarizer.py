"""
AI Summarizer for GK Digest Agent.

Uses Google Gemini 2.0 Flash (free tier) via the new google-genai SDK
to generate a complete daily GK digest and quiz in a single API call.
Uses a raw JSON Schema dictionary to avoid Pydantic conversion issues.
"""

import os
import json
import time
from typing import Optional, Dict

from google import genai
from google.genai import types
from google.genai.errors import APIError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


# System instruction for the Gemini model
SYSTEM_INSTRUCTION = """You are an expert GK (General Knowledge) compiler for Indian defence exam 
preparation — specifically CDS (Combined Defence Services) and AFCAT (Air Force Common Admission Test).

Your job is to compile a daily exam-focused digest and a quiz from raw news articles.

RULES FOR DIGEST SUMMARIES:
1. For each topic, select the 2-4 MOST exam-relevant items from the provided articles list.
2. Each bullet must be a SINGLE concise line (max 20 words for the core fact).
3. Bullet format: "- **Bold key term** -- fact. ([Source Name](url))"
   Where "url" is the exact string value from the "link" field of the selected article.
   Example: "- **INS Tushil** -- stealth frigate commissioned. ([PIB](https://pib.gov.in/release/123))"
4. Focus on facts that could appear as MCQs: names, dates, numbers, places, organizations.
5. Skip a topic entirely (set its field value to null/None) if nothing is genuinely exam-relevant.
6. Do NOT editorialize or add opinions. Be factual and neutral.
7. Do NOT repeat information across bullets.
8. Prioritize: government appointments, policy changes, defence procurements/exercises,
   international summits, awards, records, and scientific achievements.

RULES FOR QUIZ:
1. Generate exactly 5 quick-recall quiz questions and answers based on the selected digest highlights.
2. Format the quiz string exactly as:
Q: [question]
A: [short answer]
Q: [question]
A: [short answer]
...
"""

PROMPT_TEMPLATE = """You are given a JSON object containing raw news articles categorized by topic keys.
Please process these articles and return the daily GK digest and quiz.

INPUT ARTICLES:
{input_json}

Please fill in the JSON schema response with:
1. The summarized bullets string for each specific topic key. If a topic has no exam-relevant articles, set its value to null.
2. The 5 Q&A pairs for the quiz under the "quiz" key.
"""

# Native JSON Schema dictionary for structured output
# This prevents Pydantic schema serialization bugs (like 'additional_properties')
RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "defence": {"type": "STRING"},
        "polity": {"type": "STRING"},
        "economics": {"type": "STRING"},
        "science_tech": {"type": "STRING"},
        "geography": {"type": "STRING"},
        "environment": {"type": "STRING"},
        "history": {"type": "STRING"},
        "art_culture": {"type": "STRING"},
        "organisations": {"type": "STRING"},
        "awards": {"type": "STRING"},
        "sports": {"type": "STRING"},
        "current_affairs": {"type": "STRING"},
        "quiz": {"type": "STRING"}
    }
}


# Module-level client (initialized once)
_client: Optional[genai.Client] = None
_MODEL_NAME = 'gemini-2.0-flash'


def _get_client() -> genai.Client:
    """Get or create the Gemini client."""
    global _client
    if _client is None:
        api_key = os.environ.get('GEMINI_API_KEY', '')
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY not found. Set it in .env or as an environment variable.\n"
                "Get a free key at: https://aistudio.google.com"
            )
        _client = genai.Client(api_key=api_key)
    return _client


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=4, max=15),
    retry=retry_if_exception_type(APIError),
    reraise=True
)
def _generate_digest_single_call(input_json_str: str) -> dict:
    """Generate the full digest and quiz in a single structured API call."""
    client = _get_client()
    prompt = PROMPT_TEMPLATE.format(input_json=input_json_str)

    response = client.models.generate_content(
        model=_MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.2,
            response_mime_type="application/json",
            response_schema=RESPONSE_SCHEMA,
        ),
    )

    if not response.text:
        raise ValueError("Gemini API returned an empty response.")

    return json.loads(response.text)


def summarize_all_topics(
    topic_articles: dict,
    topic_config: dict,
) -> dict[str, Optional[str]]:
    """
    Deprecated in favor of full pipeline execution, but kept for compatibility.
    """
    raise NotImplementedError(
        "Use summarize_and_quiz_single_call() instead of separate summarization."
    )


def summarize_and_quiz_single_call(
    topic_articles: dict,
    topic_config: dict,
    max_articles_per_topic: int = 12,
) -> tuple[dict[str, Optional[str]], Optional[str]]:
    """
    Scrapes and processes all articles, calling Gemini exactly once to get
    the daily digest and the quiz.

    Args:
        topic_articles: Dict of topic_key -> list of Article objects.
        topic_config: The 'topics' section from feeds.yaml.
        max_articles_per_topic: Max articles to send per topic to stay within token limits.

    Returns:
        A tuple of (summaries_dict, quiz_string).
    """
    # Step 1: Format the input articles into a clean, minimal JSON object for the API
    input_data = {}
    for topic_key, articles in topic_articles.items():
        if not articles:
            continue
        
        topic_name = topic_config.get(topic_key, {}).get('name', topic_key)
        input_data[topic_key] = {
            "topic_name": topic_name,
            "articles": [
                {
                    "title": a.title,
                    "summary": a.summary[:200],  # Keep summaries concise to save tokens
                    "source": a.source,
                    "link": a.link
                }
                for a in articles[:max_articles_per_topic]
            ]
        }

    input_json_str = json.dumps(input_data, indent=2)

    # Step 2: Make the single API call with retry wrapper
    try:
        print("  [AI] Sending articles to Gemini in a single structured call...")
        result = _generate_digest_single_call(input_json_str)
        print("  [AI] Generation successful!")
        
        # Ensure any missing topic keys are present and set to None
        summaries = {
            "defence": result.get("defence"),
            "polity": result.get("polity"),
            "economics": result.get("economics"),
            "science_tech": result.get("science_tech"),
            "geography": result.get("geography"),
            "environment": result.get("environment"),
            "history": result.get("history"),
            "art_culture": result.get("art_culture"),
            "organisations": result.get("organisations"),
            "awards": result.get("awards"),
            "sports": result.get("sports"),
            "current_affairs": result.get("current_affairs"),
        }
            
        return summaries, result.get("quiz")

    except Exception as e:
        print(f"\n  [!] Single-call Gemini generation failed: {e}")
        print("  [!] Executing fallback mode (generating basic summaries from raw titles)...")
        
        # Fallback: Create basic summaries from raw titles
        fallback_summaries = {}
        for topic_key in topic_config.keys():
            articles = topic_articles.get(topic_key, [])
            fallback_summaries[topic_key] = _fallback_summarize(articles[:4])
            
        fallback_quiz = (
            "Q: Why did the Gemini API call fail?\n"
            "A: Check API key configuration or Internet connection.\n"
            "Q: Can I still read the daily news highlights?\n"
            "A: Yes, fallback title compilation has been generated below."
        )
        return fallback_summaries, fallback_quiz


def _fallback_summarize(articles: list) -> Optional[str]:
    """Fallback: create bullets from raw titles when Gemini fails."""
    if not articles:
        return None
    lines = []
    for a in articles[:4]:
        words = a.title.split()
        source_part = f"[{a.source}]({a.link})" if a.link else a.source
        if len(words) > 3:
            bold_part = ' '.join(words[:3])
            rest = ' '.join(words[3:])
            lines.append(f"- **{bold_part}** -- {rest}. ({source_part})")
        else:
            lines.append(f"- **{a.title}**. ({source_part})")
    return '\n'.join(lines)


if __name__ == '__main__':
    """Quick test: run with dummy data to verify schema validation."""
    from dotenv import load_dotenv
    load_dotenv()
    
    test_articles = {
        "defence": [
            {"title": "INS Tushil stealth frigate commissioned at Goa Shipyard", "summary": "Stealth frigate INS Tushil joins Western Command.", "source": "PIB"}
        ]
    }
    
    # Format into Article objects for test
    from src.scraper import Article
    mapped_articles = {
        "defence": [
            Article(title=test_articles["defence"][0]["title"], summary=test_articles["defence"][0]["summary"], link="", source="PIB")
        ]
    }
    
    config = {"defence": {"name": "Defence — Army, Navy, Air Force"}}
    
    print("Testing single-call generation...")
    summaries, quiz = summarize_and_quiz_single_call(mapped_articles, config)
    print("\nSUMMARIES:")
    print(json.dumps(summaries, indent=2))
    print("\nQUIZ:")
    print(quiz)
