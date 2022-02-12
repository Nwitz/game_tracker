import requests
import json
from enum import Enum

games_map_file = 'Data/games_map.json' # Mapping from app ID to Game name (fetched from Steam)
wishlist_file = 'Data/wishlist.json' # Games being tracked by server (modified by us)

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
    #  Check if game ID exists
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
    print(json.dumps(app_data, indent=4, sort_keys=True))

    #  Add if doesn't exist
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
    print("Entering the delete_games function")
    app_to_delete = f'{app_tuple[0]}'
    if app_to_delete in wishlist_json:
        del wishlist_json[app_to_delete]
        deleted_game_status = True
    else:
        deleted_game_status = False
    sync_wishlist_file()
    print(f'The result of the delete_game function is: {deleted_game_status}')
    return deleted_game_status

class GameAddStatus(Enum):
    EXISTS = 1
    FREE_GAME = 2
    SUCCESS = 3