import discord
from Config.config import discord_config
from steam import *

client = discord.Client()
token = discord_config["token"]
#this is the password for the bot to enter the discord server, you have to give it access to the server on the discord developer portal

@client.event
async def on_ready():
    print('---------------------------------------------')
    print('We have logged in as {0.user}'.format(client))
    print('---------------------------------------------')
    return

@client.event
async def on_message(message):
    #reading user input
    user_input = message.content
    if message.content == 'fetch':
        print('Fetching steam list')
        call_game_list()
    elif message.content == 'list':
        print('Reading steam list')
        read_games_list()
    else:
        get_entry(message.content.lower())

client.run(token)