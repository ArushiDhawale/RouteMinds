# RouteMinds

Prototype of an AI-based Section Controller for Railway Traffic Management

## **Overview**

RouteMinds is a prototype AI-driven section controller designed to optimize railway traffic management. It leverages a rule-based expert system to analyze real-time data on waiting trains and platform availability, dynamically updating train schedules to improve efficiency and reduce delays.

This system considers a dataset of 70 trains and generates updated schedules based on a prioritized evaluation of trains using:

1. Priority Level (highest priority first)

2. Delay Duration (longest waiting trains prioritized)

3. Clearance Time (shortest clearance times first)

The output is an actionable, ranked list of recommendations that assists human controllers in making optimized decisions for train dispatch and platform allocation.

## **Key Features**

1. Data-Driven: Reads real-time train and platform status from CSV files for easy integration and updates.

2. Rule-Based AI: Implements clear multi-level sorting to rank trains based on Priority → Delay → Clearance Time.

3. Intelligent Platform Allocation: Matches the highest-ranked trains to available platforms, maximizing throughput.

4. Manual Overrides: Allows human controllers to manually adjust train priority within queues for flexibility.

5. Auto-Refreshing Dashboard: Keeps the display up-to-date automatically, reflecting real-time changes.

6. Clean, Modern UI: Built with Streamlit, featuring custom styling and interactive data editors for ease of use.

7. Scalable Prototype: Designed to be easily extendable for larger datasets and more complex logic.

## **How It Works**

![Screenshot_20250929_152505_Slides(1)](https://github.com/user-attachments/assets/178a01f6-db35-4cab-a681-e23a1d0ec02a)


1. Load Data: Imports current train waitlist (trains.csv) and platform status (platform_dataset.csv).

2. Identify Resources: Detects platforms currently available for assignment.

3. Rank Trains: Sorts trains by priority, delay, and clearance time using a rule-based AI system.

4. Generate Recommendations: Pairs the top-ranked trains with available platforms, displaying a ranked list.

5. Manual Intervention: Allows users to override AI priorities for queued trains directly via the UI.

6. Update & Refresh: Automatically refreshes the dashboard periodically and allows manual refresh.

## **Dataset**

Prototype tested with a dataset consisting of 70 trains.

Train data includes trip IDs, names, priority levels, delay durations, and clearance times.

Platform dataset tracks availability status of multiple platforms and their corresponding lines.

## **Getting Started**
**Prerequisites**

1. Python 3.8+

2. streamlit

3. pandas

4. numpy

5. streamlit-autorefresh

**Install dependencies via pip:**
pip install streamlit pandas numpy streamlit-autorefresh

**Running the Application**

1. Place your trains.csv and platform_dataset.csv files in the project directory.

2. Run the Streamlit app:
streamlit run dashboard.py

3. Open the browser at the URL provided by Streamlit (usually http://localhost:8501) to access the dashboard.
