import pymongo
import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv
from MongoDB import connect_database

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.voice_states = True

bot = commands.Bot(command_prefix='/', intents=intents, help_command=None)


@bot.event
async def on_ready():
    print("Bot is ready")
    activity = discord.Activity(type=discord.ActivityType.playing, name="TESTING! DON'T USE")
    await bot.change_presence(activity=activity)


async def load():
    for filename in os.listdir("Discord/cogs"):
        if filename.endswith(".py"):
            await bot.load_extension(f"Discord.cogs.{filename[:-3]}")
            # use dots for directories no / for this^^


async def main():
    connect_database.get_mongo_client()

    async with bot:
        await load()
        await bot.start(os.getenv("DISCORD_TOKEN"))

    # client.close()

asyncio.run(main())


