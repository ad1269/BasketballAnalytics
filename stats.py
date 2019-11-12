# Pulls stats from basketball-reference.com, cleans it up, and presents it to the analyzer
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from bs4 import BeautifulSoup

import numpy as np
import scipy.stats as st

import time 
import pickle
import unidecode

# Mapping of stat name to index for basketball-reference
statIndex = {p:i for p, i in zip(["Name", "Pos", "Age", "Tm", "G", "GS",
        "MP", "FG", "FGA", "FG%", "3P", "3PA", "3P%", "2P", "2PA", "2P%",
        "eFG%", "FT", "FTA", "FT%", "ORB", "DRB", "TRB", "AST", "STL",
        "BLK", "TOV", "PF", "PTS"], range(100))}

# PUBLIC VARIABLE
rotoStatNames = ["TOV", "TRB", "BLK", "STL", "PTS", "AST", "3P", "FG%", "FT%"]

# Mapping of stat name to index for Fantasy Basketball
rotoStatIndex = {p:i for p, i in zip(rotoStatNames, range(20))}

def download_data():
    # Download webpage
    driver = webdriver.Chrome("/Users/admohanraj/Downloads/chromedriver")
    driver.get("https://www.basketball-reference.com/leagues/NBA_2019_totals.html")
    content = driver.page_source

    # Parse webpage into 2-D list
    soup = BeautifulSoup(content)
    full_table = []
    for player_row in soup.findAll('tr', attrs={'class':'full_table'}):
        stats = []
        for stat in player_row.findChildren('td', recursive=False):
            stats.append(stat.text)
        full_table.append(stats)
    driver.quit()
    return full_table

def save_data_to_disk(table):
    with open('bbref_data.pkl', 'wb') as f:
        pickle.dump(table, f)
        
# Load table from file, or download if it doesn't exist
def get_data():
    try:
        with open('bbref_data.pkl', 'rb') as f:
            return pickle.load(f)
    except FileNotFoundError:
        tbl = download_data()
        save_data_to_disk(tbl)
        return tbl
    
def get_fantasy_stats_from_row(player_row):
    name = unidecode.unidecode(player_row[statIndex["Name"]])
    points = int(player_row[statIndex["PTS"]])
    assists = int(player_row[statIndex["AST"]])
    rebounds = int(player_row[statIndex["TRB"]])
    blocks = int(player_row[statIndex["BLK"]])
    steals = int(player_row[statIndex["STL"]])
    
    fg_made = int(player_row[statIndex["FG"]])
    fg_attempted = int(player_row[statIndex["FGA"]])
    ft_made = int(player_row[statIndex["FT"]])
    ft_attempted = int(player_row[statIndex["FTA"]])

    three_ptrs_made = int(player_row[statIndex["3P"]])
    turnovers = int(player_row[statIndex["TOV"]])
    return (name, (-turnovers, rebounds, blocks, steals, points, assists, 
            three_ptrs_made, fg_made, fg_attempted, ft_made, ft_attempted))

def clean_up_table(full_table):
    # Transform into form that algorithm can use
    return list(map(get_fantasy_stats_from_row, full_table))

# Make more efficient if needed
# Calculates the percentile of each stat, assuming a normal distribution of each stat
def player_percentile_tables(clean_table):
    stat_count = len(clean_table[0][1])
    pp_table = {player: [] for player, _ in clean_table}
    for i in range(stat_count):
        stat_col = []
        for name, stats in clean_table:
            stat_col.append([name, stats[i]])

        # Sort by stats
        stat_col.sort(key=lambda x:x[1], reverse=True)
        stat_avg, stat_std = np.average([y for _, y in stat_col]), np.std([y for _, y in stat_col])
        for i, val in enumerate(stat_col):
            percentile = st.norm.cdf((val[1] - stat_avg) / stat_std)
            pp_table[val[0]].append(percentile)        
    return pp_table

def avg_percentile_table(pp_table):
    stat_count = len(pp_table["Stephen Curry"])
    avg_table = []
    for player in pp_table:
        avg_table.append((player, sum(pp_table[player]) / stat_count))
    avg_table.sort(key=lambda x: x[1], reverse=True)
    return avg_table

def get_top_fantasy_stats_table(fantasy_stats_table, player_values, N=-1):
    top_table = []
    for i in range(len(fantasy_stats_table)):
        name = player_values[i][0]
        for row in fantasy_stats_table:
            if name == row[0]:
                top_table.append(row)
    return top_table[:N]

def get_player_values(fantasy_stats_table, categories=()):
    if categories == ():
        stat_percentiles = player_percentile_tables(fantasy_stats_table)
    else:
        # Select only categories from fantasy_stats_table
        selected_stats_table = select(fantasy_stats_table, categories)
        stat_percentiles = player_percentile_tables(selected_stats_table)

    return avg_percentile_table(stat_percentiles)

def select(fantasy_stats_table, categories):
    selected_table = []
    for player, stats in fantasy_stats_table:
        selected_stats = tuple([stats[rotoStatIndex[cat]] for cat in categories])
        selected_table.append((player, selected_stats))
    return selected_table

def download_espn_data():
    full_table = {}

    # Download webpage
    driver = webdriver.Chrome("/Users/admohanraj/Downloads/chromedriver")
    driver.get("https://fantasy.espn.com/basketball/livedraftresults")
    next_page = 2
    while next_page < 20:
        # Wait for page to load and retrieve source
        WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.XPATH, "//tbody[@class='Table2__tbody']")))
        content = driver.page_source

        # Parse webpage
        soup = BeautifulSoup(content)
        for player_row in soup.findAll('tr', attrs={'data-idx':True}):
            # Get the second td tag and search it for a div with title
            name_tag = player_row.findAll('td')[1].find('div', attrs={'title':True})
            player_name = name_tag['title']

            # Get player draft position
            dp_tag = player_row.find('div', attrs={'title':'Average draft slot player is selected at'})
            draft_position = float(dp_tag.text)

            full_table[player_name] = draft_position

        # Click next page button
        button = driver.find_element_by_xpath("//button[@data-nav-item=" + str(next_page) + "]") 
        driver.execute_script("arguments[0].click()", button)
        next_page += 1

    driver.quit()

    return full_table    
        
def get_and_save_espn_draft_data():
    tbl = download_espn_data()
    with open('espn_draft.pkl', 'wb') as f:
        pickle.dump(tbl, f)
    return tbl

def download_rosters():
    all_rosters = []

    # Download webpage
    driver = webdriver.Chrome("/Users/admohanraj/Downloads/chromedriver")
    driver.get("https://fantasy.espn.com/basketball/league/rosters?leagueId=84420677")
    
    # Wait for page to load
    time.sleep(3)
    driver.switch_to.frame(driver.find_element_by_xpath("//iframe[@id='disneyid-iframe']"))
    
    # Fill in username and password
    userField = driver.find_element_by_xpath("//input[@type='email']") 
    userField.send_keys("admohanraj@gmail.com")
    
    passField = driver.find_element_by_xpath("//input[@type='password']") 
    # password removed for Github
    passField.send_keys("")
    
    # Click login button
    button = driver.find_element_by_xpath("//button[@aria-label='Log In']") 
    driver.execute_script("arguments[0].click()", button)
    
    # Wait until rosters load
    time.sleep(2)
    driver.switch_to.default_content()
    content = driver.page_source

    # Parse webpage
    soup = BeautifulSoup(content)
    count = 0
    for roster_tbl in soup.findAll('tbody', attrs={'class':'Table2__tbody'}):
        current_roster = []
        for i in range(13):
            player_row = roster_tbl.find('tr', attrs={'data-idx': i})
            player_name = player_row.findAll('td')[1].find('div')['title']
            current_roster.append(player_name)
            
        all_rosters.append(current_roster)
    driver.quit()

    with open('current_rosters.pkl', 'wb') as f:
        pickle.dump(all_rosters, f)

    return all_rosters    

## PUBLIC FUNCTIONS
def retrieve_rosters(refresh=False):
    # Load table from file and download if it doesn't exist
    try:
        with open('current_rosters.pkl', 'rb') as f:
            tbl = pickle.load(f)
    except FileNotFoundError:
        return download_rosters()

    # Refresh the table if requested
    if refresh:
        return download_rosters()
    else:
        return tbl

def get_player_draft_order(refresh=False):
    # Load table from file and download if it doesn't exist
    try:
        with open('espn_draft.pkl', 'rb') as f:
            tbl = pickle.load(f)
    except FileNotFoundError:
        return get_and_save_espn_draft_data()

    # Refresh the table if requested
    if refresh:
        return get_and_save_espn_draft_data()
    else:
        return tbl

def get_players(order_by=()):
    raw_data = get_data()

    fantasy_stats_table = clean_up_table(raw_data)
    player_values = get_player_values(fantasy_stats_table, order_by)

    return get_top_fantasy_stats_table(fantasy_stats_table, player_values)

def calculate_percentage_stats(player):
    name, stats = player

    # We calculate total FG and FT percentage
    fg_percentage = 0 if stats[-3] == 0 else stats[-4] / stats[-3]
    ft_percentage = 0 if stats[-1] == 0 else stats[-2] / stats[-1]

    # Concatenate while dropping FG, FGA, FT, and FTA
    return (name, stats[:-4] + (fg_percentage, ft_percentage))

