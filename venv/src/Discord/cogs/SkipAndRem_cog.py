import discord
import asyncio
from discord.ext import commands
from Database.RetAndUpdateFunctions import find_document, music_sessions

# TODO: fix remove to align with database
class SkipAndRem_cog(commands.Cog):
    def __init__(self, bot):
        self.update_lock = asyncio.Lock()
        self.bot = bot

    @commands.command(name="skip", aliases=["s"], help="Skips playing the current song")
    async def skip(self, ctx, *args):
        server_ID = ctx.message.guild.id
        document = find_document(server_ID)
        collection = music_sessions()
        vc = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        music_queue = document.get("music_queue", [])

        if vc is not None and document['is_Playing']:  # if in voice channel
            voice_channel = ctx.author.voice.channel
            num_members = len(voice_channel.members) - 1  # account for bot
            num_success_vote = (num_members // 2) + 1

            queue_length = len(music_queue)
            if num_members > 2:
                vc.stop()  # stop playing current song
                document['is_Playing'] = False
                document['is_Paused'] = False

                await ctx.send(f"The song: **__{document['current_track']}__** has been skipped.")
                if queue_length == 0:
                    document['current_track'] = None
                    document['current_person'] = None

                collection.update_one({"_id": server_ID}, {"$set": document})
                await self.play_next(vc, find_document(server_ID), server_ID)  # move next
            elif num_members <= 2:
                message = await ctx.send(
                    f"Should **__{document['current_track']}__** be skipped? 15 seconds to vote")
                await message.add_reaction('\u2705')
                await message.add_reaction('\u274C')

                def check(react, user):
                    return user != self.bot.user and str(react.emoji) in ['\u2705', '\u274C'] and \
                        react.message == message

                try:
                    Check_Count = 0
                    X_Count = 0

                    # while loop runs until all votes counted
                    while True:
                        reaction, _ = await self.bot.wait_for('reaction_add', timeout=15.0, check=check)

                        if str(reaction.emoji) == '\u2705':
                            Check_Count += 1
                        elif str(reaction.emoji) == '\u274C':
                            X_Count += 1

                        total_votes = Check_Count + X_Count
                        if total_votes >= num_members or total_votes >= num_success_vote:
                            break

                    if Check_Count >= num_success_vote:
                        vc.stop()  # stop playing current song
                        document['is_Playing'] = False
                        document['is_Paused'] = False

                        await ctx.send(f"The song: **__{document['current_track']}__** has been skipped.\n"
                                       f" Who put this shit song here? \n"
                                       f"Of course it was {document['current_person']} !")

                        if queue_length == 0:
                            document['current_track'] = None
                            document['current_person'] = None

                        collection.update_one({"_id": server_ID}, {"$set": document})

                        await self.play_next(vc, find_document(server_ID), server_ID)  # move next
                    else:
                        await ctx.send(f"The song: **__{document['current_track']}__** has not been skipped. "
                                       f"Not enough votes.")
                except asyncio.TimeoutError:
                    await ctx.send("No votes were cast within 15 seconds. The song will not be skipped.")
        else:
            await ctx.send("There is nothing to skip!!!")

    @commands.command(name="remove", aliases=["rem"], help="Removes specific song in queue")
    async def remove(self, ctx, *args):
        query = " ".join(args)
        num_queue = int(query)

        if num_queue > len(self.music_queue):
            await ctx.send("Does not exist in queue!!!")

        elif self.vc is not None and self.is_Playing:
            if num_queue <= len(self.music_queue):
                voice_channel = ctx.author.voice.channel
                num_members = len(voice_channel.members) - 1  # account for bot
                num_success_vote = (num_members // 2) + 1

                if num_members <= 2:
                    removed = self.music_queue[num_queue - 1][0]['title']
                    self.music_queue.pop(num_queue - 1)
                    await ctx.send(f"The song: **__{removed}__** was removed from queue!!!")
                elif num_members > 2:
                    removed = self.music_queue[num_queue - 1][0]['title']
                    message = await ctx.send(f"Should **__{removed}__** be removed? 15 seconds to vote")
                    await message.add_reaction('\u2705')
                    await message.add_reaction('\u274C')

                    def check(react, user):
                        return user != self.bot.user and str(react.emoji) in ['\u2705', '\u274C'] and \
                            react.message == message

                    try:
                        Check_Count = 0
                        X_Count = 0

                        # while loop runs until all votes counted
                        while True:
                            reaction, _ = await self.bot.wait_for('reaction_add', timeout=15.0, check=check)

                            if str(reaction.emoji) == '\u2705':
                                Check_Count += 1
                            elif str(reaction.emoji) == '\u274C':
                                X_Count += 1

                            total_votes = Check_Count + X_Count
                            if total_votes >= num_members or total_votes >= num_success_vote:
                                break

                        if Check_Count >= num_success_vote:
                            removed = self.music_queue[num_queue - 1][0]['title']
                            user_id = self.music_queue[num_queue - 1][0]['queuer']
                            self.music_queue.pop(num_queue - 1)

                            await ctx.send(f"The song: **__{removed}__** has been skipped.\n"
                                           f" Who put this shit song here? \n"
                                           f" Of course it was {user_id} !")
                        else:
                            await ctx.send("The song has not been removed. Not enough votes!!!")
                    except asyncio.TimeoutError:
                        await ctx.send("No votes were cast within 15 seconds. The song will not be skipped!!!")
            else:
                await ctx.send("Can't be skipped if it doesn't exist!!!")
        else:
            await ctx.send("There is nothing to skip!!!")


async def setup(bot):
    await bot.add_cog(SkipAndRem_cog(bot))
