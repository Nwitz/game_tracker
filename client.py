import discord
from discord.ext import commands, tasks
from Config.config import discord_config
from steam import *
import re
from enum import Enum
import time
from datetime import datetime, timedelta
import asyncio

client = discord.Client()
token = discord_config["token"]
#this is the password for the bot to enter the discord server, you have to give it access to the server on the discord developer portal

@client.event
async def on_ready(): #called once after bot is started and Discord channel opens connection.
    print('---------------------------------------------')
    print('We have logged in as {0.user}'.format(client))
    print('---------------------------------------------')
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
    elif 'day' in user_input: 
        await daily_wishlist_check()
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
    games_list = list_games_for_reply()
    reply = f"Games we're tracking:{games_list}"
    await message.reply(reply)

async def debug_day_request(message):
    results = check_game_sales()
    reply = ''
    for key in results:
        formatted_game = format_game_for_reply(results[key])
        reply = f'{reply}\n{formatted_game}'
    await message.reply(f"A day happened {reply}")

def format_game_for_reply(game):
    # TODO add url, need to bring in app id.
    # TODO get Noah's oppinion on .replace(), seems unstable
    name = game['name']
    discounted_percent = game['price_overview']["discount_percent"]
    discounted_price = game['price_overview']['final_formatted']
    formatted_discounted_price = discounted_price.replace('CDN$ ','')
    formatted_game = f'**{name}** is on sale for ${formatted_discounted_price} - {discounted_percent}% off!'
    return formatted_game

@tasks.loop(hours=24)
async def daily_wishlist_check():
    games = check_game_sales()
    channel = client.get_channel(discord_config["channel_id"])
    print(channel)
    print(games)
    await channel.send(games)

@daily_wishlist_check.before_loop
async def configure_daily_wishlist_check():
    print('here')
    hour = 10
    minute = 00
    await client.wait_until_ready()
    now = datetime.now()
    future = datetime(now.year, now.month, now.day, hour, minute)
    print(f'now - hour:{now.hour}, minute:{now.minute}\ntarget - hour:{hour}, minute: {minute}')
    if now.hour > hour or (now.hour == hour and now.minute > minute): 
        print("Going to next day")
        future += timedelta(days=1)
    print(future)
    print(future - now)
    await asyncio.sleep((future-now).seconds)

load_games() 
daily_wishlist_check.start()
client.run(token)