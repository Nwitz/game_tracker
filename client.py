import discord

client = discord.Client()
token = 'OTM0ODM2NzAzMzkzMzUzNzcx.Ye14hg.LaW_DkWQWKVSXJqWWSB9bhcNrVU'
#this is the password for the bot to enter the discord server, you have to give it access to the server on the discord developer portal


@client.event
async def on_ready():
    print('---------------------------------------------')
    print('We have logged in as {0.user}'.format(client))
    print('---------------------------------------------')
    return

client.run(token)