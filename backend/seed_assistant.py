from condition_extractor import extract_conditions
from recommender import SeedRecommender
from explanation_generator import explain_recommendations


def main():
    message = input("Describe your growing conditions: ")
    conditions = extract_conditions(message)

    questions = list(conditions.clarification_questions)

    if conditions.crop_type is None and not questions:
        questions.append("Which crop would you like to grow?")

    # Budget must match the dataset's currency and price basis.
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
        print("\nPlease clarify:")
        for question in dict.fromkeys(questions):
            print("-", question)
        return

    # These requirements are captured but not evaluated yet.
    unsupported_requirements = []

    if conditions.water_availability:
        unsupported_requirements.append("water availability")

    if conditions.disease_requirement:
        unsupported_requirements.append("disease resistance")

    if unsupported_requirements:
        print(
            "\nYour request includes: "
            + ", ".join(unsupported_requirements)
            + "."
        )
        print(
            "This version cannot evaluate those requirements yet, "
            "so it will not claim that a product meets them."
        )
        return

    recommender = SeedRecommender()

    results = recommender.recommend(
        crop_type=conditions.crop_type,
        season=conditions.season,
        soil_preference=conditions.soil_preference,
        max_maturity_days=conditions.max_maturity_days,
        budget_usd=conditions.budget_amount,
        top_n=3
    )

    if not results:
        print("\nNo products meet the specified filters.")
        return

    print("\nMatching catalogue products:")

    for number, product in enumerate(results, start=1):
        print(f"\n{number}. {product['product_name']}")

        maturity = product["maturity_period_days"]
        print(
            "Published maturity:",
            maturity if maturity is not None else "Not specified"
        )

        print(
            f"Catalogue price: "
            f"${product['price_usd_per_packet']:.2f} per packet"
        )

        print(
            "Soil guidance:",
            product["soil_type"] or "Not specified"
        )

        print(
            "Water guidance:",
            product["water_requirement"] or "Not specified"
        )

    # Generate simple explanations from the selected records.
    print("\nSimple explanations:")

    try:
        explanation = explain_recommendations(
            conditions,
            results
        )

        for number, product in enumerate(
            explanation.products,
            start=1
        ):
            print(f"\n{number}. {product.product_name}")
            print(product.explanation)

        if explanation.limitations:
            print("\nThings to keep in mind:")
            for limitation in explanation.limitations:
                print("-", limitation)

    except Exception:
        print(
            "The explanation could not be generated. "
            "The catalogue matches above are still available."
        )

    if conditions.soil_preference:
        print(
            "\nSoil was used as a text preference. "
            "Soil suitability has not been confirmed."
        )

    if conditions.growing_location:
        print(
            f"\nSuitability for {conditions.growing_location} "
            "has not been verified by this dataset."
        )

    print(
        "\nThese are catalogue matches, not guarantees of "
        "harvest time or successful growth."
    )


if __name__ == "__main__":
    main()