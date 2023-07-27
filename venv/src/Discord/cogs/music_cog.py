import bson
import pymongo
import discord
import asyncio
import os
from discord.ext import commands
from yt_dlp import YoutubeDL
from Database.connect_database import db
from Database.RetAndUpdateFunctions import find_document, add_music_queue, music_sessions


# TODO: maybe cache certain components
# TODO: pick out the video from playlist that you want to play
# TODO: Connect spotify API, add song titles to queue from a playlist, or add songs to a playlist
# TODO: Make queue look better, get the album cover or something to display
# TODO: Clean Up code. Lots of repetitive methods
# note to self: if FFMPeg does not work, just restart pycharm and file -> invalidate cache, dont click anything else


class music_cog(commands.Cog):

    # in future database would contain all this information, for now, just global variables
    def __init__(self, bot):
        self.update_lock = asyncio.Lock()
        self.bot = bot
        self.ydl_opts = {'format': 'm4a/bestaudio/best', 'postprocessors': [{
            'key': 'FFmpegExtractAudio', 'preferredcodec': 'm4a', }],
                         'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                         'noplaylist': True,
                         'outtmpl': 'Discord/Song_Downloads/%(id)s.%(ext)s'}
        self.FFMPEG_OPTIONS = {'options': '-vn -af loudnorm=I=-23:LRA=7', }

    # check to see if bot is running
    @commands.Cog.listener()
    async def on_ready(self):
        print("music_cog is ready!!!")

    def search_yt(self, item, person_queue):
        with YoutubeDL(self.ydl_opts) as ydl:
            try:
                # make sure video is not in playlist before you play the song
                info = ydl.sanitize_info(ydl.extract_info(f"ytsearch:{item}"))['entries'][0]
                source = f"Discord/Song_Downloads/{info['id']}.m4a"

                return {'source': source, 'title': info['title'], 'queuer': person_queue}
            except Exception:
                return False

    def play_next(self, vc, document, id):
        # if there is music in queue
        music_queue = document.get("music_queue", [])
        collection = music_sessions()
        if len(music_queue) > 0:
            document['is_Playing'] = True
            m_url = music_queue[0]['source']

            update = {
                "$set": {
                    "is_Playing": True,
                    "current_track": music_queue[0]['title'],
                    "current_person": music_queue[0]['queuer'],
                    "music_queue": music_queue[1:]  # Pop the first item from the queue
                }
            }

            collection.update_one({"_id": id}, update)

            # def remove_music():
            #     if len(self.music_queue) == 0:
            #         os.remove(f"{m_url}")
            #         return
            #     for item in self.music_queue:
            #         if 'source' in item[0] and item[0]['source'] == m_url:
            #             return  # The song is still in the queue, don't remove it
            #     # If the loop completes without finding the song in the queue, and it's not the next song, remove it
            #     next_url = self.music_queue[0][0]['source'] if self.music_queue[0] else None
            #     if next_url != m_url:
            #         os.remove(f"{m_url}")

            # keeps calling itself until the queue is empty recursively
            vc.play(discord.FFmpegPCMAudio(m_url, **self.FFMPEG_OPTIONS), after=lambda e: (
                self.play_next(vc, find_document(id), id)))

        else:
            document['is_Playing'] = False
            document['current_track'] = None
            document['current_person'] = None
            # maybe add disconnect function in the else statement
            collection.update_one({"_id": id}, {"$set": document})

    async def play_music(self, ctx, document, id):
        music_queue = document.get("music_queue", [])
        collection = music_sessions()

        if len(music_queue) > 0:
            document['is_Playing'] = True
            collection.update_one({"_id": id}, {"$set": document})

            m_url = music_queue[0]['source']

            vc = None
            voice_channel = self.bot.get_channel(music_queue[0]['channel'])

            if vc is None or not vc.is_connected():
                vc = await voice_channel.connect()
                document['vc'] = True
                collection.update_one({"_id": id}, {"$set": document})

                if vc is None:
                    await ctx.send("Could not connect to the voice channel!!!")
                    return
            elif vc is False:
                await vc.move_to(music_queue[0]['channel'])  # moves into channel with people in it
            # pops currently playing music from queue
            music_queue.pop(0)
            collection.update_one({"_id": id}, {"$set": {"music_queue": music_queue}})

            # def remove_music():
            #     if len(self.music_queue) == 0:
            #         os.remove(f"{m_url}")
            #         return
            #     for item in self.music_queue:
            #         if 'source' in item[0] and item[0]['source'] == m_url:
            #             return  # The song is still in the queue, don't remove it
            #     # If the loop completes without finding the song in the queue, and it's not the next song, remove it
            #     next_url = self.music_queue[0][0]['source'] if self.music_queue[0] else None
            #     if next_url != m_url:
            #         os.remove(f"{m_url}")

            # starts playing the song
            vc.play(discord.FFmpegPCMAudio(m_url, **self.FFMPEG_OPTIONS), after=lambda e: (
                self.play_next(vc, find_document(id), id)))

    @commands.command(name="join", aliases=["j"], help=" initializes document")
    async def join(self, ctx, *args):
        print(ctx.message.guild.id)
        guild_id = ctx.message.guild.id
        session = {
            "_id": guild_id,
            # every server has unique ID, so use this to search for the document that corresponds to server
            "is_Playing": False,
            "is_Paused": False,
            # current song
            "current_track": None,
            # person who queued current song
            "current_person": None,
            "music_queue": [],
            # settings for optimal audio
            "vc": False
        }

        print(session)
        # test post function
        collection = music_sessions()
        try:
            post_id = collection.insert_one(session)
            print("Inserted document ID:", post_id)
        except Exception as e:
            print("Error during insertion:", e)
    @commands.command(name="now_playing", aliases=["np"], help=" shows what is currently being played")
    async def now_playing(self, ctx):
        document = find_document(ctx.message.guild.id)

        if document['current_track'] is None:
            await ctx.send("Nothing is playing right now!!!")
        else:
            await ctx.send(f"Currently listening to: **__{document['current_track']}__**")

    @commands.command(name="play", aliases=["p"], help="Plays the selected song from youtube")
    async def play(self, ctx, *args):
        query = " ".join(args)

        collection = music_sessions()
        print(collection)
        server_ID = ctx.message.guild.id

        async with self.update_lock:
            document = find_document(server_ID)
            print(document)

            voice_channel = ctx.author.voice
            person_queue = ctx.author.mention

            if voice_channel:
                print(voice_channel.channel)
                song = self.search_yt(query, person_queue)

                if isinstance(song, bool):
                    await ctx.send("Could not play song. Try different keywords or make sure song is not in a playlist.")
                else:
                    if document['is_Playing']:
                        await ctx.send("Song added to queue")

                    # add song to the queue
                    music_queue = document.get("music_queue", [])
                    new = add_music_queue(song['source'], song['title'], song['queuer'], voice_channel.channel.id)
                    music_queue.append(new)
                    update = {"$set": {"music_queue": music_queue}}

                    try:
                        collection.update_one({"_id": server_ID}, update)
                        print("Update successful")
                    except Exception as e:
                        print("Error during update:", e)

                    if not document['is_Playing']:
                        await ctx.send(f"Listening to: {music_queue[0]['title']}")
                        current_track = music_queue[0]['title']
                        current_person = music_queue[0]['queuer']
                        update = {"$set": {"current_person": current_person, "current_track": current_track}}
                        print(update)
                        try:
                            collection.update_one({"_id": server_ID}, update)
                            print(find_document(server_ID))
                            print("Update successful")
                        except Exception as e:
                            print("Error during update:", e)

                        await self.play_music(ctx, find_document(server_ID), server_ID)
            elif document['is_Paused'] is True:
                self.vc.resume()
            else:
                await ctx.send('You need to be in a voice channel to use this command!!!')

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

    @commands.command(name="skip", aliases=["s"], help="Skips playing the current song")
    async def skip(self, ctx, *args):
        server_ID = ctx.message.guild.id
        document = find_document(server_ID)
        collection = music_sessions()
        vc = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        music_queue = document.get("music_queue", [])

        async with self.update_lock:
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
                    message = await ctx.send(f"Should **__{document['current_track']}__** be skipped? 15 seconds to vote")
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

    # shows queue
    @commands.command(name="queue", aliases=["q"], help="Lists current songs in the queue")
    async def queue(self, ctx):
        retval = ""
        for i in range(0, len(self.music_queue)):
            if i > 5:
                break
            retval += str(i) + '. ' + self.music_queue[i][0]['title'] + '\n'

        if not retval:
            await ctx.send("There are no songs in the queue!")
        else:
            return await ctx.send(retval)

    @commands.command(name="clear", aliases=["c"], help="Removes all songs")
    async def clear(self, ctx, *args):
        if self.vc is not None and self.is_Playing and (len(self.music_queue) != 0):
            self.vc.stop()
            self.is_Playing = False
            self.is_Paused = False
            self.current = None
            self.person = None
            self.music_queue.clear()
            await ctx.send("cleared music queue!!!")
        else:
            await ctx.send("There is nothing to clear!!!")

    # need fix
    @commands.command(name="disconnect", aliases=["dc"], help="Forces bot to leave the vc")
    async def kick(self, ctx):
        if self.vc is not None:
            self.is_Playing = False
            self.is_Paused = False
            self.current = None
            self.person = None
            await self.vc.disconnect()
            await ctx.send("bot kicked!!!")
            self.vc = None
        else:
            ctx.send("Add me to the voice channel!!!")


async def setup(bot):
    await bot.add_cog(music_cog(bot))
