from operator import contains
import string
import discord
from discord.ext import commands, tasks
from Config.config import discord_config
from steam import *
from state import ClientStateManager
import re
from enum import Enum
import time
from datetime import date, datetime, timedelta
import asyncio

client = discord.Client()
token = discord_config["token"]
client_state = ClientStateManager()
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
    # Telling bot which channel to listen to
    if message.channel.name != discord_config['channel']: 
        return

    user_input = message.content.lower()
    input_parts = re.split(' ', user_input)
    command = input_parts[0].lower()
    clear_matching_games = True
    print(f'input: {user_input}')
    if len(input_parts) > 1 and ('"' in user_input): #meaning a quote is present
        game_name = re.split('"', user_input)[1]
        command = input_parts[0].lower()
        if command == 'add':
            clear_matching_games = False
            await handle_add_game_request(message, game_name)
        elif command == 'delete':
            entry = get_entry(game_name.lower())
            await handle_delete_game_request(message,entry)
    elif len(input_parts) == 2:
        index = input_parts[1]
        if command == 'add' and index.isnumeric():
            clear_matching_games = False
            await handle_add_game_request_from_match(message, index)
    elif len(input_parts) == 1: 
        if command == 'fetch': 
            print('Fetching steam list')
            fetch_games_mapping()
        elif command == 'games_m':
            log_wishlist_memory()
        elif command == 'games': #Allow user to list the games we are tracking
            await handle_list_game_request(message)
        elif command == 'sales':
            await list_sales(message)
        elif command == 'yes':
            await handle_add_game_request_from_match(message, '0')
        # elif command == 'clear':
        #     clear_wishlist()
        #     await message.reply ('The wishlist has been cleared.')
        elif command == 'help':
            am = discord.AllowedMentions(users = False, everyone = False, roles = False, replied_user = True)
            await message.reply("""----------------------------------------------------------
Hello! I am your customizeable Steam sales tracker!
Use me to add games to your server's wishlist and I will let you know when they go on sale so the lads, and lassies never miss a deal 😎.

Here are some prompts for you to use:
add "game" - will add this game to the wishlist and I will begin tracking it. (full game name must be writtin in quotations)
delete "game" - will delete this game from the wishlist and I will no longer track it. (full game name must be written in quotations)
games - will show you the list of games I am tracking and if they are on sale.
sales - will show you all the games currently on sale from your wishlist.

Every Friday I will be posting a message with games from your wishlist that are on sale.
Every day that a new game from your wishlist goes on sale, I will let you know.

That's pretty much it, if you have questions message <@375852152544952322> or <@650136117227683877>.

Love you
 - Steam Tracker
----------------------------------------------------------""", allowed_mentions = am)
    if clear_matching_games == True: 
        client_state.clear_game_matches()

async def handle_add_game_request_from_match(message, index_string):
    index = int(index_string) - 1
    game_matches = client_state.get_game_matches()
    if len(game_matches) == 0:
        print('game matches is empty')
        return
    entry = game_matches[index]
    print(entry)
    added_game_result = add_game((entry["appid"], entry["name"]))
    status = added_game_result[0]
    print(status)
    if status == GameAddStatus.EXISTS:
        reply = 'Game already being tracked'
    elif status ==  GameAddStatus.FREE_GAME:
        reply = 'This game is free'
    else:
        reply = (f'**{entry["name"].title()}** was successfully added to our tracking list.\nsteam://openurl/https://store.steampowered.com/app/{entry["appid"]}\n')
    await message.reply (reply)


async def handle_add_game_request(message, game_name):
    reply = ''
    matching_titles = get_entries(game_name.lower())
    print(matching_titles)
    if len(matching_titles) == 1:
        if matching_titles[0]['name'].lower() == game_name.lower(): #exact match
            entry = matching_titles[0]
            added_game_result = add_game((entry["appid"], entry["name"]))
            status = added_game_result[0]
            client_state.clear_game_matches()
            print(status)
            if status == GameAddStatus.EXISTS:
                reply = 'Game already being tracked'
            elif status ==  GameAddStatus.FREE_GAME:
                reply = 'This game is free'
            else:
                reply = (f'**{entry["name"].title()}** was successfully added to our tracking list.\nsteam://openurl/https://store.steampowered.com/app/{entry["appid"]}\n')
        else: # Not exact match
            reply = f'Did you mean **{matching_titles[0]["name"]}**? Write "Yes" to confirm'
            client_state.store_game_matches(matching_titles)
    elif len(matching_titles) > 1:
        reply = 'There\'s no game with that exact title, did you mean one of these?'
        store_matches = True
        for index, app in enumerate(matching_titles):
            reply = reply + f'\n{index + 1}: {app["name"]}'
            if len(reply) > 2000: 
                reply = f'There are {len(matching_titles)} apps that contain that title, can you be more specific?'
                store_matches = False
                break
        if store_matches: 
            client_state.store_game_matches(matching_titles)
            reply = reply + f'\n\nType "add #" to add the specific title. We\'ll keep track of this list for 2 minutes.'
    else:
        reply = 'This game doesn\'t exist on steam, try gamepass.'
    await message.reply (reply)

# Function to handle client side of a delete game request, builds reply with list_games_for_reply function
async def handle_delete_game_request(message,entry):
    reply = ''
    if entry != None:
        status = delete_game((entry["appid"], entry["name"]))
        if status == True:
            reply = f'**{entry["name"].title()}** was successfully deleted from our tracking list.'
    else:
        output = games_were_tracking_string()
        reply = f'There was a problem deleting the game, are we tracking it?\n{output}'
    await message.reply (reply)

# Essentially list_games but without the reply at the bottom, lets us use output to build into other strings
def list_games_for_reply():
    formatted_games = ''
    formatted_on_sale_games = ''
    formatted_not_on_sale_games = ''
    games = get_games()

    for key in games: 
        game_title = games[key]['name']
        game_url = f'steam://openurl/https://store.steampowered.com/app/{key}'
        discounted_percent = games[key]['price_overview']['discount_percent']
        discounted_price = games[key]['price_overview']['final_formatted'] 
        formatted_discounted_price = discounted_price.replace('CDN$ ','$')
        full_price = games[key]['price_overview']['final_formatted']
        formatted_full_price = full_price.replace('CDN$ ','$')
        if discounted_percent > 0:
            formatted_on_sale_games += f'\n•\t**{game_title.title()}** is on sale for {formatted_discounted_price} - {discounted_percent}% off!\n\t  {game_url}'
        else:
            formatted_not_on_sale_games += f'\n•\t**{game_title.title()}** is full price - {formatted_full_price}\n\t  {game_url}'
    formatted_games += f'{formatted_on_sale_games}{formatted_not_on_sale_games}'
    return formatted_games

# Essentially list_games_for_reply but only grabs sale data, called when user_input == sales
async def list_sales(message):
    line_string = '----------------------------'
    formatted_sales = f'{line_string}\nGames on sale from your wishlist:\n'
    games = get_games()
    discount_percent_list = []
    # Make a list of the values of discounted percent to then run through a check to see if any of them are on sale.
    for key in games:
        discount_percent_list.append(games[key]['price_overview']['discount_percent'])
    # Here's our check.
    any_sales_check = any(i > 0 for i in discount_percent_list)
    if any_sales_check == True:
        for key in games:
            game_title = games[key]['name']
            game_url = f'steam://openurl/https://store.steampowered.com/app/{key}'
            discounted_price = games[key]['price_overview']['final_formatted'] 
            formatted_discounted_price = discounted_price.replace('CDN$ ','$')
            discounted_percent = games[key]['price_overview']['discount_percent']
            if discounted_percent > 0:
                formatted_sales += f'\n•\t**{game_title}** is on sale for {formatted_discounted_price} - {discounted_percent}% off!\n\t  {game_url}'
    else:
        formatted_sales = f'{line_string}\nNo games from your wishlist are currently on sale :sob:.'
    formatted_sales += f'\n{line_string}'
    await message.reply(formatted_sales)

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

def format_game_for_reply(game, game_id):
    url = f'steam://openurl/https://store.steampowered.com/app/{game_id}'
    name = game['name']
    discounted_percent = game['price_overview']['discount_percent']
    discounted_price = game['price_overview']['final_formatted'] 
    formatted_discounted_price = discounted_price.replace('CDN$ ','$')
    formatted_game = f'**{name}** is on sale for {formatted_discounted_price} - {discounted_percent}% off!\n\t  {url}'
    return formatted_game

def format_games_for_reply(games):
    reply = ''
    for key in games:
        formatted_game = f'•\t{format_game_for_reply(games[key],key)}'
        reply += f'{formatted_game}\n'
    return reply

# Not perfect, still needs to played with manually to get nice centering but its pretty good
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

# Made it a function to better compartmentalize it, organization really.
def friday_reminder_formatter():
    games_on_sale = get_game_sales()
    if games_on_sale == {}:
        return None
    formatted_games_string = format_games_for_reply(games_on_sale)
    phrase = friday_phrase_randomizer()
    date = date_as_string()
    line = '------------------------------------------------------------------'
    message = f'{line}\n{phrase}\n\n{formatted_games_string}{line}'
    return (message)

@tasks.loop(hours=24)
async def daily_wishlist_check():
    new_sales, sales = update_game_sales()
    line = '----------------------------------------------------------'
    toppa_string = '**TOPPA DA MORNIN!**'
    at_here_string = '@everyone'
    centered_toppa_string = center_string(toppa_string,line)
    centered_date_string = center_string(date_as_string(),centered_toppa_string)
    centered_at_here_string = center_string(at_here_string,centered_date_string)
    sales_start_string = 'These sales started **today**:\n'
    reply = f'{line}\n{centered_toppa_string}\n{centered_date_string}\n{centered_at_here_string}\n{line}\n{sales_start_string}\n'
    if new_sales != {}:
        new_sales_formatted = f'{format_games_for_reply(new_sales)}'
        sales_formatted = f'{format_games_for_reply(sales)}'
        print('sales formatted is', sales_formatted)
        if sales_formatted != '':
            sales_formatted = f'{line}\nThese games are **still on sale**:\n\n{sales_formatted}'
        channel = client.get_channel(discord_config["channel_id"])
        reply += f'{new_sales_formatted}{sales_formatted}{line}'
        await channel.send(reply)

@daily_wishlist_check.before_loop
async def configure_daily_wishlist_check():
    hour = 10
    minute = 00
    await client.wait_until_ready()
    now = datetime.now()
    future = datetime(now.year, now.month, now.day, hour, minute)
    if now.hour > hour or (now.hour == hour and now.minute >= minute): 
        future += timedelta(days=1)
    print(f'delay to start wishlist check loop: {future-now}')
    await asyncio.sleep((future-now).seconds)

@tasks.loop(hours=168) # 7 day cycle 
async def friday_reminder():
    channel = client.get_channel(discord_config["channel_id"])
    message = friday_reminder_formatter()
    if message != None: 
        await channel.send(message)

@friday_reminder.before_loop
async def configure_friday_check():
    hour = 17
    minute = 30
    friday = 4
    await client.wait_until_ready()
    now = datetime.now()
    future = datetime(now.year, now.month, now.day, hour, minute)
    days = ((friday - now.weekday()) % 7)
    if now.weekday() == friday and (now.hour > hour or (now.hour == hour and now.minute >= minute)): 
        days += 7
    future += timedelta(days=days)
    print(f'delay to start friday check loop: {(future-now)}')
    await asyncio.sleep((future-now).total_seconds())

load_games() 
daily_wishlist_check.start()
friday_reminder.start()
client.run(token)