import json
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
import sys
import os
import re

sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../..")
    )
)

from app.config import GROQ_API_KEY
from app.logger import get_logger


logger = get_logger("pdf_summarizer.llm")


# ============================================================
# Initialize LLM
# ============================================================

llm = ChatGroq(
    groq_api_key=GROQ_API_KEY,
    model_name="llama-3.3-70b-versatile",
    temperature=0
)


# ============================================================
# Clean LLM JSON response
# ============================================================

def clean_json_response(text: str):
    """
    Clean common markdown wrappers from the LLM response.

    The LLM may return:
        {...}

    or:

        [
            {...}
        ]

    We intentionally DO NOT extract only {...} using regex,
    because doing so can break valid JSON arrays.
    """

    if not text:
        raise ValueError("LLM returned an empty response")

    text = text.strip()

    # Remove ```json wrapper
    text = re.sub(
        r"^```json\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    # Remove generic ``` wrapper
    text = re.sub(
        r"^```\s*",
        "",
        text
    )

    # Remove closing ```
    text = re.sub(
        r"\s*```$",
        "",
        text
    )

    text = text.strip()

    if not text:
        raise ValueError(
            "LLM returned an empty response after cleaning"
        )

    return text


# ============================================================
# Rate-limit detection
# ============================================================

def _is_rate_limit_error(error: Exception) -> bool:
    """
    Return True when the failure seems to be caused by
    rate limiting or quota issues.
    """

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


# ============================================================
# Extract company information
# ============================================================

def extract_company_info(text: str):
    """
    Extract company name, summary, and sentiment using
    LangChain + Groq.
    """

    prompt = ChatPromptTemplate.from_template("""
You are a financial news analyzer specializing in
NSE-listed Indian companies.

Analyze the article below and extract the following:

1. Company Name
   - Identify the main NSE-listed company discussed in the article.
   - Use the company's proper name.

2. Summary
   - Write a concise 5-6 line summary.
   - Focus on information useful for a stock broker
     looking for short-term trading opportunities.
   - Mention the important announcement/event,
     why it matters, and its likely market impact.

3. Sentiment
   Classify the overall news sentiment as exactly one of:
   - positive
   - negative
   - neutral

IMPORTANT:
Return ONLY valid JSON.

Do NOT return:
- Markdown
- ```json
- Explanations
- Text before the JSON
- Text after the JSON

Preferred JSON format:

{{
    "company_name": "Company Name",
    "summary": "5-6 line summary",
    "sentiment": "positive"
}}

Article:
{article}
""")

    try:

        # ----------------------------------------------------
        # Create chain
        # ----------------------------------------------------

        chain = prompt | llm

        logger.info(
            "Invoking LLM for article text of length %s",
            len(text)
        )

        # ----------------------------------------------------
        # Call LLM
        # ----------------------------------------------------

        response = chain.invoke({
            "article": text[:3000]
        })

        # ----------------------------------------------------
        # Get raw response
        # ----------------------------------------------------

        content = response.content

        logger.info(
            "Raw LLM response type: %s",
            type(content).__name__
        )

        logger.info(
            "Raw LLM response: %r",
            content
        )

        # ----------------------------------------------------
        # Handle non-string response
        # ----------------------------------------------------

        if isinstance(content, list):

            logger.warning(
                "LLM returned response as a list"
            )

            content = "".join(
                item.get("text", "")
                if isinstance(item, dict)
                else str(item)
                for item in content
            )

        content = str(content).strip()

        if not content:
            raise ValueError(
                "LLM returned an empty response"
            )

        # ----------------------------------------------------
        # Clean JSON
        # ----------------------------------------------------

        cleaned = clean_json_response(content)

        logger.info(
            "Cleaned LLM JSON: %s",
            cleaned
        )

        # ----------------------------------------------------
        # Parse JSON
        # ----------------------------------------------------

        result = json.loads(cleaned)

        logger.info(
            "Parsed JSON type: %s",
            type(result).__name__
        )

        # ====================================================
        # Handle JSON ARRAY
        # ====================================================
        #
        # Example LLM response:
        #
        # [
        #     {},
        #     {
        #         "company_name": "3i Infotech Limited",
        #         "summary": "...",
        #         "sentiment": "positive"
        #     }
        # ]
        #
        # ====================================================

        if isinstance(result, list):

            logger.warning(
                "LLM returned a JSON array with %d item(s)",
                len(result)
            )

            valid_result = None

            for item in result:

                if not isinstance(item, dict):
                    continue

                if item.get("company_name"):
                    valid_result = item
                    break

            if valid_result is None:

                raise ValueError(
                    "LLM returned a JSON array but no valid "
                    "company information was found"
                )

            result = valid_result

            logger.info(
                "Valid company information extracted from "
                "LLM JSON array"
            )

        # ====================================================
        # Handle JSON OBJECT
        # ====================================================

        elif isinstance(result, dict):

            logger.info(
                "LLM returned a JSON object"
            )

        # ====================================================
        # Unexpected JSON type
        # ====================================================

        else:

            raise ValueError(
                "Unexpected LLM JSON type: "
                f"{type(result).__name__}"
            )

        # ----------------------------------------------------
        # Extract fields
        # ----------------------------------------------------

        company_name = result.get(
            "company_name",
            "Not Found"
        )

        summary = result.get(
            "summary",
            "No summary available"
        )

        sentiment = result.get(
            "sentiment",
            "unknown"
        )

        # ----------------------------------------------------
        # Clean values
        # ----------------------------------------------------

        if not company_name:
            company_name = "Not Found"

        if not summary:
            summary = "No summary available"

        # ----------------------------------------------------
        # Validate sentiment
        # ----------------------------------------------------

        if isinstance(sentiment, str):

            sentiment = sentiment.strip().lower()

        else:

            sentiment = "unknown"

        if sentiment not in [
            "positive",
            "negative",
            "neutral"
        ]:

            logger.warning(
                "Invalid sentiment returned by LLM: %s",
                sentiment
            )

            sentiment = "unknown"

        # ----------------------------------------------------
        # Final result
        # ----------------------------------------------------

        final_result = {
            "company_name": company_name,
            "summary": summary,
            "sentiment": sentiment
        }

        logger.info(
            "Final parsed LLM result: %s",
            final_result
        )

        return final_result

    # ========================================================
    # Error handling
    # ========================================================

    except Exception as e:

        if _is_rate_limit_error(e):

            logger.error(
                "LLM request failed due to rate limit "
                "or quota issue: %s",
                str(e)
            )

        else:

            logger.exception(
                "LLM processing failed: %s",
                str(e)
            )

        # ----------------------------------------------------
        # Return fallback result
        # ----------------------------------------------------

        return {
            "company_name": "Not Found",
            "summary": "Error generating summary",
            "sentiment": "unknown"
        }


# ============================================================
# Local testing
# ============================================================

# if __name__ == "__main__":
#
#     sample_text = """
#     3i Infotech Limited has completed the necessary
#     procedures for listing of its equity shares after
#     implementing a Scheme of Arrangement.
#
#     The company's equity shares will commence trading
#     again on the BSE and NSE from October 22, 2021.
#     """
#
#     result = extract_company_info(sample_text)
#
#     print("Extracted Info:")
#     print(json.dumps(result, indent=4))
