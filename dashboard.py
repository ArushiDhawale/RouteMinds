import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
from main import get_platform_queues  # Import your platform queue logic

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
    """
    AI Engine that ranks trains and suggests an available platform for each of the top 10.
    """
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

    # --- Editable Platform Status ---
    st.sidebar.write("Platform Status (Toggle availability below):")

    df_platforms = st.sidebar.data_editor(
        df_platforms,
        column_config={
            "Is_Available": st.column_config.CheckboxColumn(
                "Is Available",
                help="Tick to mark platform as available",
                default=True
            )
        },
        hide_index=True
    )

    # Persist updates to CSV so toggles stay after refresh
    df_platforms.to_csv(os.path.join(BASE_DIR, "platform_dataset.csv"), index=False)

    # --- AI Recommendations Table ---
    full_recommendations = get_recommendations_with_platforms(df_trains, df_platforms)
    st.header("🏆 Top Actionable Recommendations")
    if full_recommendations:
        output_data = []
        for i, (train, platform) in enumerate(full_recommendations):
            output_data.append({
                "Rank": i + 1,
                "Trip ID": train.get('Trip_ID', 'Unknown'),
                "Priority": train.get('priority', 0),
                "Delay (s)": train.get('delay', 0),
                "Suggested Platform": f"{platform.get('Platform_ID', 'N/A')}, {platform.get('Line_ID', 'N/A')}"
            })
        df_display = pd.DataFrame(output_data)
        st.dataframe(df_display.set_index("Rank"))
    else:
        st.info("ℹ️ No recommendations to display. Either no trains are waiting or no platforms are available.")

    # --- Platform Queues: Separate Tables per Platform ---
    st.header("📊 Platform Queue Status")
    platform_queues = get_platform_queues(df_trains, df_platforms)

    if not platform_queues:
        st.info("✅ No queues to display. All platforms are busy or no trains are waiting.")
    else:
        import re
        def platform_sort_key(p):
            match = re.search(r'\d+', p)
            return int(match.group()) if match else float('inf')

        for platform in sorted(platform_queues.keys(), key=platform_sort_key):
            queue = platform_queues[platform]
            st.subheader(f"Platform: {platform}")
            if not queue:
                st.write("- No trains in queue.")
                continue

            platform_rows = []
            for i, train in enumerate(queue):
                status = "Arriving" if i == 0 else "Queued"
                platform_rows.append({
                    "Status": status,
                    "Train Name": train.get('Train_Name', 'Unknown'),
                    "Trip ID": train.get('Trip_ID', 'N/A'),
                    "Priority": train.get('priority', 0),
                    "Delay (s)": train.get('delay', 0)
                })
            
            df_platform = pd.DataFrame(platform_rows)

            # --- Color-coding rows ---
            def highlight_row(row):
                if row.Status == "Arriving":
                    return [] * len(row)
                elif row.Status == "Queued":
                    return [] * len(row)
                elif row['Delay (s)'] > 300:  # example threshold for high delay
                    return [] * len(row)
                else:
                    return [] * len(row)

            st.dataframe(df_platform.style.apply(highlight_row, axis=1))

except FileNotFoundError as e:
    st.error(f"❌ Error: Could not find the file '{e.filename}'. Please ensure both CSV files are in the same directory.")
