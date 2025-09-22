import streamlit as st
import pandas as pd

# --- (Copy your existing functions here) ---
def get_recommendations_with_platforms(trains_df, platforms_df):
    """
    AI Engine that ranks trains and suggests an available platform for each of the top 10.
    """
    available_lines = platforms_df[platforms_df['Is_Available'] == True].to_dict('records')
    trains_list = trains_df.to_dict('records')
    sorted_trains = sorted(trains_list, key=lambda train: (
        train['priority'],
        -train['delay'],
        train['clearance_time']
    ))
    num_suggestions = min(len(sorted_trains), len(available_lines), 10)
    recommendations = []
    for i in range(num_suggestions):
        recommendations.append((sorted_trains[i], available_lines[i]))
    return recommendations

# --- Streamlit App Layout ---

st.set_page_config(page_title="Train Section Controller", layout="wide")

st.title("🚂 AI Train Section Controller Dashboard")
st.write(f"Displaying recommendations for **{pd.Timestamp.now(tz='Asia/Kolkata').strftime('%A, %d %B %Y %I:%M %p IST')}**")

# --- Load Data ---
try:
    df_trains = pd.read_csv("trains.csv")
    df_platforms = pd.read_csv("platform_dataset.csv")

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
        # Create a clean DataFrame for display
        output_data = []
        for i, (train, platform) in enumerate(full_recommendations):
            output_data.append({
                "Rank": i + 1,
                "Train Name": train.get('Train_Name', train.get('Trip_ID')),
                "Priority": train['priority'],
                "Delay (s)": train['delay'],
                "Suggested Platform": f"{platform['Platform_ID']}, {platform['Line_ID']}"
            })
        
        df_display = pd.DataFrame(output_data)
        st.table(df_display.set_index("Rank"))

    else:
        st.info("ℹ️ No recommendations to display. Either no trains are waiting or no platforms are available.")

except FileNotFoundError as e:
    st.error(f"❌ Error: Could not find the file '{e.filename}'. Please ensure both CSV files are in the same directory.")