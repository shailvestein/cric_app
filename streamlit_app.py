import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from datetime import datetime, timedelta
import streamlit as st
import io

# Step 1: Get Player Profile URL for IPL from Cricbuzz
def get_player_profile_url(player_name):
    query = player_name.replace(' ', '+')
    url = f"https://www.cricbuzz.com/search?q={query}"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Search for player profile link
    links = soup.find_all('a', href=True)
    for link in links:
        # Check if the URL contains '/player/', this is the format Cricbuzz uses for player pages
        if '/player/' in link['href']:
            player_url = 'https://www.cricbuzz.com' + link['href']
            return player_url
    return None  # If no link is found

# Step 2: Extract Player ID from Cricbuzz Profile URL
def get_player_id(profile_url):
    match = re.search(r'/player/(.+?)/', profile_url)
    return match.group(1) if match else None

# Step 3: Generate Filtered URL for IPL matches
def generate_filtered_url(player_id, filters, stats_type="batting", tournament="ipl"):
    base = f"https://www.cricbuzz.com/profiles/{player_id}/career-stats"
    params = [f"stats_type={stats_type}", f"tournament={tournament}"]
    for key, val in filters.items():
        if val:
            params.append(f"{key}={val}")
    return base + "?" + "&".join(params)

# Step 4: Scrape Stats Table from Cricbuzz
def scrape_stats_table(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', class_='cb-col cb-col-100 cb-ltst-wgt-hdr')
        if table:
            return pd.read_html(str(table))[0]
    except Exception as e:
        print(f"Error scraping stats: {e}")
        return None
    return None

# Step 5: Extract Ground Venue and Pitch Report (if available)
def get_match_details(match_url):
    response = requests.get(match_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Extract Ground Venue
    venue = soup.find('div', class_='cb-col cb-col-100 cb-ltst-wgt-hdr')
    venue_name = venue.get_text() if venue else "Not available"
    
    # Extract Pitch Report
    pitch_report = soup.find('div', class_='cb-col cb-col-100 cb-ltst-wgt-hdr')
    pitch_info = pitch_report.get_text() if pitch_report else "Pitch report not available"
    
    return venue_name, pitch_info

# Convert DataFrame to CSV
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

# Streamlit Web App
def main():
    st.title("IPL Player Performance Analyzer")
    
    # Player Name Input
    player_name = st.text_input("Enter Player Name", "")
    
    if player_name:
        profile_url = get_player_profile_url(player_name)
        
        if not profile_url:
            st.error("Player not found. Please try with another name.")
            return

        player_id = get_player_id(profile_url)
        if not player_id:
            st.error("Unable to extract player ID.")
            return
        
        st.success(f"Found Player ID: {player_id}")
        
        # Filter Inputs for IPL only
        st.subheader("Apply Filters for IPL Matches")
        
        bp = st.text_input("Batting Position (1-7 or leave blank): ")
        opp = st.text_input("Opposition Team ID (e.g., Mumbai Indians=7, CSK=4, etc.): ")
        res = st.selectbox("Match Result", ["All", "Won", "Lost", "Draw"])
        inn = st.selectbox("Innings Number", ["All", "1", "2"])
        
        # Date Range for last 1 year
        today = datetime.today()
        spanmax = today.strftime('%Y-%m-%d')
        spanmin = (today - timedelta(days=365)).strftime('%Y-%m-%d')
        
        filters = {
            "batting_position": bp,
            "opposition": opp,
            "result": "1" if res == "Won" else "2" if res == "Lost" else "3" if res == "Draw" else "",
            "innings_number": inn if inn != "All" else "",
            "spanmin": spanmin,
            "spanmax": spanmax
        }
        
        # Batting Stats
        st.subheader("Batting Stats")
        batting_url = generate_filtered_url(player_id, filters, stats_type="batting", tournament="ipl")
        batting_df = scrape_stats_table(batting_url)
        
        if batting_df is not None:
            st.write(batting_df)
            # Add Download Button for Batting Stats CSV
            csv_batting = convert_df_to_csv(batting_df)
            st.download_button(
                label="Download Batting Stats as CSV",
                data=csv_batting,
                file_name=f"{player_name}_ipl_batting_stats.csv",
                mime="text/csv"
            )
        else:
            st.warning("No Batting stats found for the applied filters.")
        
        # Bowling Stats
        st.subheader("Bowling Stats")
        bowling_url = generate_filtered_url(player_id, filters, stats_type="bowling", tournament="ipl")
        bowling_df = scrape_stats_table(bowling_url)
        
        if bowling_df is not None:
            st.write(bowling_df)
            # Add Download Button for Bowling Stats CSV
            csv_bowling = convert_df_to_csv(bowling_df)
            st.download_button(
                label="Download Bowling Stats as CSV",
                data=csv_bowling,
                file_name=f"{player_name}_ipl_bowling_stats.csv",
                mime="text/csv"
            )
        else:
            st.warning("No Bowling stats found for the applied filters.")
        
        # Fetch Match Details (Ground Venue and Pitch Report)
        st.subheader("Ground Venue and Pitch Report")
        
        match_url = f"https://www.cricbuzz.com/live-cricket-scorecard/{player_id}"  # Replace with accurate match URL
        venue_name, pitch_info = get_match_details(match_url)
        
        st.write(f"**Ground Venue**: {venue_name}")
        st.write(f"**Pitch Report**: {pitch_info}")

if __name__ == "__main__":
    main()
