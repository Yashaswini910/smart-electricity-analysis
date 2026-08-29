import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import urllib.request
import zipfile
import os

# Set up page configurations
st.set_page_config(page_title="Smart Electricity Analytics", page_icon="⚡", layout="wide")

# --- DATA ACQUISITION & CACHING ---
@st.cache_data
def load_and_clean_data():
    """Downloads, extracts, and cleans the UCI Household Electricity Dataset."""
    url = "https://uci.edu"
    zip_path = "electricity_data.zip"
    txt_filename = 'household_power_consumption.txt'
    
    # Download if not already present
    if not os.path.exists(txt_filename):
        urllib.request.urlretrieve(url, zip_path)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(".")
            
    # Load 100,000 rows for fast performance in the web application
    df = pd.read_csv(txt_filename, sep=';', nrows=100000, low_memory=False, na_values=['?'])
    
    # Process Timestamps
    df['Timestamp'] = pd.to_datetime(df['Date'] + ' ' + df['Time'], dayfirst=True)
    df.drop(['Date', 'Time'], axis=1, inplace=True)
    df.dropna(inplace=True)
    
    # Extract structural time components
    df['Hour'] = df['Timestamp'].dt.hour
    return df

# Initialize data loading with loading indicator
with st.spinner("📥 Initializing community dataset and optimizing analytics engine..."):
    try:
        data = load_and_clean_data()
        data_loaded = True
    except Exception as e:
        data_loaded = False
        st.error(f"Failed to load dataset: {e}")

# --- APP UI HEADER ---
st.title("⚡ Smart Electricity Analysis Portal")
st.markdown("### *A Data-Driven Community Service Initiative*")
st.write(
    "This web application translates millions of household energy data rows into actionable intelligence. "
    "Use this tool to discover regional peak demand patterns, evaluate your utility costs, and simulate personal carbon reductions."
)

st.write("---")

# Establish app navigation tabs
tab1, tab2, tab3 = st.tabs(["📈 Community Energy Insights", "💰 Dynamic Bill Calculator", "💡 Interactive Action Planner"])

# --- TAB 1: COMMUNITY ENERGY INSIGHTS ---
with tab1:
    st.header("📊 Regional Energy Consumption Trends")
    st.write("Data insights derived from a residential framework tracking granular appliance usage.")
    
    if data_loaded:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Timing Demand: Hourly Peak Profile")
            st.write("Identifies heavy system loads to help neighbors schedule tasks during optimal grid windows.")
            
            # Compute hourly means
            hourly_avg = data.groupby('Hour')['Global_active_power'].mean().reset_index()
            
            fig1, ax1 = plt.subplots(figsize=(7, 4.5))
            sns.lineplot(data=hourly_avg, x='Hour', y='Global_active_power', marker='o', color='#008080', ax=ax1, linewidth=2)
            ax1.set_xlabel("Hour of the Day (0 - 23)")
            ax1.set_ylabel("Average Active Power Draw (kW)")
            ax1.grid(True, linestyle='--', alpha=0.5)
            plt.xticks(range(0, 24, 2))
            st.pyplot(fig1)
            
            st.info("💡 **Community Service Advice:** Notice the evening spike? Shifting utility tasks (like washing machines) to early morning or midday relieves grid stress and minimizes localized blackouts.")
            
        with col2:
            st.subheader("Allocation Map: Where Energy is Consumed")
            st.write("Breaks down macro energy footprint across primary operational household domains.")
            
            # Compute categorical breakdowns
            sub1_total = data['Sub_metering_1'].sum()  # Kitchen
            sub2_total = data['Sub_metering_2'].sum()  # Laundry
            sub3_total = data['Sub_metering_3'].sum()  # Climate Control
            
            total_active_wh = (data['Global_active_power'] * 1000 / 60).sum()
            other_total = max(0, total_active_wh - (sub1_total + sub2_total + sub3_total))
            
            labels = ['Kitchen Zone', 'Laundry/Utility', 'AC & Water Heat', 'Other Unmapped (TVs/Lights)']
            sizes = [sub1_total, sub2_total, sub3_total, other_total]
            colors = ['#ff9999','#66b3ff','#99ff99','#ffcc99']
            
            fig2, ax2 = plt.subplots(figsize=(6, 6))
            ax2.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140, colors=colors,
                    wedgeprops={'edgecolor': 'black', 'linewidth': 0.8})
            st.pyplot(fig2)
            
            st.info("⚠️ **Ghost Load Notice:** The 'Other Unmapped' segment contains hidden 'Phantom Loads'—vampire energy consumed by standby TVs and smart appliances left switched on at the wall.")

# --- TAB 2: DYNAMIC BILL CALCULATOR ---
with tab2:
    st.header("🧮 Personalized Utility Expense Estimator")
    st.write("Input your household's monthly metric readings to map costs against typical structural tiered tariff scales.")
    
    # User Input Panel
    user_kwh = st.number_input("Enter your Monthly Energy Consumption (in kWh/Units):", min_value=0.0, value=250.0, step=10.0)
    
    # Standard Tiered Tariff Logic Matrix
    def calculate_bill(kwh):
        fixed_charge = 100.0  # Base account fee
        tax_rate = 0.18       # 18% energy duty tax
        
        # Tiered energy pricing per unit
        if kwh <= 100:
            energy_cost = kwh * 3.50
        elif kwh <= 300:
            energy_cost = (100 * 3.50) + ((kwh - 100) * 5.25)
        else:
            energy_cost = (100 * 3.50) + (200 * 5.25) + ((kwh - 300) * 7.75)
            
        subtotal = energy_cost + fixed_charge
        total_bill = subtotal + (subtotal * tax_rate)
        return energy_cost, fixed_charge, total_bill

    energy_c, fixed_c, final_bill = calculate_bill(user_kwh)
    
    # Render Financial Overview Output Cards
    c1, c2, c3 = st.columns(3)
    c1.metric("Raw Consumption Cost", f"₹{energy_c:,.2f}")
    c2.metric("Fixed Operational Fee", f"₹{fixed_c:,.2f}")
    c3.metric("Projected Monthly Bill (inc. Tax)", f"₹{final_bill:,.2f}")
    
    st.markdown("""
    ##### 📌 Tariff Threshold Breakdown Details
    *   **Tier 1 (First 100 Units):** ₹3.50 / Unit
    *   **Tier 2 (101 to 300 Units):** ₹5.25 / Unit
    *   **Tier 3 (Above 300 Units):** ₹7.75 / Unit *(High Demand Penalty Tier)*
    """)

# --- TAB 3: INTERACTIVE ACTION PLANNER ---
with tab3:
    st.header("🌱 Community Action & Conservation Simulator")
    st.write("Check the sustainable action checkboxes below to visualize your personal household savings and environmental benefits.")
    
    # Define conservation metrics mapping
    actions = {
        "Upgrade 5 major light fixtures to 9W LEDs": {"kwh": 30, "cost": 150, "co2": 24},
        "Unplug desktop electronics and chargers daily (Kill Phantom Loads)": {"kwh": 15, "cost": 75, "co2": 12},
        "Optimize AC settings to a recommended 24°C - 26°C zone": {"kwh": 45, "cost": 235, "co2": 36},
        "Shift laundry schedules entirely to off-peak slots (Before 6 PM)": {"kwh": 10, "cost": 50, "co2": 8}
    }
    
    saved_kwh = 0
    saved_money = 0
    saved_co2 = 0
    
    st.subheader("Select Your Commitments:")
    for action, metrics in actions.items():
        if st.checkbox(action):
            saved_kwh += metrics["kwh"]
            saved_money += metrics["cost"]
            saved_co2 += metrics["co2"]
            
    st.write("---")
    st.subheader("📉 Your Collective Monthly Impact Summary")
    
    a1, a2, a3 = st.columns(3)
    a1.metric("Energy Conservation Target", f"{saved_kwh} kWh Saved")
    a2.metric("Direct Financial Savings", f"₹{saved_money} Retained")
    a3.metric("Carbon Footprint Reduction", f"{saved_co2} kg CO₂ Prevented")
    
    if saved_kwh > 0:
        st.success("🌟 **Inspirational Fact:** If just **100 families** in your residential area implement your chosen checklist actions, the community will collectively stop over **3 metric tonnes of CO₂ emissions** from entering the atmosphere every single month!")
    else:
        st.info("💡 Select one or more action checkboxes above to initialize the target conservation simulator.")
