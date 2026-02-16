import json
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import re
from app.config import GROQ_API_KEY


# Initialize LLM
# meta-llama/llama-4-scout-17b-16e-instruct
# llama-3.3-70b-versatile
#
llm = ChatGroq(
    groq_api_key=GROQ_API_KEY,
    model_name="meta-llama/llama-4-scout-17b-16e-instruct",
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

        response = chain.invoke({
            "article": text[:3000]
        })

        content = response.content.strip()

        print("Raw LLM Response:", content)

        cleaned = clean_json_response(content)



        # Convert to JSON
        result = json.loads(cleaned)

        print ("Parsed Result:", result)

        return result

    except Exception as e:
        print("LLM Error:", e)
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