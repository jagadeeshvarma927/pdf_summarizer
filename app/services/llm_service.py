import json
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import re
from app.config import GROQ_API_KEY
from app.logger import get_logger

logger = get_logger("pdf_summarizer.llm")

# Initialize LLM
# meta-llama/llama-4-scout-17b-16e-instruct
# llama-3.3-70b-versatile
#
llm = ChatGroq(
    groq_api_key=GROQ_API_KEY,
    model_name="llama-3.1-8b-instant",
    temperature=0
)

def clean_json_response(text: str):
    """
    Removes markdown code blocks and extracts valid JSON
    """
    # Remove ```json or ``` wrappers
    text = re.sub(r"```json", "", text)
    text = re.sub(r"```", "", text)

    # Extract JSON object only
    json_match = re.search(r"\{.*\}", text, re.DOTALL)

    if json_match:
        return json_match.group(0)

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
    Extract company name and summary using LangChain + Groq
    """

    prompt = ChatPromptTemplate.from_template("""
You are a financial news analyzer.

From the article below, extract:

1. Company Name (Main company discussed)
2. A concise 5-6 line summary

Return ONLY valid JSON in this format:

{{
  "company_name": "...",
  "summary": "..."
}}

Article:
{article}
""")

    try:
        chain = prompt | llm

        logger.info("Invoking LLM for article text of length %s", len(text))
        response = chain.invoke({
            "article": text[:3000]
        })

        content = response.content.strip()
        logger.info("LLM response received successfully")

        cleaned = clean_json_response(content)

        # Convert to JSON
        result = json.loads(cleaned)
        logger.info("Parsed LLM result successfully")

        return result

    except Exception as e:
        if _is_rate_limit_error(e):
            logger.error("LLM request failed due to rate limit or quota issue: %s", str(e))
        else:
            logger.exception("LLM processing failed: %s", str(e))
        return {
            "company_name": "Not Found",
            "summary": "Error generating summary"
        }


# if __name__ == "__main__":
#     # Test with a sample article
#     sample_text = """
#     Apple Inc. reported its quarterly earnings on Tuesday, surpassing Wall Street expectations. The tech giant posted a revenue of $90 billion, driven by strong sales of the iPhone 15 and increased services revenue. CEO Tim Cook highlighted the company's focus on innovation and sustainability during the earnings call. Despite supply chain challenges, Apple continues to demonstrate resilience in the competitive technology market.
#     """

#     result = extract_company_info(sample_text)
#     print("Extracted Info:", result)