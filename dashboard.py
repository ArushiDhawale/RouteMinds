import streamlit as st
import pandas as pd
import numpy as np
import os
import time
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
from main import get_platform_queues
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
st.title("🚂 AI Train Section Controller Dashboard")

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

# --- Load Data ---
BASE_DIR = os.getcwd()
df_trains = pd.read_csv(os.path.join(BASE_DIR, "trains.csv"))
df_platforms = pd.read_csv(os.path.join(BASE_DIR, "platform_dataset.csv"))
overrides_file = os.path.join(BASE_DIR, "queued_overrides.csv")

# --- Session State ---
if "platform_original" not in st.session_state:
    st.session_state.platform_original = df_platforms["Is_Available"].copy()
if "pending_platform" not in st.session_state:
    st.session_state.pending_platform = None
if "pending_priority_platforms" not in st.session_state:
    st.session_state.pending_priority_platforms = {}  # key: platform, value: pending changes
if "platform_original_priority" not in st.session_state:
    st.session_state.platform_original_priority = {}  # key: platform, value: original priority df
if "platforms_sidebar" not in st.session_state:
    st.session_state.platforms_sidebar = df_platforms.copy()  # For sidebar editor control

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
    if col1.button("✅ Agree - Apply Changes"):
        df_platforms_edit.to_csv(os.path.join(BASE_DIR, "platform_dataset.csv"), index=False)
        st.session_state.platform_original = df_platforms_edit["Is_Available"].copy()
        st.session_state.pending_platform = None
        st.session_state.platforms_sidebar = df_platforms_edit.copy()
        st.experimental_rerun()
    if col2.button("❌ Disagree - Revert Changes"):
        # Revert editor to original
        st.session_state.platforms_sidebar["Is_Available"] = st.session_state.platform_original.copy()
        st.session_state.pending_platform = None
        st.experimental_rerun()

# --- Load overrides ---
if os.path.exists(overrides_file):
    df_overrides = pd.read_csv(overrides_file, dtype={"Trip ID": str})
    if "Manual Priority" not in df_overrides.columns:
        df_overrides["Manual Priority"] = ""
    df_overrides["Manual Priority"] = df_overrides["Manual Priority"].apply(
        lambda x: str(x).strip() if str(x).strip() in ALLOWED_LABELS else ""
    )
else:
    df_overrides = pd.DataFrame(columns=["Trip ID", "Manual Priority"])

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
    st.info("ℹ️ No recommendations to display.")

# --- Platform Queues ---
st.header("📊 Platform Queue Status")
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
            manual_priority = ""
            match = df_overrides[df_overrides["Trip ID"] == trip_id]
            if not match.empty:
                manual_priority = str(match.iloc[0]["Manual Priority"]).strip()
            table_rows.append({
                "Status": status,
                "Train Name": train.get("Train_Name", "Unknown"),
                "Trip ID": trip_id,
                "AI Priority": train.get("priority", 0),
                "Manual Priority": manual_priority if status == "Queued" else "",
                "Delay (s)": train.get("delay", 0)
            })

        df_platform = pd.DataFrame(table_rows)

        # Save original priority for revert
        if platform not in st.session_state.platform_original_priority:
            st.session_state.platform_original_priority[platform] = df_platform["Manual Priority"].copy()

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
        df_sorted["Sr. No"] = df_sorted.index
        cols = ["Sr. No"] + [c for c in df_sorted.columns if c != "Sr. No"]
        df_sorted = df_sorted[cols]

        # Editable table
        edited_df = st.data_editor(
            df_sorted,
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
        edited_df_local = edited_df[["Trip ID", "Manual Priority"]].copy()
        edited_df_local = edited_df_local[edited_df_local["Manual Priority"].isin(ALLOWED_LABELS)]
        old_subset = df_overrides[df_overrides["Trip ID"].isin(edited_df_local["Trip ID"])]
        old_map = dict(zip(old_subset["Trip ID"], old_subset["Manual Priority"]))
        new_map = dict(zip(edited_df_local["Trip ID"], edited_df_local["Manual Priority"]))

        if old_map != new_map and platform not in st.session_state.pending_priority_platforms:
            st.session_state.pending_priority_platforms[platform] = edited_df_local.copy()

        # Confirmation alert for this platform
        if platform in st.session_state.pending_priority_platforms:
            st.warning(f"⚠️ Manual priority changes detected for Platform {platform}! Apply changes?")
            col1, col2 = st.columns(2)
            if col1.button(f"✅ Agree - Apply Changes for Platform {platform}"):
                df_overrides = df_overrides[~df_overrides["Trip ID"].isin(st.session_state.pending_priority_platforms[platform]["Trip ID"])]
                df_overrides = pd.concat([df_overrides, st.session_state.pending_priority_platforms[platform]], ignore_index=True)
                df_overrides.to_csv(overrides_file, index=False)
                del st.session_state.pending_priority_platforms[platform]
                st.experimental_rerun()
            if col2.button(f"❌ Disagree - Revert Changes for Platform {platform}"):
                # Revert to original values
                for idx, trip_id in enumerate(df_platform["Trip ID"]):
                    df_platform.at[idx, "Manual Priority"] = st.session_state.platform_original_priority[platform].iloc[idx]
                del st.session_state.pending_priority_platforms[platform]
                st.experimental_rerun()
