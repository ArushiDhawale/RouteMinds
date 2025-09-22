import pandas as pd

def recommend_next_train(trains_df, platforms_df):
    """
    AI Engine that recommends a train based on rules and platform availability.

    Args:
        trains_df (pd.DataFrame): DataFrame of trains waiting for clearance.
        platforms_df (pd.DataFrame): DataFrame of platform and line statuses.

    Returns:
        A tuple containing the recommended train (dict) and the assigned line (dict),
        or (None, None) if no action can be taken.
    """
    # Rule 0: Check for available lines first.
    available_lines = platforms_df[platforms_df['Is_Available'] == True]
    
    if available_lines.empty:
        print("🛑 No available lines. All trains must hold.")
        return None, None
    
    if trains_df.empty:
        print("✅ No trains waiting. All clear.")
        return None, None
        
    # Convert DataFrame to a list of dictionaries for easier processing
    trains_list = trains_df.to_dict('records')

    # Apply the sorting rules (Priority -> Delay -> Clearance Time)
    # Note: A lower number is a higher priority.
    # We use a negative sign for delay to sort the highest delay first.
    sorted_trains = sorted(trains_list, key=lambda train: (
        train['priority'],
        -train['delay'],
        train['clearance_time']
    ))
    
    # The top-ranked train is our best recommendation
    top_recommendation = sorted_trains[0]
    
    # Assign it to the first available line found
    assigned_line = available_lines.iloc[0].to_dict()
    
    return top_recommendation, assigned_line

def run_simulation(trains_filepath, platforms_filepath):
    """
    Main function to load data and run the simulation.
    """
    # --- Step 1: Load the datasets from the provided files ---
    try:
        df_trains = pd.read_csv(trains_filepath)
        df_platforms = pd.read_csv(platforms_filepath)
    except FileNotFoundError as e:
        print(f"❌ Error: Could not find the file '{e.filename}'.")
        print("Please ensure both CSV files are in the same directory as the script.")
        return

    # --- Step 2: Run the AI Engine ---
    print("--- 🚂 Section Controller AI ---")
    print(f"Checking status for {len(df_trains)} waiting trains...")
    print(f"Found {len(df_platforms[df_platforms['Is_Available'] == True])} available platform lines.")
    print("---------------------------------")

    recommended_train, assigned_line = recommend_next_train(df_trains, df_platforms)

    # --- Step 3: Output the final decision ---
    if recommended_train and assigned_line:
        print("\n✅ Recommendation Found:")
        print(f"  -> Clear Train: {recommended_train.get('Train_Name', recommended_train.get('Trip_ID'))}")
        print(f"     (Priority: {recommended_train['priority']}, Delay: {recommended_train['delay']}s, Clearance: {recommended_train['clearance_time']}s)")
        print(f"  -> Assign to:   {assigned_line['Platform_ID']}, {assigned_line['Line_ID']}")

# --- Main execution block ---
if __name__ == "__main__":
    # Define the file paths for your datasets
    train_data_file = "trains.csv"
    platform_data_file = "platform_dataset.csv"
    
    # Run the simulation with your files
    run_simulation(train_data_file, platform_data_file)
