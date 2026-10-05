from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from pathlib import Path
from fastapi.responses import FileResponse
from condition_extractor import extract_conditions
from recommender import SeedRecommender
from explanation_generator import explain_recommendations
from fastapi.staticfiles import StaticFiles
import json
from typing import Literal


app = FastAPI(title="Seed Recommendation API")
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
app.mount(
    "/static",
    StaticFiles(directory=str(FRONTEND_DIR)),
    name="static",
)


@app.get("/", response_class=FileResponse)
def homepage():
    return FileResponse(FRONTEND_DIR / "index.html")

recommender = SeedRecommender()


class ConversationMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class RecommendationRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[ConversationMessage] = Field(
        default_factory=list,
        max_length=12,
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/recommend")
def recommend(request: RecommendationRequest):
    message = request.message.strip()

    if not message:
        raise HTTPException(
            status_code=422,
            detail="Please describe your growing conditions."
        )

    # Understand the farmer's message.
    try:
        conversation = [
            item.model_dump()
            for item in request.history
        ]

        conversation.append({
            "role": "user",
            "content": message,
        })

        conditions = extract_conditions(
            json.dumps(
                {"conversation": conversation},
                ensure_ascii=False,
            )
        )
    except Exception:
        raise HTTPException(
            status_code=502,
            detail=(
                "Could not understand the message right now. "
                "Please try again."
            )
        ) from None

    questions = list(conditions.clarification_questions)

    if conditions.crop_type is None and not questions:
        questions.append("Which crop would you like to grow?")

    if conditions.budget_amount is not None:
        currency = (conditions.budget_currency or "").upper()

        if currency != "USD":
            questions.append(
                "This prototype uses USD prices. "
                "What is your budget in US dollars?"
            )

        if conditions.budget_basis != "per packet":
            questions.append(
                "What is your budget per seed packet?"
            )

    if questions:
        return {
            "status": "needs_clarification",
            "conditions": conditions.model_dump(),
            "questions": list(dict.fromkeys(questions)),
            "products": [],
            "explanation": None,
            "warnings": []
        }

    unsupported = []

    if conditions.water_availability:
        unsupported.append("water availability")

    if conditions.disease_requirement:
        unsupported.append("disease resistance")

    if unsupported:
        return {
            "status": "unsupported_requirements",
            "conditions": conditions.model_dump(),
            "questions": [],
            "products": [],
            "explanation": None,
            "warnings": [
                "This version cannot evaluate these requirements: "
                + ", ".join(unsupported)
                + ". No products have been presented as meeting them."
            ]
        }

    # Find products meeting the supported filters.
    products = recommender.recommend(
        crop_type=conditions.crop_type,
        season=conditions.season,
        soil_preference=conditions.soil_preference,
        max_maturity_days=conditions.max_maturity_days,
        budget_usd=conditions.budget_amount,
        top_n=3
    )

    if not products:
        return {
            "status": "no_matches",
            "conditions": conditions.model_dump(),
            "questions": [],
            "products": [],
            "explanation": None,
            "warnings": [
                "No catalogue products meet the specified filters."
            ]
        }

    warnings = [
        "Published maturity is an estimate, not a guaranteed "
        "harvest deadline. Its starting point may be unspecified.",
        "Prices are USD wholesale catalogue quotes, "
        "not local retail prices.",
        "These catalogue records do not verify regional suitability."
    ]

    if conditions.soil_preference:
        warnings.append(
            "Soil was used as a text preference; "
            "soil suitability has not been confirmed."
        )

    if conditions.growing_location:
        warnings.append(
            f"Suitability for {conditions.growing_location} "
            "has not been verified."
        )

    # Explanation failure should not discard catalogue results.
    explanation = None

    try:
        explanation = explain_recommendations(
            conditions,
            products
        ).model_dump()
    except Exception:
        warnings.append(
            "The simple explanation is temporarily unavailable. "
            "Catalogue results are still shown."
        )

    return {
        "status": "success",
        "conditions": conditions.model_dump(),
        "questions": [],
        "products": products,
        "explanation": explanation,
        "warnings": warnings
    }