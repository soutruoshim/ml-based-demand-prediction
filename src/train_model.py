#!/usr/bin/env python3
"""Reproducible demand-prediction workflow for the final ML project."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".cache" / "matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(ROOT / ".cache"))

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeRegressor

DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "outputs"
FIG_DIR = OUT_DIR / "figures"
RANDOM_STATE = 16

PRODUCTS = {
    "Body Wash": {"base": 1070, "price": 3.85, "stock": 260},
    "Laundry Detergent": {"base": 1660, "price": 6.20, "stock": 410},
    "Shampoo": {"base": 1320, "price": 4.55, "stock": 340},
}


def season(month: int) -> str:
    return ("Dry-Q1" if month <= 3 else "Hot-Q2" if month <= 6 else
            "Wet-Q3" if month <= 9 else "Peak-Q4")


def generate_data(path: Path) -> pd.DataFrame:
    """Generate 59 forecast months x 3 products using a fixed seed."""
    rng = np.random.default_rng(RANDOM_STATE)
    dates = pd.date_range("2021-02-01", "2025-12-01", freq="MS")
    previous = {"Body Wash": 1058, "Laundry Detergent": 1664, "Shampoo": 1275}
    rows = []
    seasonal = {1: 80, 2: 65, 3: 35, 4: 15, 5: -10, 6: -35,
                7: -60, 8: -50, 9: -15, 10: 35, 11: 85, 12: 125}
    for t, dt in enumerate(dates):
        for product, cfg in PRODUCTS.items():
            promo = int(rng.random() < 0.28)
            price = cfg["price"] + rng.normal(0, .11) + (0.03 * (t / 12))
            stock = max(40, round(cfg["stock"] + rng.normal(0, 65)))
            orders = round(cfg["base"] * .69 + seasonal[dt.month] * .35 +
                           promo * 115 + rng.normal(0, 75))
            prev_prod = max(0, round(previous[product] + rng.normal(15, 90)))
            demand = round(
                0.52 * previous[product] + 0.35 * orders +
                0.22 * cfg["base"] + seasonal[dt.month] + 125 * promo -
                90 * (price - cfg["price"]) + 2.3 * t + rng.normal(0, 67)
            )
            rows.append({
                "forecast_month": dt.strftime("%Y-%m"), "product_type": product,
                "month": dt.month, "season": season(dt.month),
                "previous_sales": previous[product], "stock_quantity": stock,
                "price": round(price, 2), "promotion": promo,
                "customer_order_quantity": orders,
                "previous_production_quantity": prev_prod,
                "target_demand": max(0, demand),
            })
            previous[product] = max(0, demand)
    df = pd.DataFrame(rows).sort_values(["forecast_month", "product_type"]).reset_index(drop=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return df


def make_pipeline(model):
    categorical = ["product_type", "season"]
    numeric = ["month", "previous_sales", "stock_quantity", "price", "promotion",
               "customer_order_quantity", "previous_production_quantity"]
    preprocessing = ColumnTransformer([
        ("cat", Pipeline([("impute", SimpleImputer(strategy="most_frequent")),
                          ("encode", OneHotEncoder(handle_unknown="ignore"))]), categorical),
        ("num", Pipeline([("impute", SimpleImputer(strategy="median")),
                          ("scale", StandardScaler())]), numeric),
    ])
    return Pipeline([("preprocessing", preprocessing), ("model", model)])


def save_plots(evaluation, test_results, importance):
    plt.style.use("seaborn-v0_8-whitegrid")
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(8, 4.8))
    order = evaluation.sort_values("RMSE")
    bars = ax.bar(order["Model"], order["RMSE"], color=["#176B87", "#64CCC5", "#DA7F8F"])
    ax.bar_label(bars, fmt="%.1f"); ax.set_ylabel("RMSE (units)"); ax.set_title("Model RMSE Comparison")
    fig.tight_layout(); fig.savefig(FIG_DIR / "model_rmse.png", dpi=180); plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.8, 5.5))
    ax.scatter(test_results["actual_demand"], test_results["predicted_demand"], alpha=.75, color="#176B87")
    lo = min(test_results["actual_demand"].min(), test_results["predicted_demand"].min())
    hi = max(test_results["actual_demand"].max(), test_results["predicted_demand"].max())
    ax.plot([lo, hi], [lo, hi], "--", color="#D1495B", label="Ideal prediction")
    ax.set(xlabel="Actual demand (units)", ylabel="Predicted demand (units)", title="Actual vs. Predicted Demand")
    ax.legend(); fig.tight_layout(); fig.savefig(FIG_DIR / "actual_vs_predicted.png", dpi=180); plt.close(fig)

    fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
    for ax, (product, group) in zip(axes, test_results.groupby("product_type")):
        group = group.sort_values("forecast_month")
        ax.plot(group["forecast_month"], group["actual_demand"], marker="o", label="Actual")
        ax.plot(group["forecast_month"], group["predicted_demand"], marker="s", label="Predicted")
        ax.set_title(product); ax.set_ylabel("Units"); ax.tick_params(axis="x", rotation=45)
    axes[0].legend(ncol=2); fig.suptitle("Held-Out Demand Trends by Product")
    fig.tight_layout(); fig.savefig(FIG_DIR / "demand_trends.png", dpi=180); plt.close(fig)

    top = importance.head(10).sort_values("Permutation importance")
    fig, ax = plt.subplots(figsize=(8, 5.2))
    ax.barh(top["Feature"], top["Permutation importance"], color="#64CCC5")
    ax.set(xlabel="Increase in MAE after permutation (units)", title="Feature Importance")
    fig.tight_layout(); fig.savefig(FIG_DIR / "feature_importance.png", dpi=180); plt.close(fig)


def production_scenario(best_model) -> pd.DataFrame:
    rows = pd.DataFrame([
        {"forecast_month":"2026-01", "product_type":"Shampoo", "month":1, "season":"Dry-Q1", "previous_sales":1425, "stock_quantity":353, "price":4.66, "promotion":1, "customer_order_quantity":1100, "previous_production_quantity":1470},
        {"forecast_month":"2026-01", "product_type":"Body Wash", "month":1, "season":"Dry-Q1", "previous_sales":1080, "stock_quantity":101, "price":3.96, "promotion":0, "customer_order_quantity":800, "previous_production_quantity":1110},
        {"forecast_month":"2026-01", "product_type":"Laundry Detergent", "month":1, "season":"Dry-Q1", "previous_sales":1700, "stock_quantity":391, "price":6.35, "promotion":0, "customer_order_quantity":1200, "previous_production_quantity":1760},
    ])
    rows["predicted_demand"] = np.rint(best_model.predict(rows)).astype(int)
    rows["safety_stock_10_percent"] = np.rint(rows["predicted_demand"] * .10).astype(int)
    rows["recommended_production"] = np.maximum(0, rows["predicted_demand"] + rows["safety_stock_10_percent"] - rows["stock_quantity"])
    return rows[["product_type", "predicted_demand", "stock_quantity", "safety_stock_10_percent", "recommended_production"]]


def run(data_path: Path | None = None):
    DATA_DIR.mkdir(exist_ok=True); OUT_DIR.mkdir(exist_ok=True)
    if data_path is None:
        data_path = DATA_DIR / "synthetic_factory_demand_dataset.csv"
        df = generate_data(data_path)
    else:
        df = pd.read_csv(data_path)
    df = df.sort_values(["forecast_month", "product_type"]).reset_index(drop=True)
    features = ["product_type", "month", "season", "previous_sales", "stock_quantity", "price",
                "promotion", "customer_order_quantity", "previous_production_quantity"]
    missing = set(features + ["forecast_month", "target_demand"]) - set(df.columns)
    if missing: raise ValueError(f"Missing required columns: {sorted(missing)}")

    split = int(len(df) * .80)
    # Keep complete months together: 47 of 59 months = 141 training records.
    split -= split % len(PRODUCTS)
    train, test = df.iloc[:split], df.iloc[split:]
    models = {
        "Linear Regression": LinearRegression(),
        "Decision Tree": DecisionTreeRegressor(max_depth=5, min_samples_leaf=4, random_state=RANDOM_STATE),
        "Random Forest": RandomForestRegressor(n_estimators=400, max_depth=8, min_samples_leaf=2, random_state=RANDOM_STATE, n_jobs=1),
    }
    fitted, records = {}, []
    for name, estimator in models.items():
        pipe = make_pipeline(estimator).fit(train[features], train["target_demand"])
        pred = pipe.predict(test[features]); fitted[name] = (pipe, pred)
        records.append({"Model": name, "MAE": mean_absolute_error(test["target_demand"], pred),
                        "RMSE": mean_squared_error(test["target_demand"], pred) ** .5,
                        "R2": r2_score(test["target_demand"], pred)})
    evaluation = pd.DataFrame(records).sort_values("RMSE").reset_index(drop=True)
    best_name = evaluation.iloc[0]["Model"]; best_model, best_pred = fitted[best_name]
    evaluation.round(4).to_csv(OUT_DIR / "model_evaluation_results.csv", index=False)

    test_results = test[["forecast_month", "product_type", "target_demand"]].copy()
    test_results = test_results.rename(columns={"target_demand":"actual_demand"})
    test_results["predicted_demand"] = np.round(best_pred, 2)
    test_results["absolute_error"] = np.round(np.abs(test_results["actual_demand"] - best_pred), 2)
    test_results.to_csv(OUT_DIR / "test_predictions.csv", index=False)

    perm = permutation_importance(best_model, test[features], test["target_demand"], scoring="neg_mean_absolute_error", n_repeats=30, random_state=RANDOM_STATE, n_jobs=1)
    importance = pd.DataFrame({"Feature": features, "Permutation importance": perm.importances_mean,
                               "Std. deviation": perm.importances_std}).sort_values("Permutation importance", ascending=False)
    importance.round(4).to_csv(OUT_DIR / "feature_importance.csv", index=False)
    plan = production_scenario(best_model)
    plan.to_csv(OUT_DIR / "jan_2026_production_recommendation.csv", index=False)
    joblib.dump(best_model, OUT_DIR / "best_model.joblib")
    save_plots(evaluation, test_results, importance)
    metadata = {"dataset_type":"synthetic demonstration", "random_seed":RANDOM_STATE,
                "records":len(df), "training_records":len(train), "test_records":len(test),
                "best_model":best_name, "primary_metric":"RMSE"}
    (OUT_DIR / "run_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(evaluation.round(4).to_string(index=False)); print("\nProduction recommendation:\n", plan.to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, help="Authorized CSV with the documented columns; omit to regenerate synthetic data")
    run(parser.parse_args().data)
