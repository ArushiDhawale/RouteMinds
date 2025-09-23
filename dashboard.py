import streamlit as st
import pandas as pd
import numpy as np
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
    # Persist updates to CSV
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

    # --- Platform Queues: SINGLE combined editable table per platform ---
    st.header("📊 Platform Queue Status")
    platform_queues = get_platform_queues(df_trains, df_platforms)

    # File to persist manual overrides (global across platforms)
    overrides_file = os.path.join(BASE_DIR, "queued_overrides.csv")
    if os.path.exists(overrides_file):
        df_overrides = pd.read_csv(overrides_file, dtype={"Trip ID": str})
        # Ensure Manual Priority column exists and is string for safe display
        if "Manual Priority" not in df_overrides.columns:
            df_overrides["Manual Priority"] = ""
        df_overrides["Manual Priority"] = df_overrides["Manual Priority"].astype(str)
    else:
        df_overrides = pd.DataFrame(columns=["Trip ID", "Manual Priority"])

    # helper to extract numeric manual priority or NaN
    def parse_manual_priority(x):
        try:
            if pd.isna(x) or x == "":
                return np.nan
            return int(float(x))
        except Exception:
            return np.nan

    import re
    def platform_sort_key(p):
        match = re.search(r'\d+', p)
        return int(match.group()) if match else float('inf')

    if not platform_queues:
        st.info("✅ No queues to display. All platforms are busy or no trains are waiting.")
    else:
        for platform in sorted(platform_queues.keys(), key=platform_sort_key):
            queue = platform_queues[platform]
            st.subheader(f"Platform: {platform}")
            if not queue:
                st.write("- No trains in queue.")
                continue

            # Build combined table rows
            table_rows = []
            for i, train in enumerate(queue):
                status = "Arriving" if i == 0 else "Queued"
                trip_id = str(train.get("Trip_ID", "N/A"))
                # get stored manual priority if any
                manual_priority = ""
                match = df_overrides[df_overrides["Trip ID"] == trip_id]
                if not match.empty:
                    manual_priority = match.iloc[0]["Manual Priority"]

                table_rows.append({
                    "Status": status,
                    "Train Name": train.get("Train_Name", "Unknown"),
                    "Trip ID": trip_id,
                    "AI Priority": train.get("priority", 0),
                    "Manual Priority": manual_priority,
                    "Delay (s)": train.get("delay", 0)
                })

            df_platform = pd.DataFrame(table_rows)

            # Prepare a stable sort value for display BEFORE showing to user
            # (Arriving => -1, otherwise Manual if present else AI Priority)
            df_platform["_Manual_Num"] = df_platform["Manual Priority"].apply(parse_manual_priority)
            df_platform["_SortVal"] = df_platform.apply(
                lambda r: -1 if r["Status"] == "Arriving" else (int(r["_Manual_Num"]) if not np.isnan(r["_Manual_Num"]) else int(r["AI Priority"])),
                axis=1
            )
            # Secondary sort: Delay desc for ties (higher delay first)
            df_platform_sorted = df_platform.sort_values(by=["_SortVal", "Delay (s)"], ascending=[True, False]).drop(columns=["_Manual_Num", "_SortVal"]).reset_index(drop=True)

            # Show single editable table (Manual Priority editable)
            edited_df = st.data_editor(
                df_platform_sorted,
                column_config={
                    "Manual Priority": st.column_config.NumberColumn(
                        "Manual Priority (0 = Topmost)",
                        help="Set manual override priority (0 = topmost). Leave blank to use AI Priority.",
                        min_value=0
                    )
                },
                hide_index=True,
                disabled=["Status", "Train Name", "Trip ID", "AI Priority", "Delay (s)"]
            )

            # After edit: sync overrides for this platform back into global df_overrides
            # Build current platform overrides from edited_df (keep only non-empty manual priorities)
            edited_df_local = edited_df[["Trip ID", "Manual Priority"]].copy()
            # Normalize manual priority to numeric (drop blanks)
            edited_df_local["Manual Priority"] = pd.to_numeric(edited_df_local["Manual Priority"], errors="coerce")
            edited_df_local = edited_df_local.dropna().astype({"Manual Priority": int})
            # Convert Trip ID to str
            edited_df_local["Trip ID"] = edited_df_local["Trip ID"].astype(str)

            # Determine if there is any change compared to df_overrides for the Trip IDs in this platform
            platform_trip_ids = set(df_platform["Trip ID"].astype(str).tolist())
            old_subset = df_overrides[df_overrides["Trip ID"].isin(platform_trip_ids)].copy()
            # Build comparable dicts
            old_map = {str(r["Trip ID"]): parse_manual_priority(r["Manual Priority"]) for _, r in old_subset.iterrows()}
            new_map = {str(r["Trip ID"]): int(r["Manual Priority"]) for _, r in edited_df_local.iterrows()}

            # If old_map != new_map (considering absent keys as NaN), update global df_overrides
            changed = False
            # Check added/changed keys
            for k, v in new_map.items():
                if k not in old_map or old_map.get(k) != v:
                    changed = True
                    break
            # Check removed keys
            if not changed:
                for k in old_map.keys():
                    if k not in new_map:
                        changed = True
                        break

            if changed:
                # Remove any existing overrides for this platform's trips
                df_overrides = df_overrides[~df_overrides["Trip ID"].isin(platform_trip_ids)].copy()
                # Append updated overrides for this platform (if any)
                if not edited_df_local.empty:
                    # store Manual Priority as int (string-safe)
                    to_append = edited_df_local.copy()
                    to_append["Manual Priority"] = to_append["Manual Priority"].astype(int).astype(str)
                    # Ensure columns names match
                    to_append = to_append[["Trip ID", "Manual Priority"]]
                    df_overrides = pd.concat([df_overrides, to_append], ignore_index=True)
                # Save global overrides file
                df_overrides.to_csv(overrides_file, index=False)
                # Re-run so the displayed table redraws in updated sorted order
                st.experimental_rerun()

except FileNotFoundError as e:
    st.error(f"❌ Error: Could not find the file '{e.filename}'. Please ensure both CSV files are in the same directory.")
