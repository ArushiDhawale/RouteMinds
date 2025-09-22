# RouteMinds
Prototype of an AI-based section controller for railway traffic management.

AI-Based Train Section Controller
📖 Overview
This project is a prototype of an AI-based section controller for railway traffic management. It uses a rule-based expert system to analyze real-time data about waiting trains and platform availability. The system's goal is to provide a ranked list of actionable recommendations to a human controller, helping them make efficient and logical decisions to optimize train flow and minimize delays.

This script is designed for simulation and can be easily adapted for more complex scenarios.

✨ Key Features
Data-Driven: Reads train schedules and platform statuses directly from CSV files.
Rule-Based AI: Implements a clear, priority-driven logic to rank trains based on:

Priority Level (Highest first)
Delay Duration (Longest wait first)
Clearance Time (Shortest time first)

Intelligent Matching: Automatically pairs the highest-priority trains with available platforms.
Actionable Output: Generates a top-10 list of clear, ranked recommendations for the controller.
Modular and Scalable: Built with Python and pandas, making it easy to modify rules or expand functionality.

⚙️ How It Works
The controller operates in a simple yet effective sequence:
Load Data: It ingests the current state from trains.csv (the list of waiting trains) and platform_dataset.csv (the status of all platforms and lines).
Identify Resources: It first identifies all platform lines that are currently marked as available.

Rank Candidates: It then evaluates all waiting trains and sorts them in-memory according to the multi-level rule set (Priority -> Delay -> Clearance Time).
Generate Recommendations: Finally, it pairs the top-ranked trains with the available platforms and presents this prioritized list as its final output.
