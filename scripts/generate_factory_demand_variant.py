"""Generate a factory-demand variant compatible with the web CSV importer."""
from __future__ import annotations

import csv
import argparse
import math
import random
from datetime import date
from pathlib import Path


OUTPUT = Path(__file__).resolve().parents[1] / "data" / "synthetic_factory_demand_variant.csv"
PRODUCTS = {
    "Standard Pump": (7800, 18.50),
    "Industrial Valve": (5250, 32.00),
    "Control Sensor": (9600, 12.00),
    "Drive Motor": (3600, 74.00),
}
FIELDS = [
    "forecast_month", "product_type", "month", "season", "previous_sales",
    "stock_quantity", "price", "promotion", "customer_order_quantity",
    "previous_production_quantity", "target_demand",
]


def season_for(month: int) -> str:
    if month <= 3:
        return "Dry-Q1"
    if month <= 6:
        return "Hot-Q2"
    if month <= 9:
        return "Wet-Q3"
    return "Cool-Q4"


def generate(row_count: int, output: Path, seed: int) -> None:
    if row_count < 1:
        raise ValueError("--rows must be at least 1")
    random.seed(seed)
    output.parent.mkdir(parents=True, exist_ok=True)
    previous = {
        product: {"sales": round(base * 0.96), "production": round(base * 1.02)}
        for product, (base, _) in PRODUCTS.items()
    }

    products = list(PRODUCTS.items())
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()

        # Stream rows rather than building a list, allowing very large datasets.
        # Multiple observations per product/month represent separate demand samples.
        for row_index in range(row_count):
            product, (base, unit_price) = products[row_index % len(products)]
            observation_index = row_index // len(products)
            month_index = observation_index % 60
            year = 2021 + month_index // 12
            month = month_index % 12 + 1
            current = date(year, month, 1)
            annual = 1 + 0.16 * math.sin(2 * math.pi * (month - 2) / 12)
            growth = 1 + 0.0045 * month_index
            promotion = int(month in (4, 9) and product in ("Standard Pump", "Control Sensor"))
            promo_factor = 1.22 if promotion else 1.0
            target = max(0, round(base * annual * growth * promo_factor * random.gauss(1.0, 0.06)))
            orders = max(0, round(target * random.uniform(0.72, 0.91)))
            stock = max(0, round(target * random.uniform(0.14, 0.34)))
            production = max(0, round(target * random.uniform(0.96, 1.08)))
            price = unit_price * random.uniform(0.97, 1.04)

            writer.writerow({
                "forecast_month": current.strftime("%Y-%m"),
                "product_type": product,
                "month": month,
                "season": season_for(month),
                "previous_sales": previous[product]["sales"],
                "stock_quantity": stock,
                "price": f"{price:.2f}",
                "promotion": promotion,
                "customer_order_quantity": orders,
                "previous_production_quantity": previous[product]["production"],
                "target_demand": target,
            })
            previous[product] = {"sales": target, "production": production}

    print(f"Generated {row_count:,} web-compatible rows: {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=240, help="number of rows to generate (default: 240)")
    parser.add_argument("--output", type=Path, default=OUTPUT, help=f"output CSV (default: {OUTPUT})")
    parser.add_argument("--seed", type=int, default=20260813, help="random seed")
    args = parser.parse_args()
    generate(args.rows, args.output.resolve(), args.seed)


if __name__ == "__main__":
    main()
