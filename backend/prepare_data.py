from pathlib import Path
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent / "data"

df = pd.read_csv(DATA_DIR / "seed_products_200.csv")

# Clean text without changing the original CSV.
text_columns = df.columns.drop("price_usd_per_packet")

for column in text_columns:
    df[column] = (
        df[column]
        .astype("string")
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
    )

df = df.replace({
    "Not specified": pd.NA,
    "": pd.NA
})

# Keep prices numeric.
df["price_usd_per_packet"] = pd.to_numeric(
    df["price_usd_per_packet"],
    errors="raise"
)

# Examples: "60" becomes 60–60; "80-90" becomes 80–90.
maturity = df["maturity_period_days"].astype("string")

bounds = maturity.str.extract(
    r"^(\d+)(?:\s*[-–]\s*(\d+))?$"
)

# Stop if a published value cannot be parsed.
invalid = maturity.notna() & bounds[0].isna()

if invalid.any():
    raise ValueError(
        "Check these maturity values:\n"
        + df.loc[invalid, [
            "product_name", "maturity_period_days"
        ]].to_string(index=False)
    )

df["maturity_min_days"] = pd.to_numeric(
    bounds[0]
).astype("Int64")

df["maturity_max_days"] = pd.to_numeric(
    bounds[1].fillna(bounds[0])
).astype("Int64")

if (df["maturity_min_days"] > df["maturity_max_days"]).any():
    raise ValueError("A maturity range has reversed bounds.")

output_path = DATA_DIR / "seed_products_cleaned.csv"
df.to_csv(output_path, index=False, encoding="utf-8-sig")

print(f"Saved: {output_path.name}")
print(f"Products: {len(df)}")
print(f"Columns: {len(df.columns)}")

print("\nMaturity preview:")
print(df[[
    "product_name",
    "maturity_period_days",
    "maturity_min_days",
    "maturity_max_days"
]].head(10).to_string(index=False))