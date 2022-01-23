import requests
import json

games_list_file = 'Data/games_list.json'

def call_game_list():
    r = requests.get('https://api.steampowered.com/ISteamApps/GetAppList/v2/')
    data = json.loads(r.text)
    list_string = json.dumps(data)
    print(list_string)
    games_list = open(games_list_file, 'w' )
    games_list.write(list_string)
    games_list.close


def read_games_list():
    f = open(games_list_file, 'r')
    games_list = f.read()
    f.close()
    return json.loads(games_list)


def get_entry(app_name):
    games_list = read_games_list()
    apps = games_list['applist']['apps']
    for app in apps:
        if app_name == app['name'].lower():
            print(app)
            return

