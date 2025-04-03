import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import folium
from streamlit_folium import folium_static

# Set page config
st.set_page_config(page_title="Water Quality Dashboard", layout="wide")

# Custom CSS for better styling
st.markdown("""
    <style>
        .main {padding: 2rem;}
        .stSelectbox, .stFileUploader {margin-bottom: 1rem;}
        .plot-container {margin-top: 2rem;}
        .map-container {margin-top: 2rem;}
        .stAlert {margin-bottom: 1rem;}
    </style>
    """, unsafe_allow_html=True)

# Title and description
st.title("Water Quality Analysis Dashboard")
st.markdown("""
This interactive dashboard allows you to explore water quality data through:
- Time-series trends of different water quality characteristics
- Geographic visualization of monitoring locations
""")

# Sidebar for file uploads and settings
with st.sidebar:
    st.header("Data Input")
    st.markdown("Upload your water quality data files:")
    
    # File uploaders
    results_file = st.file_uploader("Upload Measurement Data (CSV)", type=['csv'], key='results')
    stations_file = st.file_uploader("Upload Station Data (CSV)", type=['csv'], key='stations')
    
    # Default file paths (if no upload)
    default_results = "narrowresult.csv"
    default_stations = "station.csv"
    
    st.header("Analysis Settings")
    second_char = st.selectbox(
        "Select second characteristic to compare with Aluminum",
        ['Ammonium', 'pH', 'Dissolved oxygen (DO)', 'Escherichia coli', 'Nitrate', 'Chloride'],
        index=0
    )

# Tab layout for different visualizations
tab1, tab2 = st.tabs(["Trend Analysis", "Geographic View"])

# Trend Analysis Tab
with tab1:
    st.header("Water Quality Trend Analysis")
    
    if results_file is not None:
        df = pd.read_csv(results_file)
        st.success("Measurement data loaded successfully!")
    else:
        try:
            df = pd.read_csv(default_results)
            st.info(f"Using default measurement data: {default_results}")
        except:
            st.error("Please upload measurement data or ensure default file exists.")
            st.stop()
    
    # Plotting function
    def plot_water_quality_comparison(second_characteristic='Ammonium', df=df):
        try:
            # Preprocess data
            df['ActivityStartDate'] = pd.to_datetime(df['ActivityStartDate'])
            
            # Create figure with two subplots
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
            
            # Plot Aluminum trends
            plot_characteristic_trend(df, 'Aluminum', ax1)
            
            # Plot second characteristic trends
            plot_characteristic_trend(df, second_characteristic, ax2)
            
            plt.tight_layout()
            st.pyplot(fig)
            
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")

    def plot_characteristic_trend(df, characteristic_name, ax):
        """Helper function to plot trends for a specific characteristic"""
        # Filter and clean data
        filtered_df = df[df['CharacteristicName'].str.contains(characteristic_name, case=False, na=False)].copy()
        filtered_df['ResultMeasureValue'] = pd.to_numeric(filtered_df['ResultMeasureValue'], errors='coerce')
        filtered_df = filtered_df.dropna(subset=['ResultMeasureValue'])
        
        if filtered_df.empty:
            ax.set_title(f'No {characteristic_name} data available', pad=20)
            ax.set_ylabel('')
            return
        
        # Pivot and plot
        pivot_df = filtered_df.pivot_table(
            index='ActivityStartDate',
            columns='MonitoringLocationIdentifier',
            values='ResultMeasureValue',
            aggfunc='mean'
        )
        
        # Plot each site's data
        for site in pivot_df.columns:
            site_data = pivot_df[site].dropna()
            if not site_data.empty:
                ax.plot(site_data.index, site_data.values, 
                        marker='o', linestyle='-', label=site)
        
        # Format subplot
        units = filtered_df['ResultMeasure/MeasureUnitCode'].iloc[0] if 'ResultMeasure/MeasureUnitCode' in filtered_df.columns else ''
        ax.set_title(f'Trend of {characteristic_name} Measurements', pad=20)
        ax.set_ylabel(f'{characteristic_name} ({units})' if units else characteristic_name)
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        ax.grid(True, alpha=0.3)

    # Display the plot
    with st.spinner("Generating trends..."):
        plot_water_quality_comparison(second_characteristic=second_char)

# Geographic View Tab
with tab2:
    st.header("Water Quality Monitoring Locations")
    
    if stations_file is not None:
        stations_df = pd.read_csv(stations_file)
        st.success("Station data loaded successfully!")
    else:
        try:
            stations_df = pd.read_csv(default_stations)
            st.info(f"Using default station data: {default_stations}")
        except:
            st.error("Please upload station data or ensure default file exists.")
            st.stop()
    
    # Function to process station data
    def get_unique_sites(df):
        required_columns = ['MonitoringLocationName', 'MonitoringLocationTypeName', 
                           'LatitudeMeasure', 'LongitudeMeasure']
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            st.error(f"Missing required columns in station data: {missing_columns}")
            return None
        
        unique_sites = df[required_columns].drop_duplicates()
        unique_sites = unique_sites.dropna(subset=['LatitudeMeasure', 'LongitudeMeasure'])
        return unique_sites
    
    unique_sites = get_unique_sites(stations_df)
    
    if unique_sites is not None:
        st.success(f"Found {len(unique_sites)} unique monitoring locations")
        
        # Show data table
        with st.expander("View Station Data"):
            st.dataframe(unique_sites)
        
        # Create and display map
        st.subheader("Monitoring Locations Map")
        
        # Calculate map center
        avg_lat = unique_sites['LatitudeMeasure'].mean()
        avg_lon = unique_sites['LongitudeMeasure'].mean()
        
        # Create Folium map
        site_map = folium.Map(location=[avg_lat, avg_lon], zoom_start=7)
        
        # Add markers
        for _, row in unique_sites.iterrows():
            folium.Marker(
                location=[row['LatitudeMeasure'], row['LongitudeMeasure']],
                popup=f"{row['MonitoringLocationName']}<br>Type: {row['MonitoringLocationTypeName']}",
                tooltip=row['MonitoringLocationName'],
                icon=folium.Icon(color="blue", icon="tint", prefix="fa")
            ).add_to(site_map)
        
        # Display map in Streamlit
        folium_static(site_map, width=1000, height=600)

