import requests
import json

games_map_file = 'Data/games_map.json' # Mapping from app ID to Game name (fetched from Steam)
games_list_file = 'Data/game_list.json' # Games being tracked by server (modified by us)

# Dictionary containing the list of games that have been added by members of the Discord Server
games_list_json = []

def load_games(): 
    # TODO create file if it doesn't exist, currently: Make file in Data named game_list.json, and populate wiht {"game_list":[]}
    global games_list_json #Reference the file variable games_list_json
    
    # open and read file containing games that have been previously stored
    file = open(games_list_file, 'r') 
    list_string = file.read()

    # File is read as String, decode that String into a JSON dictionary so we can work with it.
    file_json = json.loads(list_string) #Contains the JSON obect representing games_list_file
    
    #Pull out the game_list object from inside the JSON dictionary. 
    games_list_json = file_json['game_list']

    file.close() # Close file - important, if we don't close we could have conflicts when trying to open later. 

# Fetch and store apps list from steam
# This file contains the mappings between appid and game title
def call_game_list():
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
def read_games_list():
    f = open(games_map_file, 'r')
    games_list = f.read()
    f.close()
    return json.loads(games_list)

# Read the appid - game title mappings from the mapping file, then check each app's game title to find a match with app_name
def get_entry(app_name):
    games_list = read_games_list()
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
    for app in games_list_json: 
        if app_tuple[0] == app["appid"]:
            print(f"\"{app_tuple[1]}\" already exists, nice try buckaroo")
            return
    #  Add if doesn't exist
    new_app = {"appid":app_tuple[0], "name":app_tuple[1]}
    games_list_json.append(new_app)
    sync_game_list_file()
    return

def list_games():
    print(games_list_json)

# Write the current value stored in games_list_json to the games_list_file
# Note: We write to this file for every addition/deletion of games, but only read from it one time: when the bot is ready. 
def sync_game_list_file():
    # Open file in write mode
    file = open(games_list_file, 'w')

    # Convert games_list_json to a valid JSON objec
    game_object_json = {'game_list':games_list_json}

    # Dump JSON object into String format and write string to file
    game_list_string = json.dumps(game_object_json)
    file.write(game_list_string)

    # Close file
    file.close()

