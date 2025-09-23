import pandas as pd
import sys

def get_platform_queues(trains_df, platforms_df):
    """
    Sorts all trains based on priority rules and assigns them to a virtual queue
    for each platform.

    Returns:
        dict: A dictionary where keys are platform IDs and values are lists of
              dictionaries representing the trains in that platform's queue.
    """
    queues = {}
    
    # Sort all trains based on the defined rules: Priority -> Delay -> Clearance Time
    sorted_trains = trains_df.sort_values(
        by=['priority', 'delay', 'clearance_time'], 
        ascending=[True, False, True]
    )
    
    # Assign trains to platforms based on the `Platform_No` in the trains dataset
    for i, train in sorted_trains.iterrows():
        assigned_platform_id = f"Platform_{int(train['Platform_No'])}"
        
        if assigned_platform_id not in queues:
            queues[assigned_platform_id] = []
        
        queues[assigned_platform_id].append(train.to_dict())

    return queues

def get_recommendations_with_platforms(trains_df, platforms_df):
    """
    AI Engine that ranks trains and suggests an available platform for each of the top 10.

    Args:
        trains_df (pd.DataFrame): DataFrame of trains.
        platforms_df (pd.DataFrame): DataFrame of platform and line statuses.

    Returns:
        list: A list of tuples, where each tuple contains a recommended train (dict)
              and its suggested platform (dict).
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

def recommend_next_train(trains_df, platforms_df):
    """
    AI Engine that recommends a single train based on rules and platform availability.

    Args:
        trains_df (pd.DataFrame): DataFrame of trains.
        platforms_df (pd.DataFrame): DataFrame of platform statuses.

    Returns:
        tuple: (recommended_train_dict, assigned_platform_dict)
    """
    available_lines = platforms_df[platforms_df['Is_Available'] == True]
    
    if available_lines.empty or trains_df.empty:
        return None, None

    trains_list = trains_df.to_dict('records')
    sorted_trains = sorted(trains_list, key=lambda train: (
        train['priority'],
        -train['delay'],
        train['clearance_time']
    ))
    
    top_recommendation = sorted_trains[0]
    assigned_line = available_lines.iloc[0].to_dict()
    
    return top_recommendation, assigned_line

def interactive_update_delays(df):
    """
    Prompts the user for changes to train delays.

    Args:
        df (pd.DataFrame): The DataFrame of train data.

    Returns:
        pd.DataFrame: The updated DataFrame.
    """
    print("\n--- Current Train Delays ---")
    print(df[['Trip_ID', 'Train_Name', 'delay']].head(10))  # Show top rows for context
    
    while True:
        train_id = input("\nEnter the Trip_ID of the train to update (or 'q' to quit): ").strip()
        if train_id.lower() == 'q':
            break

        if train_id not in df['Trip_ID'].values:
            print("❌ Error: Trip_ID not found. Please try again.")
            continue

        try:
            new_delay = int(input(f"Enter the new delay in seconds for {train_id}: "))
        except ValueError:
            print("❌ Error: Invalid input. Please enter a number.")
            continue

        # Update the DataFrame
        df.loc[df['Trip_ID'] == train_id, 'delay'] = new_delay
        print(f"✅ Updated delay for {train_id} to {new_delay} seconds.")
        
    return df

def run_simulation(trains_filepath, platforms_filepath, df_trains_updated):
    """
    Main function to load data and run the simulation.
    """
    try:
        df_platforms = pd.read_csv(platforms_filepath)
    except FileNotFoundError as e:
        print(f"❌ Error: Could not find the file '{e.filename}'.")
        return

    print("\n--- 🚂 Section Controller AI ---")
    print(f"Ranking {len(df_trains_updated)} trains against {len(df_platforms[df_platforms['Is_Available'] == True])} available platform lines.")
    print("---------------------------------")

    full_recommendations = get_recommendations_with_platforms(df_trains_updated, df_platforms)

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

    try:
        df_trains_original = pd.read_csv(train_data_file)
        df_trains_updated = interactive_update_delays(df_trains_original.copy())
        run_simulation(train_data_file, platform_data_file, df_trains_updated)

    except FileNotFoundError as e:
        print(f"❌ Error: The file '{e.filename}' was not found.")
        print("Please ensure both CSV files are in the same directory as the script.")
