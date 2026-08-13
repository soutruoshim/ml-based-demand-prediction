"""HTTP API for uploading demand CSV files and returning ML results."""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sklearn.ensemble import RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.tree import DecisionTreeRegressor

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from train_model import RANDOM_STATE, make_pipeline  # noqa: E402

FEATURES = ["product_type", "month", "season", "previous_sales", "stock_quantity",
            "price", "promotion", "customer_order_quantity", "previous_production_quantity"]
REQUIRED = ["forecast_month", *FEATURES, "target_demand"]
NUMERIC = ["month", "previous_sales", "stock_quantity", "price", "promotion",
           "customer_order_quantity", "previous_production_quantity", "target_demand"]
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

app = FastAPI(title="Factory Demand Prediction API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def clean_records(frame: pd.DataFrame) -> list[dict]:
    return frame.replace({np.nan: None}).to_dict(orient="records")


def validate_dataset(df: pd.DataFrame) -> dict:
    errors, warnings = [], []
    missing = [column for column in REQUIRED if column not in df.columns]
    if missing:
        errors.append("Missing required columns: " + ", ".join(missing))
        return {"valid": False, "errors": errors, "warnings": warnings,
                "summary": {"rows": len(df), "columns": len(df.columns)},
                "columns": list(df.columns), "preview": clean_records(df.head(8))}

    data = df[REQUIRED].copy()
    if len(data) < 15:
        errors.append("The dataset needs at least 15 rows for a meaningful train/test split.")
    duplicate_count = int(data.duplicated().sum())
    if duplicate_count:
        warnings.append(f"Found {duplicate_count:,} duplicate rows.")

    invalid_numeric = {}
    for column in NUMERIC:
        converted = pd.to_numeric(data[column], errors="coerce")
        count = int(converted.isna().sum())
        if count:
            invalid_numeric[column] = count
        if converted.isna().all():
            errors.append(f"Column {column} contains no valid numeric values.")
        if column in {"previous_sales", "stock_quantity", "price", "customer_order_quantity",
                      "previous_production_quantity", "target_demand"}:
            negative = int((converted < 0).sum())
            if negative:
                warnings.append(f"Column {column} contains {negative:,} negative values.")
    if invalid_numeric:
        warnings.append("Blank or invalid numeric values: " + ", ".join(
            f"{column} ({count:,})" for column, count in invalid_numeric.items()))
    target = pd.to_numeric(data["target_demand"], errors="coerce")
    if target.isna().any():
        errors.append("target_demand cannot contain blank or non-numeric values.")

    parsed_month = pd.to_datetime(data["forecast_month"], format="%Y-%m", errors="coerce")
    invalid_dates = int(parsed_month.isna().sum())
    if invalid_dates:
        errors.append(f"forecast_month contains {invalid_dates:,} invalid values; use YYYY-MM.")
    month_number = pd.to_numeric(data["month"], errors="coerce")
    invalid_months = int((~month_number.between(1, 12) & month_number.notna()).sum())
    if invalid_months:
        errors.append(f"month contains {invalid_months:,} values outside 1–12.")

    blank_categories = int(data[["product_type", "season"]].isna().any(axis=1).sum())
    if blank_categories:
        errors.append(f"Found {blank_categories:,} rows with a blank product_type or season.")
    return {
        "valid": not errors, "errors": errors, "warnings": warnings,
        "summary": {"rows": len(data), "columns": len(data.columns),
                    "products": int(data["product_type"].nunique(dropna=True)),
                    "duplicates": duplicate_count, "invalid_numeric": sum(invalid_numeric.values())},
        "columns": list(data.columns), "preview": clean_records(data.head(8)),
    }


def analyze(df: pd.DataFrame) -> dict:
    validation = validate_dataset(df)
    if not validation["valid"]:
        raise ValueError(" ".join(validation["errors"]))
    df = df[REQUIRED].copy()
    for column in NUMERIC:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    invalid = [column for column in NUMERIC if df[column].isna().all()]
    if invalid:
        raise ValueError("These columns contain no valid numeric values: " + ", ".join(invalid))
    if df["target_demand"].isna().any():
        raise ValueError("target_demand cannot contain blank or non-numeric values.")
    df["forecast_month"] = df["forecast_month"].astype(str)
    df = df.sort_values(["forecast_month", "product_type"]).reset_index(drop=True)

    split = max(1, int(len(df) * .8))
    if split >= len(df): split = len(df) - 1
    train, test = df.iloc[:split], df.iloc[split:]
    models = {
        "Linear Regression": LinearRegression(),
        "Decision Tree": DecisionTreeRegressor(max_depth=5, min_samples_leaf=4, random_state=RANDOM_STATE),
        "Random Forest": RandomForestRegressor(n_estimators=250, max_depth=8, min_samples_leaf=2,
                                                random_state=RANDOM_STATE, n_jobs=1),
    }
    fitted, scores = {}, []
    for name, estimator in models.items():
        pipeline = make_pipeline(estimator).fit(train[FEATURES], train["target_demand"])
        prediction = pipeline.predict(test[FEATURES])
        fitted[name] = (pipeline, prediction)
        scores.append({"model": name,
                       "mae": round(float(mean_absolute_error(test["target_demand"], prediction)), 4),
                       "rmse": round(float(mean_squared_error(test["target_demand"], prediction) ** .5), 4),
                       "r2": round(float(r2_score(test["target_demand"], prediction)), 4) if len(test) > 1 else None})
    scores.sort(key=lambda item: item["rmse"])
    best_name = scores[0]["model"]
    best_model, best_prediction = fitted[best_name]

    predictions = test[["forecast_month", "product_type", "target_demand"]].copy()
    predictions.columns = ["forecast_month", "product_type", "actual_demand"]
    predictions["predicted_demand"] = np.round(best_prediction, 2)
    predictions["absolute_error"] = np.round(np.abs(predictions["actual_demand"] - best_prediction), 2)

    perm = permutation_importance(best_model, test[FEATURES], test["target_demand"],
                                  scoring="neg_mean_absolute_error", n_repeats=10,
                                  random_state=RANDOM_STATE, n_jobs=1)
    importance = sorted(
        ({"feature": feature, "importance": round(float(value), 4)}
         for feature, value in zip(FEATURES, perm.importances_mean)),
        key=lambda item: item["importance"], reverse=True,
    )

    # Use the latest imported row for each product as an illustrative next planning input.
    latest = df.groupby("product_type", as_index=False).tail(1).copy()
    latest["predicted_demand"] = np.maximum(0, np.rint(best_model.predict(latest[FEATURES]))).astype(int)
    latest["safety_stock"] = np.rint(latest["predicted_demand"] * .10).astype(int)
    latest["recommended_production"] = np.maximum(
        0, latest["predicted_demand"] + latest["safety_stock"] - latest["stock_quantity"].fillna(0)
    ).astype(int)
    recommendations = latest[["product_type", "predicted_demand", "stock_quantity",
                              "safety_stock", "recommended_production"]]

    return {
        "summary": {"rows": len(df), "training_rows": len(train), "test_rows": len(test),
                    "products": int(df["product_type"].nunique()), "best_model": best_name},
        "models": scores,
        "feature_importance": importance,
        "predictions": clean_records(predictions),
        "recommendations": clean_records(recommendations),
    }


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/template")
def template():
    path = ROOT / "data" / "synthetic_factory_demand_dataset.csv"
    return FileResponse(path, media_type="text/csv", filename="demand_data_template.csv")


@app.post("/api/analyze")
async def analyze_upload(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Please upload a CSV file.")
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "CSV is larger than the 10 MB upload limit.")
    try:
        frame = pd.read_csv(BytesIO(content))
        return analyze(frame)
    except (UnicodeDecodeError, pd.errors.ParserError) as exc:
        raise HTTPException(400, f"The file is not a valid CSV: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/api/validate")
async def validate_upload(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Please upload a CSV file.")
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "CSV is larger than the 10 MB upload limit.")
    try:
        return validate_dataset(pd.read_csv(BytesIO(content)))
    except (UnicodeDecodeError, pd.errors.ParserError) as exc:
        raise HTTPException(400, f"The file is not a valid CSV: {exc}") from exc
