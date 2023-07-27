import discord
import asyncio
from discord.ext import commands
from Database.RetAndUpdateFunctions import find_document, music_sessions


# TODO: Connect spotify API, add song titles to queue from a playlist, or add songs to a playlist
# TODO: Make queue look better, get the album cover or something to display
# TODO: fix commands on this apge to align with database

class BasicCommands_cog(commands.Cog):
    def __init__(self, bot):
        self.update_lock = asyncio.Lock()
        self.bot = bot

    # pauses song
    @commands.command(name="pause", aliases=["stop"], help="Pauses ")
    async def pause(self, ctx, *args):
        document = find_document(ctx.message.guild.id)
        vc = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        if document['is_Playing']:  # if playing pause
            document['is_Playing'] = False
            document['is_Paused'] = True
            vc.pause()
        elif document['is_Paused']:  # if paused, resume
            document['is_Playing'] = True
            document['is_Paused'] = False
            vc.resume()

        try:
            collection = music_sessions()
            collection.update_one({"_id": ctx.message.guild.id}, {"$set": document})
            print("Update successful")
        except Exception as e:
            print("Error during update:", e)

    # resumes playing song
    @commands.command(name="resume", aliases=["r"], help="Resumes playing the current song")
    async def resume(self, ctx, *args):

        document = find_document(ctx.message.guild.id)
        vc = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        if document['is_Playing']:  # if playing pause
            document['is_Playing'] = False
            document['is_Paused'] = True
            vc.pause()
        elif document['is_Paused']:  # if paused, resume
            document['is_Playing'] = True
            document['is_Paused'] = False
            vc.resume()

        try:
            collection = music_sessions()
            collection.update_one({"_id": ctx.message.guild.id}, {"$set": document})
            print("Update successful")
        except Exception as e:
            print("Error during update:", e)

    # shows queue
    @commands.command(name="queue", aliases=["q"], help="Lists current songs in the queue")
    async def queue(self, ctx):
        server_ID = ctx.message.guild.id
        document = find_document(server_ID)
        music_queue = document.get("music_queue", [])

        retval = ""
        for i in range(0, len(music_queue)):
            if i > 5:
                break
            retval += str(i) + '. ' + music_queue[i]['title'] + '\n'

        if not retval:
            await ctx.send("There are no songs in the queue!")
        else:
            return await ctx.send(retval)

    @commands.command(name="clear", aliases=["c"], help="Removes all songs")
    async def clear(self, ctx, *args):
        server_ID = ctx.message.guild.id
        document = find_document(server_ID)
        vc = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        music_queue = document.get("music_queue", [])
        if vc is not None and document['is_Playing'] and (len(music_queue) != 0):
            vc.stop()
            document['is_Playing'] = False
            document['is_Paused'] = False
            document['current_track'] = None
            document['current_person'] = None
            music_queue.clear()
            document["music_queue"] = music_queue

            try:
                collection = music_sessions()
                collection.update_one({"_id": ctx.message.guild.id}, {"$set": document})
                print("Update successful")
            except Exception as e:
                print("Error during update:", e)

            await ctx.send("cleared music queue!!!")
        else:
            await ctx.send("There is nothing to clear!!!")

    # need fix
    @commands.command(name="disconnect", aliases=["dc"], help="Forces bot to leave the vc")
    async def kick(self, ctx):
        server_ID = ctx.message.guild.id
        document = find_document(server_ID)
        vc = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        if vc is not None:
            document['is_Playing'] = False
            document['is_Paused'] = False
            document['current_track'] = None
            document['current_person'] = None
            document['vc'] = False

            try:
                collection = music_sessions()
                collection.update_one({"_id": ctx.message.guild.id}, {"$set": document})
                print("Update successful")
            except Exception as e:
                print("Error during update:", e)

            await vc.disconnect()
            await ctx.send("bot kicked!!!")

        else:
            ctx.send("Add me to the voice channel!!!")


async def setup(bot):
    await bot.add_cog(BasicCommands_cog(bot))
