import pandas as pd

def get_recommendations_with_platforms(trains_df, platforms_df):
    """
    AI Engine that ranks trains and suggests an available platform for each of the top 10.

    Args:
        trains_df (pd.DataFrame): DataFrame of trains waiting for clearance.
        platforms_df (pd.DataFrame): DataFrame of platform and line statuses.

    Returns:
        A list of tuples, where each tuple contains a recommended train (dict)
        and its suggested platform (dict).
    """
    # Step 1: Get all available platforms
    available_lines = platforms_df[platforms_df['Is_Available'] == True].to_dict('records')
    
    # Step 2: Get all waiting trains and sort them
    trains_list = trains_df.to_dict('records')
    sorted_trains = sorted(trains_list, key=lambda train: (
        train['priority'],
        -train['delay'],
        train['clearance_time']
    ))
    
    # Step 3: Pair the top-ranked trains with available platforms
    # We'll take the top 10 trains and match them with the available lines.
    # The number of suggestions will be limited by whichever list is shorter.
    num_suggestions = min(len(sorted_trains), len(available_lines), 10)
    
    recommendations = []
    for i in range(num_suggestions):
        recommendations.append((sorted_trains[i], available_lines[i]))
        
    return recommendations

def run_simulation(trains_filepath, platforms_filepath):
    """
    Main function to load data and run the simulation.
    """
    # --- Load the datasets ---
    try:
        df_trains = pd.read_csv(trains_filepath)
        df_platforms = pd.read_csv(platforms_filepath)
    except FileNotFoundError as e:
        print(f"❌ Error: Could not find the file '{e.filename}'.")
        return

    # --- Run the AI Engine ---
    print("--- 🚂 Section Controller AI ---")
    print(f"Ranking {len(df_trains)} trains against {len(df_platforms[df_platforms['Is_Available'] == True])} available platform lines.")
    print("---------------------------------")

    full_recommendations = get_recommendations_with_platforms(df_trains, df_platforms)

    # --- Output the final decision ---
    if full_recommendations:
        print("\n🏆 Top Actionable Recommendations:")
        for i, (train, platform) in enumerate(full_recommendations):
            train_name = train.get('Train_Name', train.get('Trip_ID'))
            platform_name = f"{platform['Platform_ID']}, {platform['Line_ID']}"
            
            print(f"  {i+1}. Clear Train: {train_name:<18} -> Assign to: {platform_name}")
            print(f"     (Priority: {train['priority']}, Delay: {train['delay']:>4}s)")
    else:
        print("ℹ️ No recommendations. Either no trains are waiting or no platforms are available.")


# --- Main execution block ---
if __name__ == "__main__":
    train_data_file = "trains.csv"
    platform_data_file = "platform_dataset.csv"
    run_simulation(train_data_file, platform_data_file)
