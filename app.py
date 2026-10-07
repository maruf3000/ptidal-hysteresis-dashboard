import io
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import streamlit as st

# ==============================================================================
# PAGE CONFIGURATION
# ==============================================================================
st.set_page_config(
    page_title="Tidal Hysteresis Dashboard",
    page_icon="🌊",
    layout="wide"
)

st.title("🌊 Tidal Hysteresis Dashboard")
st.markdown("Select a water quality parameter, tide condition, and month to visualize and download hysteresis loops for **Karamjol** and **Joymoni**.")

# ==============================================================================
# DATA LOADING & PREPROCESSING
# ==============================================================================
@st.cache_data
def load_data():
    # Load dataset from repository
    try:
        df = pd.read_csv("dataset.csv")
        if len(df.columns) <= 1:
            df = pd.read_csv("dataset.csv", sep='\t')
    except Exception:
        df = pd.read_excel("dataset.xlsx")

    # Clean text columns
    text_cols = ['location', 'tide_type', 'month', 'season', 'weather', 'time']
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    # Parse sampling time for chronological sorting
    if 'time' in df.columns:
        df['time_dt'] = pd.to_datetime(df['time'], format='%I:%M %p', errors='coerce')
    elif 'hour' in df.columns:
        df['time_dt'] = pd.to_datetime(df['hour'].astype(str) + ':00', format='%H:%M', errors='coerce')

    return df

# Load data
df = load_data()

# Exclude metadata from parameter selection
metadata_cols = [
    'sample_id', 'date', 'year', 'month', 'month_num', 'season', 'location', 
    'latitude', 'longitude', 'tide_type', 'tide_phase', 'sampling_start', 
    'sampling_end', 'time', 'hour', 'interval_hr', 'weather', 'wind_direction', 
    'remarks', 'time_dt', 'depth_m'
]
param_options = [col for col in df.columns if col not in metadata_cols]

# ==============================================================================
# SIDEBAR / DASHBOARD CONTROLS
# ==============================================================================
st.sidebar.header("🎯 Filter Options")

available_tides = sorted(df['tide_type'].dropna().unique().tolist())
available_months = sorted(df['month'].dropna().unique().tolist())

selected_param = st.sidebar.selectbox("Select Water Quality Parameter:", param_options, index=param_options.index('do_mg_l') if 'do_mg_l' in param_options else 0)
selected_tide = st.sidebar.selectbox("Select Tide Condition:", available_tides)
selected_month = st.sidebar.selectbox("Select Month:", available_months)

# ==============================================================================
# FILTER DATA & GENERATE PLOT
# ==============================================================================
filtered_df = df[
    (df['tide_type'].str.lower() == selected_tide.lower()) & 
    (df['month'].astype(str).str.lower() == selected_month.lower())
].copy()

if filtered_df.empty:
    st.warning(f"⚠️ No data available for Tide: **{selected_tide}** and Month: **{selected_month}**.")
else:
    # Sort chronologically
    if 'time_dt' in filtered_df.columns:
        filtered_df = filtered_df.sort_values('time_dt')

    # Create figure
    fig, ax = plt.subplots(figsize=(10, 6), dpi=300)
    
    color_map = {'karamjol': '#1f77b4', 'joymoni': '#ff7f0e'}
    marker_map = {'karamjol': 'o', 'joymoni': 's'}
    
    unique_locations = filtered_df['location'].str.lower().unique()
    
    for loc in unique_locations:
        loc_df = filtered_df[filtered_df['location'].str.lower() == loc].copy()
        if loc_df.empty:
            continue
        
        x = loc_df['depth_m'].values
        y = loc_df[selected_param].values
        times = loc_df['time'].values if 'time' in loc_df.columns else loc_df['hour'].values

        c = color_map.get(loc, '#2ca02c')
        m = marker_map.get(loc, '^')
        
        # Plot trajectory line and markers
        ax.plot(x, y, label=loc.capitalize(), color=c, linestyle='-', 
                linewidth=2.2, marker=m, markersize=8, alpha=0.9)

        # Plot direction arrows
        for i in range(len(x) - 1):
            dx = x[i+1] - x[i]
            dy = y[i+1] - y[i]
            if dx != 0 or dy != 0:
                ax.annotate(
                    '', xy=(x[i+1], y[i+1]), xytext=(x[i], y[i]),
                    arrowprops=dict(arrowstyle="->", color=c, lw=1.8, mutation_scale=16)
                )

        # Add time annotations
        for xi, yi, t in zip(x, y, times):
            ax.annotate(
                str(t), (xi, yi), textcoords="offset points", 
                xytext=(6, 6), fontsize=8.5, fontweight='bold', color='#333333'
            )

    pretty_param = selected_param.replace('_', ' ').title()
    ax.set_title(f"Tidal Hysteresis Loop: {pretty_param} vs Water Depth\n(Tide: {selected_tide.capitalize()} | Month: {selected_month.capitalize()})", 
                 fontsize=12, fontweight='bold', pad=15)
    ax.set_xlabel("Water Depth (m)", fontsize=11, fontweight='bold')
    ax.set_ylabel(f"{pretty_param}", fontsize=11, fontweight='bold')
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.legend(title="Location", fontsize=10, title_fontsize='11', loc='best', frameon=True)
    plt.tight_layout()

    # Display figure on Streamlit dashboard
    st.pyplot(fig)

    # ==========================================================================
    # DOWNLOAD BUTTON
    # ==========================================================================
    # Save Matplotlib plot to buffer for download
    fn_param = selected_param.replace('/', '_')
    img_buffer = io.BytesIO()
    fig.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
    img_buffer.seek(0)

    st.download_button(
        label="📥 Download Graph (High Res PNG)",
        data=img_buffer,
        file_name=f"Hysteresis_{fn_param}_{selected_tide}_{selected_month}.png",
        mime="image/png"
    )