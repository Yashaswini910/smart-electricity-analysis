import re
from datetime import datetime
from io import BytesIO

import matplotlib.pyplot as plt
import pandas as pd
import pytesseract
import streamlit as st
from PIL import Image, ImageEnhance, ImageFilter, ImageOps


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Smart Home Electricity Auditor",
    page_icon="⚡",
    layout="centered",
)

st.title("⚡ Smart Home Electricity Auditor")
st.markdown("### *Measure • Understand • Save*")
st.write(
    "Estimate household electricity consumption, analyze an actual electricity "
    "bill from a photo, identify the biggest energy consumers, and simulate "
    "practical savings."
)

st.info(
    "📌 This is an independent estimation/analysis tool. It does not replace "
    "the official bill issued by your electricity provider."
)


# ============================================================
# DATA
# ============================================================

DISCOMS = {
    "Andhra Pradesh": ["APSPDCL", "APEPDCL", "Other / Not Sure"],
    "Assam": ["APDCL", "Other / Not Sure"],
    "Bihar": ["NBPDCL", "SBPDCL", "Other / Not Sure"],
    "Chhattisgarh": ["CSPDCL", "Other / Not Sure"],
    "Delhi": [
        "BSES Rajdhani Power Limited (BRPL)",
        "BSES Yamuna Power Limited (BYPL)",
        "Tata Power Delhi Distribution Limited (TPDDL)",
        "NDMC",
        "Other / Not Sure",
    ],
    "Gujarat": ["DGVCL", "MGVCL", "PGVCL", "UGVCL", "Torrent Power", "Other / Not Sure"],
    "Haryana": ["DHBVN", "UHBVN", "Other / Not Sure"],
    "Himachal Pradesh": ["HPSEBL", "Other / Not Sure"],
    "Jharkhand": ["JBVNL", "Other / Not Sure"],
    "Karnataka": ["BESCOM", "HESCOM", "GESCOM", "MESCOM", "CESCOM", "Other / Not Sure"],
    "Kerala": ["KSEB", "Other / Not Sure"],
    "Madhya Pradesh": ["MPPKVVCL", "MPEZ", "MPMKVVCL", "Other / Not Sure"],
    "Maharashtra": ["MSEDCL", "BEST", "Adani Electricity", "Tata Power", "Other / Not Sure"],
    "Odisha": ["TPCODL", "TPNODL", "TPWODL", "TPSODL", "Other / Not Sure"],
    "Punjab": ["PSPCL", "Other / Not Sure"],
    "Rajasthan": ["JVVNL", "AVVNL", "JDVVNL", "Other / Not Sure"],
    "Tamil Nadu": ["TNPDCL / TANGEDCO", "Other / Not Sure"],
    "Telangana": ["TGSPDCL", "TGNPDCL", "Other / Not Sure"],
    "Uttar Pradesh": ["PVVNL", "MVVNL", "DVVNL", "PuVVNL", "KESCO", "Other / Not Sure"],
    "Uttarakhand": ["UPCL", "Other / Not Sure"],
    "West Bengal": ["WBSEDCL", "CESC", "Other / Not Sure"],
    "Goa": ["Electricity Department, Goa", "Other / Not Sure"],
    "Other State / Union Territory": ["Other / Not Sure"],
}

COMMON_APPLIANCES = [
    {"Appliance": "❄️ Air Conditioner", "Quantity": 1, "Wattage (W)": 1500, "Hours/day": 4.0},
    {"Appliance": "🧊 Refrigerator", "Quantity": 1, "Wattage (W)": 150, "Hours/day": 10.0},
    {"Appliance": "📺 Television", "Quantity": 1, "Wattage (W)": 150, "Hours/day": 3.0},
    {"Appliance": "💡 LED Bulb", "Quantity": 6, "Wattage (W)": 9, "Hours/day": 6.0},
    {"Appliance": "🌀 Ceiling Fan", "Quantity": 4, "Wattage (W)": 75, "Hours/day": 8.0},
    {"Appliance": "🚿 Geyser", "Quantity": 1, "Wattage (W)": 2000, "Hours/day": 0.5},
    {"Appliance": "🧺 Washing Machine", "Quantity": 1, "Wattage (W)": 500, "Hours/day": 0.5},
    {"Appliance": "💻 Laptop", "Quantity": 1, "Wattage (W)": 65, "Hours/day": 5.0},
    {"Appliance": "🚰 Water Pump", "Quantity": 1, "Wattage (W)": 750, "Hours/day": 0.5},
    {"Appliance": "🍳 Induction Stove", "Quantity": 1, "Wattage (W)": 1800, "Hours/day": 0.5},
    {"Appliance": "🍲 Microwave", "Quantity": 1, "Wattage (W)": 1200, "Hours/day": 0.3},
]

STANDBY_WATTS = {
    "TV": 1.0,
    "Set-top Box": 5.0,
    "Laptop Charger": 1.0,
    "Desktop Computer": 3.0,
    "Gaming Console": 2.0,
    "Microwave": 3.0,
    "Wi-Fi Router": 8.0,
    "Printer": 2.0,
}


# ============================================================
# BILL OCR HELPERS
# ============================================================

def preprocess_bill_image(image: Image.Image) -> Image.Image:
    """Prepare a bill photo for OCR."""
    img = image.convert("L")
    img = ImageOps.autocontrast(img)
    img = img.resize((img.width * 2, img.height * 2))
    img = ImageEnhance.Contrast(img).enhance(1.8)
    img = ImageEnhance.Sharpness(img).enhance(1.5)
    img = img.filter(ImageFilter.SHARPEN)
    return img


def ocr_bill(image: Image.Image) -> tuple[str, float]:
    """
    OCR with confidence estimate.
    Returns (text, mean confidence).
    """
    processed = preprocess_bill_image(image)

    data = pytesseract.image_to_data(
        processed,
        config="--psm 6",
        output_type=pytesseract.Output.DICT,
    )

    words = []
    confidences = []

    for text, conf in zip(data["text"], data["conf"]):
        text = text.strip()
        try:
            conf_value = float(conf)
        except (ValueError, TypeError):
            conf_value = -1

        if text:
            words.append(text)

        if conf_value >= 0:
            confidences.append(conf_value)

    extracted_text = " ".join(words)
    mean_conf = sum(confidences) / len(confidences) if confidences else 0.0

    return extracted_text, mean_conf


def clean_number(value: str):
    """Convert OCR number text such as 1,234.50 into float."""
    if not value:
        return None

    value = value.replace(",", "").replace("₹", "").replace("Rs.", "").replace("Rs", "")
    match = re.search(r"\d+(?:\.\d+)?", value)

    if not match:
        return None

    try:
        return float(match.group())
    except ValueError:
        return None


def extract_first_number_after(text: str, patterns: list[str]):
    """Find a number appearing near one of the supplied labels."""
    for pattern in patterns:
        match = re.search(
            pattern + r".{0,100}?(\d[\d,]*(?:\.\d+)?)",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if match:
            return clean_number(match.group(1))
    return None


def extract_units(text: str):
    patterns = [
        r"(?:units?\s*consumed)",
        r"(?:consumption)",
        r"(?:energy\s*consumption)",
        r"(?:kwh)",
        r"(?:units)",
    ]
    return extract_first_number_after(text, patterns)


def extract_bill_amount(text: str):
    patterns = [
        r"(?:net\s*amount\s*payable)",
        r"(?:amount\s*payable)",
        r"(?:total\s*amount)",
        r"(?:bill\s*amount)",
        r"(?:grand\s*total)",
        r"(?:total\s*bill)",
    ]
    return extract_first_number_after(text, patterns)


def extract_energy_charge(text: str):
    patterns = [
        r"(?:energy\s*charges?)",
        r"(?:energy\s*charge)",
        r"(?:units?\s*charges?)",
    ]
    return extract_first_number_after(text, patterns)


def extract_fixed_charge(text: str):
    patterns = [
        r"(?:fixed\s*charges?)",
        r"(?:customer\s*charges?)",
        r"(?:service\s*charges?)",
    ]
    return extract_first_number_after(text, patterns)


def extract_duty(text: str):
    patterns = [
        r"(?:electricity\s*duty)",
        r"(?:electricity\s*tax)",
        r"(?:duty\s*/?\s*tax)",
        r"(?:tax)",
        r"(?:duty)",
    ]
    return extract_first_number_after(text, patterns)


def extract_meter_readings(text: str):
    previous = extract_first_number_after(
        text,
        [
            r"(?:previous\s*reading)",
            r"(?:prev\.?\s*reading)",
            r"(?:previous\s*meter)",
            r"(?:old\s*reading)",
        ],
    )

    current = extract_first_number_after(
        text,
        [
            r"(?:current\s*reading)",
            r"(?:present\s*reading)",
            r"(?:current\s*meter)",
            r"(?:new\s*reading)",
        ],
    )

    return previous, current


def extract_due_date(text: str):
    patterns = [
        r"(?:due\s*date)\s*[:\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"(?:pay\s*by)\s*[:\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1)

    return None


def parse_bill(image: Image.Image):
    text, confidence = ocr_bill(image)

    previous, current = extract_meter_readings(text)

    return {
        "ocr_text": text,
        "ocr_confidence": confidence,
        "units": extract_units(text),
        "bill_amount": extract_bill_amount(text),
        "energy_charge": extract_energy_charge(text),
        "fixed_charge": extract_fixed_charge(text),
        "duty": extract_duty(text),
        "previous_reading": previous,
        "current_reading": current,
        "due_date": extract_due_date(text),
    }


# ============================================================
# APPLIANCE CALCULATION
# ============================================================

def calculate_appliance_units(df: pd.DataFrame) -> pd.DataFrame:
    results = []

    for _, row in df.iterrows():
        appliance = str(row["Appliance"]).strip()

        if not appliance or appliance.lower() == "nan":
            continue

        quantity = max(0.0, float(row["Quantity"]))
        wattage = max(0.0, float(row["Wattage (W)"]))
        hours = min(24.0, max(0.0, float(row["Hours/day"])))

        monthly_units = quantity * wattage * hours * 30 / 1000

        results.append(
            {
                "Appliance": appliance,
                "Quantity": quantity,
                "Wattage (W)": wattage,
                "Hours/day": hours,
                "Monthly Units (kWh)": monthly_units,
            }
        )

    return pd.DataFrame(results)


def safe_float(value, default=0.0):
    try:
        if value is None or pd.isna(value):
            return default
        return float(value)
    except (ValueError, TypeError):
        return default


# ============================================================
# SMART INSIGHT ENGINE
# ============================================================

def generate_smart_insights(
    appliance_df: pd.DataFrame,
    estimated_units: float,
    bill_units: float | None,
    bill_amount: float | None,
    energy_rate: float,
    fixed_charge: float,
    duty: float,
):
    insights = []

    if not appliance_df.empty and estimated_units > 0:
        top = appliance_df.sort_values(
            "Monthly Units (kWh)", ascending=False
        ).iloc[0]

        top_share = 100 * top["Monthly Units (kWh)"] / estimated_units

        insights.append(
            f"Your largest estimated energy consumer is **{top['Appliance']}**, "
            f"at about **{top['Monthly Units (kWh)']:.1f} kWh/month** "
            f"({top_share:.1f}% of the appliance estimate)."
        )

        if top["Hours/day"] >= 8:
            insights.append(
                f"**{top['Appliance']}** runs for around {top['Hours/day']:.1f} "
                "hours/day in your input. Reducing unnecessary runtime is "
                "likely to have a larger impact than reducing low-power loads."
            )

    if bill_units is not None and bill_units > 0 and estimated_units > 0:
        difference_pct = 100 * (estimated_units - bill_units) / bill_units

        if abs(difference_pct) <= 15:
            insights.append(
                f"Your appliance estimate ({estimated_units:.1f} kWh) is within "
                f"about 15% of the bill's reported consumption ({bill_units:.1f} kWh). "
                "That is a reasonably close match for a usage-based estimate."
            )
        elif estimated_units > bill_units:
            insights.append(
                f"Your appliance estimate ({estimated_units:.1f} kWh) is about "
                f"{abs(difference_pct):.1f}% higher than the bill's reported "
                f"{bill_units:.1f} kWh. Check appliance wattages, hours, and "
                "whether some appliances are intermittent rather than continuously "
                "drawing their rated wattage."
            )
        else:
            insights.append(
                f"Your appliance estimate ({estimated_units:.1f} kWh) is about "
                f"{abs(difference_pct):.1f}% lower than the bill's reported "
                f"{bill_units:.1f} kWh. This may indicate missing appliances, "
                "higher actual runtime, or loads such as pumps, geysers, chargers, "
                "or other equipment not included in the estimate."
            )

    if bill_units is not None and bill_units > 0 and bill_amount is not None:
        effective_rate = bill_amount / bill_units

        insights.append(
            f"The bill's effective cost is approximately **₹{effective_rate:.2f}/kWh** "
            "(total payable divided by reported units). This is a blended figure, "
            "not necessarily the tariff energy rate, because fixed charges, duties, "
            "taxes, subsidies and other adjustments may be included."
        )

    if bill_amount is not None and fixed_charge > 0:
        fixed_share = 100 * fixed_charge / bill_amount
        if 0 < fixed_share < 100:
            insights.append(
                f"The fixed charge you entered is about **{fixed_share:.1f}%** of "
                "the bill amount you entered. Reducing units will not remove "
                "a fixed charge that is independent of consumption."
            )

    if bill_units is not None and bill_units > 300:
        insights.append(
            "Your bill reports more than 300 units for this billing period. "
            "Check the tariff slab/category printed on the bill before assuming "
            "that a particular nationwide slab or tax rate applies."
        )

    return insights


# ============================================================
# CONNECTION / TARIFF INPUT
# ============================================================

st.write("---")
st.header("🇮🇳 1. Your Electricity Connection")

states = list(DISCOMS.keys())

state = st.selectbox(
    "State / Union Territory",
    states,
    index=states.index("Telangana"),
)

discom = st.selectbox(
    "DISCOM / Electricity Provider",
    DISCOMS[state],
)

consumer_category = st.selectbox(
    "Consumer category",
    [
        "Domestic / Residential",
        "Other / I don't know",
    ],
)

st.caption(
    "The DISCOM and consumer category are recorded so the app can interpret "
    "the bill correctly. Actual tariff rules are utility- and category-specific."
)


# ============================================================
# BILL UPLOAD + OCR
# ============================================================

st.write("---")
st.header("📷 2. Upload Your Electricity Bill")

st.write(
    "Upload a clear photo of the bill. The app uses OCR to extract visible "
    "values such as units, bill amount, energy charges, fixed charges, duty/tax, "
    "meter readings and due date."
)

uploaded_bills = st.file_uploader(
    "Upload electricity bill photo(s)",
    type=["jpg", "jpeg", "png", "webp"],
    accept_multiple_files=True,
)

bill_records = []

if uploaded_bills:
    for file in uploaded_bills:
        try:
            image = Image.open(file).convert("RGB")
            parsed = parse_bill(image)
            parsed["filename"] = file.name
            parsed["image"] = image
            bill_records.append(parsed)
        except Exception as exc:
            st.error(f"Could not process {file.name}: {exc}")

if bill_records:
    st.success(f"Processed {len(bill_records)} bill image(s).")

    for i, record in enumerate(bill_records, start=1):
        with st.expander(f"Bill {i}: {record['filename']}", expanded=(i == 1)):
            st.image(record["image"], caption=record["filename"], use_container_width=True)

            confidence = record["ocr_confidence"]

            if confidence >= 75:
                st.success(f"OCR confidence: {confidence:.0f}%")
            elif confidence >= 50:
                st.warning(
                    f"OCR confidence: {confidence:.0f}%. Check extracted values below."
                )
            else:
                st.error(
                    f"OCR confidence: {confidence:.0f}%. The photo may be unclear. "
                    "Use the manual correction fields."
                )

            st.text_area(
                "OCR text",
                record["ocr_text"],
                height=150,
                key=f"ocr_{i}",
            )

    # Use first uploaded bill as the current bill.
    current_bill = bill_records[0]

else:
    current_bill = None


# ============================================================
# MANUAL BILL VALUE CONFIRMATION
# ============================================================

st.subheader("🧾 Confirm / Correct Bill Values")

st.write(
    "OCR is not guaranteed to read every bill correctly. The fields below are "
    "editable, so the user can correct them using the printed bill."
)

ocr_units = safe_float(current_bill["units"], 0) if current_bill else 0
ocr_amount = safe_float(current_bill["bill_amount"], 0) if current_bill else 0
ocr_energy = safe_float(current_bill["energy_charge"], 0) if current_bill else 0
ocr_fixed = safe_float(current_bill["fixed_charge"], 0) if current_bill else 0
ocr_duty = safe_float(current_bill["duty"], 0) if current_bill else 0

b1, b2 = st.columns(2)

with b1:
    bill_units = st.number_input(
        "Units shown on bill (kWh)",
        min_value=0.0,
        value=ocr_units,
        step=1.0,
        help="Check the Units Consumed / kWh / Consumption field on the bill.",
    )

    bill_amount = st.number_input(
        "Total / Net bill amount (₹)",
        min_value=0.0,
        value=ocr_amount,
        step=1.0,
    )

with b2:
    bill_energy_charge = st.number_input(
        "Energy charge from bill (₹)",
        min_value=0.0,
        value=ocr_energy,
        step=1.0,
    )

    bill_fixed_charge = st.number_input(
        "Fixed charge from bill (₹)",
        min_value=0.0,
        value=ocr_fixed,
        step=1.0,
    )

bill_duty = st.number_input(
    "Electricity duty / tax from bill (₹)",
    min_value=0.0,
    value=ocr_duty,
    step=0.1,
)

if current_bill and current_bill["due_date"]:
    st.caption(f"📅 OCR-detected due date: {current_bill['due_date']}")


# ============================================================
# ENERGY RATE
# ============================================================

st.write("---")
st.header("💰 3. Tariff / Cost Inputs")

if bill_units > 0 and bill_energy_charge > 0:
    bill_effective_energy_rate = bill_energy_charge / bill_units
else:
    bill_effective_energy_rate = 6.50

energy_rate = st.number_input(
    "Energy rate used for appliance-cost estimation (₹/kWh)",
    min_value=0.0,
    max_value=100.0,
    value=float(round(bill_effective_energy_rate, 2)),
    step=0.10,
    help=(
        "If the bill contains an Energy Charges amount and Units, the app "
        "suggests Energy Charges / Units. You can change it."
    ),
)

st.caption(
    "This is an appliance-cost estimation rate. It is different from the "
    "bill's blended effective cost, which can include fixed charges, duty/tax, "
    "subsidies and other adjustments."
)


# ============================================================
# APPLIANCE INPUTS
# ============================================================

st.write("---")
st.header("🔌 4. Household Appliance Usage")

st.write(
    "Adjust common appliances and add any additional appliances. Use the rated "
    "wattage from the appliance label where possible."
)

common_df = pd.DataFrame(COMMON_APPLIANCES)

common_df = st.data_editor(
    common_df,
    use_container_width=True,
    hide_index=True,
    num_rows="fixed",
    column_config={
        "Appliance": st.column_config.TextColumn("Appliance", disabled=True),
        "Quantity": st.column_config.NumberColumn(
            "Quantity", min_value=0, max_value=100, step=1
        ),
        "Wattage (W)": st.column_config.NumberColumn(
            "Wattage (W)", min_value=0, max_value=50000, step=1
        ),
        "Hours/day": st.column_config.NumberColumn(
            "Hours/day", min_value=0.0, max_value=24.0, step=0.5
        ),
    },
    key="common_appliances",
)

st.subheader("➕ Extra Appliances")

custom_default = pd.DataFrame(
    [
        {
            "Appliance": "",
            "Quantity": 1,
            "Wattage (W)": 100,
            "Hours/day": 1.0,
        }
    ]
)

custom_df = st.data_editor(
    custom_default,
    use_container_width=True,
    hide_index=True,
    num_rows="dynamic",
    column_config={
        "Appliance": st.column_config.TextColumn("Appliance Name"),
        "Quantity": st.column_config.NumberColumn(
            "Quantity", min_value=0, max_value=100, step=1
        ),
        "Wattage (W)": st.column_config.NumberColumn(
            "Wattage (W)", min_value=0, max_value=50000, step=1
        ),
        "Hours/day": st.column_config.NumberColumn(
            "Hours/day", min_value=0.0, max_value=24.0, step=0.5
        ),
    },
    key="custom_appliances",
)

common_results = calculate_appliance_units(common_df)
custom_results = calculate_appliance_units(custom_df)

all_results = pd.concat(
    [common_results, custom_results],
    ignore_index=True,
)

if not all_results.empty:
    all_results["Estimated Cost (₹)"] = (
        all_results["Monthly Units (kWh)"] * energy_rate
    )

total_monthly_units = (
    all_results["Monthly Units (kWh)"].sum()
    if not all_results.empty
    else 0.0
)

estimated_energy_cost = total_monthly_units * energy_rate


# ============================================================
# SMART BILL ANALYSIS
# ============================================================

st.write("---")
st.header("🧠 5. Smart Electricity Analysis")

if bill_units > 0:
    bill_days = st.number_input(
        "Billing period (days), if known",
        min_value=1,
        max_value=100,
        value=30,
        step=1,
    )

    daily_bill_units = bill_units / bill_days
    monthly_30day_bill_units = daily_bill_units * 30
else:
    bill_days = 30
    daily_bill_units = 0.0
    monthly_30day_bill_units = 0.0

m1, m2, m3 = st.columns(3)

m1.metric(
    "Appliance Estimate",
    f"{total_monthly_units:.1f} kWh/month",
)

m2.metric(
    "Bill Consumption",
    f"{bill_units:.1f} kWh",
)

if bill_units > 0:
    m3.metric(
        "Bill Effective Cost",
        f"₹{bill_amount / bill_units:.2f}/kWh" if bill_amount > 0 else "—",
    )
else:
    m3.metric("Bill Effective Cost", "Upload/enter bill data")


# ============================================================
# BILL VS APPLIANCE COMPARISON
# ============================================================

if bill_units > 0 and total_monthly_units > 0:
    difference = total_monthly_units - monthly_30day_bill_units
    difference_pct = 100 * difference / monthly_30day_bill_units

    st.subheader("🔍 Actual Bill vs Appliance Model")

    comparison = pd.DataFrame(
        {
            "Measure": [
                "Bill consumption (30-day equivalent)",
                "Appliance-based estimate",
                "Difference",
            ],
            "kWh": [
                monthly_30day_bill_units,
                total_monthly_units,
                difference,
            ],
        }
    )

    st.dataframe(
        comparison.style.format({"kWh": "{:.1f}"}),
        use_container_width=True,
        hide_index=True,
    )

    if abs(difference_pct) <= 15:
        st.success(
            f"Close match: the appliance estimate differs from the bill by "
            f"{abs(difference_pct):.1f}%."
        )
    elif difference > 0:
        st.warning(
            f"The appliance model is {abs(difference_pct):.1f}% higher than the "
            "30-day-equivalent bill consumption. Check wattages and runtime."
        )
    else:
        st.warning(
            f"The appliance model is {abs(difference_pct):.1f}% lower than the "
            "30-day-equivalent bill consumption. Look for missing or underestimated "
            "loads such as pumps, geysers, chargers, coolers, EV charging or other equipment."
        )


# ============================================================
# SMART BILL COMPONENT CHECK
# ============================================================

if bill_amount > 0:
    st.subheader("🧾 Bill Component Analysis")

    known_components = (
        bill_energy_charge
        + bill_fixed_charge
        + bill_duty
    )

    other_or_unidentified = bill_amount - known_components

    component_df = pd.DataFrame(
        {
            "Component": [
                "Energy charge",
                "Fixed charge",
                "Electricity duty / tax",
                "Other / adjustment / unrecognized",
                "Total bill",
            ],
            "Amount (₹)": [
                bill_energy_charge,
                bill_fixed_charge,
                bill_duty,
                max(0.0, other_or_unidentified),
                bill_amount,
            ],
        }
    )

    st.dataframe(
        component_df.style.format({"Amount (₹)": "₹{:,.2f}"}),
        use_container_width=True,
        hide_index=True,
    )

    if other_or_unidentified > max(50, 0.10 * bill_amount):
        st.info(
            "A noticeable part of the bill is not explained by the three fields "
            "entered above. It may contain subsidies, arrears, adjustments, rebates, "
            "fuel/power-purchase adjustments, or other utility-specific items. "
            "Check the detailed bill rather than treating this amount as tax."
        )


# ============================================================
# TOP CONSUMERS
# ============================================================

if not all_results.empty and total_monthly_units > 0:
    st.subheader("🚨 Biggest Energy Consumers")

    top = all_results.sort_values(
        "Monthly Units (kWh)",
        ascending=False,
    ).head(7)

    for _, row in top.iterrows():
        share = 100 * row["Monthly Units (kWh)"] / total_monthly_units
        st.write(
            f"**{row['Appliance']}** — "
            f"{row['Monthly Units (kWh)']:.1f} kWh/month "
            f"({share:.1f}%)"
        )

    fig, ax = plt.subplots(figsize=(8, 6))
    chart = all_results[
        all_results["Monthly Units (kWh)"] > 0
    ].sort_values(
        "Monthly Units (kWh)",
        ascending=True,
    )

    ax.barh(
        chart["Appliance"],
        chart["Monthly Units (kWh)"],
    )
    ax.set_xlabel("Monthly electricity consumption (kWh)")
    ax.set_title("Estimated Consumption by Appliance")
    st.pyplot(fig)


# ============================================================
# SAVINGS SIMULATOR
# ============================================================

st.subheader("🌱 Savings Simulator")

if not all_results.empty:
    selected_appliance = st.selectbox(
        "Choose an appliance to optimize",
        all_results["Appliance"].tolist(),
    )

    selected_row = all_results[
        all_results["Appliance"] == selected_appliance
    ].iloc[0]

    selected_reduction = st.slider(
        "Reduce its operating hours by (%)",
        min_value=0,
        max_value=80,
        value=20,
        step=5,
    )

    selected_monthly_units = selected_row["Monthly Units (kWh)"]

    saving_units = (
        selected_monthly_units
        * selected_reduction
        / 100
    )

    saving_money = saving_units * energy_rate
    annual_saving = saving_money * 12

    s1, s2, s3 = st.columns(3)

    s1.metric("Energy saved", f"{saving_units:.1f} kWh/month")
    s2.metric("Estimated saving", f"₹{saving_money:,.0f}/month")
    s3.metric("Potential annual saving", f"₹{annual_saving:,.0f}")

    st.caption(
        "Savings are estimated using the appliance-cost rate. Actual bill savings "
        "can differ because tariff slabs, fixed charges and other bill components "
        "may change with consumption."
    )


# ============================================================
# STANDBY POWER
# ============================================================

st.subheader("🔌 Standby Power Check")

standby_devices = st.multiselect(
    "Devices that may remain plugged in while not actively used",
    list(STANDBY_WATTS.keys()),
)

total_standby_watts = sum(
    STANDBY_WATTS[d] for d in standby_devices
)

standby_units = total_standby_watts * 24 * 30 / 1000
standby_cost = standby_units * energy_rate

if standby_devices:
    s1, s2 = st.columns(2)
    s1.metric("Estimated standby load", f"{total_standby_watts:.1f} W")
    s2.metric("Estimated standby energy", f"{standby_units:.2f} kWh/month")
    st.write(
        f"At the selected appliance-cost rate, that is approximately "
        f"**₹{standby_cost:.2f}/month**."
    )


# ============================================================
# SMART RECOMMENDATIONS
# ============================================================

st.subheader("💡 Smart Recommendations")

insights = generate_smart_insights(
    all_results,
    total_monthly_units,
    bill_units if bill_units > 0 else None,
    bill_amount if bill_amount > 0 else None,
    energy_rate,
    bill_fixed_charge,
    bill_duty,
)

if insights:
    for insight in insights:
        st.info("💡 " + insight)
else:
    st.info(
        "Enter appliance usage and/or upload a bill to generate personalized insights."
    )

if not all_results.empty:
    highest_name = (
        all_results.loc[
            all_results["Monthly Units (kWh)"].idxmax(),
            "Appliance",
        ]
    )

    if "Air Conditioner" in highest_name:
        st.warning(
            "❄️ AC optimization: check thermostat setting, room insulation, "
            "filter cleanliness and unnecessary runtime."
        )

    if "Geyser" in highest_name:
        st.warning(
            "🚿 Geyser optimization: use a timer and avoid leaving water heating "
            "on when hot water is not needed."
        )

    if "Water Pump" in highest_name:
        st.warning(
            "🚰 Pump optimization: check leaks, tank overflow and unnecessary "
            "long pump operation."
        )


# ============================================================
# OPTIONAL METER READING
# ============================================================

st.write("---")
st.header("📟 6. Compare With Your Meter")

previous_reading = st.number_input(
    "Previous meter reading (kWh)",
    min_value=0.0,
    value=0.0,
    step=1.0,
)

current_reading = st.number_input(
    "Current meter reading (kWh)",
    min_value=0.0,
    value=0.0,
    step=1.0,
)

meter_days = st.number_input(
    "Days between readings",
    min_value=1,
    max_value=1000,
    value=30,
    step=1,
)

if current_reading >= previous_reading and current_reading > 0:
    actual_meter_units = current_reading - previous_reading
    actual_daily = actual_meter_units / meter_days

    m1, m2 = st.columns(2)
    m1.metric("Meter consumption", f"{actual_meter_units:.1f} kWh")
    m2.metric("Average daily use", f"{actual_daily:.2f} kWh/day")


# ============================================================
# BILL HISTORY
# ============================================================

if len(bill_records) > 1:
    st.write("---")
    st.header("📈 Bill History Comparison")

    history_rows = []

    for record in bill_records:
        if record["units"] is not None or record["bill_amount"] is not None:
            history_rows.append(
                {
                    "Bill": record["filename"],
                    "Units (kWh)": record["units"],
                    "Bill Amount (₹)": record["bill_amount"],
                }
            )

    history_df = pd.DataFrame(history_rows)

    if not history_df.empty:
        st.dataframe(
            history_df,
            use_container_width=True,
            hide_index=True,
        )

        if history_df["Units (kWh)"].notna().sum() >= 2:
            chart_df = history_df.dropna(subset=["Units (kWh)"])

            fig, ax = plt.subplots(figsize=(8, 4))
            ax.plot(
                range(1, len(chart_df) + 1),
                chart_df["Units (kWh)"],
                marker="o",
            )
            ax.set_xlabel("Uploaded bill order")
            ax.set_ylabel("Units (kWh)")
            ax.set_title("Consumption trend")
            ax.grid(True, alpha=0.25)
            st.pyplot(fig)


# ============================================================
# IMPORTANT DISCLAIMER
# ============================================================

st.write("---")
st.header("ℹ️ Important")

st.info(
    """
**How this app becomes useful in real life**

1. The bill photo is converted into text using OCR.
2. Important bill values are extracted and can be corrected by the user.
3. Appliance usage is converted into estimated monthly kWh.
4. The app compares the appliance model with the actual bill consumption.
5. It identifies the largest estimated electricity consumers.
6. It estimates the blended cost shown by the bill.
7. It separates known energy/fixed/duty components from unexplained amounts.
8. It provides a savings simulator and practical recommendations.

**Important:** Electricity tariffs, duties, subsidies, fixed charges and other
billing components vary by state, DISCOM, consumer category and applicable tariff
order. The app therefore does not claim that one nationwide tax or tariff applies
to every household. Use the actual bill and the current tariff order for official
billing information.
"""
)

st.caption(
    "OCR quality depends on image quality, lighting, bill layout and print clarity. "
    "For official payment information, always rely on the electricity provider's bill."
)
