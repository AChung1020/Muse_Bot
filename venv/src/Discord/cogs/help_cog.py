import discord
from discord.ext import commands


class help_cog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.help_message = """
        ```
        General Commands:
        /help - list of commands if you forget you baka ~~~
        /p or /play [URL] or [search words] - play a song!
        /q or /queue - see whats playing next!
        /skip - skip song
        /remove [number in queue] - removes queued song
        /clear - clear all songs
        /dc - kick me from the channel onii chan ~~~
        /pause - pauses song
        /resume - you get the point
        /now_playing or /np - shows what is currently playing

        To Start, use /play with a link from youtube
        (VIDEO SHOULD NOT BE IN A PLAYLIST)
        or search keywords
        ```
        """
        self.text_channel_text = []

    # @commands.Cog.listener()
    # async def on_ready(self):  # specifies that this function will run whenever music bot come online(listener)
    #     for guild in self.bot.guilds:
    #         for channel in guild.text_channels:
    #             self.text_channel_text.append(channel)
    #
    #     await self.send_to_all(self.help_message)

    async def send_to_all(self, msg):
        for text_channel in self.text_channel_text:
            await text_channel.send(msg)

    @commands.command(name='help', help='Displays all available commands')
    async def help(self, ctx):
        await ctx.send(self.help_message)


async def setup(bot):
    await bot.add_cog(help_cog(bot))


