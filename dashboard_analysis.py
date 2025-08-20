"""
Streamlit Dashboard for GitHub Trends Analysis
- Connects to MongoDB and retrieves latest analysis
- Displays repositories in interactive table
- Provides sorting and filtering functionality
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timezone
from pymongo import MongoClient
import os


def get_mongodb_connection():
    """Establish MongoDB connection using environment variables."""
    mongo_uri = st.secrets.get("MONGODB_URI")
    mongo_db = "github_trends"
    
    if not mongo_uri:
        st.error("MONGODB_URI is not set. Please add it to your .env file.")
        return None
    
    client = MongoClient(mongo_uri)
    db = client[mongo_db]
    return db

def get_latest_analysis():
    """Retrieve the latest analysis from MongoDB."""
    db = get_mongodb_connection()
    if db is None:
        return None
    
    analysis_collection = db['analysis']
    
    # Find the most recent analysis date
    latest_analysis_date = analysis_collection.find_one(
        sort=[('analysis_date', -1)]
    )
    
    if latest_analysis_date is None:
        st.error("No analysis data found in MongoDB.")
        return None
    
    latest_date = latest_analysis_date.get('analysis_date')
    
    # Get all repositories from the latest analysis
    latest_analysis = list(analysis_collection.find(
        {'analysis_date': latest_date}
    ))
    
    if not latest_analysis:
        st.error("No analysis data found for the latest analysis date.")
        return None
    
    return latest_analysis

def convert_analysis_to_dataframe(analysis_data):
    """Convert MongoDB analysis documents to pandas DataFrame."""
    if not analysis_data:
        return None
    
    # Convert list of repository documents to DataFrame
    df = pd.DataFrame(analysis_data)
    
    # Extract analysis metadata from the first document
    if not df.empty:
        first_doc = analysis_data[0]
        df['analysis_date'] = first_doc.get('analysis_date')
        df['analysis_period_days'] = first_doc.get('analysis_period_days')
        df['analysis_start_date'] = first_doc.get('analysis_start_date')
        df['analysis_end_date'] = first_doc.get('analysis_end_date')
    
    return df

def format_metrics(df):
    """Format numeric columns for better display."""
    if df is None:
        return df
    
    if df.empty:
        return df
    
    # Format percentage columns
    if 'growth_percent' in df.columns:
        df['growth_percent'] = df['growth_percent'].fillna(0)
        df['growth_percent'] = df['growth_percent'].replace([float('inf'), float('-inf')], 0)
        df['growth_percent'] = df['growth_percent'].round(2)
    
    # Format growth per day
    if 'growth_per_day' in df.columns:
        df['growth_per_day'] = df['growth_per_day'].fillna(0)
        df['growth_per_day'] = df['growth_per_day'].replace([float('inf'), float('-inf')], 0)
        df['growth_per_day'] = df['growth_per_day'].round(2)
    
    # Format star counts - handle NaN and infinite values
    star_columns = ['start_stars', 'end_stars', 'star_growth']
    for col in star_columns:
        if col in df.columns:
            # Fill NaN values with 0 and convert infinite values to 0
            df[col] = df[col].fillna(0)
            df[col] = df[col].replace([float('inf'), float('-inf')], 0)
            df[col] = df[col].astype(int)
    
    return df

def check_password():
    """Returns `True` if the user had the correct password."""
    # Get password from secrets or environment variable
    expected_password = st.secrets.get("password") or os.getenv("STREAMLIT_PASSWORD")
    
    if not expected_password:
        st.error("Password not configured. Please set STREAMLIT_PASSWORD environment variable or add to .streamlit/secrets.toml")
        st.stop()
    
    def password_entered():
        if st.session_state["password"] == expected_password:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password incorrect, show input + error
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        # Password correct
        return True

def main():
    st.set_page_config(
        page_title="GitHub Trends Analysis Dashboard",
        page_icon="📊",
        layout="wide"
    )
    
    # Check password
    if not check_password():
        st.stop()
    
    st.title("📊 GitHub Trends Analysis Dashboard")
    st.markdown("---")
    
    # Load data
    with st.spinner("Loading latest analysis from MongoDB..."):
        analysis_data = get_latest_analysis()
    
    if analysis_data is None:
        st.stop()
    
    # Convert to DataFrame
    df = convert_analysis_to_dataframe(analysis_data)
    if df is None:
        st.error("No analysis results found.")
        st.stop()
    
    if df.empty:
        st.error("Analysis results are empty.")
        st.stop()
    
    # Format metrics
    df = format_metrics(df)
    
    # Display analysis metadata
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Repositories", 
            f"{len(df):,}"
        )
    
    with col2:
        # Get analysis date from the first document
        if analysis_data and len(analysis_data) > 0:
            analysis_date = analysis_data[0].get('analysis_date')
            if analysis_date:
                if isinstance(analysis_date, str):
                    analysis_date = datetime.fromisoformat(analysis_date.replace('Z', '+00:00'))
                st.metric(
                    "Analysis Date", 
                    analysis_date.strftime("%Y-%m-%d %H:%M")
                )
    
    with col3:
        # Get start and end dates from the first document
        if analysis_data and len(analysis_data) > 0:
            start_date = analysis_data[0].get('analysis_start_date')
            end_date = analysis_data[0].get('analysis_end_date')
            if start_date and end_date:
                if isinstance(start_date, str):
                    start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                if isinstance(end_date, str):
                    end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                st.metric(
                    "Analysis Period", 
                    f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
                )
    
    with col4:
        # Get period days from the first document
        if analysis_data and len(analysis_data) > 0:
            period_days = analysis_data[0].get('analysis_period_days', 0)
            st.metric(
                "Period (Days)", 
                period_days
            )
    
    st.markdown("---")
    
    # Filters
    st.subheader("🔍 Filters")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Filter by minimum growth percentage
        min_growth = st.number_input(
            "Minimum Growth %", 
            min_value=0.0, 
            max_value=1000.0, 
            value=0.0, 
            step=0.1
        )
    
    with col2:
        # Filter by minimum star growth
        min_star_growth = st.number_input(
            "Minimum Star Growth", 
            min_value=0, 
            max_value=10000, 
            value=0, 
            step=1
        )
    
    with col3:
        # Filter by minimum end stars
        min_end_stars = st.number_input(
            "Minimum End Stars", 
            min_value=0, 
            max_value=100000, 
            value=0, 
            step=100
        )
    
    # Apply filters
    filtered_df = df.copy()
    
    if min_growth > 0:
        filtered_df = filtered_df[filtered_df['growth_percent'] >= min_growth]
    
    if min_star_growth > 0:
        filtered_df = filtered_df[filtered_df['star_growth'] >= min_star_growth]
    
    if min_end_stars > 0:
        filtered_df = filtered_df[filtered_df['end_stars'] >= min_end_stars]
    
    # Display filtered results count
    st.info(f"Showing {len(filtered_df)} of {len(df)} repositories")
    
    # Interactive table
    st.subheader("📋 Repository Analysis Results")
    
    # Select columns to display
    display_columns = [
        'full_name', 'author', 'description', 'start_stars', 
        'end_stars', 'star_growth', 'growth_per_day', 'growth_percent', 'url'
    ]
    
    # Filter DataFrame to only show selected columns
    display_df = filtered_df[display_columns].copy()
    
    # Rename columns for better display
    column_mapping = {
        'full_name': 'Repository',
        'author': 'Author',
        'description': 'Description',
        'start_stars': 'Start Stars',
        'end_stars': 'End Stars',
        'star_growth': 'Star Growth',
        'growth_per_day': 'Growth/Day',
        'growth_percent': 'Growth %',
        'url': 'URL'
    }
    
    display_df = display_df.rename(columns=column_mapping)
    
    # Display the table with sorting
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Repository": st.column_config.TextColumn(
                "Repository",
                width="medium",
                help="Repository name (owner/repo)"
            ),
            "Author": st.column_config.TextColumn(
                "Author",
                width="small"
            ),
            "Description": st.column_config.TextColumn(
                "Description",
                width="large",
                help="Repository description"
            ),
            "Start Stars": st.column_config.NumberColumn(
                "Start Stars",
                format="%d",
                width="small"
            ),
            "End Stars": st.column_config.NumberColumn(
                "End Stars",
                format="%d",
                width="small"
            ),
            "Star Growth": st.column_config.NumberColumn(
                "Star Growth",
                format="%d",
                width="small"
            ),
            "Growth/Day": st.column_config.NumberColumn(
                "Growth/Day",
                format="%.2f",
                width="small"
            ),
            "Growth %": st.column_config.NumberColumn(
                "Growth %",
                format="%.2f%%",
                width="small"
            ),
            "URL": st.column_config.LinkColumn(
                "URL",
                width="medium"
            )
        }
    )
    
    # Summary statistics
    st.markdown("---")
    st.subheader("📈 Summary Statistics")
    
    if filtered_df is not None and not filtered_df.empty:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            avg_growth = filtered_df['growth_percent'].mean()
            st.metric("Average Growth %", f"{avg_growth:.2f}%")
        
        with col2:
            max_growth = filtered_df['growth_percent'].max()
            st.metric("Max Growth %", f"{max_growth:.2f}%")
        
        with col3:
            total_star_growth = filtered_df['star_growth'].sum()
            st.metric("Total Star Growth", f"{total_star_growth:,}")
        
        with col4:
            avg_stars = filtered_df['end_stars'].mean()
            st.metric("Average End Stars", f"{avg_stars:.0f}")
    
    # Top performers
    st.markdown("---")
    st.subheader("🏆 Top Performers")
    
    if filtered_df is not None and not filtered_df.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Top 5 by Growth %**")
            top_growth = filtered_df.nlargest(5, 'growth_percent')[['full_name', 'growth_percent', 'star_growth']]
            st.dataframe(top_growth, hide_index=True)
        
        with col2:
            st.write("**Top 5 by Star Growth**")
            top_stars = filtered_df.nlargest(5, 'star_growth')[['full_name', 'star_growth', 'growth_percent']]
            st.dataframe(top_stars, hide_index=True)

if __name__ == "__main__":
    main()
