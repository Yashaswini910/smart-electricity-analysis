import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Smart Home Electricity Auditor",
    page_icon="⚡",
    layout="centered"
)


# ============================================================
# INDIA - DISCOM DATA
# ============================================================

DISCOMS = {

    "Andhra Pradesh": [
        "APSPDCL",
        "APEPDCL",
        "Other / Not Sure"
    ],

    "Assam": [
        "APDCL",
        "Other / Not Sure"
    ],

    "Bihar": [
        "NBPDCL",
        "SBPDCL",
        "Other / Not Sure"
    ],

    "Chhattisgarh": [
        "CSPDCL",
        "Other / Not Sure"
    ],

    "Delhi": [
        "BSES Rajdhani Power Limited (BRPL)",
        "BSES Yamuna Power Limited (BYPL)",
        "Tata Power Delhi Distribution Limited (TPDDL)",
        "NDMC",
        "Other / Not Sure"
    ],

    "Gujarat": [
        "DGVCL",
        "MGVCL",
        "PGVCL",
        "UGVCL",
        "Torrent Power",
        "Other / Not Sure"
    ],

    "Haryana": [
        "DHBVN",
        "UHBVN",
        "Other / Not Sure"
    ],

    "Himachal Pradesh": [
        "HPSEBL",
        "Other / Not Sure"
    ],

    "Jharkhand": [
        "JBVNL",
        "Other / Not Sure"
    ],

    "Karnataka": [
        "BESCOM",
        "HESCOM",
        "GESCOM",
        "MESCOM",
        "CESCOM",
        "Other / Not Sure"
    ],

    "Kerala": [
        "KSEB",
        "Other / Not Sure"
    ],

    "Madhya Pradesh": [
        "MPPKVVCL",
        "MPEZ",
        "MPMKVVCL",
        "Other / Not Sure"
    ],

    "Maharashtra": [
        "MSEDCL",
        "BEST",
        "Adani Electricity",
        "Tata Power",
        "Other / Not Sure"
    ],

    "Odisha": [
        "TPCODL",
        "TPNODL",
        "TPWODL",
        "TPSODL",
        "Other / Not Sure"
    ],

    "Punjab": [
        "PSPCL",
        "Other / Not Sure"
    ],

    "Rajasthan": [
        "JVVNL",
        "AVVNL",
        "JDVVNL",
        "Other / Not Sure"
    ],

    "Tamil Nadu": [
        "TNPDCL / TANGEDCO",
        "Other / Not Sure"
    ],

    "Telangana": [
        "TGSPDCL",
        "TGNPDCL",
        "Other / Not Sure"
    ],

    "Uttar Pradesh": [
        "PVVNL",
        "MVVNL",
        "DVVNL",
        "PuVVNL",
        "KESCO",
        "Other / Not Sure"
    ],

    "Uttarakhand": [
        "UPCL",
        "Other / Not Sure"
    ],

    "West Bengal": [
        "WBSEDCL",
        "CESC",
        "Other / Not Sure"
    ],

    "Goa": [
        "Electricity Department, Goa",
        "Other / Not Sure"
    ],

    "Other State / Union Territory": [
        "Other / Not Sure"
    ]
}


# ============================================================
# REGIONAL DUTY/TAX REFERENCE
# ============================================================
#
# IMPORTANT:
# These are reference duty/tax components from the CEA
# Electricity Tariff & Duty publication, March 2026.
#
# They should NOT be interpreted as universal current tax
# rates for every consumer.
#
# Actual duty/tax can vary with:
# - consumption
# - consumer category
# - utility
# - tariff order
# - subsidies
# - local rules
#
# Therefore the app allows the user to override the value
# using the duty/tax shown on their bill.
#
# Values below are approximate reference ₹/kWh components
# based on the CEA domestic reference table.
# ============================================================

REGIONAL_DUTY_REFERENCE = {

    "Andhra Pradesh": 0.06,
    "Arunachal Pradesh": 0.00,
    "Assam": 0.42,
    "Bihar": 0.58,
    "Chandigarh": 0.09,
    "Chhattisgarh": 0.72,
    "Dadra & Nagar Haveli and Daman & Diu": 0.00,
    "Delhi": 0.28,
    "Goa": 0.20,
    "Gujarat": 0.74,
    "Haryana": 0.25,
    "Himachal Pradesh": 0.28,
    "Jammu & Kashmir": 0.00,
    "Jharkhand": 0.41,
    "Karnataka": 0.52,
    "Kerala": 0.92,
    "Ladakh": 0.56,
    "Lakshadweep": 0.00,
    "Madhya Pradesh": 1.11,
    "Maharashtra": 2.59,
    "Manipur": 0.00,
    "Meghalaya": 0.05,
    "Mizoram": 0.00,
    "Nagaland": 0.00,
    "Odisha": 0.23,
    "Puducherry": 0.00,
    "Punjab": 1.10,
    "Rajasthan": 0.55,
    "Sikkim": 0.00,
    "Tamil Nadu": 0.00,
    "Telangana": 0.06,
    "Tripura": 0.44,
    "Uttar Pradesh": 0.37,
    "Uttarakhand": 0.15,
    "West Bengal": 0.89,

    "Other State / Union Territory": 0.00
}


# ============================================================
# COMMON APPLIANCES
# ============================================================

COMMON_APPLIANCES = [

    {
        "Appliance": "❄️ Air Conditioner",
        "Quantity": 1,
        "Wattage (W)": 1500,
        "Hours/day": 4.0
    },

    {
        "Appliance": "🧊 Refrigerator",
        "Quantity": 1,
        "Wattage (W)": 150,
        "Hours/day": 10.0
    },

    {
        "Appliance": "📺 Television",
        "Quantity": 1,
        "Wattage (W)": 150,
        "Hours/day": 3.0
    },

    {
        "Appliance": "💡 LED Bulb",
        "Quantity": 6,
        "Wattage (W)": 9,
        "Hours/day": 6.0
    },

    {
        "Appliance": "🌀 Ceiling Fan",
        "Quantity": 4,
        "Wattage (W)": 75,
        "Hours/day": 8.0
    },

    {
        "Appliance": "🚿 Geyser",
        "Quantity": 1,
        "Wattage (W)": 2000,
        "Hours/day": 0.5
    },

    {
        "Appliance": "🧺 Washing Machine",
        "Quantity": 1,
        "Wattage (W)": 500,
        "Hours/day": 0.5
    },

    {
        "Appliance": "💻 Laptop",
        "Quantity": 1,
        "Wattage (W)": 65,
        "Hours/day": 5.0
    },

    {
        "Appliance": "🚰 Water Pump",
        "Quantity": 1,
        "Wattage (W)": 750,
        "Hours/day": 0.5
    },

    {
        "Appliance": "🍳 Induction Stove",
        "Quantity": 1,
        "Wattage (W)": 1800,
        "Hours/day": 0.5
    },

    {
        "Appliance": "🍲 Microwave",
        "Quantity": 1,
        "Wattage (W)": 1200,
        "Hours/day": 0.3
    }
]


# ============================================================
# HEADER
# ============================================================

st.title("⚡ Smart Home Electricity Auditor")

st.markdown(
    "### *Calculate, Analyze, and Reduce Your Electricity Bill*"
)

st.write(
    "Enter your household appliances, add your own appliances, "
    "select your electricity region and DISCOM, and estimate "
    "your monthly electricity consumption and cost."
)

st.info(
    "💡 For better accuracy, enter the actual wattage printed "
    "on your appliance label or specification sheet."
)


# ============================================================
# STEP 1 — REGION
# ============================================================

st.write("---")

st.header("🇮🇳 Step 1: Electricity Connection Details")

states = list(DISCOMS.keys())

state = st.selectbox(
    "Select your State / Union Territory:",
    states,
    index=states.index("Telangana")
)

available_discoms = DISCOMS[state]

discom = st.selectbox(
    "Select your DISCOM / Electricity Provider:",
    available_discoms
)

area_type = st.radio(
    "Area type:",
    ["Urban", "Rural"],
    horizontal=True
)


# ============================================================
# TARIFF INPUT
# ============================================================

st.subheader("💰 Tariff Information")

st.write(
    "Your electricity tariff depends on the DISCOM, consumer "
    "category and applicable tariff order. For the most useful "
    "estimate, enter the energy rate shown on your electricity bill."
)

energy_rate = st.number_input(
    "Energy Charge / Average Energy Rate (₹ per kWh)",
    min_value=0.0,
    max_value=50.0,
    value=6.50,
    step=0.10,
    help=(
        "Look for Energy Charges / Energy Rate on your electricity bill."
    )
)

fixed_charge = st.number_input(
    "Monthly Fixed Charge (₹)",
    min_value=0.0,
    max_value=10000.0,
    value=150.0,
    step=10.0,
    help="Enter the fixed/customer charge from your electricity bill."
)


# ============================================================
# REGIONAL DUTY
# ============================================================

reference_duty = REGIONAL_DUTY_REFERENCE.get(
    state,
    0.0
)

st.subheader("🏛️ Regional Electricity Duty / Tax")

st.write(
    f"Reference duty/tax component for **{state}**: "
    f"₹{reference_duty:.2f} per kWh"
)

use_reference_duty = st.checkbox(
    "Use the regional reference duty/tax automatically",
    value=True
)

if use_reference_duty:

    duty_per_unit = reference_duty

else:

    duty_per_unit = st.number_input(
        "Enter electricity duty / tax from your bill (₹ per kWh):",
        min_value=0.0,
        max_value=20.0,
        value=float(reference_duty),
        step=0.01
    )

st.caption(
    "The regional duty/tax values are reference values derived "
    "from CEA's March 2026 tariff/duty publication. Actual "
    "consumer charges can differ by tariff category, consumption "
    "level, utility and current tariff order."
)


# ============================================================
# STEP 2 — COMMON APPLIANCES
# ============================================================

st.write("---")

st.header("🔌 Step 2: Common Appliance Usage")

st.write(
    "Change the quantity, wattage and daily operating hours "
    "to match your actual household."
)

common_df = pd.DataFrame(COMMON_APPLIANCES)

common_df = st.data_editor(
    common_df,
    use_container_width=True,
    hide_index=True,
    num_rows="fixed",

    column_config={

        "Appliance":
            st.column_config.TextColumn(
                "Appliance",
                disabled=True
            ),

        "Quantity":
            st.column_config.NumberColumn(
                "Quantity",
                min_value=0,
                max_value=100,
                step=1
            ),

        "Wattage (W)":
            st.column_config.NumberColumn(
                "Wattage (W)",
                min_value=0,
                max_value=50000,
                step=1
            ),

        "Hours/day":
            st.column_config.NumberColumn(
                "Hours/day",
                min_value=0.0,
                max_value=24.0,
                step=0.5
            )
    }
)


# ============================================================
# STEP 3 — CUSTOM APPLIANCES
# ============================================================

st.write("---")

st.header("➕ Step 3: Add Your Own Appliances")

st.write(
    "Add any appliance that is not already listed."
)

custom_default = pd.DataFrame(
    [
        {
            "Appliance": "",
            "Quantity": 1,
            "Wattage (W)": 100,
            "Hours/day": 1.0
        }
    ]
)

custom_df = st.data_editor(
    custom_default,
    use_container_width=True,
    hide_index=True,
    num_rows="dynamic",

    column_config={

        "Appliance":
            st.column_config.TextColumn(
                "Appliance Name",
                help=(
                    "Examples: Iron, Air Cooler, Desktop PC, "
                    "EV Charger, Hair Dryer, Water Purifier"
                )
            ),

        "Quantity":
            st.column_config.NumberColumn(
                "Quantity",
                min_value=0,
                max_value=100,
                step=1
            ),

        "Wattage (W)":
            st.column_config.NumberColumn(
                "Wattage (W)",
                min_value=0,
                max_value=50000,
                step=1
            ),

        "Hours/day":
            st.column_config.NumberColumn(
                "Hours/day",
                min_value=0.0,
                max_value=24.0,
                step=0.5
            )
    }
)


# ============================================================
# CALCULATION FUNCTION
# ============================================================

def calculate_appliance_units(df):

    results = []

    for _, row in df.iterrows():

        appliance = str(
            row["Appliance"]
        ).strip()

        if appliance == "":
            continue

        quantity = float(
            row["Quantity"]
        )

        wattage = float(
            row["Wattage (W)"]
        )

        hours = float(
            row["Hours/day"]
        )

        daily_kwh = (
            quantity *
            wattage *
            hours /
            1000
        )

        monthly_kwh = (
            daily_kwh *
            30
        )

        results.append(
            {
                "Appliance": appliance,
                "Quantity": quantity,
                "Wattage (W)": wattage,
                "Hours/day": hours,
                "Monthly Units (kWh)": monthly_kwh
            }
        )

    return pd.DataFrame(results)


# ============================================================
# CALCULATE USAGE
# ============================================================

common_results = calculate_appliance_units(
    common_df
)

custom_results = calculate_appliance_units(
    custom_df
)

all_results = pd.concat(
    [
        common_results,
        custom_results
    ],
    ignore_index=True
)


if len(all_results) > 0:

    all_results["Energy Cost (₹)"] = (
        all_results["Monthly Units (kWh)"]
        *
        energy_rate
    )

    total_monthly_units = (
        all_results["Monthly Units (kWh)"]
        .sum()
    )

else:

    total_monthly_units = 0


# ============================================================
# BILL CALCULATION
# ============================================================

energy_charge = (
    total_monthly_units *
    energy_rate
)

electricity_duty = (
    total_monthly_units *
    duty_per_unit
)

estimated_bill = (
    energy_charge +
    electricity_duty +
    fixed_charge
)


# ============================================================
# STEP 4 — RESULTS
# ============================================================

st.write("---")

st.header("📊 Step 4: Your Personalized Energy Report")


c1, c2, c3 = st.columns(3)

c1.metric(
    "Monthly Consumption",
    f"{total_monthly_units:.1f} kWh"
)

c2.metric(
    "Energy Charge",
    f"₹{energy_charge:,.0f}"
)

c3.metric(
    "Estimated Bill",
    f"₹{estimated_bill:,.0f}"
)


# ============================================================
# BILL BREAKDOWN
# ============================================================

st.subheader("💰 Estimated Bill Breakdown")

bill_breakdown = pd.DataFrame(
    {
        "Bill Component": [
            "Energy Charges",
            "Fixed Charge",
            "Electricity Duty / Tax",
            "Estimated Total"
        ],

        "Amount (₹)": [
            energy_charge,
            fixed_charge,
            electricity_duty,
            estimated_bill
        ]
    }
)

st.dataframe(
    bill_breakdown,
    use_container_width=True,
    hide_index=True
)

st.caption(
    f"State: {state} | "
    f"DISCOM: {discom} | "
    f"Area: {area_type}"
)


# ============================================================
# APPLIANCE ANALYSIS
# ============================================================

st.subheader("🔌 Appliance-by-Appliance Analysis")

if len(all_results) > 0:

    display_df = all_results.copy()

    display_df[
        "Monthly Units (kWh)"
    ] = display_df[
        "Monthly Units (kWh)"
    ].round(2)

    display_df[
        "Energy Cost (₹)"
    ] = display_df[
        "Energy Cost (₹)"
    ].round(2)

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# PIE CHART
# ============================================================

st.subheader("💡 Where Is Your Electricity Going?")

if total_monthly_units > 0:

    chart_df = all_results[
        all_results[
            "Monthly Units (kWh)"
        ] > 0
    ].copy()

    fig, ax = plt.subplots(
        figsize=(8, 6)
    )

    ax.pie(
        chart_df[
            "Monthly Units (kWh)"
        ],

        labels=chart_df[
            "Appliance"
        ],

        autopct="%1.1f%%",

        startangle=140,

        wedgeprops={
            "edgecolor": "black",
            "linewidth": 0.8
        }
    )

    ax.set_title(
        "Monthly Electricity Consumption"
    )

    st.pyplot(fig)

else:

    st.info(
        "Enter appliance usage to generate the chart."
    )


# ============================================================
# TOP CONSUMERS
# ============================================================

if total_monthly_units > 0:

    st.subheader(
        "🚨 Your Biggest Electricity Consumers"
    )

    top_consumers = (
        all_results
        .sort_values(
            "Monthly Units (kWh)",
            ascending=False
        )
        .head(5)
    )

    for _, row in top_consumers.iterrows():

        percentage = (
            row["Monthly Units (kWh)"]
            /
            total_monthly_units
        ) * 100

        st.write(
            f"**{row['Appliance']}** — "
            f"{row['Monthly Units (kWh)']:.1f} kWh/month "
            f"({percentage:.1f}%)"
        )


# ============================================================
# SAVINGS SIMULATOR
# ============================================================

st.write("---")

st.header("🌱 Step 5: Savings Simulator")

st.write(
    "See what happens if you reduce your electricity consumption."
)

reduction_percent = st.slider(
    "Reduce your consumption by:",
    min_value=0,
    max_value=50,
    value=10,
    step=5
)

reduced_units = (
    total_monthly_units *
    reduction_percent /
    100
)

new_units = (
    total_monthly_units -
    reduced_units
)

new_energy_charge = (
    new_units *
    energy_rate
)

new_duty = (
    new_units *
    duty_per_unit
)

new_bill = (
    new_energy_charge +
    new_duty +
    fixed_charge
)

monthly_saving = (
    estimated_bill -
    new_bill
)

annual_saving = (
    monthly_saving *
    12
)


s1, s2, s3 = st.columns(3)

s1.metric(
    "New Monthly Usage",
    f"{new_units:.1f} kWh"
)

s2.metric(
    "Monthly Saving",
    f"₹{monthly_saving:,.0f}"
)

s3.metric(
    "Annual Saving",
    f"₹{annual_saving:,.0f}"
)


# ============================================================
# PERSONALIZED ADVICE
# ============================================================

st.subheader(
    "🌱 Personalized Energy-Saving Advice"
)

if len(all_results) > 0:

    highest = all_results.loc[
        all_results[
            "Monthly Units (kWh)"
        ].idxmax()
    ]

    highest_name = highest[
        "Appliance"
    ]

    highest_units = highest[
        "Monthly Units (kWh)"
    ]

    if "Air Conditioner" in highest_name:

        st.warning(
            "❄️ Your AC is your largest estimated consumer. "
            "Reducing unnecessary operating hours and using "
            "a moderate temperature setting can reduce consumption."
        )

    elif "Geyser" in highest_name:

        st.warning(
            "🚿 Your geyser is a major estimated consumer. "
            "Using a timer and avoiding unnecessary heating "
            "can reduce electricity consumption."
        )

    elif "Water Pump" in highest_name:

        st.warning(
            "🚰 Your water pump is a significant consumer. "
            "Check for leaks and avoid unnecessarily long pump operation."
        )

    elif "Refrigerator" in highest_name:

        st.info(
            "🧊 Your refrigerator is one of the major consumers "
            "in this estimate. Check door seals and maintain "
            "appropriate temperature settings."
        )

    elif "Fan" in highest_name:

        st.info(
            "🌀 Fans contribute significantly to your usage. "
            "When replacing old fans, efficient BLDC models "
            "can reduce electricity consumption."
        )

    else:

        st.info(
            f"💡 Your largest estimated electricity consumer is "
            f"**{highest_name}**, using approximately "
            f"**{highest_units:.1f} kWh/month**."
        )


# ============================================================
# STANDBY POWER
# ============================================================

st.write("---")

st.subheader(
    "🔌 Standby Power Check"
)

standby_devices = st.multiselect(
    "Which devices are commonly left plugged in?",
    [
        "TV",
        "Set-top Box",
        "Laptop Charger",
        "Desktop Computer",
        "Gaming Console",
        "Microwave",
        "Wi-Fi Router",
        "Printer"
    ]
)

standby_watts = {

    "TV": 1.0,

    "Set-top Box": 5.0,

    "Laptop Charger": 1.0,

    "Desktop Computer": 3.0,

    "Gaming Console": 2.0,

    "Microwave": 3.0,

    "Wi-Fi Router": 8.0,

    "Printer": 2.0
}

total_standby_watts = sum(
    standby_watts[device]
    for device in standby_devices
)

standby_units = (
    total_standby_watts
    *
    24
    *
    30
    /
    1000
)

standby_cost = (
    standby_units
    *
    energy_rate
)

if standby_devices:

    c1, c2 = st.columns(2)

    c1.metric(
        "Standby Consumption",
        f"{standby_units:.2f} kWh/month"
    )

    c2.metric(
        "Standby Cost",
        f"₹{standby_cost:.2f}/month"
    )

else:

    st.caption(
        "Select devices above to estimate standby consumption."
    )


# ============================================================
# METER READING TOOL
# ============================================================

st.write("---")

st.header(
    "📟 Optional: Actual Meter Reading"
)

st.write(
    "If you know your meter readings, you can compare "
    "actual consumption with the appliance estimate."
)

previous_reading = st.number_input(
    "Previous Meter Reading (kWh)",
    min_value=0.0,
    value=0.0,
    step=1.0
)

current_reading = st.number_input(
    "Current Meter Reading (kWh)",
    min_value=0.0,
    value=0.0,
    step=1.0
)

billing_days = st.number_input(
    "Number of Billing Days",
    min_value=1,
    max_value=100,
    value=30,
    step=1
)

if current_reading >= previous_reading:

    actual_units = (
        current_reading -
        previous_reading
    )

    daily_actual = (
        actual_units /
        billing_days
    )

    monthly_actual = (
        daily_actual *
        30
    )

    m1, m2, m3 = st.columns(3)

    m1.metric(
        "Actual Units",
        f"{actual_units:.1f} kWh"
    )

    m2.metric(
        "Daily Average",
        f"{daily_actual:.2f} kWh"
    )

    m3.metric(
        "30-Day Equivalent",
        f"{monthly_actual:.1f} kWh"
    )

    if total_monthly_units > 0:

        difference = (
            monthly_actual -
            total_monthly_units
        )

        if abs(difference) > 20:

            st.warning(
                f"Your actual meter-based consumption differs "
                f"from the appliance estimate by approximately "
                f"{abs(difference):.1f} kWh/month."
            )

        else:

            st.success(
                "Your appliance estimate is reasonably close "
                "to your meter-based consumption."
            )

else:

    st.error(
        "Current meter reading cannot be lower than previous reading."
    )


# ============================================================
# IMPORTANT INFORMATION
# ============================================================

st.write("---")

st.header(
    "ℹ️ Important Information"
)

st.info(
    """
This application provides an ESTIMATE.

The calculation is based on:

• Appliance wattage
• Number of appliances
• Hours of operation
• 30-day month assumption
• User-entered energy rate
• User-entered fixed charge
• Regional electricity duty/tax reference

Actual electricity bills can differ because of:

• DISCOM-specific tariff orders
• Consumer category
• Consumption slabs
• Fixed charges
• Electricity duty / cess
• Fuel or power-purchase adjustment charges
• Government subsidies
• Rebates
• Meter reading dates
• Arrears or previous adjustments
• Other utility-specific charges

Always use the official electricity bill for the final payable amount.
"""
)

st.caption(
    "Reference: Central Electricity Authority, "
    "Electricity Tariff & Duty & Average Rates of Electricity "
    "Supply in India, March 2026."
)
