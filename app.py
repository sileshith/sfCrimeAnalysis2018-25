import requests  # add at top of app.py

@st.cache_data(show_spinner="Fetching and cleaning data from DataSF API...", ttl=24*3600)
def load_incidents():
    base_url = "https://data.sfgov.org/resource/wg3w-h783.json"

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
        "incident_date between '2018-01-01T00:00:00.000' "
        "and '2025-12-31T23:59:59.999'"
    )

    limit = 50000
    offset = 0
    frames = []

    while True:
        params = {
            "$select": select_cols,
            "$where": where_clause,
            "$limit": limit,
            "$offset": offset
        }

        try:
            r = requests.get(base_url, params=params, timeout=60)
            r.raise_for_status()
            chunk = pd.DataFrame(r.json())
        except Exception as e:
            st.error(f"Could not load data from DataSF API. Error: {e}")
            return pd.DataFrame()

        if chunk.empty:
            break

        frames.append(chunk)
        offset += limit

        if offset > 600000:  # safety guard
            break

    df = pd.concat(frames, ignore_index=True)

    df = df.rename(columns={
        "incident_date": "date",
        "incident_datetime": "incident_datetime",
        "analysis_neighborhood": "neighborhood",
        "incident_category": "category",
        "incident_day_of_week": "weekday",
        "latitude": "latitude",
        "longitude": "longitude"
    })

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["incident_datetime"] = pd.to_datetime(df["incident_datetime"], errors="coerce")

    df = df.dropna(subset=["date", "neighborhood", "category", "latitude", "longitude"])

    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()
    df["hour"] = df["incident_datetime"].dt.hour

    df = df[(df["year"] >= 2018) & (df["year"] <= 2025)].copy()
    return df
