import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh

# --- Constants ---
REFRESH_INTERVAL = 180  # Auto-refresh interval in seconds
COUNTDOWN_REFRESH = 1   # Update countdown every 1 second

# --- Auto-refresh the page for countdown ---
st_autorefresh(interval=COUNTDOWN_REFRESH * 1000, key="countdown_timer")

# --- Session state for last full refresh ---
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

# --- Remaining time calculation ---
elapsed = time.time() - st.session_state.last_refresh
remaining = max(0, REFRESH_INTERVAL - int(elapsed))

# --- Trigger full refresh if interval passed ---
if remaining == 0:
    st.session_state.last_refresh = time.time()
    st.experimental_rerun()

# --- AI Recommendation Engine ---
def get_recommendations_with_platforms(trains_df, platforms_df):
    available_lines = platforms_df[platforms_df['Is_Available'] == True].to_dict('records')
    trains_list = trains_df.to_dict('records')
    sorted_trains = sorted(trains_list, key=lambda train: (
        train.get('priority', 0),
        -train.get('delay', 0),
        train.get('clearance_time', 0)
    ))
    num_suggestions = min(len(sorted_trains), len(available_lines), 10)
    recommendations = []
    for i in range(num_suggestions):
        recommendations.append((sorted_trains[i], available_lines[i]))
    return recommendations

# --- Streamlit Layout ---
st.set_page_config(page_title="Train Section Controller", layout="wide")
st.title("🚂 AI Train Section Controller Dashboard")

# --- Manual Refresh Button ---
if st.button("🔄 Refresh Now"):
    st.session_state.last_refresh = time.time()
    st.experimental_rerun()

# --- Countdown display ---
st.caption(f"⏳ Next auto-refresh in **{remaining} seconds**")

# --- Timestamp ---
st.write(f"Displaying recommendations for **{pd.Timestamp.now(tz='Asia/Kolkata').strftime('%A, %d %B %Y %I:%M %p IST')}**")

# --- Load Data ---
try:
    BASE_DIR = os.getcwd()
    df_trains = pd.read_csv(os.path.join(BASE_DIR, "trains.csv"))
    df_platforms = pd.read_csv(os.path.join(BASE_DIR, "platform_dataset.csv"))

    # --- Sidebar for Data Preview ---
    st.sidebar.header("Live Data Preview")
    st.sidebar.write("Waiting Trains:")
    st.sidebar.dataframe(df_trains.head())
    st.sidebar.write("Platform Status:")
    st.sidebar.dataframe(df_platforms)

    # --- Run AI Engine ---
    full_recommendations = get_recommendations_with_platforms(df_trains, df_platforms)

    # --- Display Recommendations ---
    st.header("🏆 Top Actionable Recommendations")
    if full_recommendations:
        output_data = []
        for i, (train, platform) in enumerate(full_recommendations):
            output_data.append({
                "Rank": i + 1,
                "Train Name": train.get('Train_Name', train.get('Trip_ID', 'Unknown')),
                "Priority": train.get('priority', 0),
                "Delay (s)": train.get('delay', 0),
                "Suggested Platform": f"{platform.get('Platform_ID', 'N/A')}, {platform.get('Line_ID', 'N/A')}"
            })
        df_display = pd.DataFrame(output_data)
        st.table(df_display.set_index("Rank"))
    else:
        st.info("ℹ️ No recommendations to display. Either no trains are waiting or no platforms are available.")

except FileNotFoundError as e:
    st.error(f"❌ Error: Could not find the file '{e.filename}'. Please ensure both CSV files are in the same directory.")
