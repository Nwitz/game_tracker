import discord
from Config.config import discord_config
from steam import *
import re

client = discord.Client()
token = discord_config["token"]
#this is the password for the bot to enter the discord server, you have to give it access to the server on the discord developer portal

@client.event
async def on_ready():
    print('---------------------------------------------')
    print('We have logged in as {0.user}'.format(client))
    print('---------------------------------------------')
    load_games() 
    return

@client.event
async def on_message(message):
    #reading user input
    if message.channel.name != discord_config["channel"]: 
        return

    user_input = message.content
    if user_input == 'fetch':
        print('Fetching steam list')
        call_game_list()
    elif user_input == 'list':
        print('Reading steam list')
        read_games_list()
    elif user_input == 'games_memory':
        list_games()
    elif 'delete_' in user_input:
        game_in_input = re.split('_',user_input)
        game_name = game_in_input[1]
        entry = get_entry(game_name.lower())
        print(f'The entry to be deleted is {entry}')
        if game_name != None:
            delete_game((entry["appid"], entry["name"]))
    else:
        entry = get_entry(message.content.lower())
        print(f'The entry to be added is {entry}.')
        if entry != None:
            add_game((entry["appid"], entry["name"]))

client.run(token)