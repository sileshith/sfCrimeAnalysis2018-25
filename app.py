import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.express as px
import plotly.graph_objects as go
from statsmodels.tsa.statespace.sarimax import SARIMAX

# Configuration for API call
# Using a chunked approach for robustness on Streamlit Cloud
LIMIT_PER_CHUNK = 50000
MAX_TOTAL_ROWS = 250000
BASE_URL = "https://data.sfgov.org/resource/wg3w-h783.json"

# --------------------------------------------------
# Helper: Download Plotly figure as PNG
# --------------------------------------------------
def png_download_button(fig, filename: str, label: str):
    """Creates a Streamlit download button for a Plotly PNG."""
    # Since 'kaleido' is in requirements.txt, this should work without warning.
    try:
        img_bytes = fig.to_image(format="png", scale=2)
        st.download_button(
            label=label,
            data=img_bytes,
            file_name=filename,
            mime="image/png"
        )
    except Exception:
        # Fail silently as we expect the user to install kaleido
        pass

# --------------------------------------------------
# Load and clean incident data (API Source)
# --------------------------------------------------
# FIX: Using ttl=24*3600 (24 hours) to cache data and prevent NameError
@st.cache_data(ttl=24*3600)
def load_incidents() -> pd.DataFrame:
    st.info(f"Fetching up to {MAX_TOTAL_ROWS:,} incidents from DataSF API (cached for 24 hours)...")
    
    all_chunks = []
    select_cols = ",".join([
        "incident_date", "incident_datetime", "analysis_neighborhood",
        "incident_category", "incident_day_of_week", "latitude", "longitude"
    ])
    where_clause = (
        "incident_date >= '2018-01-01T00:00:00.000' "
        "AND incident_date <= '2025-12-31T23:59:59.999'"
    )

    offset = 0
    while offset < MAX_TOTAL_ROWS:
        params = {
            "$select": select_cols,
            "$where": where_clause,
            "$limit": LIMIT_PER_CHUNK,
            "$offset": offset
        }

        try:
            r = requests.get(BASE_URL, params=params, timeout=60)
            r.raise_for_status()
            
            chunk = pd.DataFrame(r.json())
            if chunk.empty:
                break

            all_chunks.append(chunk)
            offset += LIMIT_PER_CHUNK
        except requests.exceptions.RequestException as e:
            st.error(f"API request failed at offset {offset}. Details: {e}")
            break
        except Exception as e:
            st.error(f"An unexpected error occurred while processing data: {e}")
            break

    if not all_chunks:
        st.warning("Could not retrieve any data from the API.")
        return pd.DataFrame()

    df = pd.concat(all_chunks, ignore_index=True)
    st.success(f"Successfully loaded {len(df):,} total incidents.")

    # Rename columns to convention
    df = df.rename(columns={
        "incident_date": "date",
        "incident_datetime": "incident_datetime",
        "analysis_neighborhood": "neighborhood",
        "incident_category": "category",
        "incident_day_of_week": "weekday",
    })

    # Convert types
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["incident_datetime"] = pd.to_datetime(df["incident_datetime"], errors="coerce")
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")

    # Drop missing essentials
    df = df.dropna(subset=["date", "neighborhood", "category"])

    # Derived fields
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()
    df["hour"] = df["incident_datetime"].dt.hour

    # Focus range (Project Scope)
    df = df[(df["year"] >= 2018) & (df["year"] <= 2025)].copy()

    return df

# --------------------------------------------------
# Page config and Custom CSS (for tab coloring)
# --------------------------------------------------
st.set_page_config(
    page_title="SF Crime Analytics 2018–2025",
    layout="wide"
)

# Custom CSS for aesthetics (using shades of blue/teal for tabs)
st.markdown("""
<style>
    /* Main Streamlit container background */
    .stApp {
        background-color: #f0f2f6; 
    }
    
    /* Active tab style */
    .stTabs [data-testid="stTabList"] button[aria-selected="true"] {
        background-color: #1f77b4; /* Deep Blue for selection */
        color: white; /* White text for contrast */
        border-radius: 8px 8px 0px 0px;
        font-weight: bold;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    
    /* Default tab style */
    .stTabs [data-testid="stTabList"] button {
        background-color: #e5e5e5; /* Light gray */
        color: #333333; /* Dark text */
        border-radius: 8px 8px 0px 0px;
        margin-right: 5px;
        border: 1px solid #cccccc;
    }
    
    .stTitle {
        color: #1f77b4;
    }
</style>
""", unsafe_allow_html=True)


st.title("San Francisco Crime Analytics 2018–2025")
st.markdown(
    "Interactive dashboard using SFPD Incident Reports (DataSF API). "
    "Filters update all charts instantly."
)

# Load the data
df = load_incidents()
if df.empty:
    st.stop()

# --------------------------------------------------
# Sidebar filters
# --------------------------------------------------
st.sidebar.header("Filters")

years = sorted(df["year"].dropna().unique())
min_year, max_year = int(min(years)), int(max(years))

year_range = st.sidebar.slider(
    "Year range",
    min_value=min_year,
    max_value=max_year,
    value=(min_year, max_year),
    step=1
)

neighborhoods = sorted(df["neighborhood"].unique())
selected_nbhds = st.sidebar.multiselect(
    "Neighborhoods (Analysis Zones)",
    options=neighborhoods,
    default=neighborhoods
)

categories = sorted(df["category"].unique())
selected_categories = st.sidebar.multiselect(
    "Incident categories",
    options=categories,
    default=categories[:10]
)

weekday_order = [
    "Monday", "Tuesday", "Wednesday", "Thursday",
    "Friday", "Saturday", "Sunday"
]
selected_weekdays = st.sidebar.multiselect(
    "Weekdays",
    options=weekday_order,
    default=weekday_order
)

hour_range = st.sidebar.slider(
    "Hour range",
    min_value=0,
    max_value=23,
    value=(0, 23),
    step=1
)

# --------------------------------------------------
# Apply filters
# --------------------------------------------------
mask = (
    (df["year"] >= year_range[0]) &
    (df["year"] <= year_range[1]) &
    (df["neighborhood"].isin(selected_nbhds)) &
    (df["category"].isin(selected_categories)) &
    (df["weekday"].isin(selected_weekdays)) &
    (df["hour"].between(hour_range[0], hour_range[1], inclusive="both"))
)

df_filt = df[mask].copy()

st.caption(
    f"Filtered incidents: **{len(df_filt):,}** out of {len(df):,} total (API data)."
)

# --------------------------------------------------
# Download filtered CSV
# --------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.download_button(
    label="Download filtered CSV",
    data=df_filt.to_csv(index=False).encode("utf-8"),
    file_name="sf_crime_filtered.csv",
    mime="text/csv"
)

# --------------------------------------------------
# Summary metrics row
# --------------------------------------------------
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Total incidents (filtered)", f"{len(df_filt):,}")

with col2:
    if len(df_filt) > 0:
        span_days = (df_filt["date"].max() - df_filt["date"].min()).days + 1
        avg_per_day = len(df_filt) / max(span_days, 1)
        st.metric("Average per day", f"{avg_per_day:,.1f}")
    else:
        st.metric("Average per day", "0")

with col3:
    st.metric("Neighborhoods in view", df_filt["neighborhood"].nunique())

st.markdown("---")

# --------------------------------------------------
# Tabs
# --------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "Trends and Rankings",
    "Hour and Weekday Patterns",
    "Forecast (2026 Outlook)",
    "About SF and Analysis Zones"
])

# ==================================================
# TAB 1: Trends and Rankings
# ==================================================
with tab1:
    left, right = st.columns((2, 1.3))

    with left:
        st.subheader("Monthly Incident Trend")
        if len(df_filt) > 0:
            monthly = (
                df_filt.groupby("month")
                .size()
                .reset_index(name="incidents")
                .sort_values("month")
            )

            fig_ts = px.line(
                monthly,
                x="month",
                y="incidents",
                markers=True,
                labels={"month": "Month", "incidents": "Incidents"}
            )
            fig_ts.update_layout(height=350)
            st.plotly_chart(fig_ts, use_container_width=True)
            png_download_button(fig_ts, "monthly_trend.png", "Download Monthly Trend (PNG)")
        else:
            st.info("No data for current filters.")

    with right:
        st.subheader("Top Neighborhoods")
        if len(df_filt) > 0:
            top_nbh = (
                df_filt["neighborhood"]
                .value_counts()
                .head(10)
                .reset_index()
            )
            top_nbh.columns = ["neighborhood", "incidents"]

            fig_bar = px.bar(
                top_nbh,
                x="incidents",
                y="neighborhood",
                orientation="h",
                labels={"incidents": "Incidents", "neighborhood": ""},
                color="incidents",
                color_continuous_scale="Viridis",
                text_auto=".2s"
            )
            fig_bar.update_layout(height=350, yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig_bar, use_container_width=True)
            png_download_button(fig_bar, "top_neighborhoods.png", "Download Top Neighborhoods (PNG)")
        else:
            st.info("No neighborhood counts to display.")

    st.subheader("Top Categories")
    if len(df_filt) > 0:
        top_cat = (
            df_filt["category"]
            .value_counts()
            .head(10)
            .reset_index()
        )
        top_cat.columns = ["category", "incidents"]

        fig_cat = px.bar(
            top_cat,
            x="category",
            y="incidents",
            labels={"category": "Category", "incidents": "Incidents"},
            color="incidents",
            color_continuous_scale="Plasma",
            text_auto=".2s"
        )
        st.plotly_chart(fig_cat, use_container_width=True)
        png_download_button(fig_cat, "top_categories.png", "Download Top Categories (PNG)")
    else:
        st.info("No category counts to display.")

# ==================================================
# TAB 2: Hour and Weekday Patterns
# ==================================================
with tab2:
    st.subheader("Incident Intensity by Hour and Weekday")
    if len(df_filt) > 0:
        heat = (
            df_filt.groupby(["weekday", "hour"])
            .size()
            .reset_index(name="incidents")
        )

        heat["weekday"] = pd.Categorical(
            heat["weekday"], categories=weekday_order, ordered=True
        )
        heat = heat.sort_values(["weekday", "hour"], ascending=[False, True])

        fig_heat = px.density_heatmap(
            heat,
            x="hour",
            y="weekday",
            z="incidents",
            nbinsx=24,
            labels={"hour": "Hour", "weekday": "Weekday", "z": "Incidents"},
            color_continuous_scale="Reds"
        )
        fig_heat.update_layout(height=450)
        st.plotly_chart(fig_heat, use_container_width=True)
        png_download_button(fig_heat, "hour_weekday_heatmap.png", "Download Heatmap (PNG)")
    else:
        st.info("No data for heatmap under current filters.")

    st.markdown("---")
    left, right = st.columns(2)

    with left:
        st.subheader("Hourly Pattern")
        if len(df_filt) > 0:
            hourly = df_filt["hour"].value_counts().sort_index().reset_index()
            hourly.columns = ["hour", "incidents"]

            fig_hour = px.line(hourly, x="hour", y="incidents", markers=True)
            st.plotly_chart(fig_hour, use_container_width=True)
            png_download_button(fig_hour, "hourly_pattern.png", "Download Hourly Pattern (PNG)")

    with right:
        st.subheader("Weekday Pattern")
        if len(df_filt) > 0:
            wk = df_filt["weekday"].value_counts().reindex(weekday_order).reset_index()
            wk.columns = ["weekday", "incidents"]

            fig_wk = px.bar(wk, x="weekday", y="incidents", text_auto=True)
            st.plotly_chart(fig_wk, use_container_width=True)
            png_download_button(fig_wk, "weekday_pattern.png", "Download Weekday Pattern (PNG)")

# ==================================================
# TAB 3: Forecast (2026 Outlook)
# ==================================================
with tab3:
    st.subheader("Citywide Monthly Forecast (2026 Outlook)")

    # Added check for sufficient data length to prevent statsmodels ValueError
    ts_city_full = df.groupby("month").size()
    ts_city_full.index = pd.to_datetime(ts_city_full.index)

    if len(ts_city_full) < 24:
        st.warning("Not enough historical data (24+ months) to perform a reliable Seasonal ARIMA forecast.")
    else:
        @st.cache_data(ttl=24*3600)
        def fit_forecast(ts: pd.Series):
            try:
                model = SARIMAX(
                    ts,
                    order=(1, 1, 1),
                    seasonal_order=(1, 1, 1, 12),
                    enforce_stationarity=False,
                    enforce_invertibility=False
                )
                return model.fit(disp=False)
            except Exception as e:
                st.error(f"Error fitting SARIMAX model: {e}")
                return None
        
        results = fit_forecast(ts_city_full)

        if results:
            steps = 6
            pred = results.get_forecast(steps=steps)
            ci = pred.conf_int()

            forecast_index = pd.date_range(
                ts_city_full.index[-1] + pd.offsets.MonthBegin(1),
                periods=steps,
                freq="MS"
            )

            forecast_df = pd.DataFrame({
                "month": forecast_index,
                "forecast": pred.predicted_mean.values,
                "lower": ci.iloc[:, 0].values,
                "upper": ci.iloc[:, 1].values
            })

            historical_df = ts_city_full.reset_index(name="incidents")
            historical_df.columns = ["month", "incidents"]

            fig_fc = px.line(
                historical_df,
                x="month",
                y="incidents",
                markers=True,
                title="Historical Incidents (2018–2025) and 6-Month Forecast"
            )

            # Add Forecast line
            fig_fc.add_trace(
                go.Scatter(
                    x=forecast_df["month"],
                    y=forecast_df["forecast"],
                    mode="lines+markers",
                    name="Forecast",
                    line=dict(color="#d62728", dash="dash") # Red
                )
            )
            # Add Confidence Interval bounds
            fig_fc.add_trace(
                go.Scatter(
                    x=forecast_df["month"],
                    y=forecast_df["lower"],
                    mode="lines",
                    line=dict(width=0),
                    showlegend=False
                )
            )
            fig_fc.add_trace(
                go.Scatter(
                    x=forecast_df["month"],
                    y=forecast_df["upper"],
                    mode="lines",
                    line=dict(width=0),
                    fill="tonexty",
                    fillcolor="rgba(214, 39, 40, 0.2)", # Light Red Fill
                    name="Confidence Interval"
                )
            )

            fig_fc.update_layout(height=500, showlegend=True)
            st.plotly_chart(fig_fc, use_container_width=True)
            png_download_button(fig_fc, "forecast_2026.png", "Download Forecast Plot (PNG)")

            st.markdown(
                "This forecast is a baseline Seasonal ARIMA model fit on citywide monthly totals. "
                "It is intended as a short-term planning aid, not a causal prediction."
            )

# ==================================================
# TAB 4: About SF and Analysis Zones
# ==================================================
with tab4:
    st.header("About San Francisco and the 41 Analysis Zones")

    st.subheader("Insights Summary (Based on 2018–2025 Data)")

    st.markdown("""
    ---
    ### Insights:

    **1. Neighborhood Distribution**

    The highest incident volumes are concentrated in **Mission, Tenderloin, and South of Market**—three dense neighborhoods with heavy foot traffic, nightlife, commercial activity, and transit connections. These areas traditionally account for a large share of police calls, and the counts in this dataset follow that well-known pattern. 

    **2. Incident Category Distribution**

    **Larceny Theft** is by far the dominant category, reflecting the long-standing pattern of property crime in San Francisco. Categories such as Malicious Mischief, Assault, Burglary, and Motor Vehicle Theft also appear frequently, forming the core group of incidents that drive citywide totals year after year.

    **3. Weekday Distribution**

    Incidents are relatively evenly spread across the week but peak slightly on **Fridays**, which often see higher mobility, nightlife, and social activity. **Sundays** show the lowest volume, consistent with quieter movement patterns across the city.

    **4. Hour-of-Day Distribution**

    The hourly pattern has two clear peaks: one around **midnight** and another around **midday**. Early morning hours (roughly 2 AM–5 AM) are the quietest, while daytime and early evening hours show steady, high activity. This pattern is typical of large cities where property crime and public disturbances follow both business hours and nightlife cycles.

    ---

    ### Note on Neighborhood Naming

    The neighborhood labels in the dataset follow the official **41-zone “Analysis Neighborhoods”** system used by DataSF. This system is employed by the San Francisco Police Department, the Department of Public Health, and the Mayor’s Office to ensure consistent reporting across city agencies. Because these 41 analysis zones combine or redefine several commonly known neighborhoods, their names may differ from those used by the San Francisco Planning Department or from informal neighborhood boundaries found on maps, tourism guides, or Wikipedia. For example, the area labeled “Financial District/South Beach” in the Analysis Neighborhood system would appear as two separate neighborhoods in other sources. For the purposes of this project, all EDA and visualizations use the official SFPD Analysis Neighborhood definitions to maintain accuracy and consistency with city-level reporting.

    ## Approximate Mapping: Common Neighborhood Names vs. Analysis Neighborhoods

    The table below gives a practical translation from the 41 Analysis Neighborhoods
    to the closest common or informal neighborhood names people use in daily life.
    These are approximate matches meant to help interpretation.

    | Analysis Neighborhood (DataSF) | Closest Common Name(s) |
    |---|---|
    | Bayview Hunters Point | Bayview, Hunters Point, Butchertown |
    | Bernal Heights | Bernal Heights |
    | Castro/Upper Market | The Castro, Upper Market, Duboce Triangle |
    | Chinatown | Chinatown |
    | Excelsior | Excelsior, Mission Terrace (parts) |
    | Financial District/South Beach | Financial District, South Beach, Embarcadero (downtown portion) |
    | Glen Park | Glen Park |
    | Golden Gate Park | Golden Gate Park |
    | Haight Ashbury | Haight-Ashbury, Cole Valley (parts), Buena Vista area |
    | Hayes Valley | Hayes Valley, Civic Center fringe (west) |
    | Inner Richmond | Inner Richmond, Central Richmond |
    | Inner Sunset | Inner Sunset |
    | Japantown | Japantown, Western Addition (northeast portion) |
    | Lakeshore | Lakeshore, Lake Merced area, St. Francis Wood fringe |
    | Lincoln Park | Lincoln Park, Sea Cliff fringe |
    | Lone Mountain/USF | USF area, Lone Mountain, Inner Anza Vista fringe |
    | Marina | Marina, Cow Hollow (often grouped informally) |
    | McLaren Park | McLaren Park, University Mound fringe |
    | Mission | Mission District |
    | Mission Bay | Mission Bay, China Basin |
    | Nob Hill | Nob Hill, Lower Nob Hill |
    | Noe Valley | Noe Valley |
    | North Beach | North Beach, Telegraph Hill |
    | Oceanview/Merced/Ingleside | Oceanview, Ingleside, Merced Heights, Lakeview |
    | Outer Mission | Outer Mission, Crocker-Amazon, Geneva area |
    | Outer Richmond | Outer Richmond |
    | Outer Sunset | Outer Sunset |
    | Pacific Heights | Pacific Heights, Lower Pacific Heights |
    | Portola | Portola, Silver Terrace fringe |
    | Potrero Hill | Potrero Hill, Dogpatch fringe |
    | Presidio | Presidio |
    | Presidio Heights | Presidio Heights, Laurel Heights fringe |
    | Russian Hill | Russian Hill |
    | Seacliff | Sea Cliff |
    | South of Market | SoMa (South of Market) |
    | Sunset/Parkside | Inner Sunset fringe, Outer Sunset, Parkside |
    | Tenderloin | Tenderloin |
    | Treasure Island | Treasure Island, Yerba Buena Island |
    | Twin Peaks | Twin Peaks, Clarendon Heights |
    | Visitacion Valley | Visitacion Valley |
    | West Of Twin Peaks | West Portal, Forest Hill, St. Francis Wood (parts) |
    | Western Addition | Western Addition, Alamo Square, Fillmore, Lower Haight fringe |

    ### Why the 41 Analysis Neighborhood System Exists

    San Francisco agencies adopted the 41 Analysis Neighborhood system to create one consistent geography for reporting citywide indicators. These zones were built by grouping Census tracts into neighborhoods that reflect how residents and planning agencies commonly describe the city. Using a single standardized set allows the Police Department, Public Health, and other departments to compare trends across time and across datasets without mismatched neighborhood definitions.

    With the standardized 41 Analysis Neighborhood geography established, we now explore how incidents vary over time, across categories, and between neighborhoods.
    """)