import requests
import json

games_map_file = 'Data/games_map.json' # Mapping from app ID to Game name (fetched from Steam)
games_list_file = 'Data/game_list.json' # Games being tracked by server (modified by us)

games_list_json = []

def load_games(): 
    # TODO create file if it doesn't exist, currently: Make file in Data named game_list.json, and populate wiht {"game_list":[]}
    global games_list_json
    file = open(games_list_file, 'r')
    list_string = file.read()
    file_json = json.loads(list_string) #Contains the JSON obect representing games_list_file
    games_list_json = file_json['game_list']
    file.close()

def call_game_list():
    r = requests.get('https://api.steampowered.com/ISteamApps/GetAppList/v2/')
    data = json.loads(r.text)
    list_string = json.dumps(data)
    print(list_string)
    games_list = open(games_map_file, 'w' )
    games_list.write(list_string)
    games_list.close


def read_games_list():
    f = open(games_map_file, 'r')
    games_list = f.read()
    f.close()
    return json.loads(games_list)


def get_entry(app_name):
    games_list = read_games_list()
    apps = games_list['applist']['apps']
    for app in apps:
        if app_name == app['name'].lower():
            print(app)
            return app

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

def sync_game_list_file():
    file = open(games_list_file, 'w')
    game_object_json = {'game_list':games_list_json}
    game_list_string = json.dumps(game_object_json)
    file.write(game_list_string)
    file.close()

