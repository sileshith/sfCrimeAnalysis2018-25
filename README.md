<!-- HERO HEADER (Jupyter Notebook & HTML Export) -->
<div style="
position: relative;
width: 100%;
min-height: 520px;
border-radius: 10px;
overflow: hidden;
">
<img src="goldenGateBridge.png"
alt="Golden Gate Bridge"
style="width: 100%; height: auto; display: block;">
<div style="
position: absolute;
top: 0; left: 0; right: 0; bottom: 0;
background-color: rgba(0,0,0,0.45);
"></div>
<div style="
position: absolute;
top: 30%;
left: 50%;
transform: translate(-50%, -50%);
width: 90%;
max-width: 900px;
text-align: center;
color: white;
z-index: 2;
">
<h1 style="
font-size: 42px;
font-weight: 800;
line-height: 1.15;
margin: 0;
padding: 0;
">
San Francisco Crime Analytics (2018–2025)
</h1>
<h2 style="
font-size: 22px;
font-weight: 500;
margin-top: 10px;
padding: 0;
">
Forecasting, Neighborhood Patterns, and Patrol Optimization Using Python
</h2>
</div>
<div style="
position: absolute;
bottom: 40px;
left: 40px;
z-index: 2;
color: white;
font-size: 15px;
line-height: 1.45;
background-color: rgba(0,0,0,0.45);
padding: 12px 20px;
border-radius: 6px;
white-space: nowrap;
">
<strong>Author:</strong> Sileshi Hirpa<br>
<strong>Course:</strong> DAT 301 (Exploring Data in R & Python)<br>
<strong>Project:</strong> Project 2 (Python)<br>
<strong>Professor:</strong> Dr. Neha Joshi (PhD)<br>
<strong>Data Source:</strong> SFPD Incident Reports (DataSF)<br>
<strong>Time Window:</strong> 2018–2025
</div>
<div style="
position: absolute;
bottom: 40px;
right: 40px;
z-index: 2;
color: white;
font-size: 14px;
font-style: italic;
text-align: right;
">
Arizona State University • December 2025
</div>
</div>
<div style="text-align: center; font-size: 12px; color: gray; margin-top: 6px;">
Cover Image Source: Britannica — “Golden Gate Bridge”
</div>

---

# San Francisco Crime Analytics (2018–2025)

A structured, end-to-end analysis of nearly one million SFPD incident reports, covering **data cleaning, exploratory visualization, geospatial patterns, time-series forecasting, and an interactive Streamlit dashboard.** This project demonstrates practical analytical workflow skills aligned with business analytics and data science roles.

---

## Table of Contents
1. [Project Overview](#project-overview)
2. [Research Goals](#research-goals)
3. [Dataset](#dataset)
4. [Repository Structure](#repository-structure)
5. [Analytical Summary](#analytical-summary)
   - [Citywide Trend](#1-citywide-trend-2018-2025)
   - [Neighborhood Hotspots](#2-neighborhood-hotspots)
   - [Leading Crime Categories](#3-leading-crime-categories)
   - [Daily & Weekly Patterns](#4-daily-and-weekly-patterns)
   - [Neighborhood Profiles](#5-neighborhood-crime-profiles)
   - [Forecasting Early 2026](#6-forecasting-early-2026-sarima)
   - [Dashboard Features](#7-dashboard-highlights)
6. [How to Run This Project](#how-to-run-this-project)
7. [Dashboard Snapshot](#dashboard-snapshot)
8. [Key Skills Demonstrated](#key-skills-demonstrated)

---

## Project Overview

This analysis explores crime trends in San Francisco using **2018–2025 SFPD incident data**. The work includes:
- Detailed data cleaning and feature engineering
- Temporal and weekday/hourly analysis
- Profiling across DataSF’s **41 Analysis Neighborhoods**
- Category-level exploration
- SARIMA-based forecasting for early 2026
- Dual dashboards (local and API-powered) for interactive exploration

The project follows a practical, real-world analytic workflow.

---

## Research Goals

1. Identify which neighborhoods and categories contribute most to incident volume.
2. Examine hourly and weekly crime cycles.
3. Track citywide trends from 2018 through 2025.
4. Produce a baseline SARIMA forecast for early 2026.
5. Build dashboards for analysts and public audiences.

---

## Dataset

- **Source:** DataSF Open Data Portal
- **Dataset:** Police Incident Reports
- **Time Span:** 2018–2025
- **Geographical Standard:** DataSF’s **41 Analysis Neighborhoods**

---

## Repository Structure
 
│  
├── project2_SH.ipynb # Full analysis notebook   
├── project2_SH.html # HTML export   
├── app.py # Streamlit dashboar    
├── goldenGatebrge.png # Cover image    
├── dashboard_charts/ # Dashboard snapshot assets   
└── Police_Department_Incident_Reports__2018_to_20251121.csv   



---

## Analytical Summary

### 1. Citywide Trend (2018–2025)

Incident volume declines significantly beginning in 2020 and stabilizes at lower levels through 2024–2025 due to:
- Hybrid and remote work
- Fewer commuters in downtown areas
- Changing tourism patterns
- Targeted safety initiatives

San Francisco appears to have settled into a **post-2020 baseline**.

### 2. Neighborhood Hotspots

Consistently high-activity neighborhoods include:
1. Mission
2. Tenderloin
3. South of Market (SoMa)
4. Financial District / South Beach
5. Bayview–Hunters Point

Lower-activity residential regions include Sunset/Parkside, Marina, Seacliff, Outer Richmond.

### 3. Leading Crime Categories

Top categories across years:
- **Larceny/Theft**
- **Malicious Mischief**
- **Assault**
- **Other Miscellaneous**
- **Motor Vehicle Theft**
- **Burglary**

These categories define the city's crime signature.

### 4. Daily and Weekly Patterns

#### Hourly
- Quietest: **4–6 AM**
- Midday peak: **12–3 PM**
- Evening plateau: **3–7 PM**
- Weekend nightlife spike: **12–3 AM**

#### Weekly
- Highest: **Wednesday & Friday**
- Lowest: **Sunday**

### 5. Neighborhood Crime Profiles
- **Theft-heavy areas:** Financial District, South Beach, Union Square, SoMa
- **Vehicle-crime clusters:** Mission, Tenderloin, Bayview
- **Lower-risk residential:** Sunset, Richmond, Marina

### 6. Forecasting Early 2026 (SARIMA)

SARIMA projections estimate:
- **3,900–4,600 incidents per month** early in 2026
- Levels remain **~41% below** pre-2020 averages
- Seasonal cycles remain stable
- No evidence of return to pre-pandemic highs

### 7. Dashboard Highlights

#### Full Local Dashboard
Includes:
- Spatial heatmaps
- Hourly/weekday trends
- Category breakdowns
- Neighborhood comparisons
- Forecast visualization

#### API-Based Dashboard
Includes:
- Dynamic filters
- Real-time updated visuals
- CSV export
- Neighborhood & category exploration

---

## How to Run This Project

### Run the Notebook
```bash
# Launch Jupyter Notebook or Lab
jupyter notebook
# or
jupyter lab

# Open project2_SH.ipynb and run all cells