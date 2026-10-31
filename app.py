import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import date, datetime
from pathlib import Path
import re
import io

# ==========================================================
# PAGE CONFIGURATION
# ==========================================================

st.set_page_config(
    page_title="Smart Home Electricity Auditor",
    page_icon="⚡",
    layout="wide"
)

st.title("⚡ Smart Home Electricity Auditor")
st.markdown("### Calculate, Analyze, and Reduce Your Electricity Bill")
st.write(
    "Understand household electricity usage, estimate costs, "
    "compare bills and discover practical ways to reduce consumption."
)

HISTORY_FILE = Path("electricity_history.csv")


# ==========================================================
# AUTOMATIC TARIFF DATABASE
# ==========================================================
# Only configured tariff schedules are used.
# Do not add estimated or example rates to this database.
# Source information is retained internally and is not
# displayed in the normal app interface.
#
# Note: Verify tariff orders and connection-specific charges
# before using these values for a real bill.
# ==========================================================

TARIFFS = {
    ("Andhra Pradesh", "APEPDCL", "Domestic - General"): {
        "name": "Domestic LT",
        "effective": "2026-04-01",
        "slabs": [
            {"upper": 30, "rate": 1.90},
            {"upper": 75, "rate": 3.00},
            {"upper": 125, "rate": 4.50},
            {"upper": 225, "rate": 6.00},
            {"upper": 400, "rate": 8.75},
            {"upper": None, "rate": 9.75},
        ],
        "fixed": 10.0,
        "max_units": None,
        "source": "APERC FY 2026-27 tariff schedule"
    },

    ("Andhra Pradesh", "APSPDCL", "Domestic - General"): {
        "name": "Domestic LT",
        "effective": "2026-04-01",
        "slabs": [
            {"upper": 30, "rate": 1.90},
            {"upper": 75, "rate": 3.00},
            {"upper": 125, "rate": 4.50},
            {"upper": 225, "rate": 6.00},
            {"upper": 400, "rate": 8.75},
            {"upper": None, "rate": 9.75},
        ],
        "fixed": 10.0,
        "max_units": None,
        "source": "APERC FY 2026-27 tariff schedule"
    },

    ("Telangana", "TGSPDCL", "Domestic - General"): {
        "name": "Domestic LT",
        "effective": "2026-04-01",
        "slabs": [
            {"upper": 50, "rate": 1.95},
            {"upper": 100, "rate": 3.10},
        ],
        "fixed": 10.0,
        "max_units": 100,
        "source": "TGERC FY 2026-27 tariff schedule"
    },

    ("Telangana", "TGNPDCL", "Domestic - General"): {
        "name": "Domestic LT",
        "effective": "2026-04-01",
        "slabs": [
            {"upper": 50, "rate": 1.95},
            {"upper": 100, "rate": 3.10},
        ],
        "fixed": 10.0,
        "max_units": 100,
        "source": "TGERC FY 2026-27 tariff schedule"
    },
}


# ==========================================================
# DISCOM DATABASE
# ==========================================================

DISCOMS = {
    "Andhra Pradesh": [
        "APEPDCL",
        "APSPDCL",
        "APCPDCL / Other"
    ],
    "Telangana": [
        "TGSPDCL",
        "TGNPDCL"
    ],
    "Karnataka": [
        "BESCOM",
        "MESCOM",
        "HESCOM",
        "GESCOM",
        "CESC"
    ],
    "Tamil Nadu": ["TNPDCL / TANGEDCO"],
    "Maharashtra": [
        "MSEDCL",
        "BEST",
        "Adani Electricity",
        "Tata Power"
    ],
    "Delhi": ["BRPL", "BYPL", "TPDDL", "NDMC"],
    "Kerala": ["KSEB"],
    "Gujarat": [
        "DGVCL",
        "MGVCL",
        "PGVCL",
        "UGVCL",
        "Torrent Power"
    ],
    "Rajasthan": ["JVVNL", "AVVNL", "JDVVNL"],
    "Punjab": ["PSPCL"],
    "Haryana": ["DHBVN", "UHBVN"],
    "Uttar Pradesh": [
        "PVVNL",
        "MVVNL",
        "DVVNL",
        "PuVVNL",
        "KESCO"
    ],
    "West Bengal": ["WBSEDCL", "CESC"],
    "Odisha": ["TPCODL", "TPNODL", "TPWODL", "TPSODL"],
    "Bihar": ["NBPDCL", "SBPDCL"],
    "Assam": ["APDCL"],
    "Jharkhand": ["JBVNL"],
    "Chhattisgarh": ["CSPDCL"],
    "Himachal Pradesh": ["HPSEBL"],
    "Uttarakhand": ["UPCL"],
    "Goa": ["Electricity Department Goa"],
    "Other State / UT": ["Other / Not Listed"]
}


# ==========================================================
# COMMON APPLIANCES
# ==========================================================

COMMON_APPLIANCES = [
    ["Air Conditioner", 1, 1500, 4.0],
    ["Refrigerator", 1, 150, 10.0],
    ["Television", 1, 150, 3.0],
    ["LED Bulbs", 6, 9, 6.0],
    ["Ceiling Fans", 4, 75, 8.0],
    ["Geyser", 1, 2000, 0.5],
    ["Washing Machine", 1, 500, 0.5],
    ["Laptop", 1, 65, 5.0],
    ["Water Pump", 1, 750, 0.5],
    ["Induction Stove", 1, 1800, 0.5],
    ["Microwave", 1, 1200, 0.3],
]


# ==========================================================
# CUSTOM EXCEPTIONS
# ==========================================================

class TariffUnavailable(Exception):
    pass


# ==========================================================
# APPLIANCE CALCULATION
# ==========================================================

def calculate_appliances(df, days):

    results = []

    for _, row in df.iterrows():

        name = str(row.get("Appliance", "")).strip()

        if not name:
            continue

        try:
            quantity = float(row["Quantity"])
            wattage = float(row["Wattage (W)"])
            hours = float(row["Hours/day"])
        except (ValueError, TypeError):
            continue

        if quantity < 0 or wattage < 0:
            continue

        if not 0 <= hours <= 24:
            continue

        daily_units = quantity * wattage * hours / 1000
        monthly_units = daily_units * days

        results.append({
            "Appliance": name,
            "Quantity": quantity,
            "Wattage (W)": wattage,
            "Hours/day": hours,
            "Daily Units": daily_units,
            "Monthly Units": monthly_units
        })

    return pd.DataFrame(results)


# ==========================================================
# AUTOMATIC SLAB CALCULATION
# ==========================================================

def calculate_slab_charges(units, tariff):

    if units < 0:
        raise ValueError("Units cannot be negative.")

    maximum = tariff.get("max_units")

    if maximum is not None and units > maximum:
        raise TariffUnavailable(
            f"The configured tariff schedule covers only up to "
            f"{maximum} units. Your estimated consumption is "
            f"{units:.2f} units. A higher-usage verified tariff "
            f"schedule is not currently configured."
        )

    remaining = float(units)
    previous_limit = 0.0
    total = 0.0
    breakdown = []

    for slab in tariff["slabs"]:

        upper = slab["upper"]
        rate = float(slab["rate"])

        if upper is None:
            slab_units = remaining
        else:
            slab_units = min(
                remaining,
                max(0.0, float(upper) - previous_limit)
            )

        if slab_units > 0:

            charge = slab_units * rate
            total += charge

            breakdown.append({
                "Slab": (
                    f"{previous_limit:g} units onwards"
                    if upper is None
                    else f"{previous_limit:g}–{upper:g} units"
                ),
                "Units": round(slab_units, 2),
                "Rate (₹/unit)": rate,
                "Charge (₹)": round(charge, 2)
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


# ==========================================================
# BILL CALCULATION
# ==========================================================

def calculate_bill(units, tariff):

    energy, slab_details = calculate_slab_charges(
        units,
        tariff
    )

    fixed_charge = tariff.get("fixed")

    if fixed_charge is None:
        raise TariffUnavailable(
            "The fixed charge for this connection has not "
            "been configured. A complete bill estimate "
            "cannot be calculated."
        )

    fixed_charge = float(fixed_charge)

    total = energy + fixed_charge

    return {
        "energy": energy,
        "fixed": fixed_charge,
        "total": total,
        "slabs": slab_details
    }


# ==========================================================
# BILL HISTORY FUNCTIONS
# ==========================================================

def load_history():

    if HISTORY_FILE.exists():

        try:
            return pd.read_csv(HISTORY_FILE)

        except Exception:
            pass

    return pd.DataFrame(columns=[
        "Saved At",
        "Month",
        "State",
        "DISCOM",
        "Billing Days",
        "Appliance Units",
        "Meter Units",
        "Actual Bill (₹)",
        "Estimated Bill (₹)"
    ])


def save_history(record):

    history = load_history()

    history = pd.concat(
        [history, pd.DataFrame([record])],
        ignore_index=True
    )

    history.to_csv(HISTORY_FILE, index=False)

    return history


# ==========================================================
# ELECTRICITY BILL OCR
# ==========================================================

def extract_bill_text(uploaded_file):

    filename = uploaded_file.name.lower()
    file_bytes = uploaded_file.getvalue()

    # PDF extraction
    if filename.endswith(".pdf"):

        try:
            import pdfplumber

            with pdfplumber.open(
                io.BytesIO(file_bytes)
            ) as pdf:

                pages_text = []

                for page in pdf.pages:
                    pages_text.append(page.extract_text() or "")

                return "\n".join(pages_text)

        except ImportError:
            raise RuntimeError(
                "PDF reading requires pdfplumber. "
                "Install it using: pip install pdfplumber"
            )

    # Image OCR
    try:
        from PIL import Image
        import pytesseract

        image = Image.open(io.BytesIO(file_bytes))

        return pytesseract.image_to_string(image)

    except ImportError:
        raise RuntimeError(
            "Image OCR requires Pillow and pytesseract. "
            "Install them using: pip install pillow pytesseract"
        )


# ==========================================================
# EXTRACT BILL VALUES
# ==========================================================

def parse_bill_fields(text):

    patterns = {

        "units": [
            r"(?:units consumed|consumption|kwh|units)"
            r"\D{0,25}([0-9]+(?:\.[0-9]+)?)",

            r"([0-9]+(?:\.[0-9]+)?)\s*(?:kwh|units)"
        ],

        "amount": [
            r"(?:total amount|amount payable|net amount|"
            r"bill amount|total due)"
            r"\D{0,30}(?:₹|rs\.?|inr)?\s*"
            r"([0-9,]+(?:\.[0-9]{1,2})?)"
        ],

        "days": [
            r"(?:billing days|no\.?\s*of\s*days)"
            r"\D{0,15}([0-9]{1,3})"
        ]
    }

    extracted = {}

    for field, expressions in patterns.items():

        for pattern in expressions:

            match = re.search(
                pattern,
                text,
                flags=re.IGNORECASE
            )

            if match:

                try:
                    value = match.group(1).replace(",", "")
                    extracted[field] = float(value)
                    break

                except ValueError:
                    pass

    return extracted


# ==========================================================
# STEP 1 - CONNECTION DETAILS
# ==========================================================

st.header("1. Electricity Connection Details")

col1, col2, col3 = st.columns(3)

with col1:

    state = st.selectbox(
        "State / Union Territory",
        list(DISCOMS.keys()),
        index=list(DISCOMS.keys()).index("Telangana")
    )

with col2:

    discom = st.selectbox(
        "Electricity Provider (DISCOM)",
        DISCOMS[state]
    )

with col3:

    category = st.selectbox(
        "Consumer Category",
        [
            "Domestic - General",
            "Domestic - BPL/Lifeline",
            "Other"
        ]
    )


col4, col5 = st.columns(2)

with col4:

    billing_days = st.number_input(
        "Billing period (days)",
        min_value=1,
        max_value=100,
        value=30
    )

with col5:

    sanctioned_load = st.number_input(
        "Sanctioned load (kW), if known",
        min_value=0.0,
        max_value=100.0,
        value=0.0,
        step=0.5
    )

st.caption(
    "Sanctioned load and monthly energy consumption are different "
    "measurements. Your actual tariff may depend on connection details."
)


# ==========================================================
# STEP 2 - APPLIANCE INPUTS
# ==========================================================

st.divider()
st.header("2. Household Appliance Usage")

st.write(
    "Edit the common appliances below. Use the wattage printed "
    "on the appliance label wherever possible."
)

common_df = pd.DataFrame(
    COMMON_APPLIANCES,
    columns=[
        "Appliance",
        "Quantity",
        "Wattage (W)",
        "Hours/day"
    ]
)

common_df = st.data_editor(
    common_df,
    key="common_appliance_editor",
    use_container_width=True,
    hide_index=True,
    num_rows="fixed",
    column_config={

        "Appliance": st.column_config.TextColumn(
            disabled=True
        ),

        "Quantity": st.column_config.NumberColumn(
            min_value=0,
            max_value=100,
            step=1
        ),

        "Wattage (W)": st.column_config.NumberColumn(
            min_value=0,
            max_value=50000,
            step=1
        ),

        "Hours/day": st.column_config.NumberColumn(
            min_value=0.0,
            max_value=24.0,
            step=0.5
        )
    }
)


st.subheader("➕ Add Extra Appliances")

st.write(
    "Add appliances not listed above, such as an iron box, "
    "air cooler, desktop, EV charger or water purifier."
)

custom_df = st.data_editor(
    pd.DataFrame([{
        "Appliance": "",
        "Quantity": 1,
        "Wattage (W)": 100,
        "Hours/day": 1.0
    }]),
    key="custom_appliance_editor",
    use_container_width=True,
    hide_index=True,
    num_rows="dynamic",
    column_config={

        "Appliance": st.column_config.TextColumn(),

        "Quantity": st.column_config.NumberColumn(
            min_value=0,
            max_value=100,
            step=1
        ),

        "Wattage (W)": st.column_config.NumberColumn(
            min_value=0,
            max_value=50000,
            step=1
        ),

        "Hours/day": st.column_config.NumberColumn(
            min_value=0.0,
            max_value=24.0,
            step=0.5
        )
    }
)


# ==========================================================
# STEP 3 - CONSUMPTION CALCULATION
# ==========================================================

st.divider()
st.header("3. Monthly Electricity Consumption")

common_results = calculate_appliances(
    common_df,
    billing_days
)

custom_results = calculate_appliances(
    custom_df,
    billing_days
)

all_results = pd.concat(
    [common_results, custom_results],
    ignore_index=True
)

if all_results.empty:
    st.error("Please enter at least one appliance.")
    st.stop()

total_units = float(
    all_results["Monthly Units"].sum()
)

daily_units = total_units / billing_days

c1, c2, c3 = st.columns(3)

c1.metric(
    "Estimated consumption",
    f"{total_units:.2f} kWh"
)

c2.metric(
    "Average daily consumption",
    f"{daily_units:.2f} kWh"
)

c3.metric(
    "Billing period",
    f"{billing_days} days"
)


# ==========================================================
# STEP 4 - AUTOMATIC TARIFF ENGINE
# ==========================================================

st.divider()
st.header("4. Automatic Tariff Calculation")

tariff = TARIFFS.get(
    (state, discom, category)
)

bill = None
tariff_error = None

if tariff is None:

    st.warning(
        "Automatic tariff calculation is not currently available "
        "for this connection category. Appliance consumption "
        "analysis and other features are still available."
    )

else:

    try:

        bill = calculate_bill(
            total_units,
            tariff
        )

        st.success(
            "Applicable configured tariff selected automatically."
        )

        st.caption(
            f"Tariff effective from {tariff['effective']}."
        )

        m1, m2 = st.columns(2)

        m1.metric(
            "Energy charges",
            f"₹{bill['energy']:,.2f}"
        )

        m2.metric(
            "Estimated subtotal",
            f"₹{bill['total']:,.2f}"
        )

        st.subheader("Slab-wise Calculation")

        st.dataframe(
            bill["slabs"],
            use_container_width=True,
            hide_index=True
        )

        st.info(
            "This estimate includes the configured energy and fixed "
            "charges only. Other charges, duties, adjustments, "
            "subsidies and bill-specific items may change the final amount."
        )

    except (TariffUnavailable, ValueError) as error:

        tariff_error = str(error)

        st.warning(tariff_error)


# ==========================================================
# STEP 5 - APPLIANCE CONSUMPTION ANALYSIS
# ==========================================================

st.divider()
st.header("5. Appliance Consumption Analysis")

display_results = all_results.copy()

display_results["Daily Units"] = (
    display_results["Daily Units"].round(2)
)

display_results["Monthly Units"] = (
    display_results["Monthly Units"].round(2)
)

st.dataframe(
    display_results,
    use_container_width=True,
    hide_index=True
)

positive_results = all_results[
    all_results["Monthly Units"] > 0
].copy()

if not positive_results.empty:

    col1, col2 = st.columns(2)

    with col1:

        fig, ax = plt.subplots(figsize=(7, 5))

        ax.pie(
            positive_results["Monthly Units"],
            labels=positive_results["Appliance"],
            autopct="%1.1f%%",
            startangle=140
        )

        ax.set_title("Household Electricity Consumption")

        st.pyplot(fig)

        plt.close(fig)

    with col2:

        top = positive_results.nlargest(
            5,
            "Monthly Units"
        ).sort_values("Monthly Units")

        fig, ax = plt.subplots(figsize=(7, 5))

        ax.barh(
            top["Appliance"],
            top["Monthly Units"]
        )

        ax.set_xlabel("Monthly units (kWh)")
        ax.set_title("Top 5 Electricity Consumers")

        st.pyplot(fig)

        plt.close(fig)


# ==========================================================
# STEP 6 - SMART CONSUMPTION INSIGHTS
# ==========================================================

st.divider()
st.header("6. Smart Consumption Insights")

if not positive_results.empty:

    biggest = positive_results.loc[
        positive_results["Monthly Units"].idxmax()
    ]

    share = (
        biggest["Monthly Units"] / total_units
    ) * 100 if total_units > 0 else 0

    st.info(
        f"Your largest electricity consumer is **{biggest['Appliance']}**, "
        f"using **{biggest['Monthly Units']:.2f} units** "
        f"({share:.1f}% of your estimated consumption)."
    )

    high_hours = all_results[
        all_results["Hours/day"] >= 12
    ]

    if not high_hours.empty:

        st.warning(
            "The following appliances are entered as running for "
            "12 or more hours per day: "
            + ", ".join(high_hours["Appliance"].astype(str))
            + ". Check whether these usage hours are correct."
        )

    if daily_units > 10:

        st.warning(
            "Your estimated consumption exceeds 10 units per day. "
            "Review high-wattage appliances and their usage hours."
        )

    elif daily_units < 1:

        st.info(
            "Your estimated consumption is below 1 unit per day. "
            "Check whether all regularly used appliances are included."
        )

    st.subheader("Personalized Recommendations")

    for _, row in positive_results.nlargest(
        5,
        "Monthly Units"
    ).iterrows():

        name = row["Appliance"].lower()

        if "air conditioner" in name or name == "ac":

            tip = (
                "Use a moderate temperature, clean filters regularly "
                "and keep doors/windows closed while cooling."
            )

        elif "geyser" in name or "water heater" in name:

            tip = (
                "Use a timer and switch it off after the required "
                "heating period."
            )

        elif "refrigerator" in name:

            tip = (
                "Check door seals, maintain ventilation and avoid "
                "frequent unnecessary opening."
            )

        elif "fan" in name:

            tip = (
                "Consider energy-efficient BLDC fans when replacing "
                "older models."
            )

        elif "pump" in name:

            tip = (
                "Check for leaks and avoid unnecessary pumping."
            )

        elif "bulb" in name or "light" in name:

            tip = (
                "Use LED lights and switch off lights in unoccupied rooms."
            )

        else:

            tip = (
                "Review its daily operating hours and wattage. "
                "Switch it off when it is not required."
            )

        st.write(f"**{row['Appliance']}:** {tip}")


# ==========================================================
# STEP 7 - SAVINGS SIMULATOR
# ==========================================================

st.divider()
st.header("7. Electricity Savings Simulator")

reduction = st.slider(
    "How much do you want to reduce consumption?",
    min_value=0,
    max_value=50,
    value=10,
    step=5
)

reduced_units = total_units * (
    1 - reduction / 100
)

saved_units = total_units - reduced_units

s1, s2 = st.columns(2)

s1.metric(
    "Consumption after reduction",
    f"{reduced_units:.2f} units"
)

s2.metric(
    "Units saved",
    f"{saved_units:.2f} units"
)

if tariff is not None:

    try:

        old_energy, _ = calculate_slab_charges(
            total_units,
            tariff
        )

        new_energy, _ = calculate_slab_charges(
            reduced_units,
            tariff
        )

        st.metric(
            "Estimated energy-charge savings",
            f"₹{old_energy - new_energy:,.2f}"
        )

    except TariffUnavailable:

        st.caption(
            "Tariff-based savings are unavailable for this usage range."
        )


# ==========================================================
# STEP 8 - ELECTRICITY BILL UPLOAD AND READING
# ==========================================================

st.divider()
st.header("8. Upload Your Electricity Bill")

st.write(
    "Upload a PDF or a clear photograph of your electricity bill. "
    "The app will try to extract units and the payable amount."
)

uploaded_file = st.file_uploader(
    "Upload electricity bill",
    type=["pdf", "png", "jpg", "jpeg"]
)

if uploaded_file is not None:

    if st.button("Read Electricity Bill"):

        try:

            extracted_text = extract_bill_text(
                uploaded_file
            )

            extracted_fields = parse_bill_fields(
                extracted_text
            )

            st.session_state["ocr_text"] = extracted_text
            st.session_state["ocr_fields"] = extracted_fields

        except Exception as error:

            st.error(str(error))

    if "ocr_text" in st.session_state:

        st.subheader("Extracted Bill Information")

        st.text_area(
            "Recognized bill text - verify before using",
            st.session_state["ocr_text"],
            height=180
        )

        fields = st.session_state.get(
            "ocr_fields",
            {}
        )

        if fields:

            st.write("Detected values:")

            st.json(fields)

            st.warning(
                "OCR may misread digits, decimal points and labels. "
                "Always verify extracted values against your original bill."
            )

        else:

            st.warning(
                "The app could not reliably identify the bill values. "
                "Enter the values manually in the comparison section."
            )


# ==========================================================
# STEP 9 - ACTUAL BILL COMPARISON
# ==========================================================

st.divider()
st.header("9. Compare with Your Actual Electricity Bill")

col1, col2 = st.columns(2)

with col1:

    actual_units = st.number_input(
        "Actual units from electricity bill",
        min_value=0.0,
        value=0.0,
        step=1.0
    )

with col2:

    actual_amount = st.number_input(
        "Actual payable amount (₹)",
        min_value=0.0,
        value=0.0,
        step=50.0
    )

ocr_fields = st.session_state.get(
    "ocr_fields",
    {}
)

if ocr_fields:

    st.caption(
        "OCR suggestion — Units: "
        + str(ocr_fields.get("units", "Not detected"))
        + " | Amount: ₹"
        + str(ocr_fields.get("amount", "Not detected"))
    )

if actual_units > 0:

    difference = actual_units - total_units

    st.metric(
        "Actual units minus appliance estimate",
        f"{difference:+.2f} units"
    )

if actual_amount > 0 and bill is not None:

    difference = actual_amount - bill["total"]

    st.metric(
        "Actual bill minus estimated subtotal",
        f"₹{difference:+,.2f}"
    )

    st.caption(
        "This comparison is indicative. The estimated subtotal may "
        "exclude statutory charges, adjustments, subsidies and arrears."
    )


# ==========================================================
# STEP 10 - METER READING ANALYSIS
# ==========================================================

st.divider()
st.header("10. Actual Meter Reading Analysis")

m1, m2 = st.columns(2)

with m1:

    previous_reading = st.number_input(
        "Previous meter reading",
        min_value=0.0,
        value=0.0
    )

with m2:

    current_reading = st.number_input(
        "Current meter reading",
        min_value=0.0,
        value=0.0
    )

if current_reading >= previous_reading:

    meter_units = current_reading - previous_reading

    st.metric(
        "Actual meter consumption",
        f"{meter_units:.2f} units"
    )

    st.write(
        f"Difference between meter and appliance estimate: "
        f"{meter_units - total_units:+.2f} units"
    )

else:

    meter_units = 0.0

    st.error(
        "Current meter reading cannot be lower than previous reading."
    )


# ==========================================================
# STEP 11 - MONTHLY HISTORY
# ==========================================================

st.divider()
st.header("11. Monthly Electricity History")

bill_month = st.date_input(
    "Select bill month",
    value=date.today().replace(day=1)
)

if st.button(
    "Save This Month's Audit",
    type="primary"
):

    record = {
        "Saved At": datetime.now().isoformat(timespec="seconds"),
        "Month": bill_month.strftime("%Y-%m"),
        "State": state,
        "DISCOM": discom,
        "Billing Days": billing_days,
        "Appliance Units": round(total_units, 2),
        "Meter Units": round(meter_units, 2),
        "Actual Bill (₹)": round(actual_amount, 2),
        "Estimated Bill (₹)": (
            round(bill["total"], 2)
            if bill is not None
            else None
        )
    }

    save_history(record)

    st.success("Your monthly electricity audit has been saved.")

history = load_history()

if not history.empty:

    st.subheader("Saved Audit Records")

    st.dataframe(
        history,
        use_container_width=True,
        hide_index=True
    )

    if len(history) >= 2:

        chart_history = history.copy()

        chart_history["Appliance Units"] = pd.to_numeric(
            chart_history["Appliance Units"],
            errors="coerce"
        )

        chart_history = chart_history.dropna(
            subset=["Appliance Units"]
        )

        if not chart_history.empty:

            chart_history = chart_history.sort_values("Month")

            st.subheader("Monthly Consumption Trend")

            st.line_chart(
                chart_history.set_index("Month")["Appliance Units"]
            )

    st.download_button(
        "Download Monthly History (CSV)",
        data=history.to_csv(index=False).encode("utf-8"),
        file_name="electricity_monthly_history.csv",
        mime="text/csv"
    )

else:

    st.info(
        "No saved monthly audits yet. Save an audit to start "
        "tracking your household consumption."
    )


# ==========================================================
# STEP 12 - DOWNLOAD REPORTS
# ==========================================================

st.divider()
st.header("12. Download Your Energy Audit Report")

appliance_csv = all_results.to_csv(
    index=False
).encode("utf-8")

st.download_button(
    "📥 Download Appliance Analysis (CSV)",
    data=appliance_csv,
    file_name="electricity_appliance_analysis.csv",
    mime="text/csv",
    use_container_width=True
)

if bill is not None:

    bill_table = pd.DataFrame({
        "Component": [
            "Energy charges",
            "Configured fixed charges",
            "Estimated subtotal"
        ],
        "Amount (₹)": [
            bill["energy"],
            bill["fixed"],
            bill["total"]
        ]
    })

    st.download_button(
        "📥 Download Estimated Bill (CSV)",
        data=bill_table.to_csv(index=False).encode("utf-8"),
        file_name="electricity_bill_estimate.csv",
        mime="text/csv",
        use_container_width=True
    )


# ==========================================================
# FOOTER
# ==========================================================

st.divider()

st.subheader("About this Application")

st.write(
    """
    Smart Home Electricity Auditor is a community-service project
    designed to help households understand electricity usage,
    estimate electricity expenses, identify high-consumption
    appliances and explore energy-saving opportunities.

    **Important:** This application is an estimation tool and is
    not an official DISCOM billing system. Tariff coverage is limited
    to configured schedules. The final amount on an electricity bill
    may include additional charges, duties, subsidies and adjustments.
    """
)

st.caption(
    "Smart Home Electricity Auditor | Community Service Project"
)
