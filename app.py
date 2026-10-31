
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import date

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
    "An intelligent household electricity auditing system "
    "with appliance analysis, tariff estimation and personalized savings."
)

st.caption("Tariff reference year: FY 2026–27 | Billing model: 30-day estimate")

# ==========================================================
# DISCOM DATABASE
# ==========================================================

DISCOMS = {
    "Andhra Pradesh": ["APEPDCL", "APSPDCL", "APCPDCL / Other"],
    "Telangana": ["TGSPDCL", "TGNPDCL"],
    "Karnataka": ["BESCOM", "MESCOM", "HESCOM", "GESCOM", "CESC"],
    "Tamil Nadu": ["TNPDCL / TANGEDCO"],
    "Maharashtra": ["MSEDCL", "BEST", "Adani Electricity", "Tata Power"],
    "Delhi": ["BRPL", "BYPL", "TPDDL", "NDMC"],
    "Kerala": ["KSEB"],
    "Gujarat": ["DGVCL", "MGVCL", "PGVCL", "UGVCL", "Torrent Power"],
    "Rajasthan": ["JVVNL", "AVVNL", "JDVVNL"],
    "Punjab": ["PSPCL"],
    "Haryana": ["DHBVN", "UHBVN"],
    "Uttar Pradesh": ["PVVNL", "MVVNL", "DVVNL", "PuVVNL", "KESCO"],
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
# OFFICIAL TARIFF CONFIGURATION
# ==========================================================
#
# Each tariff schedule contains:
# upper_limit: maximum units covered by the slab
# rate: price per unit in that slab
#
# The calculator uses telescopic (marginal slab) calculation.
#
# AP: FY 2026-27 general domestic LT schedule.
# Telangana: only the published <=100-unit category is
# configured here. Do not extrapolate it above 100 units.
#
# Fixed charges and statutory levies can vary by load,
# phase, category and other conditions.
# ==========================================================

TARIFFS = {
    ("Andhra Pradesh", "APEPDCL"): {
        "name": "Category I(A) Domestic LT",
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
        "source": "APERC FY 2026-27 Retail Supply Tariff Order",
        "url": "https://aperc.gov.in/page/Tariff_Orders",
        "effective": "01-04-2026",
        "note": "Fixed charge is a starter reference; verify applicable load/category."
    },
    ("Andhra Pradesh", "APSPDCL"): {
        "name": "Category I(A) Domestic LT",
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
        "source": "APERC FY 2026-27 Retail Supply Tariff Order",
        "url": "https://aperc.gov.in/page/Tariff_Orders",
        "effective": "01-04-2026",
        "note": "Fixed charge is a starter reference; verify applicable load/category."
    },
    ("Telangana", "TGSPDCL"): {
        "name": "LT-I(A) Domestic - up to 100 units",
        "slabs": [
            {"upper": 50, "rate": 1.95},
            {"upper": 100, "rate": 3.10},
        ],
        "fixed": 10.0,
        "max_units": 100,
        "source": "TGERC FY 2026-27 Retail Supply Tariff Order",
        "url": "https://www.tgerc.telangana.gov.in/tariffschdule.php",
        "effective": "01-04-2026",
        "note": "This schedule is only for eligible consumption not exceeding 100 units."
    },
    ("Telangana", "TGNPDCL"): {
        "name": "LT-I(A) Domestic - up to 100 units",
        "slabs": [
            {"upper": 50, "rate": 1.95},
            {"upper": 100, "rate": 3.10},
        ],
        "fixed": 10.0,
        "max_units": 100,
        "source": "TGERC FY 2026-27 Retail Supply Tariff Order",
        "url": "https://www.tgerc.telangana.gov.in/tariffschdule.php",
        "effective": "01-04-2026",
        "note": "This schedule is only for eligible consumption not exceeding 100 units."
    }
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
# TARIFF CALCULATION FUNCTIONS
# ==========================================================

def calculate_slab_charges(units, slabs):
    """Calculate telescopic energy charges."""
    remaining = max(0.0, float(units))
    previous_limit = 0.0
    total = 0.0
    breakdown = []

    for slab in slabs:
        upper = slab["upper"]
        rate = float(slab["rate"])

        if upper is None:
            slab_units = remaining
        else:
            slab_units = min(
                remaining,
                max(0.0, float(upper) - previous_limit)
            )

        charge = slab_units * rate

        if slab_units > 0:
            breakdown.append({
                "Slab": (
                    f"{previous_limit:g} units onwards"
                    if upper is None
                    else f"{previous_limit:g}-{upper:g} units"
                ),
                "Units": slab_units,
                "Rate (₹/unit)": rate,
                "Charge (₹)": charge
            })

        total += charge
        remaining -= slab_units

        if upper is not None:
            previous_limit = float(upper)

        if remaining <= 0:
            break

    if remaining > 0:
        raise ValueError("Tariff configuration does not cover all units.")

    return total, pd.DataFrame(breakdown)


def calculate_bill(
    units,
    slabs,
    fixed_charge,
    duty_type,
    duty_value,
    adjustment_type,
    adjustment_value,
    other_charges,
    subsidy
):
    energy, slab_details = calculate_slab_charges(units, slabs)

    if duty_type == "Percentage of energy charge":
        duty = energy * duty_value / 100
    elif duty_type == "₹ per unit":
        duty = units * duty_value
    else:
        duty = 0.0

    if adjustment_type == "₹ per unit":
        adjustment = units * adjustment_value
    elif adjustment_type == "Percentage of energy charge":
        adjustment = energy * adjustment_value / 100
    else:
        adjustment = 0.0

    before_subsidy = (
        energy + fixed_charge + duty + adjustment + other_charges
    )

    subsidy_applied = min(
        max(0.0, subsidy),
        before_subsidy
    )

    total = before_subsidy - subsidy_applied

    return {
        "energy": energy,
        "fixed": fixed_charge,
        "duty": duty,
        "adjustment": adjustment,
        "other": other_charges,
        "subsidy": subsidy_applied,
        "total": total,
        "slabs": slab_details
    }


# ==========================================================
# APPLIANCE CALCULATIONS
# ==========================================================

def calculate_appliances(df, days):
    results = []

    for _, row in df.iterrows():
        name = str(row["Appliance"]).strip()

        if not name:
            continue

        quantity = float(row["Quantity"])
        wattage = float(row["Wattage (W)"])
        hours = float(row["Hours/day"])

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
            "Monthly Units": monthly_units
        })

    return pd.DataFrame(results)


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
        ["Domestic - General", "Domestic - BPL/Lifeline", "Other"]
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
    "Sanctioned load is used for tariff verification where applicable. "
    "It is not the same as monthly energy consumption."
)

# ==========================================================
# STEP 2 - APPLIANCE INPUTS
# ==========================================================

st.divider()
st.header("2. Household Appliance Usage")

st.write(
    "Edit the common appliances below. Wattage should ideally "
    "come from the appliance nameplate or manufacturer specification."
)

common_df = pd.DataFrame(
    COMMON_APPLIANCES,
    columns=["Appliance", "Quantity", "Wattage (W)", "Hours/day"]
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
        )
    }
)

st.subheader("➕ Add Extra Appliances")

st.write(
    "Add any appliance not listed above: iron box, air cooler, "
    "desktop, EV charger, water purifier, hair dryer, etc."
)

custom_df = pd.DataFrame([
    {
        "Appliance": "",
        "Quantity": 1,
        "Wattage (W)": 100,
        "Hours/day": 1.0
    }
])

custom_df = st.data_editor(
    custom_df,
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
        )
    }
)

# ==========================================================
# STEP 3 - CONSUMPTION
# ==========================================================

st.divider()
st.header("3. Monthly Electricity Consumption")

common_results = calculate_appliances(common_df, billing_days)
custom_results = calculate_appliances(custom_df, billing_days)

all_results = pd.concat(
    [common_results, custom_results],
    ignore_index=True
)

if all_results.empty:
    st.error("Please enter at least one appliance.")
    st.stop()

total_units = all_results["Monthly Units"].sum()

st.metric(
    "Estimated consumption for billing period",
    f"{total_units:.2f} kWh"
)

st.metric(
    "Average daily consumption",
    f"{total_units / billing_days:.2f} kWh/day"
)

# ==========================================================
# STEP 4 - TARIFF ENGINE
# ==========================================================

st.divider()
st.header("4. Automatic Tariff Engine")

tariff_key = (state, discom)
tariff = TARIFFS.get(tariff_key)

if tariff and category != "Domestic - General":
    tariff = None

if tariff:
    st.success(f"Configured tariff: {tariff['name']}")
    st.write(f"Effective date: {tariff['effective']}")
    st.write(f"Source: {tariff['source']}")
    st.markdown(f"[Open tariff order / schedule]({tariff['url']})")
    st.caption(tariff["note"])

    if (
        tariff["max_units"] is not None
        and total_units > tariff["max_units"]
    ):
        st.error(
            f"This configured tariff is valid only up to "
            f"{tariff['max_units']} units. Your estimated usage is "
            f"{total_units:.2f} units. A higher-consumption schedule "
            "must be selected; the application will not extrapolate "
            "the low-consumption tariff."
        )
        tariff = None

if not tariff:
    st.warning(
        "No verified automatic tariff is configured for this "
        "connection/category/consumption. Configure the schedule "
        "below using the current official tariff order."
    )

    st.subheader("Configure tariff slabs")

    default_slabs = pd.DataFrame([
        {"Upper limit (units)": 100.0, "Rate (₹/unit)": 3.0},
        {"Upper limit (units)": 200.0, "Rate (₹/unit)": 5.0},
        {"Upper limit (units)": 300.0, "Rate (₹/unit)": 7.0},
        {"Upper limit (units)": 400.0, "Rate (₹/unit)": 8.0},
        {"Upper limit (units)": 0.0, "Rate (₹/unit)": 9.0}
    ])

    st.caption(
        "Replace the example values with the rates and boundaries "
        "from the applicable official tariff order. Enter 0 as the "
        "upper limit for the final unlimited slab."
    )

    configured_slabs = st.data_editor(
        default_slabs,
        key=f"tariff_editor_{state}_{discom}_{category}",
        num_rows="dynamic",
        hide_index=True,
        use_container_width=True
    )

    slabs = []

    for _, row in configured_slabs.iterrows():
        upper = float(row["Upper limit (units)"])
        rate = float(row["Rate (₹/unit)"])

        if rate < 0 or upper < 0:
            st.error("Tariff values cannot be negative.")
            st.stop()

        slabs.append({
            "upper": None if upper == 0 else upper,
            "rate": rate
        })

    # Require the unlimited slab to be last.
    unlimited_positions = [
        i for i, slab in enumerate(slabs)
        if slab["upper"] is None
    ]

    if len(unlimited_positions) != 1 or unlimited_positions[0] != len(slabs) - 1:
        st.error(
            "The tariff must have exactly one unlimited final slab. "
            "Set its upper limit to 0."
        )
        st.stop()

    finite_limits = [
        slab["upper"] for slab in slabs[:-1]
    ]

    if any(
        finite_limits[i] <= finite_limits[i - 1]
        for i in range(1, len(finite_limits))
    ):
        st.error("Slab upper limits must be in increasing order.")
        st.stop()

    tariff_fixed = st.number_input(
        "Monthly fixed charge (₹)",
        min_value=0.0,
        value=0.0,
        step=10.0,
        key=f"fixed_{state}_{discom}"
    )

    tariff_source = st.text_input(
        "Official tariff order source URL",
        placeholder="Paste official regulator / DISCOM order URL"
    )

    tariff_effective = st.text_input(
        "Tariff effective date",
        placeholder="DD-MM-YYYY"
    )

else:
    slabs = tariff["slabs"]
    tariff_fixed = float(tariff["fixed"])
    tariff_source = tariff["url"]
    tariff_effective = tariff["effective"]

    st.info(
        f"Configured fixed-charge reference: ₹{tariff_fixed:.2f}. "
        "Confirm this against your connection's load and phase."
    )

# ==========================================================
# STEP 5 - ADDITIONAL BILL COMPONENTS
# ==========================================================

st.divider()
st.header("5. Duty, Adjustments and Subsidies")

st.write(
    "Only enter values supported by your applicable bill or "
    "official notification. Unknown charges are not assumed to be zero."
)

duty_options = [
    "Not included / Unknown",
    "Percentage of energy charge",
    "₹ per unit"
]

duty_type = st.selectbox(
    "Electricity duty calculation",
    duty_options
)

duty_value = 0.0

if duty_type != "Not included / Unknown":
    duty_value = st.number_input(
        "Duty value",
        min_value=0.0,
        max_value=100.0,
        value=0.0,
        step=0.1,
        help="Enter the value from the relevant notification or bill."
    )

adjustment_type = st.selectbox(
    "Fuel / Power Purchase Adjustment",
    [
        "Not included / Unknown",
        "₹ per unit",
        "Percentage of energy charge"
    ]
)

adjustment_value = 0.0

if adjustment_type != "Not included / Unknown":
    adjustment_value = st.number_input(
        "Adjustment value",
        min_value=0.0,
        max_value=100.0,
        value=0.0,
        step=0.01
    )

other_charges = st.number_input(
    "Other monthly charges (₹)",
    min_value=0.0,
    max_value=50000.0,
    value=0.0,
    step=10.0,
    help="Meter rent, applicable surcharge, etc. Avoid duplicating charges."
)

subsidy = st.number_input(
    "Eligible government subsidy / rebate (₹)",
    min_value=0.0,
    max_value=50000.0,
    value=0.0,
    step=10.0,
    help="Enter only a subsidy for which the consumer is eligible."
)

if st.button("Calculate My Electricity Bill", type="primary", use_container_width=True):

    try:
        result = calculate_bill(
            total_units,
            slabs,
            tariff_fixed,
            duty_type,
            duty_value,
            adjustment_type,
            adjustment_value,
            other_charges,
            subsidy
        )

        st.session_state["bill_result"] = result
        st.session_state["bill_units"] = total_units
        st.session_state["bill_state"] = state
        st.session_state["bill_discom"] = discom
        st.session_state["bill_source"] = tariff_source
        st.session_state["bill_effective"] = tariff_effective

    except ValueError as error:
        st.error(str(error))

# ==========================================================
# STEP 6 - BILL RESULTS
# ==========================================================

if "bill_result" in st.session_state:

    result = st.session_state["bill_result"]

    st.divider()
    st.header("6. Your Estimated Electricity Bill")

    st.metric(
        "Estimated Total Bill",
        f"₹{result['total']:,.2f}"
    )

    st.metric(
        "Consumption",
        f"{st.session_state['bill_units']:.2f} units"
    )

    bill_table = pd.DataFrame({
        "Component": [
            "Energy charges",
            "Fixed charges",
            "Electricity duty",
            "Fuel / power purchase adjustment",
            "Other charges",
            "Government subsidy / rebate",
            "Estimated payable amount"
        ],
        "Amount (₹)": [
            result["energy"],
            result["fixed"],
            result["duty"],
            result["adjustment"],
            result["other"],
            -result["subsidy"],
            result["total"]
        ]
    })

    st.dataframe(
        bill_table.round(2),
        use_container_width=True,
        hide_index=True
    )

    st.subheader("Tariff Slab Calculation")

    if not result["slabs"].empty:
        st.dataframe(
            result["slabs"].round(2),
            use_container_width=True,
            hide_index=True
        )

    st.caption(
        f"State: {st.session_state['bill_state']} | "
        f"DISCOM: {st.session_state['bill_discom']}"
    )

    st.caption(
        f"Tariff source: {st.session_state['bill_source']} | "
        f"Effective date: {st.session_state['bill_effective']}"
    )

    if duty_type == "Not included / Unknown":
        st.warning(
            "Electricity duty was not included because a verified "
            "applicable value was not supplied."
        )

    if adjustment_type == "Not included / Unknown":
        st.warning(
            "Monthly fuel/power purchase adjustments were not included."
        )

# ==========================================================
# STEP 7 - APPLIANCE ANALYSIS
# ==========================================================

st.divider()
st.header("7. Appliance Consumption Analysis")

all_results["Energy Cost (₹)"] = (
    all_results["Monthly Units"] *
    (
        result["energy"] / total_units
        if "bill_result" in st.session_state and total_units > 0
        else 0
    )
)

display_results = all_results.copy()

display_results["Daily Units"] = display_results["Daily Units"].round(2)
display_results["Monthly Units"] = display_results["Monthly Units"].round(2)
display_results["Energy Cost (₹)"] = display_results["Energy Cost (₹)"].round(2)

st.dataframe(
    display_results,
    use_container_width=True,
    hide_index=True
)

if total_units > 0:

    chart_data = all_results[
        all_results["Monthly Units"] > 0
    ]

    fig, ax = plt.subplots(figsize=(9, 6))

    ax.pie(
        chart_data["Monthly Units"],
        labels=chart_data["Appliance"],
        autopct="%1.1f%%",
        startangle=140
    )

    ax.set_title("Household Electricity Consumption")
    st.pyplot(fig)

    st.subheader("Top 5 Electricity Consumers")

    top = chart_data.sort_values(
        "Monthly Units",
        ascending=False
    ).head(5)

    for _, row in top.iterrows():
        share = row["Monthly Units"] / total_units * 100

        st.write(
            f"**{row['Appliance']}** — "
            f"{row['Monthly Units']:.2f} units "
            f"({share:.1f}%)"
        )

# ==========================================================
# STEP 8 - SAVINGS SIMULATOR
# ==========================================================

st.divider()
st.header("8. Electricity Savings Simulator")

reduction = st.slider(
    "How much do you want to reduce consumption?",
    0, 50, 10, 5
)

new_units = total_units * (1 - reduction / 100)

if "bill_result" in st.session_state:

    new_bill_result = calculate_bill(
        new_units,
        slabs,
        tariff_fixed,
        duty_type,
        duty_value,
        adjustment_type,
        adjustment_value,
        other_charges,
        subsidy
    )

    monthly_saving = (
        result["total"] - new_bill_result["total"]
    )

    annual_saving = monthly_saving * 12

    c1, c2, c3 = st.columns(3)

    c1.metric("New monthly units", f"{new_units:.2f}")
    c2.metric("Monthly savings", f"₹{monthly_saving:,.2f}")
    c3.metric("Annual savings", f"₹{annual_saving:,.2f}")

else:
    st.info(
        "Calculate your bill first to view the savings estimate."
    )

# ==========================================================
# STEP 9 - ACTUAL BILL COMPARISON
# ==========================================================

st.divider()
st.header("9. Compare with Your Actual Electricity Bill")

actual_bill = st.number_input(
    "Enter actual payable amount from your electricity bill (₹)",
    min_value=0.0,
    value=0.0,
    step=100.0
)

if actual_bill > 0 and "bill_result" in st.session_state:

    difference = actual_bill - result["total"]

    if difference > 0:
        st.warning(
            f"Your actual bill is ₹{difference:,.2f} higher "
            "than this estimate."
        )
    elif difference < 0:
        st.info(
            f"Your actual bill is ₹{abs(difference):,.2f} lower "
            "than this estimate."
        )
    else:
        st.success("Your estimated bill matches your actual bill.")

    st.caption(
        "Differences can result from meter readings, billing days, "
        "subsidies, arrears, adjustments, load-based charges and "
        "other tariff conditions."
    )

# ==========================================================
# STEP 10 - METER READING
# ==========================================================

st.divider()
st.header("10. Actual Meter Reading Analysis")

m1, m2 = st.columns(2)

with m1:
    previous = st.number_input(
        "Previous meter reading",
        min_value=0.0,
        value=0.0
    )

with m2:
    current = st.number_input(
        "Current meter reading",
        min_value=0.0,
        value=0.0
    )

if current >= previous:

    meter_units = current - previous

    st.metric(
        "Actual meter consumption",
        f"{meter_units:.2f} units"
    )

    if meter_units > 0:
        difference = meter_units - total_units

        st.write(
            f"Difference between meter and appliance estimate: "
            f"{difference:.2f} units"
        )

else:
    st.error(
        "Current meter reading cannot be lower than previous reading."
    )

# ==========================================================
# STEP 11 - SMART RECOMMENDATIONS
# ==========================================================

st.divider()
st.header("11. Personalized Energy-Saving Recommendations")

top_appliances = all_results.sort_values(
    "Monthly Units",
    ascending=False
)

if not top_appliances.empty:

    biggest = top_appliances.iloc[0]

    st.info(
        f"Your biggest electricity consumer is "
        f"**{biggest['Appliance']}**, using "
        f"**{biggest['Monthly Units']:.2f} units** "
        "during the selected billing period."
    )

    for _, row in top_appliances.head(5).iterrows():

        name = row["Appliance"].lower()

        if "air conditioner" in name or name == "ac":
            st.write(
                "❄️ AC: Use a moderate temperature, clean filters "
                "regularly and close doors/windows while cooling."
            )

        elif "geyser" in name or "water heater" in name:
            st.write(
                "🚿 Geyser: Use a timer and avoid keeping it "
                "switched on unnecessarily."
            )

        elif "refrigerator" in name:
            st.write(
                "🧊 Refrigerator: Maintain door seals and avoid "
                "frequent unnecessary opening."
            )

        elif "fan" in name:
            st.write(
                "🌀 Fans: Consider energy-efficient BLDC fans "
                "when replacing older models."
            )

        elif "pump" in name:
            st.write(
                "🚰 Water pump: Check for leakage and avoid "
                "unnecessary pumping."
            )

        elif "bulb" in name or "light" in name:
            st.write(
                "💡 Lighting: Use LED lights and switch off "
                "unoccupied rooms."
            )

# ==========================================================
# STEP 12 - DOWNLOAD REPORT
# ==========================================================

st.divider()
st.header("12. Download Your Energy Audit Report")

report = all_results.copy()

report["Daily Units"] = report["Daily Units"].round(3)
report["Monthly Units"] = report["Monthly Units"].round(3)

csv = report.to_csv(index=False).encode("utf-8")

st.download_button(
    "📥 Download Appliance Analysis (CSV)",
    data=csv,
    file_name="electricity_audit_report.csv",
    mime="text/csv",
    use_container_width=True
)

if "bill_result" in st.session_state:

    bill_csv = bill_table.to_csv(index=False).encode("utf-8")

    st.download_button(
        "📥 Download Estimated Bill (CSV)",
        data=bill_csv,
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
    not an official DISCOM billing system. The accuracy of the
    estimate depends on the correctness and completeness of
    appliance and tariff information.
    """
)

st.markdown(
    """
    **Official reference resources:**

    - [Central Electricity Authority – Tariff and Duty Reports](https://cea.nic.in/financial-studies-assistance-division/)
    - [Andhra Pradesh Electricity Regulatory Commission](https://aperc.gov.in/page/Tariff_Orders)
    - [Telangana Electricity Regulatory Commission](https://www.tgerc.telangana.gov.in/tariffschdule.php)
    """
)

st.caption("Smart Home Electricity Auditor | Community Service Project")
