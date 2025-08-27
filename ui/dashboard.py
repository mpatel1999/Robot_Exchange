import streamlit as st
import requests
import time
import pandas as pd
import math

# Title of the dashboard
st.title("Robot Exchange Dashboard")
st.markdown("Real-time view of robot and task metrics.")

# Define the orchestrator's dashboard URL
DASHBOARD_URL = "http://localhost:8000/api/v1/dashboard"
ROBOT_STATE_URL = "http://localhost:8000/api/v1/heartbeat" # Re-use heartbeat endpoint for robot data

# Function to get the current dashboard data
def get_dashboard_data():
    try:
        response = requests.get(DASHBOARD_URL)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching dashboard data: {e}")
        return None

# Function to get detailed robot state
def get_robot_data():
    try:
        response = requests.get(ROBOT_STATE_URL)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching robot data: {e}")
        return None

# Use st.empty to create a container for a live-updating section
dashboard_container = st.empty()
robot_table_container = st.empty()

# The main loop for the dashboard
while True:
    data = get_dashboard_data()
    
    with dashboard_container.container():
        st.header("Overall Metrics")
        if data:
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                st.metric(label="Idle Robots", value=data.get("robots_idle", 0))
            with col2:
                st.metric(label="Busy Robots", value=data.get("robots_busy", 0))
            with col3:
                st.metric(label="Charging Robots", value=data.get("robots_charging", 0))
            with col4:
                st.metric(label="Tasks in Queue", value=data.get("tasks_in_queue", 0))
            with col5:
                st.metric(label="Robot Utilization", value=f"{data.get('robot_utilisation_pct', 0.0):.2f}%")
                
            st.markdown("---")
    
    # Refresh every 2 seconds
    time.sleep(2)