from operator import contains
import string
import discord
from discord.ext import commands, tasks
from Config.config import discord_config
from steam import *
import re
from enum import Enum
import time
from datetime import date, datetime, timedelta
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
    # TODO make 'delete' and 'add' fucntions take regex to grab everything in the quotes.
    # This will throw all logic into functions to only have a function call here.
    elif 'delete' in user_input:
        game_in_input = re.split('"',user_input)
        game_name = game_in_input[1]
        entry = get_entry(game_name.lower())
        await handle_delete_game_request(message,entry)
    elif 'add' in user_input:
        game_in_input = re.split('"',user_input)
        game_name = game_in_input[1]
        entry = get_entry(game_name.lower())
        await handle_add_game_request(message, entry)
    elif user_input == 'friday':
        await friday_reminder()
    elif 'clear' in user_input:
        clear_wishlist()
        await message.reply ('The wishlist has been cleared.')
    elif 'day' in user_input: 
        await daily_wishlist_check()
    elif 'games' in user_input.lower(): #Allow user to list the games we are tracking
        await handle_list_game_request(message)

async def handle_add_game_request(message, entry):
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
            reply = (f'**{entry["name"].capitalize()}** was successfully added to our tracking list.\nsteam://openurl/https://store.steampowered.com/app/{entry["appid"]}\n')
    else:
        reply = 'This game doesn\'t exist on steam, try gamepass.'
    await message.reply (reply)

# Function to handle client side of a delete game request, builds reply with list_games_for_reply function
async def handle_delete_game_request(message,entry):
    reply = ''
    if entry != None:
        status = delete_game((entry["appid"], entry["name"]))
        output = games_were_tracking_string()
        if status == True:
            reply = f'**{entry["name"]}** was successfully deleted from our tracking list.\n{output}'
        else:
            reply = f'There was a problem deleting the game, are we tracking it?\n{output}'
    await message.reply (reply)

# Essentially list_games but without the reply at the bottom, lets us use output to build into other strings
def list_games_for_reply():
    formatted_games = ''
    games = get_games()
    print(games)
    for key in games: 
        game_title = games[key]['name']
        game_url = f'steam://openurl/https://store.steampowered.com/app/{key}'
        formatted_games = formatted_games + f'\n•\t{game_title} - {game_url}'
    return formatted_games

# Get all games we are tracking and reply to the author of the message. 
async def handle_list_game_request(message):
    output = games_were_tracking_string()
    reply = f"{output}"
    await message.reply(reply)

# handle_list_game_request but with a return to add to other things.
def games_were_tracking_string():
    output = list_games_for_reply()
    games_were_tracking_string = f'----------------------------\nGames we\'re tracking:\n{output}\n----------------------------'
    return games_were_tracking_string

async def debug_day_request(message):
    games = update_game_sales()
    reply = ''
    for key in games:
        formatted_game = format_game_for_reply(games[key])
        reply = f'{reply}\n{formatted_game}'
    await message.reply(f"A day happened {reply}")

def format_game_for_reply(game, game_id):
    url = f'steam://openurl/https://store.steampowered.com/app/{game_id}'
    name = game['name']
    discounted_percent = game['price_overview']["discount_percent"]
    discounted_price = game['price_overview']['final_formatted']
    formatted_discounted_price = discounted_price.replace('CDN$ ','$')
    formatted_game = f'**{name}** is on sale for {formatted_discounted_price} - {discounted_percent}% off!\n\t  {url}\n'
    return formatted_game

def format_games_for_reply(games):
    reply = ''
    for key in games:
        formatted_game = f'•\t{format_game_for_reply(games[key],key)}'
        reply += f'{formatted_game}\n'
    return reply

@tasks.loop(hours=24)
async def daily_wishlist_check():
    new_sales, sales = update_game_sales()
    line = '------------------------------------------------------------------'
    toppa_string = '**TOPPA DA MORNIN!**'
    centered_toppa_string = center_string(toppa_string,line)
    centered_date_string = center_string(date_as_string(),centered_toppa_string)
    sales_start_string = 'These sales started **today**:\n'
    reply = f'{line}\n{centered_toppa_string}\n{centered_date_string}\n{line}\n{sales_start_string}\n'
    if new_sales != {}:
        new_sales_formatted = f'{format_games_for_reply(new_sales)}'
        sales_formatted = f'{format_games_for_reply(sales)}'
        print('sales formatted is', sales_formatted)
        if sales_formatted != '':
            sales_formatted = f'------------------------------------------------------------------\nThese games are **still on sale**:\n\n{sales_formatted}'
        channel = client.get_channel(discord_config["channel_id"])
        reply += f'{new_sales_formatted}{sales_formatted}{line}'
        await channel.send(reply)

# Not perfect, still needs to played with manually to get nice centering but its pretty good
# I think because characters aren't all the same length visually (that's why + 8)
def center_string(string_to_center, string_to_center_to):
    string_centered = string_to_center.center(len(string_to_center_to) + 8 )
    return string_centered

# Nearly works? Not sure why it doesn't tbh
# Not called anywhere yet.
def remove_format_to_center_string(string_to_manipulate):
    targets = ['*','_']
    removed_characters_string = ''
    print('String to manipulate is:', string_to_manipulate)
    if any(target in string_to_manipulate for target in targets):
        for target in targets:
            print('Target is:', target)
            print('Type of target is:', type(target))
            print('Type of string to manipulate is:', type(string_to_manipulate))
            removed_characters_string = string_to_manipulate.replace(target, '')
    # If check fails you don't need this function
    else:
        return string_to_manipulate
    print('removed_characters_string is:', removed_characters_string)
    return removed_characters_string

def date_as_string():
    today = date.today()
    date_string = today.strftime('%B %d, %Y')
    return date_string

@daily_wishlist_check.before_loop
async def configure_daily_wishlist_check():
    hour = 10
    minute = 00
    await client.wait_until_ready()
    now = datetime.now()
    future = datetime(now.year, now.month, now.day, hour, minute)
    if now.hour > hour or (now.hour == hour and now.minute > minute): 
        future += timedelta(days=1)
    print(f'delay to start wishlist check loop: {future-now}')
    await asyncio.sleep((future-now).seconds)

@tasks.loop(hours=168) # 7 day cycle 
async def friday_reminder():
    channel = client.get_channel(discord_config["channel_id"])
    message = friday_reminder_formatter()
    await channel.send(message)

@friday_reminder.before_loop
async def configure_friday_check():
    hour = 20
    minute = 00
    friday = 4
    await client.wait_until_ready()
    now = datetime.now()
    future = datetime(now.year, now.month, now.day, hour, minute)
    days = (friday - now.weekday()) % 7
    if now.weekday() == friday and (now.hour > hour or (now.hour == hour and now.minute > minute)): 
        days += 7
    future += timedelta(days=days)
    print(f'delay to start friday check loop: {future-now}')
    await asyncio.sleep((future-now).seconds)

# Made it a function to better compartmentalize it, organization really.
def friday_reminder_formatter():
    games_on_sale = get_game_sales()
    formatted_games_string = format_games_for_reply(games_on_sale)
    phrase = friday_phrase_randomizer()
    date = date_as_string()
    date_string = center_string(date,phrase)
    line = '------------------------------------------------------------------'
    message = f'{line}\n{phrase}\n\n{formatted_games_string}{line}'
    return (message)

load_games() 
daily_wishlist_check.start()
friday_reminder.start()
client.run(token)