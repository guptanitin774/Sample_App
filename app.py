import streamlit as st
import requests
import pandas as pd
from openai import OpenAI
from fpdf import FPDF
import json
import plotly.express as px
import re
from datetime import datetime, timedelta

# Initialize the OpenAI client
client = OpenAI(api_key=st.secrets["openai_api_key"])

api_url = 'https://tessapp.tess360.app/getTicket_IncidenceData'
request_data = {
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

def parse_prompt(prompt):
    """Parse user prompt for various filter criteria."""
    filters = {
        'customer_name': None,
        'start_date': None,
        'end_date': None,
        'status': None,
        'priority': None,
        'product_name': None,
        'customer_city': None,
        'compare_last_6_months': False
    }
    
    # Customer name
    customer_match = re.search(r"customer name\s*['\"](.*?)['\"]", prompt, re.IGNORECASE)
    if customer_match:
        filters['customer_name'] = customer_match.group(1).strip()
    
    # Date range
    date_range_match = re.search(r"from\s*['\"](.*?)['\"]?\s*to\s*['\"](.*?)['\"]", prompt, re.IGNORECASE)
    if date_range_match:
        filters['start_date'] = date_range_match.group(1).strip()
        filters['end_date'] = date_range_match.group(2).strip()

    if re.search(r"last 6 months", prompt, re.IGNORECASE):
        filters['compare_last_6_months'] = True
    
    # Status
    status_match = re.search(r"status\s*['\"](.*?)['\"]", prompt, re.IGNORECASE)
    if status_match:
        filters['status'] = status_match.group(1).strip()
    
    # Priority
    priority_match = re.search(r"priority\s*['\"](.*?)['\"]", prompt, re.IGNORECASE)
    if priority_match:
        filters['priority'] = priority_match.group(1).strip()

    # Product name
    product_name_match = re.search(r"product name\s*['\"](.*?)['\"]", prompt, re.IGNORECASE)
    if product_name_match:
        filters['product_name'] = product_name_match.group(1).strip()

    # Customer city
    customer_city_match = re.search(r"customer city\s*['\"](.*?)['\"]", prompt, re.IGNORECASE)
    if customer_city_match:
        filters['customer_city'] = customer_city_match.group(1).strip()
    
    return filters

def filter_last_six_months(df):
    
    end_date = datetime.now()
    start_date = end_date - pd.DateOffset(months=6)
    
    
    df['INCIDENCE_DATE'] = pd.to_datetime(df['INCIDENCE_DATE'], errors='coerce')
    
    
    filtered_df = df[(df['INCIDENCE_DATE'] >= start_date) & (df['INCIDENCE_DATE'] <= end_date)]
    
    return filtered_df


def filter_data(df, filters):
    """Apply filters to the DataFrame."""
    filtered_df = df.copy()
    
    try:
        
        # Apply 'last 6 months' filter if requested
        if filters.get('compare_last_6_months', False):
            filtered_df = filter_last_six_months(df)

        if filters['customer_name']:
            filtered_df = filtered_df[filtered_df["CUSTOMER_NAME"].str.contains(filters['customer_name'], case=False, na=False)]
        
        if filters['start_date'] and filters['end_date']:
            # Ensure both filters are converted to datetime
            filtered_df['INCIDENCE_DATE'] = pd.to_datetime(filtered_df['INCIDENCE_DATE'], errors='coerce')
            start_date = pd.to_datetime(filters['start_date'], errors='coerce')
            end_date = pd.to_datetime(filters['end_date'], errors='coerce')
            
            # Apply the date filter if both start_date and end_date are valid
            if pd.notna(start_date) and pd.notna(end_date):
                filtered_df = filtered_df[
                    (filtered_df['INCIDENCE_DATE'] >= start_date) & 
                    (filtered_df['INCIDENCE_DATE'] <= end_date)
                ]
        
        if filters['status']:
            filtered_df = filtered_df[filtered_df["STATUS_MEANING"].str.contains(filters['status'], case=False, na=False)]
        
        if filters['priority']:
            filtered_df = filtered_df[filtered_df["INCIDENCE_LEVEL_MEANING"].str.contains(filters['priority'], case=False, na=False)]
        
        if filters['product_name']:
            filtered_df = filtered_df[filtered_df["PRODUCT_NAME"].str.contains(filters['product_name'], case=False, na=False)]
        
        if filters['customer_city']:
            filtered_df = filtered_df[filtered_df["CUSTOMER_CITY"].str.contains(filters['customer_city'], case=False, na=False)]
        
    except Exception as e:
        st.error(f"Error applying filters: {str(e)}")
        return filtered_df
    
    return filtered_df


def generate_ai_report(ticket_data, user_prompt):
    """Generate AI report with new OpenAI API."""
    prompt = f"""
    You are an AI assistant analyzing customer support tickets. Here is the ticket data:

    {ticket_data}

    Based on the following prompt, generate a structured report:

    {user_prompt}

    Please include:
    1. Summary of the data based on the specific filters requested
    2. Key trends and patterns
    3. Notable insights about customer issues
    4. Key metrics:
       - Total number of tickets
       - Average response time
       - Most common issue types
       - Priority distribution
       - Status distribution
    5. Product-specific analysis (if product filter is applied)
    6. Recommendations for improvement

    The report should be professional, clear, and concise.
    """

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content

def generate_ticket_analytics(df):
    """Enhanced analytics with additional visualizations and metrics."""
    if df.empty:
        st.warning("No data available for the selected filters.")
        return

    # Display key metrics
    st.subheader("📊 Key Metrics")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Tickets", len(df))
    with col2:
        st.metric("Unique Customers", df["CUSTOMER_NAME"].nunique())
    with col3:
        st.metric("Unique Products", df["PRODUCT_NAME"].nunique())

    # Issue Category Distribution
    if "INCIDENCE_TYPE_MEANING" in df.columns:
        category_counts = df["INCIDENCE_TYPE_MEANING"].value_counts()
        fig_pie = px.pie(values=category_counts, names=category_counts.index, 
                        title="Issue Category Distribution")
        st.plotly_chart(fig_pie)

    # Status Distribution
    if "STATUS_MEANING" in df.columns:
        status_counts = df["STATUS_MEANING"].value_counts()
        fig_status = px.pie(values=status_counts, names=status_counts.index, 
                        title="Issue Status Distribution")
        st.plotly_chart(fig_status)

    # Product Distribution
    if "PRODUCT_NAME" in df.columns:
        product_counts = df["PRODUCT_NAME"].value_counts()
        fig_product = px.bar(x=product_counts.index, y=product_counts.values,
                        title="Tickets by Product",
                        labels={'x': 'Product', 'y': 'Ticket Count'})
        fig_product.update_xaxes(tickangle=45)
        st.plotly_chart(fig_product)

    # Tickets by Customer
    if "CUSTOMER_NAME" in df.columns:
        customer_counts = df["CUSTOMER_NAME"].value_counts().nlargest(10)
        fig_bar = px.bar(x=customer_counts.index, y=customer_counts.values,
                        title="Top 10 Customers by Ticket Volume",
                        labels={'x': 'Customer', 'y': 'Ticket Count'})
        st.plotly_chart(fig_bar)

    # Tickets Over Time
    if "INCIDENCE_DATE" in df.columns:
        df["INCIDENCE_DATE"] = pd.to_datetime(df["INCIDENCE_DATE"])
        daily_counts = df.resample('D', on='INCIDENCE_DATE')['INCIDENCE_TYPE_MEANING'].count()
        fig_line = px.line(x=daily_counts.index, y=daily_counts.values,
                          title="Ticket Trends Over Time",
                          labels={'x': 'Date', 'y': 'Number of Tickets'})
        st.plotly_chart(fig_line)

    # Priority Level Distribution
    if "INCIDENCE_LEVEL_MEANING" in df.columns:
        priority_counts = df["INCIDENCE_LEVEL_MEANING"].value_counts()
        fig_priority = px.bar(x=priority_counts.index, y=priority_counts.values,
                            title="Tickets by Priority Level",
                            labels={'x': 'Priority', 'y': 'Count'})
        st.plotly_chart(fig_priority)

# Function to save report as PDF
def save_report_as_pdf(report_text, filename):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, report_text)
    pdf.output(filename)
    return filename

# Streamlit UI for prompt entry
st.subheader("Enhanced AI-Based Ticket Analysis")
st.markdown("""
<p style="color: green;">
Enter your analysis prompts below. You can use the following keywords for analysis reports:

- customer name "ABCD"<br>
- customer city "New Delhi"<br>
- from "YYYY-MM-DD" to "YYYY-MM-DD"<br>
- status "Status"<br>
- priority "Priority"<br>
- product name "Product Name"<br>
- last 6 months<br>
<br>
<strong>Example: Show tickets for customer name "ABCD" from "2024-01-01" to "2024-02-23" with priority "High" and status "Assigned" and product name "Flosense water controller"</strong>
</p>
""", unsafe_allow_html=True)

if 'prompt_history' not in st.session_state:
    st.session_state.prompt_history = []

# Number of prompts user wants to analyze
num_prompts = st.number_input("Number of analysis prompts:", min_value=1, max_value=5, value=1)

# Handle displaying previous reports and enabling re-use of past prompts
if st.session_state.prompt_history:
    st.subheader("📋 Your previous report history")
    for idx, past_prompt in enumerate(st.session_state.prompt_history):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.text(f"{idx + 1}. {past_prompt}")
        with col2:
            # Button to reuse prompt
            if st.button(f"Use this prompt", key=f"use_prompt_{idx}"):
                st.session_state[f"prompt_input_{idx}"] = past_prompt
                st.session_state['selected_prompt_idx'] = idx  # Store the index of the selected prompt

# Store and display current prompts
prompts = []
for i in range(num_prompts):
    if f"prompt_input_{i}" not in st.session_state:
        st.session_state[f"prompt_input_{i}"] = ""
    
    # If a prompt was selected from the history, pre-fill it
    if 'selected_prompt_idx' in st.session_state and st.session_state.get('selected_prompt_idx') == i:
        st.session_state[f"prompt_input_{i}"] = st.session_state.prompt_history[st.session_state['selected_prompt_idx']]

    prompt = st.text_area(
        f"Analysis prompt {i+1}:",
        value=st.session_state[f"prompt_input_{i}"],
        placeholder="Example: Show tickets for customer name 'xyz' from '2024-01-01' to '2024-02-23' with priority 'High' and status 'Assigned' and product name 'Flosense water controller'",
        key=f"prompt_area_{i}"
    )
    prompts.append(prompt)

# After the prompt is entered, user clicks Analyze Tickets
if st.button("Analyze Tickets"):
    for prompt in prompts:
        if prompt.strip() and prompt not in st.session_state.prompt_history:
            st.session_state.prompt_history.append(prompt)
    
    st.write("Fetching ticket data...")

    response = requests.post(api_url, json=request_data)
    
    if response.status_code == 200:
        st.success("Data fetched successfully!")

        try:
            data = response.json()

            # Check if the response is a list directly or a nested dict
            if isinstance(data, list):
                ticket_list = data  # If it's a list, assign it directly
            else:
                ticket_list = data.get('data', {}).get('TICKET_LIST', [])
            
            if not ticket_list:
                st.error("No tickets found!")
            else:
                df = pd.DataFrame(ticket_list)
                
                st.subheader("📋 All Available Tickets")
                st.dataframe(df)

                st.subheader("🔑 Available Filter Values")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write("Status Values:")
                    st.write(df["STATUS_MEANING"].unique())
                with col2:
                    st.write("Priority Levels:")
                    st.write(df["INCIDENCE_LEVEL_MEANING"].unique())
                with col3:
                    st.write("Product Name:")
                    st.write(df["PRODUCT_NAME"].unique())
                
                # Loop through each prompt and generate relevant analysis
                for i, prompt in enumerate(prompts):
                    if prompt.strip():
                        st.subheader(f"📊 Analysis for Prompt {i+1}")
                        st.write(f"Analyzing: '{prompt}'")
                        
                        filters = parse_prompt(prompt)
                        filtered_df = filter_data(df, filters)
                        
                        if filtered_df.empty:
                            st.warning(f"No data found for the specified filters in prompt {i+1}")
                            continue
                        
                        st.write("Filtered Data Preview:")
                        st.dataframe(filtered_df)
                        
                        generate_ticket_analytics(filtered_df)
                        
                        with st.spinner("Generating AI Report..."):
                            ai_report = generate_ai_report(filtered_df.to_json(orient="records"), prompt)
                        
                        st.subheader("📄 AI-Generated Report:")
                        st.text_area(f"Report for Prompt {i+1}:", ai_report, height=300)
                        
                        # Save and offer PDF download
                        pdf_filename = f"AI_Report_Prompt_{i+1}.pdf"
                        pdf_file = save_report_as_pdf(ai_report, pdf_filename)
                        with open(pdf_file, "rb") as f:
                            st.download_button(
                                f"📥 Download Report {i+1} as PDF",
                                f,
                                file_name=pdf_filename
                            )
        except Exception as e:
            st.error(f"Error processing data: {str(e)}")
    else:
        st.error(f"Failed to fetch data: {response.status_code}")
