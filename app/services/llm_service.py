import json
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
import sys
import os
import re

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.config import GROQ_API_KEY
from app.logger import get_logger

logger = get_logger("pdf_summarizer.llm")


# Initialize LLM
llm = ChatGroq(
    groq_api_key=GROQ_API_KEY,
    model_name="llama-3.3-70b-versatile",
    temperature=0,
    model_kwargs={
        "response_format": {"type": "json_object"}
    }
)


def clean_json_response(text: str):
    """
    Cleans the LLM response and extracts JSON.
    """

    if not text:
        raise ValueError("LLM returned an empty response")

    text = text.strip()

    # Remove markdown code fences
    text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    text = text.strip()

    if not text:
        raise ValueError("LLM returned an empty response after cleaning")

    # Try to extract JSON object
    json_match = re.search(r"\{.*\}", text, re.DOTALL)

    if json_match:
        return json_match.group(0).strip()

    return text


def _is_rate_limit_error(error: Exception) -> bool:
    """Return True when the failure seems to be caused by rate limiting or quota issues."""

    message = str(error).lower()

    return any(
        token in message
        for token in [
            "rate limit",
            "too many requests",
            "429",
            "quota",
            "limit exceeded",
            "exceeded your current quota",
            "overloaded",
        ]
    )


def extract_company_info(text: str):
    """
    Extract company name, summary, and sentiment using LangChain + Groq.
    """

    prompt = ChatPromptTemplate.from_template("""
You are a financial news analyzer.

Analyze the article and extract:

1. Company Name:
   Identify the main NSE-listed company discussed.

2. Summary:
   Write a concise 5-6 line summary focusing on information useful
   for a stock broker looking for short-term trading opportunities.

3. Sentiment:
   Classify the overall news sentiment as exactly one of:
   - positive
   - negative
   - neutral

IMPORTANT:
Return ONLY a valid JSON object.
Do not return markdown.
Do not return ```json.
Do not add explanations before or after the JSON.

The JSON must have exactly these fields:

{{
    "company_name": "Company Name",
    "summary": "5-6 line summary",
    "sentiment": "positive"
}}

Article:
{article}
""")

    try:

        chain = prompt | llm

        logger.info(
            "Invoking LLM for article text of length %s",
            len(text)
        )

        response = chain.invoke({
            "article": text[:3000]
        })

        # Log the actual response for debugging
        logger.info(
            "Raw LLM response type: %s",
            type(response.content).__name__
        )

        logger.info(
            "Raw LLM response: %s",
            repr(response.content)
        )

        content = response.content

        # Handle possible non-string content
        if isinstance(content, list):
            content = "".join(
                item.get("text", "")
                if isinstance(item, dict)
                else str(item)
                for item in content
            )

        content = str(content).strip()

        if not content:
            raise ValueError("LLM returned an empty response")

        cleaned = clean_json_response(content)

        logger.info(
            "Cleaned LLM JSON: %s",
            cleaned
        )

        result = json.loads(cleaned)

        # Validate required fields
        company_name = result.get("company_name")
        summary = result.get("summary")
        sentiment = result.get("sentiment")

        if not company_name:
            company_name = "Not Found"

        if not summary:
            summary = "No summary available"

        if sentiment not in ["positive", "negative", "neutral"]:
            logger.warning(
                "Invalid sentiment returned by LLM: %s",
                sentiment
            )
            sentiment = "unknown"

        final_result = {
            "company_name": company_name,
            "summary": summary,
            "sentiment": sentiment
        }

        logger.info(
            "Parsed LLM result successfully: %s",
            final_result
        )

        return final_result

    except Exception as e:

        if _is_rate_limit_error(e):
            logger.error(
                "LLM request failed due to rate limit or quota issue: %s",
                str(e)
            )
        else:
            logger.exception(
                "LLM processing failed: %s",
                str(e)
            )

        return {
            "company_name": "Not Found",
            "summary": "Error generating summary",
            "sentiment": "unknown"
        }
