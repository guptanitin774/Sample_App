import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import requests
import openai  # Ensure you have an OpenAI API key

# OpenAI API Key (Replace with your key)
openai.api_key = "your-openai-api-key"

# Define the API URL
API_URL = 'https://tessapp.tess360.com/getTicket_IncidenceData'
REQUEST_DATA = {
    "INPUT_MODE": "M",
    "APPLICATION": "W",
    "DEVICE": "W",
    "VERSION_NO": "1.0.0",
    "LOCATION_ID": "244",
    "SYSTEM_ID": "S",
    "ORG_ID": "315",
    "SIGNIN_TYPE": "P",
    "TOKEN": "d9b2c69592d7eafa0bdbe6d36e60dc19",
    "APP_DOMAIN": "tmsys360.com"
}

# Function to fetch ticket data
@st.cache_data
def fetch_ticket_data():
    try:
        response = requests.post(API_URL, json=REQUEST_DATA)
        if response.status_code == 200:
            data = response.json()
            return pd.DataFrame(data.get('data', {}).get('TICKET_LIST', []))
        else:
            st.error(f"API request failed: {response.status_code}")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

# Load ticket data
df = fetch_ticket_data()

# Function to analyze tickets by category
def analyze_tickets_by_category():
    if df.empty:
        return None

    category_counts = df['INCIDENCE_DESCRIPTION'].value_counts()
    plt.figure(figsize=(10, 6))
    sns.barplot(x=category_counts.index, y=category_counts.values, palette="viridis")
    plt.xticks(rotation=45, ha="right")
    plt.title("Most Raised Ticket Categories")
    plt.xlabel("Issue Category")
    plt.ylabel("Number of Tickets")
    st.pyplot(plt)

# Function to generate AI-powered report
def generate_ai_report(prompt):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are an AI that analyzes ticket data trends."},
            {"role": "user", "content": f"Based on the ticket data, {prompt}. Provide a detailed report."}
        ]
    )
    return response["choices"][0]["message"]["content"]

# Streamlit UI
st.title("📊 AI-Powered Ticket Analysis Dashboard")
st.sidebar.header("Navigation")

# User Query Input
user_query = st.text_area("🔍 Ask a Question About the Ticket Data:", placeholder="E.g., Show trends and most raised ticket categories")

if st.button("Generate Report"):
    if user_query:
        report = generate_ai_report(user_query)
        st.subheader("📋 AI-Generated Report")
        st.write(report)
    else:
        st.warning("Please enter a query to generate a report.")

# Ticket Data Insights
st.subheader("📈 Ticket Trends Visualization")
if not df.empty:
    analyze_tickets_by_category()
else:
    st.warning("No ticket data available.")

# Display Raw Data
if st.checkbox("Show Raw Ticket Data"):
    st.write(df)
