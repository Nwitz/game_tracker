from datetime import datetime
import requests
import json
import random
from enum import Enum

games_map_file = 'Data/games_map.json' # Mapping from app ID to Game name (fetched from Steam)
wishlist_file = 'Data/wishlist.json' # Games being tracked by server (modified by us)
friday_file = 'Friday/phrases.json'

# Dictionary containing the list of games that have been added by members of the Discord Server
wishlist_json = {}

def load_games(): 
    # TODO create file if it doesn't exist, currently: Make file in Data named game_list.json, and populate wiht {"wishlist":{}}} or run clear on discord
    global wishlist_json #Reference the file variable games_list_json
    
    # open and read file containing games that have been previously stored
    file = open(wishlist_file, 'r') 
    list_string = file.read()

    # File is read as String, decode that String into a JSON dictionary so we can work with it.
    file_json = json.loads(list_string) #Contains the JSON obect representing wishlist_file
    
    #Pull out the game_list object from inside the JSON dictionary. 
    wishlist_json = file_json['wishlist']

    file.close() # Close file - important, if we don't close we could have conflicts when trying to open later. 

# Fetch and store apps list from steam
# This file contains the mappings between appid and game title
def fetch_games_mapping():
    # Perform get request to get game X appid mappings 
    r = requests.get('https://api.steampowered.com/ISteamApps/GetAppList/v2/')
    
    # Convert response text to JSON, then dump JSON to string, then back again to text (probably better way to do this)
    data = json.loads(r.text)
    list_string = json.dumps(data)
    print(list_string)

    #Open game-title X appid mapping file for writing and write in mapping string, close file
    games_list = open(games_map_file, 'w' )
    games_list.write(list_string)
    games_list.close

# Read the locally stored apps list retrieved from the 
def read_games_mapping():
    f = open(games_map_file, 'r')
    games_list = f.read()
    f.close()
    return json.loads(games_list)

# Read the appid - game title mappings from the mapping file, then check each app's game title to find a match with app_name
def get_entry(app_name):
    games_list = read_games_mapping()
    apps = games_list['applist']['apps']
    for app in apps:
        if app_name == app['name'].lower():
            # Print and return the matching app
            print(app)
            return app

# Add a game to the game list json object in memory, and sync with the file incase bot goes down. 
def add_game(app_tuple): # app_tuple = (appID, game name) 
    # Check if game ID exists
    # for app in games_list_json
    key = f'{app_tuple[0]}'
    if key in wishlist_json:
        print(f"\"{app_tuple[1]}\" already exists, nice try buckaroo")
        return (GameAddStatus.EXISTS, wishlist_json[key])

    received_app_data = fetch_game_data(key)
    if not 'price_overview' in received_app_data:
        return (GameAddStatus.FREE_GAME, None)
    
    app_data = {'name' : app_tuple[1]}
    app_data.update(received_app_data)
    app_data['sale_history'] = build_empty_sale_history()
    print(json.dumps(app_data, indent=4, sort_keys=True))

    # Add if doesn't exist
    wishlist_json[key] = app_data
    sync_wishlist_file()
    return (GameAddStatus.SUCCESS, app_data)

# Returns fetched data corresponding to app_id in the form of a dict
def fetch_game_data(app_id_string) :
    # Fetch from steampowered/api price_overview
    print(f'https://store.steampowered.com/api/appdetails?filters=price_overview,screenshots&appids={app_id_string}&cc=ca')
    r = requests.get(f'https://store.steampowered.com/api/appdetails?filters=price_overview&appids={app_id_string}&cc=ca')
    print('status code game fetch', r.status_code)
    if r.status_code == 200: 
        app_data = json.loads(r.text) # JSON - dictionary
        return app_data[app_id_string]['data'] # Internal dictionary of app_id

# Log the wishlist memory without filtering (used for testing)
def log_wishlist_memory():
    print(wishlist_json)

# Clear the memory and file wishlist (used mainly for testing)
def clear_wishlist(): 
    global wishlist_json
    print("Clearing wishlist")
    wishlist_json = {}
    sync_wishlist_file()

# Iterate through all games we track and return a list of game titles
def get_game_titles(): 
    games = []
    for key in wishlist_json:
        games.append(wishlist_json[key]['name'])
    return games

def get_games():
    return wishlist_json

# Write the current value stored in games_list_json to the wishlist_file
# Note: We write to this file for every addition/deletion of games, but only read from it one time: when the bot is ready. 
def sync_wishlist_file():
    # Open file in write mode
    file = open(wishlist_file, 'w')

    # Convert games_list_json to a valid JSON objec
    game_object_json = {'wishlist':wishlist_json}

    # Dump JSON object into String format and write string to file
    game_list_string = json.dumps(game_object_json, indent=4, sort_keys=True)
    file.write(game_list_string)

    # Close file
    file.close()

def delete_game(app_tuple):
    app_to_delete = f'{app_tuple[0]}'
    if app_to_delete in wishlist_json:
        del wishlist_json[app_to_delete]
        deleted_game_status = True
    else:
        deleted_game_status = False
    sync_wishlist_file()
    return deleted_game_status
    
def update_game_sales():
    # Get all App Ids
    app_ids = wishlist_json.keys()
    print(app_ids)

    # Convert App Ids to expected string format <id>,<id>,<id>
    app_ids_string = ','.join(map(str, app_ids))

    # Fetch all price_overviews
    url = f'https://store.steampowered.com/api/appdetails?filters=price_overview&appids={app_ids_string}'
    result = requests.get(url)
    sales = {}
    new_sales = {}
    if result.status_code == 200: 
        sale_data = json.loads(result.text)
        # TODO: clean up loop with map
        #loop through all data and extract price overview
        
        for app_id in app_ids: 
            price_overview = sale_data[app_id]['data']['price_overview']
            sale_history = wishlist_json[app_id]['sale_history']
            on_sale_yesterday = sale_history['sale_start'] != None
            on_sale = price_overview['discount_percent'] > 0

            if on_sale: 
                if not on_sale_yesterday:
                    date = datetime.now().date()
                    print(f"date: {date}")
                    sale_history['sale_start'] = f'{date}'
                    wishlist_json[app_id]['price_overview'] = price_overview
                    new_sales[app_id] = wishlist_json[app_id]
                else: 
                    sales[app_id] = wishlist_json[app_id]
            elif on_sale_yesterday:
                sale_history['last_sale_start'] = sale_history['sale_start']
                date = datetime.now().date()
                sale_history['last_sale_end'] = f'{date}'
                sale_history['sale_start'] = None
                wishlist_json[app_id]['price_overview'] = price_overview

    sync_wishlist_file()
    print(f'new sales: \n{new_sales}')
    print(f'still on sale: \n{sales}')
    return new_sales, sales

def get_game_sales(): 
    app_ids = wishlist_json.keys()
    games_on_sale = {}
    for app_id in app_ids: 
        print(f'app_id: {app_id}')
        if wishlist_json[app_id]['price_overview']['discount_percent'] > 0:
            print(f'on sale')
            games_on_sale[app_id] = wishlist_json[app_id]
    return games_on_sale
 
def build_empty_sale_history():
    sale_history = {'sale_start':None, 'last_sale_start':None, 'last_sale_end':None}
    return sale_history

# Randomly fetches a string from Friday/phrases and returns
def friday_phrase_randomizer():
    with open(friday_file) as f:
        data = json.load(f)
        phrases = data["friday"]
        random_index = random.randint(0, (len(phrases) - 1))
        phrase = phrases[random_index]
        return(phrase)

class GameAddStatus(Enum):
    EXISTS = 1
    FREE_GAME = 2
    SUCCESS = 3