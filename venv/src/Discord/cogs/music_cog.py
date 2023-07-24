import discord
import asyncio
from discord.ext import commands
from yt_dlp import YoutubeDL


# TODO: pick out the video from playlist that you want to play
# TODO: Connect spotify API, add song titles to queue from a playlist, or add songs to a playlist
# TODO: Make queue look better, get the album cover or something to display
# note to self: if FFMPeg does not work, just restart pycharm and file -> invalidate cache, dont click anything else
class music_cog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.is_Playing = False
        self.is_Paused = False

        # current song
        self.current = None

        # person who queued current song
        self.person = None

        self.music_queue = []
        # settings for optimal audio
        self.ydl_opts = {'format': 'm4a/bestaudio/best', 'postprocessors': [{
            'key': 'FFmpegExtractAudio', 'preferredcodec': 'm4a', }],
                         'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                         'noplaylist': True,
                         'outtmpl': 'Discord/Song_Downloads/%(id)s.%(ext)s'}
        self.FFMPEG_OPTIONS = {'options': '-vn -af loudnorm=I=-23:LRA=7', }
        self.vc = None

    # check to see if bot is running
    @commands.Cog.listener()
    async def on_ready(self):
        print("music_cog is ready!!!")

    def play_next(self):
        # if there is music in queue
        if len(self.music_queue) > 0:
            self.is_Playing = True
            m_url = self.music_queue[0][0]['source']

            self.current = self.music_queue[0][0]['title']
            self.person = self.music_queue[0][0]['title']
            self.music_queue.pop(0)

            # keeps calling itself until the queue is empty recursively
            self.vc.play(discord.FFmpegPCMAudio(m_url, **self.FFMPEG_OPTIONS), after=lambda e: self.play_next())
        else:
            self.is_Playing = False

    def search_yt(self, item, person_queue):
        with YoutubeDL(self.ydl_opts) as ydl:
            try:
                # make sure video is not in playlist before you play the song
                info = ydl.sanitize_info(ydl.extract_info(f"ytsearch:{item}"))['entries'][0]
                source = f"Discord/Song_Downloads/{info['id']}.m4a"

                return {'source': source, 'title': info['title'], 'Queuer': person_queue}
            except Exception:
                return False

    async def play_music(self, ctx):
        if len(self.music_queue) > 0:
            self.is_Playing = True
            m_url = self.music_queue[0][0]['source']
            print(m_url)

            # checks for if people are in the voice chat
            if self.vc is None or not self.vc.is_connected():
                self.vc = await self.music_queue[0][1].connect()

                if self.vc is None:
                    await ctx.send("Could not connect to the voice channel!!!")
                    return
            elif ctx.author.voice is None:
                await self.vc.move_to(self.music_queue[0][1])  # moves into channel with people in it
            # pops currently playing music from queue
            self.music_queue.pop(0)
            # starts playing the song
            self.vc.play(discord.FFmpegPCMAudio(m_url, **self.FFMPEG_OPTIONS), after=lambda e: self.play_next())
        else:
            self.is_Playing = False

    @commands.command(name="now_playing", aliases=["np"], help=" shows what is currently being played")
    async def now_playing(self, ctx, *args):
        if self.current is None:
            await ctx.send("Nothing is playing right now!!!")
        else:
            await ctx.send(f"Currently listening to: **__{self.current}__**")

    @commands.command(name="play", aliases=["p"], help="Plays the selected song from youtube")
    async def play(self, ctx, *args):
        query = " ".join(args)
        print(query)

        voice_channel = ctx.author.voice
        person_queue = ctx.author.mention

        if voice_channel:
            print(voice_channel.channel)
            song = self.search_yt(query, person_queue)
            if isinstance(song, bool):
                await ctx.send("Could not play song. Try different keywords or make sure song is not in a playlist.")
            else:
                if self.is_Playing:
                    await ctx.send("Song added to queue")
                self.music_queue.append([song, voice_channel.channel])
                if not self.is_Playing:
                    await ctx.send(f"Listening to: {self.music_queue[0][0]['title']}")
                    self.current = self.music_queue[0][0]['title']
                    self.person = self.music_queue[0][0]['Queuer']
                    await self.play_music(ctx)
        elif self.is_Paused is True:
            self.vc.resume()
        else:
            await ctx.send('You need to be in a voice channel to use this command!!!')

    # pauses song
    @commands.command(name="pause", aliases=["stop"], help="Pauses ")
    async def pause(self, ctx, *args):
        if self.is_Playing:  # if playing pause
            self.is_Playing = False
            self.is_Paused = True
            self.vc.pause()
        elif self.is_Paused:  # if paused, resume
            self.is_Playing = True
            self.is_Paused = False
            self.vc.resume()

    # resumes playing song
    @commands.command(name="resume", aliases=["r"], help="Resumes playing the current song")
    async def resume(self, ctx, *args):
        if self.is_Paused:  # if paused, resume
            self.is_Playing = True
            self.is_Paused = False
            self.vc.resume()
        elif self.is_Playing:  # if paused, resume
            self.is_Playing = False
            self.is_Paused = True
            self.vc.pause()

    @commands.command(name="skip", aliases=["s"], help="Skips playing the current song")
    async def skip(self, ctx, *args):
        if self.vc is not None and self.is_Playing:  # if in voice channel
            voice_channel = ctx.author.voice.channel
            num_members = len(voice_channel.members) - 1  # account for bot
            num_success_vote = (num_members // 2) + 1

            queue_length = len(self.music_queue)
            if num_members <= 2:
                self.vc.stop()  # stop playing current song
                self.is_Playing = False
                self.is_Paused = False

                await ctx.send(f"The song: **__{self.current}__** has been skipped.")
                if queue_length == 0:
                    self.current = None
                    self.person = None

                await self.play_next(ctx)  # move next
            elif num_members > 2:
                message = await ctx.send(f"Should **__{self.current}__** be skipped? 15 seconds to vote")
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
                        self.vc.stop()  # stop playing current song
                        self.is_Playing = False
                        self.is_Paused = False

                        await ctx.send(f"The song: **__{self.current}__** has been skipped.\n"
                                       f" Who put this shit song here? \n"
                                       f"Of course it was {self.person} !")

                        if queue_length == 0:
                            self.current = None
                            self.person = None

                        await self.play_next(ctx)  # move next
                    else:
                        await ctx.send(f"The song: **__{self.current}__** has not been skipped. Not enough votes.")
                except asyncio.TimeoutError:
                    await ctx.send("No votes were cast within 15 seconds. The song will not be skipped.")
        else:
            await ctx.send("There is nothing to skip!!!")

    @commands.command(name="remove", aliases=["rem"], help="Removes specific song in queue")
    async def remove(self, ctx, *args):
        query = " ".join(args)
        num_queue = int(query)

        if self.vc is not None and self.is_Playing:
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

                            self.music_queue.pop(num_queue - 1)
                            user_id = self.music_queue[num_queue - 1][0]['Queuer']
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
            if i > 4:
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
