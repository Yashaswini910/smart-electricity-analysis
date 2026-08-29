import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# Set up clean page configurations
st.set_page_config(page_title="My Smart Electricity Audit", page_icon="⚡", layout="centered")

# --- UI HEADER ---
st.title("⚡ My Home Electricity Auditor")
st.markdown("### *Calculate, Analyze, and Lower Your Electricity Bill*")
st.write(
    "Welcome! This simple tool helps you calculate your exact home electricity costs. "
    "Enter your real appliance usage below to discover what drives your bill up and how you can save money."
)
st.write("---")

# --- STEP 1: APPLIANCE USAGE INPUT PANEL ---
st.header("🔌 Step 1: Tell Us About Your Daily Usage")
st.write("Adjust the sliders below to match how many hours you run these appliances every day:")

# Layout inputs beautifully using columns
col1, col2 = st.columns(2)

with col1:
    ac_hours = st.slider("Air Conditioner (AC) - Daily Hours:", 0, 24, 4, help="Average 1.5 Ton AC uses ~1500 Watts")
    refrigerator_hours = st.slider("Refrigerator - Daily Hours:", 0, 24, 24, help="Stays on 24/7, but compressor runs ~10 hours total")
    tv_hours = st.slider("Television / Entertainment - Daily Hours:", 0, 24, 3, help="TV and setup box use ~150 Watts")

with col2:
    led_count = st.number_input("Number of LED Bulbs in House:", min_value=0, max_value=50, value=6)
    led_hours = st.slider("Average Hours Lights are ON daily:", 0, 24, 6)
    fan_count = st.number_input("Number of Ceiling Fans in House:", min_value=0, max_value=20, value=4)
    fan_hours = st.slider("Average Hours Fans are ON daily:", 0, 24, 12)

st.write("---")

# --- STEP 2: MATHEMATICAL ENERGY CALCULATIONS ---
# Standard Wattage values for common Indian appliances
WATT_AC = 1500
WATT_REF = 200  # Average cycling load
WATT_TV = 150
WATT_LED = 9
WATT_FAN = 75

# Calculate daily Wh (Watt-hours)
ac_wh = WATT_AC * ac_hours
ref_wh = WATT_REF * refrigerator_hours
tv_wh = WATT_TV * tv_hours
led_wh = WATT_LED * led_count * led_hours
fan_wh = WATT_FAN * fan_count * fan_hours

# Calculate Total Units (kWh) per month (multiplied by 30 days)
ac_units = (ac_wh / 1000) * 30
ref_units = (ref_wh / 1000) * 30
tv_units = (tv_wh / 1000) * 30
led_units = (led_wh / 1000) * 30
fan_units = (fan_wh / 1000) * 30

total_monthly_units = ac_units + ref_units + tv_units + led_units + fan_units

# --- STEP 3: TIERED TARIFF CALCULATION (Indian Slab Structure) ---
def compute_indian_bill(kwh):
    fixed_charge = 100.0  # Standard fixed connection fee
    tax_rate = 0.18       # 18% Electricity Regulatory Duty/Tax
    
    if kwh <= 100:
        energy_cost = kwh * 3.50
    elif kwh <= 300:
        energy_cost = (100 * 3.50) + ((kwh - 100) * 5.25)
    else:
        energy_cost = (100 * 3.50) + (200 * 5.25) + ((kwh - 300) * 7.75)
        
    subtotal = energy_cost + fixed_charge
    total_bill = subtotal + (subtotal * tax_rate)
    return total_bill

projected_bill = compute_indian_bill(total_monthly_units)

# --- STEP 4: DISPLAY RESULTS & LIVE INSIGHTS ---
st.header("📊 Step 2: Your Personalized Energy Bill Report")

# Display Summary Metric Cards
c1, c2 = st.columns(2)
c1.metric("Estimated Monthly Consumption", f"{total_monthly_units:.1f} Units (kWh)")
c2.metric("Projected Monthly Bill (with Tax)", f"₹{projected_bill:,.2f}")

# Render Breakdown Pie Chart
st.subheader("💡 Where is your money actually going?")
labels = ['Air Conditioner', 'Refrigerator', 'Television', 'LED Lighting', 'Ceiling Fans']
sizes = [ac_units, ref_units, tv_units, led_units, fan_units]
colors = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99', '#bcbd22']

# Only plot if there is actual usage to avoid errors
if total_monthly_units > 0:
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140, colors=colors,
            wedgeprops={'edgecolor': 'black', 'linewidth': 0.8})
    st.pyplot(fig)
else:
    st.info("Please adjust sliders above to calculate your breakdown.")

# --- STEP 5: PERSONAL SAVINGS ADVISOR ---
st.write("---")
st.header("🌱 Step 3: Customized Money-Saving Advice")

if ac_hours > 5:
    st.warning("⚠️ **AC Alert:** Your Air Conditioner makes up a massive part of your bill. **Action:** Setting your AC to **24°C instead of 18°C** can reduce your AC's electricity consumption by up to 24%!")

if total_monthly_units > 300:
    st.error("🚨 **High Tariff Warning:** Your home has crossed **300 Units**. You are now paying the highest rate (₹7.75 per unit). Reducing just 20 units this month will drop you into a cheaper tax bracket and save you hundreds of rupees instantly!")
else:
    st.success("🌟 **Great Job!** Your usage is under 300 units, keeping you in the safer, low-cost utility price brackets.")

st.info("💡 **Quick Community Tip:** Unplug your TV and set-top box at the main wall switch when going to sleep. Leaving them on standby mode can waste up to 15 Units a month for no reason!")
