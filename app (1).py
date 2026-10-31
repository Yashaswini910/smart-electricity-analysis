import io
import re
from datetime import date

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

# Optional OCR support. The app still works if pytesseract or the Tesseract
# system application is not installed.
try:
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
except Exception:
    OCR_AVAILABLE = False


# ============================================================
# PAGE CONFIGURATION
# ============================================================
st.set_page_config(
    page_title="Smart Home Electricity Auditor",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ Smart Home Electricity Auditor")
st.subheader("Community Service Project | Calculate, Understand and Reduce Electricity Use")
st.write(
    "A household energy-audit tool for community awareness and student field surveys. "
    "It estimates appliance consumption, explains the bill, identifies major loads, "
    "and suggests practical conservation actions."
)
st.info(
    "For community surveys: use the wattage printed on the appliance label where possible. "
    "This tool provides estimates, not an official electricity bill."
)


# ============================================================
# REFERENCE DATA
# These are starter values only, not a substitute for the tariff
# order/bill issued by the household's DISCOM.
# ============================================================
DISCOMS = {
    "Andhra Pradesh": ["APSPDCL", "APEPDCL", "Other / Not sure"],
    "Assam": ["APDCL", "Other / Not sure"],
    "Bihar": ["NBPDCL", "SBPDCL", "Other / Not sure"],
    "Chhattisgarh": ["CSPDCL", "Other / Not sure"],
    "Delhi": [
        "BSES Rajdhani Power Limited (BRPL)",
        "BSES Yamuna Power Limited (BYPL)",
        "Tata Power Delhi Distribution Limited (TPDDL)",
        "NDMC",
        "Other / Not sure",
    ],
    "Gujarat": ["DGVCL", "MGVCL", "PGVCL", "UGVCL", "Torrent Power", "Other / Not sure"],
    "Haryana": ["DHBVN", "UHBVN", "Other / Not sure"],
    "Himachal Pradesh": ["HPSEBL", "Other / Not sure"],
    "Jharkhand": ["JBVNL", "Other / Not sure"],
    "Karnataka": ["BESCOM", "HESCOM", "GESCOM", "MESCOM", "CESC", "Other / Not sure"],
    "Kerala": ["KSEB", "Other / Not sure"],
    "Madhya Pradesh": ["MPMKVVCL", "MPEZ", "Other / Not sure"],
    "Maharashtra": ["MSEDCL", "BEST", "Adani Electricity", "Tata Power", "Other / Not sure"],
    "Odisha": ["TPCODL", "TPNODL", "TPWODL", "TPSODL", "Other / Not sure"],
    "Punjab": ["PSPCL", "Other / Not sure"],
    "Rajasthan": ["JVVNL", "AVVNL", "JDVVNL", "Other / Not sure"],
    "Tamil Nadu": ["TNPDCL / TANGEDCO", "Other / Not sure"],
    "Telangana": ["TGSPDCL", "TGNPDCL", "Other / Not sure"],
    "Uttar Pradesh": ["PVVNL", "MVVNL", "DVVNL", "PuVVNL", "KESCO", "Other / Not sure"],
    "Uttarakhand": ["UPCL", "Other / Not sure"],
    "West Bengal": ["WBSEDCL", "CESC", "Other / Not sure"],
    "Goa": ["Electricity Department, Goa", "Other / Not sure"],
    "Other State / UT": ["Other / Not sure"],
}

# Illustrative duty reference values carried over from the project draft.
# Users should preferably enter the duty/tax shown on their actual bill.
DUTY_REFERENCE_R_PER_UNIT = {
    "Andhra Pradesh": 0.06,
    "Assam": 0.42,
    "Bihar": 0.58,
    "Chhattisgarh": 0.72,
    "Delhi": 0.28,
    "Goa": 0.20,
    "Gujarat": 0.74,
    "Haryana": 0.25,
    "Himachal Pradesh": 0.28,
    "Jharkhand": 0.41,
    "Karnataka": 0.52,
    "Kerala": 0.92,
    "Madhya Pradesh": 1.11,
    "Maharashtra": 2.59,
    "Odisha": 0.23,
    "Punjab": 1.10,
    "Rajasthan": 0.55,
    "Tamil Nadu": 0.00,
    "Telangana": 0.06,
    "Tripura": 0.44,
    "Uttar Pradesh": 0.37,
    "Uttarakhand": 0.15,
    "West Bengal": 0.89,
    "Other State / UT": 0.00,
}

COMMON_APPLIANCES = [
    {"Appliance": "Air Conditioner", "Quantity": 1, "Wattage (W)": 1500, "Hours/day": 4.0},
    {"Appliance": "Refrigerator", "Quantity": 1, "Wattage (W)": 150, "Hours/day": 10.0},
    {"Appliance": "Television", "Quantity": 1, "Wattage (W)": 150, "Hours/day": 3.0},
    {"Appliance": "LED Bulb", "Quantity": 6, "Wattage (W)": 9, "Hours/day": 6.0},
    {"Appliance": "Ceiling Fan", "Quantity": 4, "Wattage (W)": 75, "Hours/day": 8.0},
    {"Appliance": "Geyser", "Quantity": 1, "Wattage (W)": 2000, "Hours/day": 0.5},
    {"Appliance": "Washing Machine", "Quantity": 1, "Wattage (W)": 500, "Hours/day": 0.5},
    {"Appliance": "Laptop", "Quantity": 1, "Wattage (W)": 65, "Hours/day": 5.0},
    {"Appliance": "Water Pump", "Quantity": 1, "Wattage (W)": 750, "Hours/day": 0.5},
    {"Appliance": "Induction Stove", "Quantity": 1, "Wattage (W)": 1800, "Hours/day": 0.5},
    {"Appliance": "Microwave", "Quantity": 1, "Wattage (W)": 1200, "Hours/day": 0.3},
]

# ============================================================
# HELPER FUNCTIONS
# ============================================================
def calculate_slab_energy_charge(units, slabs):
    """Calculate telescopic energy charge using user-configured slabs."""
    remaining = max(float(units), 0.0)
    total = 0.0
    for upper_limit, rate in slabs:
        if remaining <= 0:
            break
        slab_units = remaining if upper_limit is None else min(remaining, upper_limit)
        total += slab_units * rate
        remaining -= slab_units
    return total


def appliance_calculations(dataframe):
    """Return appliance-level daily and 30-day energy estimates."""
    rows = []
    for _, row in dataframe.iterrows():
        name = str(row.get("Appliance", "")).strip()
        if not name:
            continue
        quantity = max(float(row.get("Quantity", 0) or 0), 0)
        wattage = max(float(row.get("Wattage (W)", 0) or 0), 0)
        hours = min(max(float(row.get("Hours/day", 0) or 0), 0), 24)
        daily_units = quantity * wattage * hours / 1000
        rows.append(
            {
                "Appliance": name,
                "Quantity": quantity,
                "Wattage (W)": wattage,
                "Hours/day": hours,
                "Daily Units (kWh)": daily_units,
                "Monthly Units (kWh)": daily_units * 30,
            }
        )
    return pd.DataFrame(
        rows,
        columns=[
            "Appliance", "Quantity", "Wattage (W)", "Hours/day",
            "Daily Units (kWh)", "Monthly Units (kWh)",
        ],
    )


def estimate_bill(units, tariff_mode, flat_rate, slabs, fixed_charge, duty_rate, other_charges):
    if tariff_mode == "Custom flat rate":
        energy = units * flat_rate
    else:
        energy = calculate_slab_energy_charge(units, slabs)
    duty = units * duty_rate
    total = energy + fixed_charge + duty + other_charges
    return energy, duty, total


def safe_filename(value):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", str(value)).strip("_") or "household"


# ============================================================
# STEP 1: HOUSEHOLD / SURVEY DETAILS
# ============================================================
st.header("1. Household and Electricity Connection Details")
left, right = st.columns(2)

with left:
    survey_id = st.text_input("Survey / Household ID", value="H001")
    respondent = st.text_input("Respondent name (optional)")
    locality = st.text_input("Village / Area / Locality")
    survey_date = st.date_input("Survey date", value=date.today())

with right:
    state_options = list(DISCOMS.keys())
    state = st.selectbox(
        "State / Union Territory",
        state_options,
        index=state_options.index("Telangana"),
    )
    discom = st.selectbox("DISCOM / Electricity provider", DISCOMS[state])
    area_type = st.radio("Area type", ["Urban", "Rural"], horizontal=True)
    connection_category = st.selectbox(
        "Connection category", ["Domestic", "Other / Not sure"]
    )

st.caption(
    "DISCOM means Distribution Company: the electricity distribution utility "
    "that supplies power and issues the household's electricity bill."
)

# ============================================================
# STEP 2: TARIFF INPUTS
# ============================================================
st.header("2. Tariff and Bill Settings")
st.warning(
    "Electricity tariffs differ by state, DISCOM, consumer category, sanctioned load, "
    "subsidy and billing period. The sample slab rates below are illustrative only. "
    "For a closer estimate, enter the rates and charges printed on the household's bill."
)

tariff_mode = st.radio(
    "How should energy charges be estimated?",
    ["Illustrative telescopic slabs", "Custom flat rate"],
    horizontal=True,
)

slabs = []
flat_rate = 6.50

if tariff_mode == "Custom flat rate":
    flat_rate = st.number_input(
        "Average energy rate (₹ per unit / kWh)",
        min_value=0.0, max_value=100.0, value=6.50, step=0.10,
    )
else:
    st.write("Edit the sample telescopic slabs if you have the applicable tariff order.")
    slab1, slab2, slab3, slab4 = st.columns(4)
    with slab1:
        rate1 = st.number_input("First 100 units (₹/unit)", 0.0, 100.0, 4.50, 0.10)
    with slab2:
        rate2 = st.number_input("Next 100 units (₹/unit)", 0.0, 100.0, 6.00, 0.10)
    with slab3:
        rate3 = st.number_input("Next 100 units (₹/unit)", 0.0, 100.0, 7.50, 0.10)
    with slab4:
        rate4 = st.number_input("Above 300 units (₹/unit)", 0.0, 100.0, 9.00, 0.10)
    slabs = [(100, rate1), (100, rate2), (100, rate3), (None, rate4)]

fixed_charge = st.number_input(
    "Monthly fixed / customer charge (₹)", min_value=0.0,
    max_value=100000.0, value=150.0, step=10.0,
)

reference_duty = DUTY_REFERENCE_R_PER_UNIT.get(state, 0.0)
use_reference = st.checkbox(
    f"Use draft reference duty value (₹{reference_duty:.2f} per unit)",
    value=False,
)
if use_reference:
    duty_rate = reference_duty
else:
    duty_rate = st.number_input(
        "Electricity duty / tax (₹ per unit; enter from bill)",
        min_value=0.0, max_value=100.0, value=0.0, step=0.01,
    )

other_charges = st.number_input(
    "Other monthly charges / adjustments (₹)", min_value=0.0,
    max_value=100000.0, value=0.0, step=10.0,
    help="For example, meter rent or other charges shown on the bill. Do not include the fixed charge or duty twice.",
)

# ============================================================
# STEP 3: APPLIANCE USAGE
# ============================================================
st.header("3. Appliance Usage Audit")
st.write(
    "Change the default quantities, wattages and hours to match the household. "
    "For appliances with thermostats or variable operation, actual usage may differ."
)

common_df = st.data_editor(
    pd.DataFrame(COMMON_APPLIANCES),
    use_container_width=True,
    hide_index=True,
    num_rows="fixed",
    key="common_appliances_editor",
    column_config={
        "Appliance": st.column_config.TextColumn("Appliance", disabled=True),
        "Quantity": st.column_config.NumberColumn("Quantity", min_value=0, max_value=100, step=1),
        "Wattage (W)": st.column_config.NumberColumn("Wattage (W)", min_value=0, max_value=50000, step=1),
        "Hours/day": st.column_config.NumberColumn("Hours/day", min_value=0.0, max_value=24.0, step=0.5),
    },
)

st.subheader("Add other appliances")
st.write("Examples: electric iron, air cooler, water purifier, computer, EV charger.")
custom_df = st.data_editor(
    pd.DataFrame(
        [{"Appliance": "", "Quantity": 1, "Wattage (W)": 100, "Hours/day": 1.0}]
    ),
    use_container_width=True,
    hide_index=True,
    num_rows="dynamic",
    key="custom_appliances_editor",
    column_config={
        "Appliance": st.column_config.TextColumn("Appliance name"),
        "Quantity": st.column_config.NumberColumn("Quantity", min_value=0, max_value=100, step=1),
        "Wattage (W)": st.column_config.NumberColumn("Wattage (W)", min_value=0, max_value=50000, step=1),
        "Hours/day": st.column_config.NumberColumn("Hours/day", min_value=0.0, max_value=24.0, step=0.5),
    },
)

common_results = appliance_calculations(common_df)
custom_results = appliance_calculations(custom_df)
all_results = pd.concat([common_results, custom_results], ignore_index=True)
total_monthly_units = float(all_results["Monthly Units (kWh)"].sum()) if not all_results.empty else 0.0
total_daily_units = total_monthly_units / 30.0

energy_charge, electricity_duty, estimated_bill = estimate_bill(
    total_monthly_units,
    tariff_mode,
    flat_rate,
    slabs,
    fixed_charge,
    duty_rate,
    other_charges,
)

if total_monthly_units > 0:
    all_results["Share of Use (%)"] = (
        all_results["Monthly Units (kWh)"] / total_monthly_units * 100
    )
    all_results["Estimated Energy Cost (₹)"] = (
        all_results["Monthly Units (kWh)"] / total_monthly_units * energy_charge
    )
else:
    all_results["Share of Use (%)"] = 0.0
    all_results["Estimated Energy Cost (₹)"] = 0.0

# ============================================================
# STEP 4: RESULTS AND VISUAL ANALYSIS
# ============================================================
st.header("4. Household Energy Analysis")
m1, m2, m3 = st.columns(3)
m1.metric("Estimated daily use", f"{total_daily_units:.2f} kWh")
m2.metric("Estimated monthly use", f"{total_monthly_units:.1f} units")
m3.metric("Estimated monthly bill", f"₹{estimated_bill:,.2f}")

st.subheader("Estimated bill breakdown")
bill_df = pd.DataFrame(
    {
        "Bill component": [
            "Energy charges",
            "Fixed charge",
            "Electricity duty / tax",
            "Other charges",
            "Estimated total",
        ],
        "Amount (₹)": [
            energy_charge,
            fixed_charge,
            electricity_duty,
            other_charges,
            estimated_bill,
        ],
    }
)
st.dataframe(bill_df, use_container_width=True, hide_index=True)

st.subheader("Appliance-by-appliance consumption")
if not all_results.empty:
    display_results = all_results.copy()
    numeric_columns = display_results.select_dtypes(include="number").columns
    display_results[numeric_columns] = display_results[numeric_columns].round(2)
    st.dataframe(display_results, use_container_width=True, hide_index=True)
else:
    st.info("Enter appliance details to calculate consumption.")

if total_monthly_units > 0:
    chart_data = all_results[all_results["Monthly Units (kWh)"] > 0].copy()
    chart_left, chart_right = st.columns(2)

    with chart_left:
        fig, ax = plt.subplots(figsize=(7, 5))
        ax.pie(
            chart_data["Monthly Units (kWh)"],
            labels=chart_data["Appliance"],
            autopct="%1.1f%%",
            startangle=140,
        )
        ax.set_title("Share of monthly electricity use")
        st.pyplot(fig)
        plt.close(fig)

    with chart_right:
        top = chart_data.sort_values("Monthly Units (kWh)", ascending=True).tail(8)
        fig, ax = plt.subplots(figsize=(7, 5))
        ax.barh(top["Appliance"], top["Monthly Units (kWh)"])
        ax.set_xlabel("Monthly units (kWh)")
        ax.set_title("Highest-consuming appliances")
        fig.tight_layout()
        st.pyplot(fig)
        plt.close(fig)

    st.subheader("Top electricity consumers")
    top_consumers = all_results.sort_values(
        "Monthly Units (kWh)", ascending=False
    ).head(5)
    for _, item in top_consumers.iterrows():
        share = item["Share of Use (%)"]
        st.write(
            f"**{item['Appliance']}** — "
            f"{item['Monthly Units (kWh)']:.1f} units/month "
            f"({share:.1f}% of estimated use)"
        )

# ============================================================
# STEP 5: COMMUNITY ENERGY-SAVING RECOMMENDATIONS
# ============================================================
st.header("5. Personalized Energy-Saving Recommendations")
if not all_results.empty and total_monthly_units > 0:
    largest = all_results.loc[all_results["Monthly Units (kWh)"].idxmax()]
    name = largest["Appliance"].lower()
    st.markdown(f"**Priority appliance:** {largest['Appliance']}")

    if "air conditioner" in name:
        st.warning(
            "Set the AC to a comfortable moderate temperature (often around 24–26°C), "
            "clean filters regularly, close doors/windows while cooling, and use a timer."
        )
    elif "geyser" in name or "water heater" in name:
        st.info(
            "Avoid leaving the water heater on unnecessarily. Use a suitable thermostat "
            "setting, repair leaking hot-water taps, and insulate hot-water pipes where practical."
        )
    elif "refrigerator" in name:
        st.info(
            "Check door seals, avoid frequent door opening, allow air circulation around "
            "the refrigerator, and do not put hot food directly inside."
        )
    elif "fan" in name:
        st.info(
            "Switch fans off in unoccupied rooms and consider efficient BEE-rated "
            "BLDC fans when replacing older units."
        )
    elif "water pump" in name:
        st.info(
            "Avoid tank overflow, repair leaks, and switch the pump off when the tank is full. "
            "A float switch can help where appropriate."
        )
    elif "bulb" in name or "light" in name:
        st.info("Use LED lamps, switch off lights in empty rooms, and use daylight where possible.")
    else:
        st.info(
            "Check whether the appliance can be used for fewer hours, operated on an efficient "
            "setting, maintained, or replaced with a more efficient model."
        )

    heavy = all_results[all_results["Wattage (W)"] >= 1000]
    if not heavy.empty:
        heavy_names = ", ".join(heavy["Appliance"].astype(str).tolist())
        st.warning(
            f"High-power appliances detected: {heavy_names}. Avoid operating several "
            "high-power appliances simultaneously if the household wiring or sanctioned "
            "load is not designed for it. Follow the DISCOM's safety guidance."
        )

    st.markdown("**General actions for the household**")
    st.markdown(
        "- Switch off lights, fans and appliances when they are not needed.\n"
        "- Unplug chargers and devices when practical; use safe switched power strips.\n"
        "- Prefer energy-efficient appliances with appropriate BEE star labels.\n"
        "- Compare the estimated use with the actual meter reading and bill each month.\n"
        "- Share these findings with other households as part of the community awareness activity."
    )
else:
    st.info("Recommendations will appear after appliance usage has been entered.")

# ============================================================
# STEP 6: SAVINGS SIMULATOR
# ============================================================
st.header("6. Electricity Savings Simulator")
reduction_percent = st.slider(
    "What reduction in monthly electricity use would you like to explore?",
    min_value=0, max_value=50, value=10, step=5,
)
simulated_units = total_monthly_units * (1 - reduction_percent / 100)
_, simulated_duty, simulated_bill = estimate_bill(
    simulated_units,
    tariff_mode,
    flat_rate,
    slabs,
    fixed_charge,
    duty_rate,
    other_charges,
)
monthly_saving = max(estimated_bill - simulated_bill, 0.0)
s1, s2, s3 = st.columns(3)
s1.metric("Simulated monthly use", f"{simulated_units:.1f} units")
s2.metric("Estimated monthly saving", f"₹{monthly_saving:,.2f}")
s3.metric("Estimated annual saving", f"₹{monthly_saving * 12:,.2f}")

# ============================================================
# STEP 7: STANDBY POWER CHECK
# ============================================================
st.header("7. Standby Power Check")
st.write(
    "Standby consumption is electricity used by devices that remain connected or "
    "in standby mode. Actual standby wattage varies by model."
)
standby_watts = {
    "Television": 1.0,
    "Set-top box": 5.0,
    "Laptop charger": 1.0,
    "Desktop computer": 3.0,
    "Gaming console": 2.0,
    "Microwave clock": 3.0,
    "Wi-Fi router": 8.0,
    "Printer": 2.0,
}
selected_standby = st.multiselect(
    "Select devices that remain on standby",
    list(standby_watts.keys()),
)
standby_hours = st.slider(
    "Standby hours per day", min_value=1, max_value=24, value=24
)
if selected_standby:
    standby_watts_total = sum(standby_watts[item] for item in selected_standby)
    standby_units = standby_watts_total * standby_hours * 30 / 1000
    if tariff_mode == "Custom flat rate":
        standby_rate = flat_rate
    else:
        standby_rate = slabs[0][1] if standby_units <= 100 else (
            slabs[1][1] if standby_units <= 200 else (
                slabs[2][1] if standby_units <= 300 else slabs[3][1]
            )
        )
    b1, b2 = st.columns(2)
    b1.metric("Estimated standby use", f"{standby_units:.2f} kWh/month")
    b2.metric("Approximate energy cost", f"₹{standby_units * standby_rate:.2f}/month")
else:
    st.caption("Select standby devices to estimate their possible monthly energy use.")

# ============================================================
# STEP 8: METER READING COMPARISON
# ============================================================
st.header("8. Compare with the Actual Electricity Meter")
st.write(
    "Enter two meter readings from the bill or meter. The current reading must be "
    "greater than or equal to the previous reading."
)
meter1, meter2, meter3 = st.columns(3)
with meter1:
    previous_reading = st.number_input(
        "Previous reading (kWh)", min_value=0.0, value=0.0, step=1.0
    )
with meter2:
    current_reading = st.number_input(
        "Current reading (kWh)", min_value=0.0, value=0.0, step=1.0
    )
with meter3:
    billing_days = st.number_input(
        "Number of days between readings", min_value=1, max_value=366, value=30
    )

if current_reading >= previous_reading:
    actual_units = current_reading - previous_reading
    actual_monthly_units = actual_units / billing_days * 30
    a1, a2, a3 = st.columns(3)
    a1.metric("Actual units in period", f"{actual_units:.1f} kWh")
    a2.metric("Average daily use", f"{actual_units / billing_days:.2f} kWh")
    a3.metric("30-day equivalent", f"{actual_monthly_units:.1f} kWh")
    if total_monthly_units > 0:
        difference = actual_monthly_units - total_monthly_units
        st.write(f"Difference between meter-based and appliance estimate: **{difference:+.1f} units/month**.")
        st.caption(
            "A difference is expected because appliance wattage and usage are estimates, "
            "and some loads may have been missed."
        )
else:
    st.error("The current meter reading cannot be lower than the previous reading.")

# ============================================================
# STEP 9: ELECTRICITY BILL PHOTO / OCR
# ============================================================
st.header("9. Upload an Electricity Bill for Review")
st.write(
    "Upload a clear image of the bill. If OCR is available on this computer, "
    "the app will try to extract text. You can also enter the bill values manually."
)
bill_image = st.file_uploader(
    "Upload bill image (JPG, JPEG or PNG)",
    type=["jpg", "jpeg", "png"],
)
ocr_text = ""
if bill_image is not None:
    st.image(bill_image, caption="Uploaded electricity bill", use_container_width=True)
    if OCR_AVAILABLE:
        try:
            image_object = Image.open(io.BytesIO(bill_image.getvalue()))
            ocr_text = pytesseract.image_to_string(image_object)
            if ocr_text.strip():
                st.text_area("Text extracted from bill (check it for accuracy)", ocr_text, height=180)
            else:
                st.warning("No readable text was detected. Try a sharper, well-lit image.")
        except Exception as exc:
            st.warning(
                "OCR could not process this image. You can still enter the bill details manually. "
                f"Technical detail: {exc}"
            )
    else:
        st.warning(
            "OCR support is not installed or configured. The image is displayed, but text "
            "cannot be extracted automatically. Enter the values below manually."
        )

bill_col1, bill_col2, bill_col3 = st.columns(3)
with bill_col1:
    bill_units = st.number_input(
        "Units shown on bill (kWh)", min_value=0.0, value=0.0, step=1.0,
        key="uploaded_bill_units",
    )
with bill_col2:
    bill_amount = st.number_input(
        "Total amount shown on bill (₹)", min_value=0.0, value=0.0, step=10.0,
        key="uploaded_bill_amount",
    )
with bill_col3:
    bill_period_days = st.number_input(
        "Bill period (days)", min_value=1, max_value=366, value=30,
        key="uploaded_bill_days",
    )
if bill_units > 0:
    st.write(f"Bill-based average daily consumption: **{bill_units / bill_period_days:.2f} kWh/day**.")
    if total_monthly_units > 0:
        st.write(
            f"Difference between bill units and appliance estimate: "
            f"**{bill_units - total_monthly_units:+.1f} units** "
            "(bill period may not be exactly 30 days)."
        )
if bill_amount > 0:
    st.write(f"Bill amount entered: **₹{bill_amount:,.2f}**.")
    if estimated_bill > 0:
        st.write(
            f"Difference from this app's estimated bill: "
            f"**₹{bill_amount - estimated_bill:+,.2f}**."
        )

# ============================================================
# STEP 10: COMMUNITY SURVEY EXPORT
# ============================================================
st.header("10. Export Community Survey Record")
st.write(
    "Download the household summary and appliance-level data. Keep one record per household "
    "and combine the downloaded files for your Community Service Project report."
)

summary = {
    "Survey_ID": survey_id,
    "Survey_Date": str(survey_date),
    "Respondent": respondent,
    "Locality": locality,
    "State": state,
    "DISCOM": discom,
    "Area_Type": area_type,
    "Connection_Category": connection_category,
    "Tariff_Mode": tariff_mode,
    "Monthly_Estimated_Units_kWh": round(total_monthly_units, 2),
    "Estimated_Energy_Charge_INR": round(energy_charge, 2),
    "Estimated_Fixed_Charge_INR": round(fixed_charge, 2),
    "Estimated_Duty_INR": round(electricity_duty, 2),
    "Other_Charges_INR": round(other_charges, 2),
    "Estimated_Total_Bill_INR": round(estimated_bill, 2),
    "Bill_Units_Entered_kWh": round(bill_units, 2),
    "Bill_Amount_Entered_INR": round(bill_amount, 2),
}
summary_df = pd.DataFrame([summary])

csv_summary = summary_df.to_csv(index=False).encode("utf-8-sig")
csv_appliances = all_results.to_csv(index=False).encode("utf-8-sig")

download1, download2 = st.columns(2)
with download1:
    st.download_button(
        "⬇️ Download household summary (CSV)",
        data=csv_summary,
        file_name=f"electricity_audit_{safe_filename(survey_id)}.csv",
        mime="text/csv",
        use_container_width=True,
    )
with download2:
    st.download_button(
        "⬇️ Download appliance details (CSV)",
        data=csv_appliances,
        file_name=f"appliance_details_{safe_filename(survey_id)}.csv",
        mime="text/csv",
        use_container_width=True,
    )

# ============================================================
# EXPLANATION AND DISCLAIMER
# ============================================================
with st.expander("Understand the terms used in this application"):
    st.markdown(
        """
        - **Unit / kWh:** One electricity unit is one kilowatt-hour (1 kWh).
        - **Watt (W):** A measure of an appliance's power rating.
        - **DISCOM:** Distribution Company that supplies electricity and bills consumers.
        - **Energy charge:** Amount charged for electricity consumed, usually based on tariff slabs.
        - **Telescopic slab:** Different portions of consumption are charged at different rates.
        - **Fixed charge:** A recurring charge that may depend on connection category or sanctioned load.
        - **Electricity duty / tax:** A state-specific charge; its basis and rate depend on applicable rules.
        - **Standby power:** Electricity consumed while a device is idle but still connected or in standby.
        - **Peak demand:** A period when electricity demand is high. Avoid unsafe overloading and follow DISCOM advice.
        """
    )

st.divider()
st.subheader("Important project disclaimer")
st.caption(
    "This application is an educational and community-awareness tool. Its appliance calculations "
    "assume 30 days per month and the entered wattage and operating hours. The sample tariff slabs "
    "and duty references are not guaranteed to match any current DISCOM tariff. Actual bills may "
    "include subsidies, minimum charges, fuel adjustments, meter rent, taxes, rebates and other "
    "items. Always use the household's current tariff order and bill for official amounts. "
    "Do not upload or retain personal account numbers or other sensitive bill details in public reports."
)
st.caption("Smart Home Electricity Auditor | Community Service Project")
