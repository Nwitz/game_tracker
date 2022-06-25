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
# this is the password for the bot to enter the discord server, you have to give it access to the server on the discord developer portal
client_state = ClientStateManager()


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
    print(f'input: {user_input}')
    if len(input_parts) > 1 and ('"' in user_input): #meaning a quote is present
        game_name = re.split('"', user_input)[1]
        command = input_parts[0].lower()
        if command == 'add':
            await handle_add_game_request(message, game_name)
        elif command == 'delete':
            clear_matching_games = False
            await handle_delete_game_request(message, game_name)

    elif len(input_parts) == 2:
        index = input_parts[1]
        if command == 'add' and index.isnumeric():
            await handle_add_game_request_from_match(message, index)
        if command =='delete' and index.isnumeric():
            clear_matching_games = False
            await handle_delete_game_request_from_match(message, index)
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

async def handle_add_game_request_from_match(message, index_string):
    index = int(index_string) - 1
    game_matches = client_state.get_game_matches()
    if len(game_matches) == 0:
        print('game matches is empty')
        return
    entry = game_matches[index]
    added_game_result = add_game((entry["appid"], entry["name"]))
    status = added_game_result[0]
    if status == GameAddStatus.EXISTS:
        reply = 'Game already being tracked'
    elif status ==  GameAddStatus.FREE_GAME:
        reply = 'This game is free'
    else:
        price_reply = price_formatter(entry["appid"])
        reply = (f'**{entry["name"]}** was successfully added to your wishlist {price_reply}\nsteam://openurl/https://store.steampowered.com/app/{entry["appid"]}\n')
    await message.reply (reply)


async def handle_add_game_request(message, game_name):
    reply = ''
    matching_titles = get_entries_from_games_map(game_name.lower())
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
                price_reply = price_formatter(entry["appid"])
                reply = (f'**{entry["name"]}** was successfully added to your wishlist {price_reply}\nsteam://openurl/https://store.steampowered.com/app/{entry["appid"]}\n')
        else: # Not exact match
            reply = f'Did you mean **{matching_titles[0]["name"]}**? Write "Yes" to confirm'
            client_state.store_game_matches(matching_titles)
    elif len(matching_titles) > 1:
        reply = 'There\'s no game with that exact title, did you mean one of these?\n'
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

async def handle_delete_game_request_from_match(message, index_string):
    index = int(index_string) - 1
    game_matches = client_state.get_game_matches()
    if len(game_matches) == 0:
        print('game matches is empty')
        return
    game_tupple = game_matches[index]
    deleted_game_result = delete_game(game_tupple)
    print('Deleted game result is:', deleted_game_result)
    if deleted_game_result == True:
        reply = f'**{game_tupple[1]}** was successfully deleted from your wishlist.'
    else:
        reply = f'There was an error deleting **{game_tupple[1]}**, it was not successfully removed from your wishlist.'
    await message.reply(reply)

# Function to handle client side of a delete game request, builds reply with list_games_for_reply function
async def handle_delete_game_request(message, game_name):
    reply = ''
    matches = get_entries_from_wishlist(game_name)
    if len(matches) == 1:
        # Working with a list with a single tupple in it from matches
        tupple = (matches[0][0], matches[0][1])
        status = delete_game(tupple)
        game_title = matches[0][1]
        client_state.clear_game_matches()
        if status == True:
            reply = f'**{game_title}** was successfully deleted from your wishlist.'
        else: # Not exact match
            reply = f'Did you mean **{game_title}**? Write "Yes" to confirm'
            client_state.store_game_matches(matches)
    elif len(matches) > 1:

        # working with a list with multiple tupples in it, iterate through list of tupples which have this format (appid, app name)
        reply = 'You are not tracking a game with that exact title, did you mean one of these?\n'
        store_matches = True
        for index, app in enumerate(matches):
            game_title = app[1]
            reply += f'\n{index + 1}: {game_title}'
            print('app is:', app)
            if len(reply) > 2000: 
                reply = f'There are {len(matches)} apps that contain that title, can you be more specific?'
                store_matches = False
                break
        if store_matches:
            client_state.store_game_matches(matches)
            reply = reply + f'\n\nType "delete #" to delete the specific title. We\'ll keep track of this list for 2 minutes.'
    else:
        reply = 'This game doesn\'t exist on steam, try gamepass.'
    await message.reply (reply)

# Formatting function for determining if a game is on sale and giving back a string to add to a reply.
def price_formatter(queried_key):
    game_info = get_complete_info_for_game(queried_key)
    discounted_percent = game_info['price_overview']['discount_percent']
    game_price = game_info['price_overview']['final_formatted']
    formatted_game_price = game_price.replace('CDN$ ', '$')
    if discounted_percent > 0:
        price_reply = f'and is **currently on sale** for {formatted_game_price} - {discounted_percent}% off!'
    else:
        price_reply = f'and is currently full price at {formatted_game_price}.'
    return price_reply

# Essentially list_games but without the reply at the bottom, lets us use output to build into other strings
def list_games_for_reply():
    formatted_games = ''
    formatted_on_sale_games = ''
    formatted_not_on_sale_games = ''
    games = get_wishlist_games()

    for key in games: 
        game_title = games[key]['name']
        game_url = f'steam://openurl/https://store.steampowered.com/app/{key}'
        discounted_percent = games[key]['price_overview']['discount_percent']
        discounted_price = games[key]['price_overview']['final_formatted'] 
        formatted_discounted_price = discounted_price.replace('CDN$ ','$')
        full_price = games[key]['price_overview']['final_formatted']
        formatted_full_price = full_price.replace('CDN$ ','$')
        if discounted_percent > 0:
            formatted_on_sale_games += f'\n•\t**{game_title}** is currently on sale for {formatted_discounted_price} - {discounted_percent}% off!\n\t  {game_url}'
        else:
            formatted_not_on_sale_games += f'\n•\t**{game_title}** is full price - {formatted_full_price}\n\t  {game_url}'
    formatted_games += f'{formatted_on_sale_games}{formatted_not_on_sale_games}'
    return formatted_games

# Essentially list_games_for_reply but only grabs sale data, called when user_input == sales
async def list_sales(message):
    line_string = '----------------------------'
    formatted_sales = f'{line_string}\nGames on sale from your wishlist:\n'
    games = get_wishlist_games()
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

# Creates reply string to use for Thursday bi-weekly(?) check of steam specials.
def format_specials_for_reply(json_object):
    # Note: using len(json_objects) and then having a clause below it to omit some objects if they dont match the currency condition is probably a bad idea.
    expiration = datetime.fromtimestamp(json_object[0]['discount_expiration'])
    pretty_date = expiration.strftime('%B %d')
    pretty_time = expiration.strftime('%I:%M %p')
    formatted_expiration = f'                 Expiring {pretty_date} - {pretty_time}'
    # This isn't a safe way to find out when most of the games are expiring
    expiration_int = json_object[0]['discount_expiration']

    reply_string =''
    line = '----------------------------------------------------------'
    centered_specials_string = '                          **STEAM SPECIALS!**'
    centered_expiration = f'  {formatted_expiration}'
    centered_at_here_string = f'                                @ everyone'
    begining_reply_string = f'{line}\n{centered_specials_string}\n{centered_expiration}\n{centered_at_here_string}\n{line}\n'
    reply_string += begining_reply_string
    for game in json_object:
        if game['currency'] == 'CAD':
            name = game['name']
            discounted_percent = game['discount_percent']
            unformatted_price = str(game['final_price'])
            # This next line will work unless steam decides to put 3 decimal places in their prices. I pray they dont
            formatted_price =f'${unformatted_price[:-2]}.{unformatted_price[-2:]}'
            app_id = game['id']
            url = f'steam://openurl/https://store.steampowered.com/app/{app_id}'
            specific_expiration = datetime.fromtimestamp(game['discount_expiration'])
            formatted_s_expiration = specific_expiration.strftime('%B %d %I:%M %p')
            #In case some games have a different expiration than most.
            if game['discount_expiration'] != expiration_int:
                reply_string += f'•\t**{name}** is on sale for {formatted_price} - {discounted_percent}% off until {formatted_s_expiration}!\n\t  {url}\n'
            else:
                reply_string += f'•\t**{name}** is on sale for {formatted_price} - {discounted_percent}% off!\n\t  {url}\n'
    reply_string += f'{line}'
    return (reply_string)

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
    fetch_games_mapping()
    if message != None: 
        await channel.send(message)

# TODO get this thursday check to happen when the sales change, we have an epoch timestamp object we could use
# Also figure out how often this sale catagory refreshes, pretty sure it's every 2 weeks
@tasks.loop(hours=336)
async def thursday_sales():
    channel = client.get_channel(discord_config["channel_id"])
    specials_json = fetch_specials()
    message = format_specials_for_reply(specials_json)
    await channel.send(message)

@thursday_sales.before_loop
async def configure_thursday_sales():
    hour = 20
    minute = 00
    thursday = 3
    await client.wait_until_ready()
    now = datetime.now()
    future = datetime(now.year, now.month, now.day, hour, minute)
    days = ((thursday - now.weekday()) % 7)
    if now.weekday() == thursday and (now.hour > hour or (now.hour == hour and now.minute >= minute)): 
        days += 7
        future += timedelta(days=days)
    print(f'delay to start thursday sales loop: {(future-now)}')
    await asyncio.sleep((future-now).total_seconds())

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
thursday_sales.start()
client.run(token)