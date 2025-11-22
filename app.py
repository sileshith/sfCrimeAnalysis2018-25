import streamlit as st
import pandas as pd
import requests
from urllib.parse import quote_plus

# --- Configuration ---
# DataSF Incident Reports (Socrata API)
SFPD_INCIDENT_API_URL = "https://data.sfgov.org/resource/wg3w-h783.json"
LIMIT = 50000

# The columns we want to fetch
SELECT_FIELDS = "incident_date,incident_datetime,analysis_neighborhood,incident_category,incident_day_of_week,latitude,longitude"

# The problematic WHERE clause, which contains spaces that must be encoded
# Note: We are setting the date range from 2018-01-01 up to the current date/time when deployed
UNENCODED_WHERE = "incident_date between '2018-01-01T00:00:00.000' and '2025-12-31T23:59:59.999'"

# --- Helper Function for Data Loading ---

@st.cache_data
def load_data():
    """
    Fetches the SFPD incident data from the DataSF API.
    
    This function uses urllib.parse.quote_plus() to correctly URL-encode the 
    WHERE clause, preventing the "URL can't contain control characters" error.
    """
    try:
        # 1. Properly URL-encode the WHERE clause
        encoded_where = quote_plus(UNENCODED_WHERE)

        # 2. Construct the final, valid API URL
        api_call = (
            f"{SFPD_INCIDENT_API_URL}?"
            f"$select={SELECT_FIELDS}&"
            f"$where={encoded_where}&" # Use $where and the encoded string
            f"$limit={LIMIT}"
        )
        
        st.info(f"Fetching data from API (Limit: {LIMIT} incidents)...")
        
        # 3. Make the request and load data into a Pandas DataFrame
        response = requests.get(api_call)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        
        data = response.json()
        df = pd.DataFrame(data)

        # Basic data processing (ensure datetime objects)
        df['incident_date'] = pd.to_datetime(df['incident_date'], errors='coerce')
        df['incident_datetime'] = pd.to_datetime(df['incident_datetime'], errors='coerce')
        
        return df, None

    except requests.exceptions.RequestException as e:
        # Handle API connection errors
        return pd.DataFrame(), f"API Request Error: Could not connect or receive data. Details: {e}"
    except Exception as e:
        # Handle other processing errors (e.g., JSON parsing)
        return pd.DataFrame(), f"An unexpected error occurred while processing data: {e}"


# --- Streamlit App Layout ---

# Load data and handle potential errors
df, error = load_data()

st.set_page_config(
    page_title="SF Crime Analytics",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply a clean, modern style using basic HTML/CSS (since custom CSS files are disallowed)
st.markdown("""
<style>
    .stApp {
        background-color: #f0f2f6;
    }
    .stButton>button {
        border: 2px solid #4B8BBE;
        border-radius: 12px;
        color: #4B8BBE;
        background-color: white;
        transition: all 0.2s ease-in-out;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .stButton>button:hover {
        background-color: #4B8BBE;
        color: white;
        transform: translateY(-2px);
    }
    .main-title {
        color: #1f77b4;
        font-weight: 700;
        text-align: center;
        padding-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)


# --- Display Dashboard ---

st.markdown('<h1 class="main-title">San Francisco Crime Analytics 2018–2025</h1>', unsafe_allow_html=True)
st.markdown("### Interactive dashboard using SFPD Incident Reports (DataSF API). Filters update all charts instantly.")

if error:
    st.error(f"Could not load data from DataSF API. {error}")
    st.stop()
    
if df.empty:
    st.warning("Data loaded successfully but the DataFrame is empty. Check the API URL and query parameters.")
    st.stop()


# --- Sidebar Filters ---

st.sidebar.header("Filter Data")

# Neighborhood Filter
neighborhoods = ['All'] + sorted(df['analysis_neighborhood'].dropna().unique().tolist())
selected_neighborhood = st.sidebar.selectbox('Neighborhood', neighborhoods)

# Category Filter
categories = ['All'] + sorted(df['incident_category'].dropna().unique().tolist())
selected_category = st.sidebar.selectbox('Incident Category', categories)

# Day of Week Filter
days = ['All', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
selected_day = st.sidebar.selectbox('Day of Week', days)

# --- Apply Filters ---
filtered_df = df.copy()

if selected_neighborhood != 'All':
    filtered_df = filtered_df[filtered_df['analysis_neighborhood'] == selected_neighborhood]

if selected_category != 'All':
    filtered_df = filtered_df[filtered_df['incident_category'] == selected_category]

if selected_day != 'All':
    filtered_df = filtered_df[filtered_df['incident_day_of_week'] == selected_day]

st.metric(label="Total Incidents Loaded", value=f"{len(df):,}")
st.metric(label="Incidents Filtered", value=f"{len(filtered_df):,}")

# --- Charts and Analysis ---

# Example 1: Incidents by Category (using filtered data)
st.subheader("Top 10 Incident Categories")
category_counts = filtered_df['incident_category'].value_counts().nlargest(10).reset_index()
category_counts.columns = ['Category', 'Count']
st.bar_chart(category_counts, x='Category', y='Count')


# Example 2: Incident Map (using filtered data)
st.subheader("Incident Locations (Map)")
# Filter out rows missing lat/lon
map_data = filtered_df.dropna(subset=['latitude', 'longitude']).rename(
    columns={'latitude': 'lat', 'longitude': 'lon'}
)
st.map(map_data, zoom=11)


# Example 3: Incident Trend Over Time (using filtered data)
st.subheader("Incidents by Day")
# Group by date and count incidents
daily_counts = filtered_df.groupby(filtered_df['incident_date'].dt.date)['incident_date'].count()
st.line_chart(daily_counts)


# --- Display Raw Filtered Data (Optional) ---
st.subheader("Raw Filtered Data Sample")
st.dataframe(filtered_df.head(10))