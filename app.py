# app.py
# San Francisco Crime Analytics 2018–2025
# Streamlit Mini-Dashboard (Upgraded)

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# Forecasting (lightweight baseline)
from statsmodels.tsa.statespace.sarimax import SARIMAX

# Geo / choropleth
import geopandas as gpd


# --------------------------------------------------
# Page config
# --------------------------------------------------
st.set_page_config(
    page_title="SF Crime Analytics 2018–2025",
    layout="wide"
)

st.title("San Francisco Crime Analytics 2018–2025")
st.markdown(
    "Interactive dashboard using SFPD Incident Reports (DataSF). "
    "Filters update all charts instantly."
)

# --------------------------------------------------
# Load and clean incident data
# --------------------------------------------------
@st.cache_data
def load_incidents(path: str) -> pd.DataFrame:
    df = pd.read_csv(
        path,
        parse_dates=["Incident Date"],
        low_memory=False
    )

    # Standardize columns you rely on
    df = df.rename(columns={
        "Incident Date": "date",
        "Incident Datetime": "incident_datetime",
        "Analysis Neighborhood": "neighborhood",
        "Incident Category": "category",
        "Incident Day of Week": "weekday",
        "Latitude": "latitude",
        "Longitude": "longitude"
    })

    # Drop missing essentials
    df = df.dropna(subset=["date", "neighborhood", "category", "latitude", "longitude"])

    # Derived fields 
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()

    # Most reliable hour source is incident_datetime
    df["incident_datetime"] = pd.to_datetime(df["incident_datetime"], errors="coerce")
    df["hour"] = df["incident_datetime"].dt.hour

    # Filter scope
    df = df[(df["year"] >= 2018) & (df["year"] <= 2025)].copy()

    return df


DATA_PATH = "crime_data_filtered_small.csv"
df = load_incidents(DATA_PATH)

# --------------------------------------------------
# Load Analysis Neighborhoods geojson (41 zones)
# --------------------------------------------------
@st.cache_data
def load_neighborhoods_geojson(path: str) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(path)  # uses pyogrio in your env
    gdf = gdf.to_crs(epsg=4326)
    # DataSF name field is usually "nhood"
    gdf = gdf.rename(columns={"nhood": "neighborhood"})
    return gdf


GEO_PATH = "Analysis_Neighborhoods_CLEAN.geojson"
gdf_nbh = load_neighborhoods_geojson(GEO_PATH)

# --------------------------------------------------
# Sidebar filters
# --------------------------------------------------
st.sidebar.header("Filters")

years = sorted(df["year"].unique())
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
    (df["hour"].between(hour_range[0], hour_range[1]))
)

df_filt = df[mask].copy()

st.caption(
    f"Filtered incidents: **{len(df_filt):,}** out of {len(df):,} total."
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
    "Maps",
    "Hour and Weekday Patterns",
    "Forecast (2026 Outlook)"
])

# ==================================================
# TAB 1: Trends and Rankings
# ==================================================
with tab1:
    left, right = st.columns((2, 1.3))

    # Monthly trend
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
        else:
            st.info("No data for current filters.")

    # Top neighborhoods
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
                labels={"incidents": "Incidents", "neighborhood": ""}
            )
            fig_bar.update_layout(height=350, yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig_bar, use_container_width=True)
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
            labels={"category": "Category", "incidents": "Incidents"}
        )
        st.plotly_chart(fig_cat, use_container_width=True)
    else:
        st.info("No category counts to display.")

# ==================================================
# TAB 2: Maps
# ==================================================
with tab2:
    st.subheader("Incident Locations (sample)")

    if len(df_filt) > 0:
        df_map = df_filt.sample(n=min(15000, len(df_filt)), random_state=42)

        fig_map = px.scatter_mapbox(
            df_map,
            lat="latitude",
            lon="longitude",
            hover_name="neighborhood",
            hover_data=["category", "weekday", "hour", "date"],
            zoom=11.3,
            height=650,
            title="Sample Incident Points (filtered)"
        )

        fig_map.update_layout(
            mapbox_style="open-street-map",
            margin={"r":0, "t":50, "l":0, "b":0}
        )
        st.plotly_chart(fig_map, use_container_width=True)
    else:
        st.info("No locations to show for current filters.")

    st.markdown("---")
    st.subheader("Choropleth by Analysis Neighborhood (41 zones)")

    if len(df_filt) > 0:
        nbh_counts = df_filt.groupby("neighborhood").size().reset_index(name="incidents")

        gdf_plot = gdf_nbh.merge(nbh_counts, on="neighborhood", how="left").fillna({"incidents": 0})

        fig_choro = px.choropleth_mapbox(
            gdf_plot,
            geojson=gdf_plot.geometry.__geo_interface__,
            locations=gdf_plot.index,
            color="incidents",
            hover_name="neighborhood",
            hover_data={"incidents":":,0f"},
            color_continuous_scale="Reds",
            mapbox_style="open-street-map",
            zoom=11,
            center={"lat": 37.77, "lon": -122.42},
            height=650,
            title="Incidents by Analysis Neighborhood (filtered)"
        )

        fig_choro.update_geos(fitbounds="locations", visible=False)
        fig_choro.update_layout(margin={"r":0, "t":50, "l":0, "b":0})
        st.plotly_chart(fig_choro, use_container_width=True)
    else:
        st.info("No data for choropleth under current filters.")

# ==================================================
# TAB 3: Hour and Weekday Patterns
# ==================================================
with tab3:
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
        heat = heat.sort_values(["weekday", "hour"])

        fig_heat = px.density_heatmap(
            heat,
            x="hour",
            y="weekday",
            z="incidents",
            nbinsx=24,
            labels={"hour": "Hour", "weekday": "Weekday", "incidents": "Incidents"}
        )
        fig_heat.update_layout(height=450)
        st.plotly_chart(fig_heat, use_container_width=True)
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

    with right:
        st.subheader("Weekday Pattern")
        if len(df_filt) > 0:
            wk = df_filt["weekday"].value_counts().reindex(weekday_order).reset_index()
            wk.columns = ["weekday", "incidents"]

            fig_wk = px.bar(wk, x="weekday", y="incidents")
            st.plotly_chart(fig_wk, use_container_width=True)

# ==================================================
# TAB 4: Forecast panel
# ==================================================
with tab4:
    st.subheader("Citywide Monthly Forecast (2026 Outlook)")

    @st.cache_data
    def fit_forecast(ts: pd.Series):
        # Baseline seasonal ARIMA
        model = SARIMAX(ts, order=(1, 1, 1), seasonal_order=(1, 1, 1, 12))
        results = model.fit(disp=False)
        return results

    # Use full citywide monthly totals for stable forecast
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

    fig_fc = px.line(
        forecast_df,
        x="month",
        y="forecast",
        markers=True,
        labels={"month": "Month", "forecast": "Forecast incidents"},
        title="Forecasted Monthly Incidents for Early 2026"
    )

    fig_fc.add_scatter(
        x=forecast_df["month"],
        y=forecast_df["lower"],
        mode="lines",
        name="Lower CI"
    )
    fig_fc.add_scatter(
        x=forecast_df["month"],
        y=forecast_df["upper"],
        mode="lines",
        name="Upper CI"
    )

    st.plotly_chart(fig_fc, use_container_width=True)

    st.markdown(
        "This forecast is a baseline seasonal ARIMA model fit on citywide monthly totals. "
        "It is intended as a short-term planning aid, not a causal prediction."
    )
