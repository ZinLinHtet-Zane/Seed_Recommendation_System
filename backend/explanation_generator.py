import json
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel, Field

from condition_extractor import FarmerConditions


load_dotenv(Path(__file__).resolve().parent / ".env")


class ProductExplanation(BaseModel):
    product_name: str
    explanation: str


class RecommendationExplanation(BaseModel):
    products: list[ProductExplanation]
    limitations: list[str] = Field(default_factory=list)


INSTRUCTIONS = """
Writing style for farmers:
- Use everyday English and short sentences.
- Write 2 or 3 short sentences per product, preferably under 60 words.
- Explain why it matches the farmer's stated conditions first.
- Avoid technical terms such as determinate, indeterminate,
  cultivar, agronomic, and foliar unless the farmer asks about them.
- Omit organic status, heirloom history, and growth habit unless
  they help answer the farmer's request.
- Do not repeat the product name inside its explanation.
- Avoid formal phrases such as "satisfies your requirement" or
  "falls within your maximum limit."
- Use phrases such as "fits your budget" and "is listed for warm weather."
- Keep limitations short and easy to understand.
- Do not add growing advice or facts that are absent from the supplied data.

Accuracy rules:
- Preserve all qualifications in the supplied records.
- For tomatoes and eggplants, explain that published maturity
  counts from transplanting, not from sowing seed.
- For lettuce, published maturity counts from direct seeding.
- If the starting point is unknown, say it is not specified.
- Never promise a harvest date or successful growth.
- Describe the price as a wholesale unit quote.
- Explain in the limitations that the quoted price applies to
  Guaranteed Sale Tier 1 orders of 150–399 total packets.
  Do not imply a farmer can buy one packet at that price.
- If a product is marked unavailable, say so clearly.
- General crop soil and water guidance does not prove that a
  particular variety suits the farmer's conditions.
- Keep partial resistance, tolerance, and unknown disease
  information distinct. Do not describe them as immunity.
- Return the existing JSON structure and exact product names
  in the same order.
"""


def explain_recommendations(
    conditions: FarmerConditions,
    products: list[dict]
) -> RecommendationExplanation:
    if not products:
        raise ValueError("There are no selected products to explain.")

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError("Add GEMINI_API_KEY to backend/.env")

    # Send factual records, without the text-similarity score.
    factual_products = [
        {
            key: value
            for key, value in product.items()
            if key != "similarity_score"
        }
        for product in products
    ]

    payload = {
        "farmer_conditions": conditions.model_dump(),
        "selected_products": factual_products,
        "filtering": {
            "crop": "Exact crop category",
            "season": "Exact category when specified",
            "maturity": "Published maximum days within requested limit",
            "budget": "USD per-packet quote within requested limit",
            "soil": "Text preference only"
        }
    }

    client = genai.Client(api_key=api_key)

    response = client.interactions.create(
        model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
        input=(
            INSTRUCTIONS
            + "\nData:\n"
            + json.dumps(payload, ensure_ascii=False, allow_nan=False)
        ),
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": RecommendationExplanation.model_json_schema()
        }
    )

    if not response.output_text:
        raise RuntimeError("Gemini returned no explanation.")

    result = RecommendationExplanation.model_validate_json(
        response.output_text
    )

    expected_names = [
        product["product_name"] for product in products
    ]
    returned_names = [
        product.product_name for product in result.products
    ]

    if returned_names != expected_names:
        raise ValueError(
            "Gemini changed the selected products or their order."
        )

    return result