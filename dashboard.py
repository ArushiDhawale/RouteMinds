import streamlit as st
import pandas as pd
import numpy as np
import os
import time
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import re

# --- Constants ---
REFRESH_INTERVAL = 180  # seconds
COUNTDOWN_REFRESH = 1
ALLOWED_LABELS = ["High", "Low"]

# --- Auto-refresh ---
st_autorefresh(interval=COUNTDOWN_REFRESH * 1000, key="countdown_timer")
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

elapsed = time.time() - st.session_state.last_refresh
remaining = max(0, REFRESH_INTERVAL - int(elapsed))
if remaining == 0:
    st.session_state.last_refresh = time.time()
    st.experimental_rerun()

st.set_page_config(page_title="Train Section Controller", layout="wide")
st.title("AI Train Section Controller Dashboard")

if st.button("🔄 Refresh Now"):
    st.session_state.last_refresh = time.time()
    st.experimental_rerun()

st.caption(f"⏳ Next auto-refresh in **{remaining} seconds**")
st.write(f"Displaying recommendations for **{pd.Timestamp.now(tz='Asia/Kolkata').strftime('%A, %d %B %Y %I:%M %p IST')}**")

# --- Helpers ---
def safe_int(x, fallback=0):
    try:
        return int(x)
    except Exception:
        return fallback

def get_platform_queues(trains_df, platforms_df):
    # This is a mock function, as the original was not provided.
    # In a real scenario, this would contain the core logic for assigning trains to platforms.
    # We will simulate some queues based on the provided data.
    platform_queues = {}
    for _, platform in platforms_df.iterrows():
        platform_id = platform["Platform_ID"]
        # Filter trains based on some criteria, e.g., platform_id in their route
        # For this example, we'll just distribute them round-robin to a few platforms
        if platform_id not in platform_queues:
            platform_queues[platform_id] = []

    # Simple mock distribution of trains
    trains_list = trains_df.to_dict('records')
    sorted_trains = sorted(trains_list, key=lambda t: t.get('priority', 0))

    platforms_with_queues = sorted([p for p in platforms_df["Platform_ID"] if p in platform_queues], key=lambda p: int(re.search(r'\d+', p).group()) if re.search(r'\d+', p) else float('inf'))
    
    for i, train in enumerate(sorted_trains):
        platform_id = platforms_with_queues[i % len(platforms_with_queues)]
        platform_queues[platform_id].append(train)
        
    return platform_queues

# --- Load Data ---
BASE_DIR = os.getcwd()
trains_file = os.path.join(BASE_DIR, "trains.csv")
platforms_file = os.path.join(BASE_DIR, "platform_dataset.csv")
overrides_file = os.path.join(BASE_DIR, "queued_overrides.csv")

# Create dummy files if they don't exist
if not os.path.exists(trains_file):
    dummy_trains = pd.DataFrame({
        "Trip_ID": [f"T{i:03}" for i in range(1, 21)],
        "Train_Name": [f"Express-{i}" for i in range(1, 21)],
        "priority": np.random.randint(1, 10, 20),
        "delay": np.random.randint(0, 3600, 20),
        "clearance_time": np.random.randint(10, 100, 20)
    })
    dummy_trains.to_csv(trains_file, index=False)

if not os.path.exists(platforms_file):
    dummy_platforms = pd.DataFrame({
        "Platform_ID": [f"P{i}" for i in range(1, 11)],
        "Line_ID": [f"Line-{i}" for i in range(1, 11)],
        "Is_Available": [True] * 10
    })
    dummy_platforms.to_csv(platforms_file, index=False)

df_trains = pd.read_csv(trains_file)
df_platforms = pd.read_csv(platforms_file)

# --- Session State ---
if "platform_original" not in st.session_state:
    st.session_state.platform_original = df_platforms["Is_Available"].copy()
if "pending_platform" not in st.session_state:
    st.session_state.pending_platform = None
if "pending_priority_platforms" not in st.session_state:
    st.session_state.pending_priority_platforms = {}  # key: platform, value: pending changes
if "platforms_sidebar" not in st.session_state:
    st.session_state.platforms_sidebar = df_platforms.copy()  # For sidebar editor control
if "df_overrides" not in st.session_state:
    if os.path.exists(overrides_file):
        st.session_state.df_overrides = pd.read_csv(overrides_file, dtype={"Trip ID": str})
        if "Manual Priority" not in st.session_state.df_overrides.columns:
            st.session_state.df_overrides["Manual Priority"] = ""
    else:
        st.session_state.df_overrides = pd.DataFrame(columns=["Trip ID", "Manual Priority"])
if "revert_trigger" not in st.session_state:
    st.session_state.revert_trigger = 0

# --- Sidebar ---
st.sidebar.header("Live Data Preview")
st.sidebar.subheader("Waiting Trains")
st.sidebar.dataframe(df_trains.head())

st.sidebar.subheader("Platform Status (Toggle availability below)")
df_platforms_edit = st.sidebar.data_editor(
    st.session_state.platforms_sidebar,
    column_config={
        "Is_Available": st.column_config.CheckboxColumn(
            "Is Available",
            help="Tick to mark platform as available",
            default=True
        )
    },
    hide_index=True
)

# --- Detect platform availability changes ---
changed_platforms = df_platforms_edit["Is_Available"] != st.session_state.platform_original
if changed_platforms.any() and st.session_state.pending_platform is None:
    st.session_state.pending_platform = df_platforms_edit.copy()

if st.session_state.pending_platform is not None:
    st.warning("⚠️ Platform availability changes detected! Apply changes?")
    col1, col2 = st.columns(2)
    if col1.button("Agree - Apply Changes"):
        st.session_state.pending_platform.to_csv(os.path.join(BASE_DIR, "platform_dataset.csv"), index=False)
        st.session_state.platform_original = st.session_state.pending_platform["Is_Available"].copy()
        st.session_state.pending_platform = None
        st.session_state.platforms_sidebar = st.session_state.pending_platform.copy()
        st.experimental_rerun()
    if col2.button("Disagree - Revert Changes"):
        st.session_state.platforms_sidebar["Is_Available"] = st.session_state.platform_original.copy()
        st.session_state.pending_platform = None
        st.experimental_rerun()

# --- AI Recommendations ---
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

full_recommendations = get_recommendations_with_platforms(df_trains, df_platforms)
st.header("Top Actionable Recommendations")
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
    st.info(" No recommendations to display.")

# --- Platform Queues ---
st.header(" Platform Queue Status")
platform_queues = get_platform_queues(df_trains, df_platforms)

if platform_queues:
    def platform_sort_key(p):
        match = re.search(r'\d+', str(p))
        return int(match.group()) if match else float('inf')

    for platform in sorted(platform_queues.keys(), key=platform_sort_key):
        queue = platform_queues[platform]
        st.subheader(f"Platform: {platform}")
        if not queue:
            st.write("- No trains in queue.")
            continue

        table_rows = []
        for i, train in enumerate(queue):
            status = "Arriving" if i == 0 else "Queued"
            trip_id = str(train.get("Trip_ID", "N/A"))
            
            # Get manual priority from the current state
            manual_priority = st.session_state.df_overrides[
                st.session_state.df_overrides["Trip ID"] == trip_id
            ]["Manual Priority"].iloc[0] if trip_id in st.session_state.df_overrides["Trip ID"].values else ""

            table_rows.append({
                "Status": status,
                "Train Name": train.get("Train_Name", "Unknown"),
                "Trip ID": trip_id,
                "AI Priority": train.get("priority", 0),
                "Manual Priority": manual_priority if status == "Queued" else "",
                "Delay (s)": train.get("delay", 0)
            })

        df_platform = pd.DataFrame(table_rows)

        # Sorting: Arriving -> High -> AI -> Low
        def sort_value(row):
            if row["Status"] == "Arriving":
                return -1
            elif row["Manual Priority"] == "High":
                return 0
            elif row["Manual Priority"] == "Low":
                return 9999
            else:
                return safe_int(row["AI Priority"], fallback=500) + 10

        df_platform["_SortVal"] = df_platform.apply(sort_value, axis=1)
        df_sorted = df_platform.sort_values(
            by=["_SortVal", "Delay (s)"], ascending=[True, False]
        ).drop(columns=["_SortVal"]).reset_index(drop=True)

        # Add Sr. No
        df_sorted["Sr. No"] = df_sorted.index + 1
        cols = ["Sr. No"] + [c for c in df_sorted.columns if c != "Sr. No"]
        df_sorted = df_sorted[cols]

        # Get a copy for comparison
        df_before_edit = df_sorted.copy()
        
        # We need a dynamic key to force a reset
        data_editor_key = f"editor_{platform}_{st.session_state.revert_trigger}"

        edited_df = st.data_editor(
            df_sorted,
            key=data_editor_key,
            column_config={
                "Manual Priority": st.column_config.SelectboxColumn(
                    "Manual Priority",
                    options=["High", "Low", ""],
                    help="Set manual override (only for queued trains)"
                )
            },
            disabled=["Sr. No", "Status", "Train Name", "Trip ID", "AI Priority", "Delay (s)"],
            hide_index=True
        )

        # Detect changes per platform
        edited_priorities = edited_df.set_index("Trip ID")["Manual Priority"].to_dict()
        original_priorities = df_before_edit.set_index("Trip ID")["Manual Priority"].to_dict()
        
        has_changes = False
        for trip_id in edited_priorities:
            if edited_priorities[trip_id] != original_priorities[trip_id]:
                has_changes = True
                break

        if has_changes and platform not in st.session_state.pending_priority_platforms:
            st.session_state.pending_priority_platforms[platform] = edited_df.copy()

        # Confirmation alert for this platform
        if platform in st.session_state.pending_priority_platforms:
            st.warning(f"⚠️ Manual priority changes detected for Platform {platform}! Apply changes?")
            col1, col2 = st.columns(2)
            if col1.button(f"Agree - Apply Changes for {platform}"):
                pending_df = st.session_state.pending_priority_platforms[platform]
                # Update the main overrides DataFrame
                for _, row in pending_df.iterrows():
                    trip_id = row["Trip ID"]
                    manual_priority = row["Manual Priority"]
                    
                    if trip_id in st.session_state.df_overrides["Trip ID"].values:
                        st.session_state.df_overrides.loc[st.session_state.df_overrides["Trip ID"] == trip_id, "Manual Priority"] = manual_priority
                    else:
                        new_row = pd.DataFrame([{"Trip ID": trip_id, "Manual Priority": manual_priority}])
                        st.session_state.df_overrides = pd.concat([st.session_state.df_overrides, new_row], ignore_index=True)
                
                # Remove rows with empty manual priority
                st.session_state.df_overrides = st.session_state.df_overrides[st.session_state.df_overrides["Manual Priority"].isin(ALLOWED_LABELS)]

                st.session_state.df_overrides.to_csv(overrides_file, index=False)
                del st.session_state.pending_priority_platforms[platform]
                st.experimental_rerun()

            if col2.button(f"Disagree - Revert Changes for {platform}"):
                if platform in st.session_state.pending_priority_platforms:
                    del st.session_state.pending_priority_platforms[platform]
                
                # Reload overrides from file to ensure the state is completely reset
                if os.path.exists(overrides_file):
                    st.session_state.df_overrides = pd.read_csv(overrides_file, dtype={"Trip ID": str})
                    if "Manual Priority" not in st.session_state.df_overrides.columns:
                        st.session_state.df_overrides["Manual Priority"] = ""
                else:
                    st.session_state.df_overrides = pd.DataFrame(columns=["Trip ID", "Manual Priority"])
                
                # Increment the trigger to force a UI reset
                st.session_state.revert_trigger += 1
                
                st.experimental_rerun()
