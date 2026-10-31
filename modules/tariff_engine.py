
import json
from pathlib import Path
import pandas as pd


class TariffUnavailable(Exception):
    pass


def load_tariffs(tariff_folder):
    tariff_folder = Path(tariff_folder)
    records = {}

    if not tariff_folder.exists():
        return records

    for file_path in tariff_folder.glob("*.json"):
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                data = json.load(file)

            for record in data:
                key = (
                    record["state"],
                    record["discom"],
                    record["category"],
                )
                records[key] = record

        except (json.JSONDecodeError, KeyError, TypeError):
            continue

    return records


def get_tariff(tariffs, state, discom, category):
    tariff = tariffs.get((state, discom, category))

    if tariff is None:
        return None

    if tariff.get("verified") is not True:
        return None

    return tariff


def calculate_slab_charges(units, tariff):
    units = float(units)

    if units < 0:
        raise ValueError("Units cannot be negative.")

    maximum = tariff.get("max_units")

    if maximum is not None and units > float(maximum):
        raise TariffUnavailable(
            f"This configured tariff covers up to {maximum} units. "
            "A verified higher-consumption schedule is required."
        )

    remaining = units
    previous_limit = 0.0
    total = 0.0
    breakdown = []

    for slab in tariff["slabs"]:
        upper = slab["upper"]
        rate = float(slab["rate"])

        if upper is None:
            slab_units = remaining
            slab_label = f"Above {previous_limit:g} units"
        else:
            upper = float(upper)
            slab_units = min(
                remaining,
                max(0.0, upper - previous_limit),
            )
            slab_label = f"{previous_limit:g}–{upper:g} units"

        if slab_units > 0:
            charge = slab_units * rate
            total += charge

            breakdown.append({
                "Slab": slab_label,
                "Units": round(slab_units, 2),
                "Rate (₹/unit)": rate,
                "Charge (₹)": round(charge, 2),
            })

            remaining -= slab_units

        if upper is not None:
            previous_limit = float(upper)

        if remaining <= 0:
            break

    if remaining > 0.000001:
        raise TariffUnavailable(
            "The configured tariff does not cover this consumption."
        )

    return round(total, 2), pd.DataFrame(breakdown)


def calculate_bill(units, tariff):
    energy, slab_details = calculate_slab_charges(units, tariff)

    fixed_charge = tariff.get("fixed_charge")

    if fixed_charge is None:
        raise TariffUnavailable(
            "The fixed charge is not configured. "
            "A complete estimate cannot be calculated."
        )

    fixed_charge = float(fixed_charge)

    return {
        "energy": energy,
        "fixed": fixed_charge,
        "total": round(energy + fixed_charge, 2),
        "slabs": slab_details,
    }
