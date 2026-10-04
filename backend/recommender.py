from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


DATA_PATH = (
    Path(__file__).resolve().parent
    / "data"
    / "seed_products_cleaned.csv"
)


class SeedRecommender:
    def __init__(self):
        self.df = pd.read_csv(DATA_PATH)

        # Exclude unknown values from similarity features.
        feature_columns = [
            "crop_type",
            "suitable_season",
            "soil_type",
            "product_description"
        ]

        features = (
            self.df[feature_columns]
            .fillna("")
            .replace("Not specified", "")
        )

        product_text = features.agg(" ".join, axis=1)

        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words="english"
        )

        self.product_vectors = self.vectorizer.fit_transform(
            product_text
        )

    def recommend(
        self,
        crop_type,
        season=None,
        soil_preference=None,
        max_maturity_days=None,
        budget_usd=None,
        top_n=3
    ):
        if not crop_type or not crop_type.strip():
            raise ValueError("Please provide a crop type.")

        if top_n < 1:
            raise ValueError("top_n must be at least 1.")

        if max_maturity_days is not None and max_maturity_days <= 0:
            raise ValueError("Maturity days must be positive.")

        if budget_usd is not None and budget_usd < 0:
            raise ValueError("Budget cannot be negative.")

        candidates = self.df[
            self.df["crop_type"].str.casefold()
            == crop_type.strip().casefold()
        ].copy()

        # Apply explicit requirements before ranking.
        if season:
            candidates = candidates[
                candidates["suitable_season"].str.casefold()
                == season.strip().casefold()
            ]

        if max_maturity_days is not None:
            # Unknown maturity does not satisfy a deadline.
            candidates = candidates[
                candidates["maturity_max_days"].notna()
                & (
                    candidates["maturity_max_days"]
                    <= max_maturity_days
                )
            ]

        if budget_usd is not None:
            candidates = candidates[
                candidates["price_usd_per_packet"].notna()
                & (
                    candidates["price_usd_per_packet"]
                    <= budget_usd
                )
            ]

        if candidates.empty:
            return []

        # Soil is a text preference, not a verified suitability filter.
        query = " ".join(
            value for value in [
                crop_type,
                season,
                soil_preference
            ]
            if value
        )

        query_vector = self.vectorizer.transform([query])

        scores = cosine_similarity(
            query_vector,
            self.product_vectors[candidates.index.to_numpy()]
        ).ravel()

        candidates["similarity_score"] = scores

        candidates = candidates.sort_values(
            ["similarity_score", "product_name"],
            ascending=[False, True]
        ).head(top_n)

        # Convert missing values to None for later API/JSON use.
        return (
            candidates.astype(object)
            .where(candidates.notna(), None)
            .to_dict(orient="records")
        )


if __name__ == "__main__":
    recommender = SeedRecommender()

    results = recommender.recommend(
        crop_type="Tomato",
        season="Warm season",
        max_maturity_days=60,
        budget_usd=3.00
    )

    if not results:
        print("No products meet these requirements.")
    else:
        for number, product in enumerate(results, start=1):
            print(f"\nRecommendation {number}")
            print("Product:", product["product_name"])
            print("Crop:", product["crop_type"])
            print("Season:", product["suitable_season"])
            print("Soil guidance:", product["soil_type"])
            print("Water guidance:", product["water_requirement"])
            print("Maturity:", product["maturity_period_days"])
            print("Price USD:", product["price_usd_per_packet"])
            print(
                "Text similarity:",
                round(product["similarity_score"], 3)
            )