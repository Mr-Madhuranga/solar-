import streamlit as st
import joblib
import pandas as pd
import requests
import datetime
import plotly.graph_objects as go
import pyttsx3
import threading

# 1. පද්ධති සැකසුම් (Page Configuration)
st.set_page_config(page_title="AI Smart Grid Pro", layout="wide", page_icon="⚡")

# --- 🎙️ AI VOICE ASSISTANT FUNCTION (English) ---
def speak_alert(text):
    def run_speech():
        try:
            engine = pyttsx3.init()
            engine.setProperty('rate', 160)
            engine.say(text)
            engine.runAndWait()
        except:
            pass
    threading.Thread(target=run_speech).start()

# Helper function for weather icons
def get_weather_emoji(desc):
    desc = desc.lower()
    if "clear" in desc: return "☀️"
    elif "cloud" in desc: return "☁️"
    elif "rain" in desc: return "🌧️"
    elif "thunder" in desc: return "⛈️"
    else: return "🌤️"

# AI Model එක Load කිරීම
try:
    model = joblib.load('solar_model.pkl')
except:
    st.error("Error: 'solar_model.pkl' ගොනුව සොයාගත නොහැක.")

# OpenWeather API Key
API_KEY = "0d307a226a4730a1745234b052fe53ff"

# 2. කාලගුණ දත්ත ලබාගන්නා Functions
def get_weather(city):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"
    try:
        r = requests.get(url).json()
        return r
    except: return None

def get_forecast(city):
    url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={API_KEY}&units=metric"
    try:
        r = requests.get(url).json()
        return r['list'][::8] 
    except: return None

# --- SIDEBAR (පාලක පුවරුව) ---
st.sidebar.title("🎮 Control Center")
if 'city' not in st.session_state:
    st.session_state.city = "Galle"

# Initialize Battery SoC if not exists
if 'battery_soc' not in st.session_state:
    st.session_state.battery_soc = 65.0 

city_input = st.sidebar.text_input("📍 Enter City", st.session_state.city)
voice_on = st.sidebar.checkbox("🔊 AI Voice Assistant On", value=True)

st.sidebar.markdown("---")
st.sidebar.subheader("🔋 BMS Status")
st.sidebar.progress(st.session_state.battery_soc / 100)
st.sidebar.caption(f"Battery SoC: {st.session_state.battery_soc:.1f}%")

st.sidebar.markdown("---")
st.sidebar.subheader("ℹ️ System Specifications")
st.sidebar.info("""
**Grid Scale:** Residential (5-7 kW)  
**Battery:** 10kWh Smart System  
**Logic:** AI predicts power based on live weather.
""")

# --- MAIN UI (ප්‍රධාන පෙනුම) ---
st.title("☀️ AI-Driven Smart Grid Management")
weather = get_weather(city_input)

if weather and 'main' in weather:
    # --- LOGIC ---
    current_hour = datetime.datetime.now().hour
    is_night = current_hour >= 18 or current_hour <= 6
    temp = weather['main']['temp']
    clouds = weather['clouds']['all']
    desc = weather['weather'][0]['description']
    
    lat = weather['coord']['lat']
    lon = weather['coord']['lon']
    
    if is_night:
        irrad = 0.0
        pred_power = 0.0
    else:
        irrad = max(0.05, (100 - clouds) / 100)
        features = pd.DataFrame([[temp, temp + 12, irrad]], 
                               columns=['AMBIENT_TEMPERATURE', 'MODULE_TEMPERATURE', 'IRRADIATION'])
        pred_power = (model.predict(features)[0]) / 2000

    # AI Assistant Notification
    st.info(f"🤖 **AI Assistant:** {desc.title()} in {city_input}. Predicted Output: {pred_power:.2f} kW")

    # --- TOP METRICS & MAP ---
    col1, col2 = st.columns([2, 1]) 
    
    with col1:
        st.markdown(f"**Live Monitoring:** {city_input.upper()} | {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("🌡️ Temp", f"{temp}°C", desc.title())
        m2.metric("🔋 Solar Gen", f"{pred_power:.2f} kW")
        m3.metric("☁️ Clouds", f"{clouds}%")
        m4.metric("☀️ Irradiation", f"{irrad:.2f} W/m²")
    
    with col2:
        map_data = pd.DataFrame({'lat': [lat], 'lon': [lon]})
        st.map(map_data, zoom=10)

    st.divider()

    # --- ANIMATED GRID FLOW SECTION ---
    st.subheader("⚡ Live Smart Grid Energy Flow")
    load = st.slider("🏠 Simulate Home Load (kW)", 0.5, 6.0, 2.5)
    balance = pred_power - load

    # Update Battery SoC simulation
    st.session_state.battery_soc = max(0.0, min(100.0, st.session_state.battery_soc + (balance * 0.5)))

    # --- 🚨 NEW: AI ALERT SYSTEM 🚨 ---
    st.subheader("🔔 AI System Alerts")
    a_col1, a_col2 = st.columns(2)
    
    with a_col1:
        if st.session_state.battery_soc < 25:
            st.error("🚨 CRITICAL ALERT: Battery level is below 25%! AI suggests reducing home load immediately.")
            if voice_on: speak_alert("Warning. Battery is low. Please reduce your home load.")
        elif pred_power > 4.5:
            st.success("🔥 PEAK PERFORMANCE: Solar output is at peak. Ideal time to use heavy appliances.")
            if voice_on: speak_alert("High solar energy detected. You can run heavy loads now.")
        else:
            st.info("ℹ️ System Status: Grid and Solar balance is stable.")

    with a_col2:
        if is_night:
            st.warning("🌙 Night Mode Active: Relying on battery and utility grid storage.")
        elif clouds > 80:
            st.warning("☁️ Low Yield Alert: High cloud cover detected. Solar generation is limited.")

    st.markdown("""
        <style>
        @keyframes pulse {
            0% { opacity: 0.4; transform: scale(0.95); }
            50% { opacity: 1; transform: scale(1.05); }
            100% { opacity: 0.4; transform: scale(0.95); }
        }
        .flow-icon { font-size: 45px; text-align: center; margin-bottom: 0px; }
        .flow-label { text-align: center; font-weight: bold; margin-top: -10px; }
        .active-solar { color: #FFD700; animation: pulse 2s infinite; }
        .active-export { color: #00CC66; animation: pulse 1s infinite; }
        .active-import { color: #FF4B4B; animation: pulse 1s infinite; }
        .static-home { color: #FFFFFF; }
        </style>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4, c5 = st.columns([1, 0.5, 1, 0.5, 1])
    with c1:
        solar_class = "active-solar" if pred_power > 0.1 else ""
        st.markdown(f"<div class='flow-icon {solar_class}'>☀️</div>", unsafe_allow_html=True)
        st.markdown("<div class='flow-label'>Solar Generation</div>", unsafe_allow_html=True)
        st.info(f"**{pred_power:.2f} kW**")
    with c2:
        arrow_class = "active-solar" if pred_power > 0.1 else ""
        st.markdown(f"<br><h1 style='text-align: center' class='{arrow_class}'>➡</h1>", unsafe_allow_html=True)
    with c3:
        st.markdown("<div class='flow-icon static-home'>🏠</div>", unsafe_allow_html=True)
        st.markdown("<div class='flow-label'>Home Consumption</div>", unsafe_allow_html=True)
        st.warning(f"**{load:.2f} kW**")
    with c4:
        if balance > 0: st.markdown("<br><h1 style='text-align: center' class='active-export'>➡</h1>", unsafe_allow_html=True)
        else: st.markdown("<br><h1 style='text-align: center' class='active-import'>⬅</h1>", unsafe_allow_html=True)
    with c5:
        grid_class = "active-export" if balance > 0 else "active-import"
        st.markdown(f"<div class='flow-icon {grid_class}'>🔌</div>", unsafe_allow_html=True)
        st.markdown("<div class='flow-label'>Utility Grid</div>", unsafe_allow_html=True)
        if balance > 0: st.success(f"Exporting: +{abs(balance):.2f}")
        else: st.error(f"Importing: -{abs(balance):.2f}")

    st.divider()

    # --- ADVANCED BMS & CARBON FOOTPRINT ---
    col_bms, col_eco = st.columns(2)
    
    with col_bms:
        st.subheader("🔋 Battery Management (BMS)")
        fig_bms = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = st.session_state.battery_soc,
            gauge = {
                'axis': {'range': [0, 100]},
                'bar': {'color': "limegreen" if balance >= 0 else "orange"},
                'steps': [
                    {'range': [0, 20], 'color': "red"},
                    {'range': [20, 100], 'color': "gray"}]
            },
            title = {'text': "Battery SoC (%)"}
        ))
        fig_bms.update_layout(height=250, margin=dict(l=20, r=20, t=50, b=20))
        st.plotly_chart(fig_bms, use_container_width=True)

    with col_eco:
        st.subheader("🌿 Environmental Impact")
        co2_saved = pred_power * 0.4 
        trees_equivalent = pred_power * 0.02
        st.metric("🌍 CO2 Offset", f"{co2_saved:.3f} kg/hr")
        st.metric("🌳 Tree Equivalent", f"{trees_equivalent:.4f} Trees")

    st.divider()

    # --- VISUALIZATION (Gauge & Economics) ---
    col_left, col_right = st.columns([1, 1]) 
    with col_left:
        st.subheader("📊 Production Intensity")
        fig = go.Figure(go.Indicator(mode = "gauge+number", value = pred_power, gauge = {'axis': {'range': [0, 7]}, 'bar': {'color': "gold"}}))
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
    with col_right:
        st.subheader("💰 Economic Impact")
        hourly_impact = balance * 37 # Unit price 37 LKR
        if balance > 0: st.success(f"PROFITABLE: Rs. {hourly_impact:.2f} / hr")
        else: st.error(f"COST: Rs. {abs(hourly_impact):.2f} / hr")
        st.bar_chart({"Solar Gen": pred_power, "Home Load": load})

    # --- 5-DAY FORECAST & DAILY PROFIT SUMMARY ---
    st.divider()
    st.subheader("📅 AI-Powered 5-Day Solar Insights & Profit Projection")
    forecast_list = get_forecast(city_input)
    
    if forecast_list:
        dates, powers, icons, descs = [], [], [], []
        for day in forecast_list:
            f_irrad = max(0.05, (100 - day['clouds']['all']) / 100)
            f_features = pd.DataFrame([[day['main']['temp'], day['main']['temp']+12, f_irrad]], 
                                       columns=['AMBIENT_TEMPERATURE', 'MODULE_TEMPERATURE', 'IRRADIATION'])
            f_power = (model.predict(f_features)[0]) / 2000
            dates.append(day['dt_txt'].split(' ')[0])
            powers.append(round(f_power, 2))
            icons.append(get_weather_emoji(day['weather'][0]['description']))
            descs.append(day['weather'][0]['description'].title())

        # Daily Cards
        cols = st.columns(5)
        for i in range(5):
            with cols[i]:
                st.markdown(f"""
                    <div style="text-align: center; border: 1px solid #444; padding: 10px; border-radius: 10px; background: #1E1E1E;">
                        <h4 style="margin:0; font-size: 14px;">{dates[i][5:]}</h4>
                        <h1 style="margin:10px 0;">{icons[i]}</h1>
                        <p style="color: #FFD700; font-weight: bold; font-size: 18px; margin:0;">{powers[i]} kW</p>
                    </div>
                """, unsafe_allow_html=True)
        
        # --- NEW: FINANCIAL SUMMARY TABLE ---
        st.write("#### 💰 Estimated Daily Profit Summary")
        unit_rate = 37.0
        # Assuming 5 peak generation hours per day for calculation
        daily_profits = [p * 5 * unit_rate for p in powers]
        
        profit_df = pd.DataFrame({
            "Date": dates,
            "Condition": descs,
            "Expected Gen (kW)": powers,
            "Daily Profit (LKR)": [f"Rs. {p:.2f}" for p in daily_profits]
        })
        st.table(profit_df)

        st.line_chart(pd.DataFrame({"Date": dates, "Predicted kW": powers}).set_index("Date"))
        
        avg_p = sum(powers)/5
        total_profit = sum(daily_profits)
        if avg_p > 2.5:
            st.success(f"🚀 **AI Prediction:** Bright days ahead! Total 5-day profit: **Rs. {total_profit:.2f}**")
        else:
            st.warning(f"⚠️ **AI Prediction:** Low yield expected. Total 5-day profit: **Rs. {total_profit:.2f}**")

else:
    st.error("Please check the city name.")