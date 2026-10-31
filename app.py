
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import date, datetime
from pathlib import Path

from modules.tariff_engine import (
    load_tariffs,
    get_tariff,
    calculate_bill,
    TariffUnavailable,
)
from modules.bill_reader import extract_bill_text, parse_bill_fields

st.set_page_config(
    page_title="Smart Home Electricity Auditor",
    page_icon="⚡",
    layout="wide",
)

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
HISTORY_FILE = BASE_DIR / "electricity_history.csv"

st.title("⚡ Smart Home Electricity Auditor")
st.markdown("### Calculate, Analyze, and Reduce Your Electricity Bill")
st.write(
    "A pan-India residential electricity analysis tool. "
    "Estimate household consumption, compare electricity bills "
    "and discover ways to reduce energy usage."
)

# --------------------------------------------------
# LOAD STATE AND DISCOM DATA
# --------------------------------------------------

import json

with open(DATA_DIR / "states.json", "r", encoding="utf-8") as f:
    state_data = json.load(f)

states = list(state_data.keys())

# --------------------------------------------------
# APPLIANCE DEFAULTS
# --------------------------------------------------

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
        except (ValueError, TypeError, KeyError):
            continue

        if quantity < 0 or wattage < 0 or not 0 <= hours <= 24:
            continue

        daily_units = quantity * wattage * hours / 1000
        monthly_units = daily_units * days

        results.append({
            "Appliance": name,
            "Quantity": quantity,
            "Wattage (W)": wattage,
            "Hours/day": hours,
            "Daily Units": daily_units,
            "Monthly Units": monthly_units,
        })

    return pd.DataFrame(results)


def load_history():
    if HISTORY_FILE.exists():
        try:
            return pd.read_csv(HISTORY_FILE)
        except Exception:
            pass

    return pd.DataFrame(columns=[
        "Saved At", "Month", "State", "DISCOM",
        "Billing Days", "Appliance Units", "Meter Units",
        "Actual Bill (₹)", "Estimated Bill (₹)",
    ])


def save_history(record):
    history = load_history()
    history = pd.concat(
        [history, pd.DataFrame([record])],
        ignore_index=True,
    )
    history.to_csv(HISTORY_FILE, index=False)
    return history


# ==================================================
# 1. CONNECTION DETAILS
# ==================================================

st.header("1. Electricity Connection Details")

col1, col2, col3 = st.columns(3)

with col1:
    state = st.selectbox(
        "State / Union Territory",
        states,
        index=states.index("Telangana") if "Telangana" in states else 0,
    )

providers = state_data[state]
provider_options = providers + ["Other / Not Listed"]

with col2:
    discom_choice = st.selectbox(
        "Electricity Provider (DISCOM)",
        provider_options,
    )

with col3:
    category = st.selectbox(
        "Consumer Category",
        ["Domestic - General"],
    )

if discom_choice == "Other / Not Listed":
    discom = st.text_input(
        "Enter your electricity provider name",
        placeholder="Enter DISCOM / electricity department",
    ).strip()
else:
    discom = discom_choice

col4, col5 = st.columns(2)

with col4:
    billing_days = st.number_input(
        "Billing period (days)",
        min_value=1,
        max_value=100,
        value=30,
    )

with col5:
    sanctioned_load = st.number_input(
        "Sanctioned load (kW), if known",
        min_value=0.0,
        max_value=100.0,
        value=0.0,
        step=0.5,
    )

st.caption(
    "This version is designed for residential/domestic connections. "
    "Tariff eligibility may also depend on sanctioned load, meter type "
    "and other provider-specific conditions."
)

# ==================================================
# 2. APPLIANCE INPUTS
# ==================================================

st.divider()
st.header("2. Household Appliance Usage")

st.write(
    "Edit the appliance quantities, wattage and daily usage hours. "
    "Use the wattage printed on the appliance label where possible."
)

common_df = pd.DataFrame(
    COMMON_APPLIANCES,
    columns=["Appliance", "Quantity", "Wattage (W)", "Hours/day"],
)

common_df = st.data_editor(
    common_df,
    key="common_appliance_editor",
    use_container_width=True,
    hide_index=True,
    num_rows="fixed",
    column_config={
        "Appliance": st.column_config.TextColumn(disabled=True),
        "Quantity": st.column_config.NumberColumn(
            min_value=0, max_value=100, step=1
        ),
        "Wattage (W)": st.column_config.NumberColumn(
            min_value=0, max_value=50000, step=1
        ),
        "Hours/day": st.column_config.NumberColumn(
            min_value=0.0, max_value=24.0, step=0.5
        ),
    },
)

st.subheader("➕ Add Extra Appliances")

custom_df = st.data_editor(
    pd.DataFrame([{
        "Appliance": "",
        "Quantity": 1,
        "Wattage (W)": 100,
        "Hours/day": 1.0,
    }]),
    key="custom_appliance_editor",
    use_container_width=True,
    hide_index=True,
    num_rows="dynamic",
    column_config={
        "Appliance": st.column_config.TextColumn(),
        "Quantity": st.column_config.NumberColumn(
            min_value=0, max_value=100, step=1
        ),
        "Wattage (W)": st.column_config.NumberColumn(
            min_value=0, max_value=50000, step=1
        ),
        "Hours/day": st.column_config.NumberColumn(
            min_value=0.0, max_value=24.0, step=0.5
        ),
    },
)

# ==================================================
# 3. CONSUMPTION CALCULATION
# ==================================================

st.divider()
st.header("3. Monthly Electricity Consumption")

common_results = calculate_appliances(common_df, billing_days)
custom_results = calculate_appliances(custom_df, billing_days)

all_results = pd.concat(
    [common_results, custom_results],
    ignore_index=True,
)

if all_results.empty:
    st.error("Please enter at least one appliance.")
    st.stop()

total_units = float(all_results["Monthly Units"].sum())
daily_units = total_units / billing_days

c1, c2, c3 = st.columns(3)
c1.metric("Estimated consumption", f"{total_units:.2f} kWh")
c2.metric("Average daily consumption", f"{daily_units:.2f} kWh")
c3.metric("Billing period", f"{billing_days} days")

# ==================================================
# 4. AUTOMATIC TARIFF CALCULATION
# ==================================================

st.divider()
st.header("4. Automatic Domestic Tariff Calculation")

tariffs = load_tariffs(BASE_DIR / "data" / "tariffs")

tariff = get_tariff(
    tariffs,
    state,
    discom,
    category,
)

bill = None

if not discom:
    st.warning("Enter or select your electricity provider.")
elif tariff is None:
    st.warning(
        "A verified tariff schedule is not yet available for "
        f"{discom}, {state}. Your consumption analysis is available, "
        "but the app will not guess your electricity rate."
    )
else:
    try:
        bill = calculate_bill(total_units, tariff)

        st.success("A verified tariff schedule was found.")

        st.caption(
            f"Tariff effective date: {tariff['effective_date']}"
        )

        a, b = st.columns(2)
        a.metric("Energy charges", f"₹{bill['energy']:,.2f}")
        b.metric("Configured subtotal", f"₹{bill['total']:,.2f}")

        st.subheader("Slab-wise Calculation")
        st.dataframe(
            bill["slabs"],
            use_container_width=True,
            hide_index=True,
        )

        st.info(
            "This estimate includes only the energy and fixed charges "
            "configured in the tariff data. Actual bills may also include "
            "electricity duty, fuel adjustments, meter charges, taxes, "
            "subsidies, arrears and other provider-specific items."
        )

    except TariffUnavailable as error:
        st.warning(str(error))

# ==================================================
# 5. APPLIANCE ANALYSIS
# ==================================================

st.divider()
st.header("5. Appliance Consumption Analysis")

display_results = all_results.copy()
display_results["Daily Units"] = display_results["Daily Units"].round(2)
display_results["Monthly Units"] = display_results["Monthly Units"].round(2)

st.dataframe(
    display_results,
    use_container_width=True,
    hide_index=True,
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
            startangle=140,
        )
        ax.set_title("Household Electricity Consumption")
        st.pyplot(fig)
        plt.close(fig)

    with col2:
        top = positive_results.nlargest(
            5, "Monthly Units"
        ).sort_values("Monthly Units")

        fig, ax = plt.subplots(figsize=(7, 5))
        ax.barh(top["Appliance"], top["Monthly Units"])
        ax.set_xlabel("Monthly units (kWh)")
        ax.set_title("Top 5 Electricity Consumers")
        st.pyplot(fig)
        plt.close(fig)

# ==================================================
# 6. SMART INSIGHTS
# ==================================================

st.divider()
st.header("6. Smart Consumption Insights")

if not positive_results.empty:
    biggest = positive_results.loc[
        positive_results["Monthly Units"].idxmax()
    ]

    share = (
        biggest["Monthly Units"] / total_units * 100
        if total_units > 0 else 0
    )

    st.info(
        f"Your largest electricity consumer is **{biggest['Appliance']}**, "
        f"using **{biggest['Monthly Units']:.2f} units** "
        f"({share:.1f}% of estimated consumption)."
    )

    high_hours = all_results[all_results["Hours/day"] >= 12]

    if not high_hours.empty:
        st.warning(
            "Check the usage hours for: "
            + ", ".join(high_hours["Appliance"].astype(str))
        )

    if daily_units > 10:
        st.warning(
            "Your estimated consumption exceeds 10 units per day. "
            "Review high-wattage appliances and their usage."
        )
    elif daily_units < 1:
        st.info(
            "Your estimated consumption is below 1 unit per day. "
            "Check whether all regularly used appliances are included."
        )

    st.subheader("Personalized Recommendations")

    for _, row in positive_results.nlargest(
        5, "Monthly Units"
    ).iterrows():

        name = row["Appliance"].lower()

        if "air conditioner" in name or name == "ac":
            tip = (
                "Use a moderate temperature, clean filters regularly "
                "and keep doors and windows closed while cooling."
            )
        elif "geyser" in name or "water heater" in name:
            tip = "Use a timer and switch it off after heating."
        elif "refrigerator" in name:
            tip = (
                "Check door seals, maintain ventilation and avoid "
                "frequent unnecessary opening."
            )
        elif "fan" in name:
            tip = "Consider energy-efficient BLDC fans when replacing old fans."
        elif "pump" in name:
            tip = "Check for leaks and avoid unnecessary pumping."
        elif "bulb" in name or "light" in name:
            tip = "Use LED lights and switch off lights in empty rooms."
        else:
            tip = (
                "Review its daily operating hours and wattage. "
                "Switch it off when not required."
            )

        st.write(f"**{row['Appliance']}:** {tip}")

# ==================================================
# 7. SAVINGS SIMULATOR
# ==================================================

st.divider()
st.header("7. Electricity Savings Simulator")

reduction = st.slider(
    "How much do you want to reduce consumption?",
    min_value=0,
    max_value=50,
    value=10,
    step=5,
)

reduced_units = total_units * (1 - reduction / 100)
saved_units = total_units - reduced_units

s1, s2 = st.columns(2)
s1.metric("Consumption after reduction", f"{reduced_units:.2f} units")
s2.metric("Units saved", f"{saved_units:.2f} units")

if tariff is not None:
    try:
        old_bill = calculate_bill(total_units, tariff)
        new_bill = calculate_bill(reduced_units, tariff)

        st.metric(
            "Estimated bill savings",
            f"₹{old_bill['total'] - new_bill['total']:,.2f}",
        )
    except TariffUnavailable:
        st.caption(
            "Tariff-based savings are unavailable for this usage range."
        )

# ==================================================
# 8. BILL UPLOAD AND OCR
# ==================================================

st.divider()
st.header("8. Upload Your Electricity Bill")

st.write(
    "Upload a PDF or clear photograph of your electricity bill. "
    "The app will attempt to identify units and the payable amount."
)

uploaded_file = st.file_uploader(
    "Upload electricity bill",
    type=["pdf", "png", "jpg", "jpeg"],
)

if uploaded_file is not None:
    if st.button("Read Electricity Bill"):
        try:
            extracted_text = extract_bill_text(uploaded_file)
            extracted_fields = parse_bill_fields(extracted_text)

            st.session_state["ocr_text"] = extracted_text
            st.session_state["ocr_fields"] = extracted_fields

        except Exception as error:
            st.error(str(error))

    if "ocr_text" in st.session_state:
        st.subheader("Extracted Bill Information")

        st.text_area(
            "Recognized bill text - verify before using",
            st.session_state["ocr_text"],
            height=180,
        )

        fields = st.session_state.get("ocr_fields", {})

        if fields:
            st.write("Detected values:")
            st.json(fields)
            st.warning(
                "OCR can misread digits and labels. Verify all values "
                "against your original electricity bill."
            )
        else:
            st.warning(
                "Bill values could not be reliably identified. "
                "Enter them manually below."
            )

# ==================================================
# 9. ACTUAL BILL COMPARISON
# ==================================================

st.divider()
st.header("9. Compare with Your Actual Electricity Bill")

ocr_fields = st.session_state.get("ocr_fields", {})

col1, col2 = st.columns(2)

with col1:
    actual_units = st.number_input(
        "Actual units from electricity bill",
        min_value=0.0,
        value=float(ocr_fields.get("units", 0.0)),
        step=1.0,
    )

with col2:
    actual_amount = st.number_input(
        "Actual payable amount (₹)",
        min_value=0.0,
        value=float(ocr_fields.get("amount", 0.0)),
        step=50.0,
    )

if actual_units > 0:
    st.metric(
        "Actual units minus appliance estimate",
        f"{actual_units - total_units:+.2f} units",
    )

if actual_amount > 0 and bill is not None:
    st.metric(
        "Actual bill minus estimated subtotal",
        f"₹{actual_amount - bill['total']:+,.2f}",
    )
    st.caption(
        "The estimate may exclude duties, adjustments, subsidies "
        "and arrears."
    )

# ==================================================
# 10. METER READING ANALYSIS
# ==================================================

st.divider()
st.header("10. Actual Meter Reading Analysis")

m1, m2 = st.columns(2)

with m1:
    previous_reading = st.number_input(
        "Previous meter reading",
        min_value=0.0,
        value=0.0,
        key="previous_reading",
    )

with m2:
    current_reading = st.number_input(
        "Current meter reading",
        min_value=0.0,
        value=0.0,
        key="current_reading",
    )

meter_units = 0.0

if current_reading >= previous_reading:
    meter_units = current_reading - previous_reading

    st.metric("Actual meter consumption", f"{meter_units:.2f} units")
    st.write(
        "Difference between meter and appliance estimate: "
        f"{meter_units - total_units:+.2f} units"
    )
else:
    st.error(
        "Current meter reading cannot be lower than previous reading."
    )

# ==================================================
# 11. MONTHLY HISTORY
# ==================================================

st.divider()
st.header("11. Monthly Electricity History")

bill_month = st.date_input(
    "Select bill month",
    value=date.today().replace(day=1),
)

if st.button("Save This Month's Audit", type="primary"):
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
            round(bill["total"], 2) if bill is not None else None
        ),
    }

    save_history(record)
    st.success("Your monthly electricity audit has been saved.")

history = load_history()

if not history.empty:
    st.subheader("Saved Audit Records")
    st.dataframe(history, use_container_width=True, hide_index=True)

    if len(history) >= 2:
        chart_history = history.copy()
        chart_history["Appliance Units"] = pd.to_numeric(
            chart_history["Appliance Units"],
            errors="coerce",
        )
        chart_history = chart_history.dropna(
            subset=["Appliance Units"]
        )

        if not chart_history.empty:
            monthly = (
                chart_history.groupby("Month")["Appliance Units"]
                .mean()
                .sort_index()
            )
            st.subheader("Monthly Consumption Trend")
            st.line_chart(monthly)

    st.download_button(
        "Download Monthly History (CSV)",
        data=history.to_csv(index=False).encode("utf-8"),
        file_name="electricity_monthly_history.csv",
        mime="text/csv",
    )
else:
    st.info("No saved monthly audits yet.")

# ==================================================
# 12. DOWNLOAD REPORTS
# ==================================================

st.divider()
st.header("12. Download Your Energy Audit Report")

st.download_button(
    "📥 Download Appliance Analysis (CSV)",
    data=all_results.to_csv(index=False).encode("utf-8"),
    file_name="electricity_appliance_analysis.csv",
    mime="text/csv",
    use_container_width=True,
)

if bill is not None:
    bill_table = pd.DataFrame({
        "Component": [
            "Energy charges",
            "Configured fixed charges",
            "Estimated subtotal",
        ],
        "Amount (₹)": [
            bill["energy"],
            bill["fixed"],
            bill["total"],
        ],
    })

    st.download_button(
        "📥 Download Estimated Bill (CSV)",
        data=bill_table.to_csv(index=False).encode("utf-8"),
        file_name="electricity_bill_estimate.csv",
        mime="text/csv",
        use_container_width=True,
    )

# ==================================================
# FOOTER
# ==================================================

st.divider()
st.subheader("About this Application")

st.write(
    """
    Smart Home Electricity Auditor is a residential energy-awareness
    application designed to help households understand electricity
    consumption, estimate expenses, identify high-consumption appliances
    and explore energy-saving opportunities.

    **Important:** This is an estimation tool, not an official DISCOM
    billing system. Tariff calculations are available only for matching
    schedules explicitly marked as verified. Actual bills may include
    additional charges, duties, adjustments, subsidies and arrears.
    """
)

st.caption(
    "Smart Home Electricity Auditor | Community Service Project"
)
