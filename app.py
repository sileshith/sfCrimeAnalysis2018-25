# app.py
# San Francisco Crime Analytics 2018–2025
# Streamlit Mini-Dashboard (Final Version: API Data Source, Cloud Ready)

import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.express as px
import plotly.graph_objects as go
from statsmodels.tsa.statespace.sarimax import SARIMAX

# --------------------------------------------------
# Helper: Download Plotly figure as PNG
# --------------------------------------------------
def png_download_button(fig, filename: str, label: str):
    """Creates a Streamlit download button for a Plotly PNG."""
    try:
        # Requires kaleido in requirements.txt
        img_bytes = fig.to_image(format="png", scale=2)
        st.download_button(
            label=label,
            data=img_bytes,
            file_name=filename,
            mime="image/png"
        )
    except Exception as e:
        st.warning(f"PNG export not available. Install kaleido. Details: {e}")

# --------------------------------------------------
# Page config
# --------------------------------------------------
st.set_page_config(
    page_title="SF Crime Analytics 2018–2025",
    layout="wide"
)

st.title("San Francisco Crime Analytics 2018–2025")
st.markdown(
    "Interactive dashboard using SFPD Incident Reports (DataSF API). "
    "Filters update all charts instantly."
)

# --------------------------------------------------
# Load and clean incident data (API Source)
# --------------------------------------------------
@st.cache_data(show_spinner="Fetching and cleaning data from DataSF API...", ttl=24*3600)
def load_incidents() -> pd.DataFrame:
    base_url = "https://data.sfgov.org/resource/wg3w-h783.json"

    # We page in chunks so Cloud does not choke on a huge request.
    limit = 50000
    max_rows = 250000  # keep it light for deployment
    all_chunks = []

    select_cols = ",".join([
        "incident_date",
        "incident_datetime",
        "analysis_neighborhood",
        "incident_category",
        "incident_day_of_week",
        "latitude",
        "longitude"
    ])

    where_clause = (
        "incident_date >= '2018-01-01T00:00:00.000' "
        "AND incident_date <= '2025-12-31T23:59:59.999'"
    )

    offset = 0
    while offset < max_rows:
        params = {
            "$select": select_cols,
            "$where": where_clause,
            "$limit": limit,
            "$offset": offset
        }

        r = requests.get(base_url, params=params, timeout=60)
        if r.status_code != 200:
            st.error(f"API request failed at offset {offset}. Status: {r.status_code}")
            break

        chunk = pd.DataFrame(r.json())
        if chunk.empty:
            break

        all_chunks.append(chunk)
        offset += limit

    if not all_chunks:
        return pd.DataFrame()

    df = pd.concat(all_chunks, ignore_index=True)

    # Rename columns to your convention
    df = df.rename(columns={
        "incident_date": "date",
        "incident_datetime": "incident_datetime",
        "analysis_neighborhood": "neighborhood",
        "incident_category": "category",
        "incident_day_of_week": "weekday",
        "latitude": "latitude",
        "longitude": "longitude"
    })

    # Convert date fields
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["incident_datetime"] = pd.to_datetime(df["incident_datetime"], errors="coerce")

    # Convert lat/lon safely
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")

    # Drop missing essentials
    df = df.dropna(subset=["date", "neighborhood", "category", "latitude", "longitude"])

    # Derived fields
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()
    df["hour"] = df["incident_datetime"].dt.hour

    # Focus range (Project Scope)
    df = df[(df["year"] >= 2018) & (df["year"] <= 2025)].copy()

    return df

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
# TAB 1
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
# TAB 2
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
# TAB 3
# ==================================================
with tab3:
    st.subheader("Citywide Monthly Forecast (2026 Outlook)")

    @st.cache_data(ttl=24*3600)
    def fit_forecast(ts: pd.Series):
        model = SARIMAX(
            ts,
            order=(1, 1, 1),
            seasonal_order=(1, 1, 1, 12),
            enforce_stationarity=False,
            enforce_invertibility=False
        )
        return model.fit(disp=False)

    ts_city = df.groupby("month").size()
    ts_city.index = pd.to_datetime(ts_city.index)

    results = fit_forecast(ts_city)

    steps = 6
    pred = results.get_forecast(steps=steps)
    ci = pred.conf_int()

    forecast_index = pd.date_range(
        ts_city.index[-1] + pd.offsets.MonthBegin(1),
        periods=steps,
        freq="MS"
    )

    forecast_df = pd.DataFrame({
        "month": forecast_index,
        "forecast": pred.predicted_mean.values,
        "lower": ci.iloc[:, 0].values,
        "upper": ci.iloc[:, 1].values
    })

    historical_df = ts_city.reset_index(name="incidents")
    historical_df.columns = ["month", "incidents"]

    fig_fc = px.line(
        historical_df,
        x="month",
        y="incidents",
        markers=True,
        title="Historical Incidents (2018–2025) and 6-Month Forecast"
    )

    fig_fc.add_trace(
        go.Scatter(
            x=forecast_df["month"],
            y=forecast_df["forecast"],
            mode="lines+markers",
            name="Forecast",
            line=dict(color="red", dash="dash")
        )
    )
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
            fillcolor="rgba(255,0,0,0.2)",
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
# TAB 4
# ==================================================
with tab4:
    st.header("About San Francisco and the 41 Analysis Zones")
    st.subheader("Insights Summary (Based on 2018–2025 Data)")
    st.markdown("Your full narrative text goes here (unchanged).")
