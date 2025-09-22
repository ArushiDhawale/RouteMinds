import pandas as pd
import sys

def get_platform_queues(trains_df, platforms_df):
    """
    Sorts all trains based on priority rules and assigns them to a virtual queue
    for each platform.

    Args:
        trains_df (pd.DataFrame): DataFrame of trains.
        platforms_df (pd.DataFrame): DataFrame of platform and line statuses.

    Returns:
        A dictionary where keys are platform IDs and values are lists of
        dictionaries representing the trains in that platform's queue.
    """
    queues = {}
    
    # Sort ALL trains based on the defined rules: Priority -> Delay -> Clearance Time
    # Higher priority is a lower number. We use a negative sign for delay
    # to sort the highest delay first. Lower clearance time is better.
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

def recommend_next_train(trains_df, platforms_df):
    """
    AI Engine that recommends a train based on rules and platform availability.

    (This function is kept for a separate recommendation feature, if needed.)
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