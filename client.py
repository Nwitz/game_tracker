import discord
from Config.config import discord_config
from steam import *
import re
from enum import Enum

client = discord.Client()
token = discord_config["token"]
#this is the password for the bot to enter the discord server, you have to give it access to the server on the discord developer portal

@client.event
async def on_ready(): #called once after bot is started and Discord channel opens connection.
    print('---------------------------------------------')
    print('We have logged in as {0.user}'.format(client))
    print('---------------------------------------------')
    load_games()  #Once bot is connected, read games from file
    return

@client.event
async def on_message(message):

    # Break so bot doesn't respond to itself
    if message.author == client.user:
        return

    #reading user input
    if message.channel.name != discord_config['channel']: 
        return

    user_input = message.content.lower()

    # Filtering out message to find out what to do with it.
    if user_input == 'fetch': 
        print('Fetching steam list')
        fetch_games_mapping()
    elif user_input == 'list':
        print('Reading steam list')
        read_games_mapping()
    elif user_input == 'games_m':
        log_wishlist_memory()
    elif 'delete' in user_input:
        game_in_input = re.split('"',user_input)
        game_name = game_in_input[1]
        entry = get_entry(game_name.lower())
        if game_name != None:
            await handle_delete_game_request(message,entry)
    elif 'clear' in user_input: 
        clear_wishlist()
    elif 'games' in user_input.lower(): #Allow user to list the games we are tracking
        await handle_list_game_request(message)
    else: #If message doesn't match any of the previous checks, add game to list
        await handle_add_game_request(message)

async def handle_add_game_request(message):
    #If message doesn't match any of the previous checks, add game to list
    entry = get_entry(message.content.lower())
    print(f'The entry to be added is {entry}.')
    reply = ''
    if entry != None:
        added_game_result = add_game((entry["appid"], entry["name"]))
        status = added_game_result[0]
        print(status)
        if status == GameAddStatus.EXISTS:
            reply = 'Game already being tracked'
        elif status ==  GameAddStatus.FREE_GAME:
            reply = 'This game is free'
        else:
            output = list_games_for_reply()
            reply = (f'Success! {added_game_result[1]}\nsteam://openurl/https://store.steampowered.com/app/{entry["appid"]}\n {output}')
    else:
        reply = 'The game doesn\'t exist on steam, try gamepass'
    await message.reply (reply)

# Function to handle client side of a delete game request, builds reply with list_games_for_reply function
async def handle_delete_game_request(message,entry):
    print(f'Entering handle_games_request function\nThe entry to be deleted is {entry}.')
    reply = ''
    if entry != None:
        status = delete_game((entry["appid"], entry["name"]))
        output = list_games_for_reply()
        if status == True:
            reply = f'The game was successfully deleted from the tracking list\n{output}'
        else:
            reply = f'There was a problem deleting the game, are we tracking it?\n{output}'
    await message.reply (reply)

# Essentially list_games but without the reply at the bottom, lets us use output to build into other strings
def list_games_for_reply():
    games = get_game_titles()
    output = ""
    for count, game in enumerate(games, start=1):
        output = output + f'\n{count}: {game}'
    return output

# Get all games we are tracking and reply to the author of the message. 
async def handle_list_game_request(message):
    print('we got here')
    games_list = list_games_for_reply()
    reply = f"Games we're tracking:{games_list}"
    await message.reply(reply)


client.run(token)