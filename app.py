%%writefile app.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import urllib.request
import zipfile
import os

st.set_page_config(page_title="Smart Electricity Analytics", page_icon="⚡", layout="wide")

@st.cache_data
def load_and_clean_data():
    url = "https://uci.edu"
    zip_path = "electricity_data.zip"
    txt_filename = 'household_power_consumption.txt'
    if not os.path.exists(txt_filename):
        urllib.request.urlretrieve(url, zip_path)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(".")
    df = pd.read_csv(txt_filename, sep=';', nrows=100000, low_memory=False, na_values=['?'])
    df['Timestamp'] = pd.to_datetime(df['Date'] + ' ' + df['Time'], dayfirst=True)
    df.drop(['Date', 'Time'], axis=1, inplace=True)
    df.dropna(inplace=True)
    df['Hour'] = df['Timestamp'].dt.hour
    return df

with st.spinner("📥 Initializing community dataset..."):
    try:
        data = load_and_clean_data()
        data_loaded = True
    except Exception as e:
        data_loaded = False

st.title("⚡ Smart Electricity Analysis Portal")
st.markdown("### *A Data-Driven Community Service Initiative*")
st.write("This web application translates millions of household energy data rows into actionable intelligence.")
st.write("---")

tab1, tab2, tab3 = st.tabs(["社区趋势 Community Insights", "账单计算 Bill Calculator", "节能计划 Action Planner"])

with tab1:
    st.header("📊 Regional Energy Consumption Trends")
    if data_loaded:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Timing Demand: Hourly Peak Profile")
            hourly_avg = data.groupby('Hour')['Global_active_power'].mean().reset_index()
            fig1, ax1 = plt.subplots(figsize=(7, 4.5))
            sns.lineplot(data=hourly_avg, x='Hour', y='Global_active_power', marker='o', color='#008080', ax=ax1)
            st.pyplot(fig1)
            st.info("💡 **Advice:** Shifting heavy usage tasks away from evening hours relieves local grid stress.")
        with col2:
            st.subheader("Allocation Map: Where Energy Goes")
            sub1 = data['Sub_metering_1'].sum()
            sub2 = data['Sub_metering_2'].sum()
            sub3 = data['Sub_metering_3'].sum()
            total_active_wh = (data['Global_active_power'] * 1000 / 60).sum()
            other_total = max(0, total_active_wh - (sub1 + sub2 + sub3))
            fig2, ax2 = plt.subplots(figsize=(6, 6))
            ax2.pie([sub1, sub2, sub3, other_total], labels=['Kitchen', 'Laundry', 'AC/Heating', 'Other Loads'], autopct='%1.1f%%', colors=['#ff9999','#66b3ff','#99ff99','#ffcc99'])
            st.pyplot(fig2)

with tab2:
    st.header("🧮 Personalized Utility Expense Estimator")
    user_kwh = st.number_input("Enter your Monthly Units (kWh):", min_value=0, value=250)
    fixed_charge = 100.0
    if user_kwh <= 100: energy_cost = user_kwh * 3.50
    elif user_kwh <= 300: energy_cost = (100 * 3.50) + ((user_kwh - 100) * 5.25)
    else: energy_cost = (100 * 3.50) + (200 * 5.25) + ((user_kwh - 300) * 7.75)
    total_bill = (energy_cost + fixed_charge) * 1.18
    st.metric("Projected Monthly Bill (inc. Tax)", f"₹{total_bill:,.2f}")

with tab3:
    st.header("🌱 Community Action & Conservation Simulator")
    saved_kwh, saved_money = 0, 0
    if st.checkbox("Upgrade 5 major light fixtures to 9W LEDs (Saves 30 kWh)"):
        saved_kwh += 30; saved_money += 150
    if st.checkbox("Unplug electronics to kill Phantom Loads (Saves 15 kWh)"):
        saved_kwh += 15; saved_money += 75
    st.metric("Energy Conservation Target", f"{saved_kwh} kWh Saved")
    st.metric("Direct Financial Savings", f"₹{saved_money} Retained")
