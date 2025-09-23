import streamlit as st
import pandas as pd
import numpy as np
import os
import time
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
from main import get_platform_queues  # Replace with your actual function
import re

# --- Constants ---
REFRESH_INTERVAL = 180  # seconds
COUNTDOWN_REFRESH = 1

# --- Auto-refresh ---
st_autorefresh(interval=COUNTDOWN_REFRESH * 1000, key="countdown_timer")

if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

elapsed = time.time() - st.session_state.last_refresh
remaining = max(0, REFRESH_INTERVAL - int(elapsed))

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

# --- Helpers ---
def safe_int(x, fallback=0):
    try:
        return int(x)
    except Exception:
        return fallback

# --- Layout ---
st.set_page_config(page_title="Train Section Controller", layout="wide")
st.title("🚂 AI Train Section Controller Dashboard")

if st.button("🔄 Refresh Now"):
    st.session_state.last_refresh = time.time()
    st.experimental_rerun()

st.caption(f"⏳ Next auto-refresh in **{remaining} seconds**")
st.write(f"Displaying recommendations for **{pd.Timestamp.now(tz='Asia/Kolkata').strftime('%A, %d %B %Y %I:%M %p IST')}**")

# --- Load Data ---
try:
    BASE_DIR = os.getcwd()
    df_trains = pd.read_csv(os.path.join(BASE_DIR, "trains.csv"))
    df_platforms = pd.read_csv(os.path.join(BASE_DIR, "platform_dataset.csv"))

    # Sidebar
    st.sidebar.header("Live Data Preview")
    st.sidebar.write("Waiting Trains:")
    st.sidebar.dataframe(df_trains.head())

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
    df_platforms.to_csv(os.path.join(BASE_DIR, "platform_dataset.csv"), index=False)

    # --- AI Recommendations ---
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
    overrides_file = os.path.join(BASE_DIR, "queued_overrides.csv")
    allowed_labels = ["High", "Low"]

    if os.path.exists(overrides_file):
        df_overrides = pd.read_csv(overrides_file, dtype={"Trip ID": str})
        if "Manual Priority" not in df_overrides.columns:
            df_overrides["Manual Priority"] = ""
        df_overrides["Manual Priority"] = df_overrides["Manual Priority"].apply(
            lambda x: str(x).strip() if str(x).strip() in allowed_labels else ""
        )
    else:
        df_overrides = pd.DataFrame(columns=["Trip ID", "Manual Priority"])

    if not platform_queues:
        st.info("✅ No queues to display.")
    else:
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

            # Save overrides
            edited_df_local = edited_df[["Trip ID", "Manual Priority"]].copy()
            edited_df_local = edited_df_local.dropna()
            edited_df_local = edited_df_local[edited_df_local["Manual Priority"] != ""]
            platform_trip_ids = set(df_platform["Trip ID"].astype(str).tolist())
            old_subset = df_overrides[df_overrides["Trip ID"].isin(platform_trip_ids)].copy()
            old_map = dict(zip(old_subset["Trip ID"], old_subset["Manual Priority"]))
            new_map = dict(zip(edited_df_local["Trip ID"], edited_df_local["Manual Priority"]))

            if old_map != new_map:
                df_overrides = df_overrides[~df_overrides["Trip ID"].isin(platform_trip_ids)].copy()
                if not edited_df_local.empty:
                    df_overrides = pd.concat([df_overrides, edited_df_local], ignore_index=True)
                df_overrides.to_csv(overrides_file, index=False)
                st.experimental_rerun()

except FileNotFoundError as e:
    st.error(f"❌ Could not find file '{e.filename}'. Please ensure CSVs are in the same directory.")
