# Music features  for "Melodies Of Arts"
# Rewritten music_commands in ext_music_cog2.py



import contextlib
from math import floor
import asyncio
from typing import Optional
import functools

#import ytpy as youtubepy
#from spotipy import *
#import youtube_dl
from json import load, dump
import discord
from discord.ext import commands
import lyricsgenius
from dotenv import load_dotenv
import logging
from os import environ as envs
# import pygicord #| (Removed)
from time import time





load_dotenv()

handler = logging.FileHandler(filename='program_logs.log', encoding='utf-8', mode='w')

formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s')

discord.utils.setup_logging(level=logging.ERROR, handler=handler, formatter=formatter)



class MusicSource(discord.PCMVolumeTransformer):
    # Suppressing Youtube_Dl warnings and  download progress messages
    sp_client = SpotifyClientCredentials(envs.get("SPOTIPY_CLIENT_ID"), envs.get("SPOTIPY_CLIENT_SECRET"))
    spotify = Spotify(auth_manager=sp_client)
    youtube_dl.utils.bug_reports_message = lambda: ''
    ytdl_format_options = {  # configuring audio format
        'format': 'bestaudio/best',
        'restrictfilenames': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0',  # IPv6 causes problem sometimes so bound to IPv4
        'youtube_include_dash_manifest': False  # Turning off dash manifest
        # (Enabling it sometimes makes the bot not play anything)
    }
    # Sending the options to the Youtube_DL class
    ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

    def __init__(self, source: discord.AudioSource, *, volume: float, data: dict):
        self.volume=volume
        self.data = data
        self.title = data.get('title') or "unknown"
        self.url = data.get('url')
        # Fetching the youtube link for the song and
        self.link = data.get('webpage_url')
        # will be used later for sending it to the user
        self.time = data.get('duration') or 0
        self.artist = data.get('artist') or "unknown"
        self.second_title = data.get("alt_title")
        self.img = data.get("thumbnail")
        super(MusicSource, self).__init__(source, self.volume)


    def __str__(self):
        return str(self.title)


    @classmethod
    # This one creates the audio source from the url
    async def create_new_source(cls, url: str, *, ctx: commands.Context, client: commands.Bot=None, volume: float=0.4, bass: int=2) -> discord.PCMVolumeTransformer:
        loops = client.loop or asyncio.get_event_loop()
        from_spotify = False
        if url.startswith(("http://youtu.be", "https://youtu.be", "http://www.youtube.com/watch?v=", "https://www.youtube.com/watch?v=")):
            weblink = url
        else:
            if url.startswith(("http://open.spotify.com/track/", "https://open.spotify.com/track/")):
                web_url = url
                track, artist, album_art = await cls.get_spotify_track_info(url)
                url = f'{track} {artist.split(", ")[0]}'
                from_spotify = True
            track_id = await cls.get_youtube_track_info(client, url)
            if track_id is None: return None
            weblink = "http://www.youtube.com/watch?v="+track_id
        if from_spotify:
            print(f"Spotify Track||URL: {weblink}")
        else: print(f"Youtube Track||URL: {weblink}")
        part = functools.partial(cls.ytdl.extract_info, weblink, download=False, process=True)
        final_data = await loops.run_in_executor(None, part)
        if final_data is None:
            return await ctx.send("`Error in processing web request. Please try again`")
        if "entries" not in final_data:
            information = final_data
        else:
            information = None
            while information is None:
                try:
                    information = final_data["entries"].pop(0)
                except IndexError:
                    await ctx.send(f"`Error! Retrying...`")
                    break
        if information is None:
            channel = ctx.voice_client.channel
            await ctx.voice_client.disconnect()
            await asyncio.sleep(1)  # A short break
            await channel.connect()
            await ctx.guild.change_voice_state(channel=channel, self_deaf=True)
            part2 = functools.partial(cls.ytdl.extract_info, weblink, download=False, process=True)
            final_data = await loops.run_in_executor(None, part2)
            if "entries" not in final_data:
                information = final_data
            else:
                information = None
                while information is None:
                    try:
                        information = final_data["entries"].pop(0)
                    except IndexError:
                        return await ctx.send(f":x: Couldn't find anything that matches with '{url}'`")
        if from_spotify:
            information["title"] = artist.split(", ")[0] + " - " + track
            information["artist"] = artist
            information["thumbnail"] = album_art
            information["webpage_url"] = web_url
        return cls(discord.FFmpegPCMAudio(information["url"], before_options=f'-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -ss 00', options=f'-vn -af bass=g={bass}'), volume=volume, data=information)


    @classmethod
    async def get_youtube_playlist_tracks(cls, client, url: str):
        playlist_id = url.rsplit("list=", 1)[1]
        yt_searcher = youtubepy.YoutubeDataApiV3Client(client.client_session, dev_key=envs.get("yt_api"))
        results = await yt_searcher.get_playlist(playlist_id=playlist_id, max_results=50)
        try:
            items = results["items"]
        except KeyError:
            return None, None
        video_links = [f'http://www.youtube.com/watch?v={item["snippet"]["resourceId"]["videoId"]}' for item in items if "private video" not in item["snippet"]["title"].lower()]
        video_names = [item["snippet"]["title"] for item in items if "private video" not in item["snippet"]["title"].lower()]
        return video_links, video_names


    @classmethod
    async def get_spotify_tracks(cls, url: str):
        if url.startswith("https://open.spotify.com/playlist"):
            results = cls.spotify.playlist(url)
            tracks = [item["track"] for item in results["tracks"]["items"]]
        elif url.startswith("https://open.spotify.com/album"):
            results = cls.spotify.album(url)
            tracks = results["tracks"]["items"]
        elif url.startswith("https://open.spotify.com/artist"):
            results = cls.spotify.artist_top_tracks(url)
            tracks = results["tracks"]
            results["name"] = tracks[0]["artists"][0]["name"]
        track_names = list()
        urls = list()
        for track in tracks:
            if track is None: continue
            with contextlib.suppress(KeyError): 
                urls.append(track["external_urls"]["spotify"])
                track_names.append(track["name"])
        return urls, track_names, results["name"]


    @classmethod
    async def get_spotify_track_info(cls, url: str, name_extraction_mode: bool=False):
        track = cls.spotify.track(str(url))
        name = track["name"]
        artists = ", ".join(artist["name"] for artist in track["artists"])
        album_art = track["album"]["images"][0]["url"]
        if name_extraction_mode:
            return name 
        else:
            return name, artists, album_art


    @classmethod
    async def get_youtube_track_info(cls, client, url: str, name_extraction_mode=False) -> str:
        yt_searcher = youtubepy.YoutubeDataApiV3Client(client.client_session, dev_key=envs["yt_api"])
        results = await yt_searcher.search(q=url, max_results=1)
        try:
            track = results["items"][0]
        except IndexError:
            return None
        title = track["snippet"]["title"]
        return title if name_extraction_mode else track["id"]["videoId"]


class Music(commands.Cog):

    def __init__(self, client: commands.Bot):
        self.client = client
        self.yt_client = youtubepy.YoutubeDataApiV3Client(self.client.client_session, dev_key=envs["yt_api"])
        lyrics_api = envs.get("lyrics_api")
        self.player = dict()
        self.links = dict()
        self.requesters = dict()
        self.loop = dict()
        self.song_queue = dict()
        self.current_timestamp = dict()
        self.last_pause_time = dict()
        self.total_pause_time = dict()
        self.voted_for_skip = dict()
        self.music_is_skipped = False
        self.vol = dict()
        self.lyricsextractor = lyricsgenius.Genius(lyrics_api, timeout=15)
        self.buttons = ["⏯️", "⏪", "🔂", u"\u23ED", "📄", "🎵", "🎶"]
        self.last_message = dict()
        self.start_timer = dict()
        self.shall_respond_to_reactions = dict()
        self.paginator = dict()
        self.last_search = dict()
        self.bass = dict()


    #A check whether the member has a dj role
    async def cog_check(self, ctx: commands.Context, member: discord.Member=None) -> bool:
        member = member or ctx.author
        if member.id == self.client.user.id:
            return False
        with open("./database/djonly_role_id.json", "r") as dj_roles:
            djrole = load(dj_roles)
        try:
            if djrole[str(ctx.guild.id)] is None:
                return True
            else:
                ids = tuple(str(role.id) for role in member.roles)
                if djrole[str(member.guild.id)] not in ids and ctx.guild.owner_id != member.id:
                    await ctx.send(":warning: I am currently in DJ only mode!`")
                    return False
                else:
                    return True
        except KeyError:
            djrole[str(ctx.guild.id)] = None
            with open("./database/djonly_role_id.json", "w") as dj_roles:
                dump(djrole, dj_roles, indent=8)
            return True

    # Below are the helper functions
    def reset_timestamp(self, ctx):
        self.current_timestamp[str(ctx.guild.id)] = time()
        self.last_pause_time[str(ctx.guild.id)] = 0
        self.total_pause_time[str(ctx.guild.id)] = 0

    def get_current_time(self, ctx) -> float:
        if self.last_pause_time[str(ctx.guild.id)] != 0:
            crnt_time = (time() - (self.current_timestamp[str(ctx.guild.id)] + self.total_pause_time[str(ctx.guild.id)] + (time() - self.last_pause_time[str(ctx.guild.id)])))
        else:
            crnt_time = (time() - (self.current_timestamp[str(ctx.guild.id)] + self.total_pause_time[str(ctx.guild.id)]))
        return crnt_time

    def get_next(self, ctx):
        self.links[str(ctx.guild.id)].pop(0)
        self.song_queue[str(ctx.guild.id)].pop(0)
        self.requesters[str(ctx.guild.id)].pop(0)

    def clear_all(self, ctx):
        self.links[str(ctx.guild.id)].clear()
        self.song_queue[str(ctx.guild.id)].clear()
        self.requesters[str(ctx.guild.id)].clear()

    def format_time(self, mins, secs) -> str:
        if mins < 10:
            mins = "0" + str(mins)
        else:
            mins = str(mins)
        if secs < 10:
            secs = "0" + str(secs)
        else:
            secs = str(secs)
        return mins + ":" + secs

    async def set_btns(self, ctx, last_message):
        if ctx.voice_client is None:
            return
        self.shall_respond_to_reactions[str(ctx.guild.id)] = True
        for reacts in self.buttons:
            if ctx.voice_client is not None:
                await last_message.add_reaction(reacts)
            else:
                return
        def verify(react, user):
            return react.emoji in self.buttons and user.id != self.client.user.id and react.message.id == last_message.id
        while self.shall_respond_to_reactions[str(ctx.guild.id)]:
            react, user = await self.client.wait_for("reaction_add", check=verify)
            if user.voice is None or user.voice.channel.id != ctx.voice_client.channel.id:
                await ctx.send("`\U0000274CYou are not in the same voice channel!`")
            else:
                if react.emoji == "⏯️":
                    if not await self.cog_check(ctx, member=user):
                        await self.last_message[str(ctx.guild.id)].remove_reaction(member=user, emoji=react.emoji)
                        continue
                    if ctx.voice_client.is_playing():
                        ctx.voice_client.pause()
                        await ctx.send(f":pause_button: Music paused by {user}`")
                        self.last_pause_time[str(ctx.guild.id)] = time()
                        await self.last_message[str(ctx.guild.id)].remove_reaction(member=user, emoji=react.emoji)
                    elif ctx.voice_client.is_paused():
                        ctx.voice_client.resume()
                        self.total_pause_time[str(ctx.guild.id)] += (time() - self.last_pause_time[str(ctx.guild.id)])
                        self.last_pause_time[str(ctx.guild.id)] = 0
                        await ctx.send(f":arrow_forward: Song resumed by {user}.`")
                elif react.emoji=="⏪":
                    if not await self.cog_check(ctx, member=user):
                        await self.last_message[str(ctx.guild.id)].remove_reaction(member=user, emoji=react.emoji)
                        continue
                    try:
                        ctx.voice_client.source = MusicSource(
                            discord.FFmpegPCMAudio(
                                ctx.voice_client.source.url,
                                before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -ss 0', 
                                options=f'-vn -af bass=g={self.bass[str(ctx.guild.id)]}'), 
                            volume=self.vol[str(ctx.guild.id)],
                            data=ctx.voice_client.source.data
                            )
                    except AttributeError:
                        return
                    else:
                        self.reset_timestamp(ctx)
                        await ctx.send(f":track_previous: Music restarted by {user}`")
                elif react.emoji == "🔂":
                    if not await self.cog_check(ctx, member=user):
                        await self.last_message[str(ctx.guild.id)].remove_reaction(member=user, emoji=react.emoji)
                        continue
                    self.loop[str(ctx.guild.id)] = not self.loop[str(user.guild.id)]  # Setting the opposite state 
                    msg = ":repeat_one: Enabled loop!`" if self.loop[str(user.guild.id)] else ":ballot_box_with_check: Disabled loop!`"
                    await ctx.send(msg)
                elif react.emoji == u"\u23ED":
                    if user.id not in self.voted_for_skip[str(ctx.guild.id)]:
                        self.voted_for_skip[str(ctx.guild.id)].append(user.id)
                        await ctx.send(f":track_next: {user} voted to skip the song`")
                    else:
                        await ctx.send(f":warning: You have already voted to skip the song!`")
                    memb = tuple(mem.id for mem in ctx.voice_client.channel.members if mem.id != self.client.user.id)
                    if floor(len(memb) * (3/4)) <= len(self.voted_for_skip[str(ctx.guild.id)]):
                        self.voted_for_skip[str(ctx.guild.id)] = list()
                        if self.loop[str(ctx.guild.id)]:
                            try:
                                self.get_next(ctx)
                            except IndexError:
                                self.clear_all(ctx)
                        self.music_is_skipped = True
                        ctx.voice_client.stop()
                        await ctx.send(":thumbsup: Skipped the song successfully!`")
                    else:
                        await ctx.send(f"`Got {len(self.voted_for_skip[str(ctx.guild.id)])} votes. Required {floor(len(memb)*(3/4))} votes`")
                elif react.emoji == "📄":
                    if not await self.cog_check(ctx, member=user):
                        await self.last_message[str(ctx.guild.id)].remove_reaction(member=user, emoji=react.emoji)
                        continue
                    await ctx.invoke(self.lyrics_)
                elif react.emoji == "🎵":
                    await ctx.invoke(self.now_playing)
                elif react.emoji == "🎶":
                    await ctx.invoke(self.queue_)
            await self.last_message[str(ctx.guild.id)].remove_reaction(member=user, emoji=react.emoji)

    def get_player_embed(self, ctx) -> discord.Embed:
        web_link = ctx.voice_client.source.link
        emoji = self.client.get_emoji(861535416175951872) if web_link.startswith(("https://open.spotify.com/track", "http://open.spotify.com/track")) else self.client.get_emoji(883035973116629033)
        playembed = discord.Embed(
            title=f'{emoji} Play music',
            description=f"**__Now Playing__:** [{ctx.voice_client.source.title}]({web_link})",
            color=ctx.author.colour
        )
        minutes, seconds = divmod(round(ctx.voice_client.source.time), 60)
        dur = self.format_time(mins=round(minutes), secs=round(seconds))
        playembed.add_field(name='Duration :stopwatch:',
                            value=f'`{dur}`', inline=True)
        playembed.add_field(name='Requested by :headphones:',
                            value=f'`{self.requesters[str(ctx.guild.id)][0]}`', inline=True)
        playembed.set_image(url=ctx.voice_client.source.img)
        playembed.set_footer(text=str(self.client.user.name))
        playembed.timestamp = discord.utils.utcnow()
        return playembed

    async def start_counting(self, ctx):
        z = 0
        try:
            while not ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
                z+=1
                await asyncio.sleep(1)
                if round(z) == 300:
                    self.clear_all(ctx)
                    self.loop[str(ctx.guild.id)] = False
                    with contextlib.suppress(KeyError, ValueError, AttributeError, discord.errors.HTTPException, discord.errors.Forbidden):
                        await self.last_message[str(ctx.guild.id)].clear_reactions()
                    self.shall_respond_to_reactions[str(ctx.guild.id)] = False
                    await ctx.voice_client.disconnect()
                    print("--Auto disconnected from {0.name}-- after {1} seconds".format(ctx.guild, round(time()-self.start_timer[str(ctx.guild.id)])))
                    await ctx.send(":white_check_mark: Disconnected Automatically.`")
                    break
        except AttributeError:
            # When bot is already disconnected the voice_client object is None.
            # And NoneType object don't have any Attribute named is_playing. So it raises Atrribute error
            # So we return without any action because we know its already disconnected
            return


    async def add_to_queue(self, ctx, url):
        with contextlib.suppress(discord.errors.NotFound):
            await ctx.message.add_reaction("\U0001F90D")
            #  Showing exact name instead of showing the url when a song url is given
        if url.startswith(('https://', 'http://')) or url.endswith(".com"):
            if url.startswith(("http://youtu.be", "https://www.youtube.com/watch?v=", "https://youtu.be", "http://www.youtube.com/watch?v=")):
                song_name = await MusicSource.get_youtube_track_info(client=self.client, url=url, name_extraction_mode=True)
                if song_name is None:
                    return await ctx.send("`Can't download! Access Denied!!!` :warning:")
            elif url.startswith(("http://youtube.com/playlist", "https://youtube.com/playlist", "http://www.youtube.com/playlist", "https://www.youtube.com/playlist")):
                urls, track_names = await MusicSource.get_youtube_playlist_tracks(self.client, url=url)
                if urls is None or track_names is None:
                    return await ctx.send(":x: Playlist data couldn't be fetched!`")
                self.links[str(ctx.guild.id)].extend(urls)
                self.song_queue[str(ctx.guild.id)].extend(track_names)
                self.requesters[str(ctx.guild.id)].extend(list(str(ctx.author) for _ in urls))
                ytmoji = self.client.get_emoji(883035973116629033)
                await ctx.send(f"{ytmoji} `Youtube Playlist added to the queue!`")
                return None
            elif url.startswith(("https://open.spotify.com/track/", "http://open.spotify.com/track/")):
                song_name = await MusicSource.get_spotify_track_info(url, name_extraction_mode=True)
            elif url.startswith(("https://open.spotify.com/", "http://open.spotify.com")):
                urls, track_names, _name = await MusicSource.get_spotify_tracks(url=url)
                self.links[str(ctx.guild.id)].extend(urls)
                self.song_queue[str(ctx.guild.id)].extend(track_names)
                self.requesters[str(ctx.guild.id)].extend(list(str(ctx.author) for _ in urls))
                spotimoji = self.client.get_emoji(861535416175951872)
                await ctx.send(f"{spotimoji} `'{_name}' added to the queue successfully!`")
                return None
            else: return await ctx.send(":x: Unsupported url! Please provide a song name or Youtube url or Spotify track url.`")
        else:
            #  When no url is given, showing the exact search term given by the user
            song_name = url.title()
        self.requesters[str(ctx.guild.id)].append(ctx.author)
        self.links[str(ctx.guild.id)].append(url)
        self.song_queue[str(ctx.guild.id)].append(song_name)
        await ctx.send(f":musical_note: \"{song_name}\" has been added to the playlist. `")
        return None


    async def next_song(self, ctx: commands.Context):
        # So len(ctx.voice_client.channel.members) would work too but I don't like that :p
        voice_member_ids = tuple(str(member.id) for member in ctx.voice_client.channel.members if member.id != self.client.user.id)
                                #Getting all members except the bot itself
        if len(voice_member_ids) == 0:  # Check if there's no member in the voice 
            self.clear_all(ctx)
            self.loop[str(ctx.guild.id)] = False
            await ctx.voice_client.disconnect()
            with contextlib.suppress(discord.errors.HTTPException, discord.errors.Forbidden, AttributeError, KeyError):
                await self.last_message[str(ctx.guild.id)].clear_reactions()
            self.shall_respond_to_reactions[str(ctx.guild.id)] = False
            print("--Auto disconnected from {0.name} after {1} seconds--".format(ctx.guild, round(time()-self.start_timer[str(ctx.guild.id)])))
            await ctx.send("`Automatically disconnected.`")
            return
        if not self.loop[str(ctx.guild.id)]:
            self.voted_for_skip[str(ctx.guild.id)].clear()
            try:
                self.get_next(ctx)
            except IndexError:
                self.clear_all(ctx)
        if len(self.links[str(ctx.guild.id)]) != 0:
            self.reset_timestamp(ctx)
            if not self.loop[str(ctx.guild.id)] or self.music_is_skipped:
                self.music_is_skipped = False
                with contextlib.suppress(AttributeError):
                    ctx.voice_client.source.cleanup()
                    self.player[str(ctx.guild.id)].cleanup()
                    self.player[str(ctx.guild.id)] = None
                loading_moji = self.client.infinity_emoji
                await ctx.send(f"{loading_moji} `Playing next song.`", delete_after=3)
                try:
                    self.player[str(ctx.guild.id)] = await MusicSource.create_new_source(url=self.links[str(ctx.guild.id)][0], client=self.client,
                                                        ctx=ctx, volume=self.vol[str(ctx.guild.id)], bass=self.bass[str(ctx.guild.id)])
                except youtube_dl.utils.DownloadError:
                    await ctx.send("\U0000274C `Access Denied! Please provide the song name.`")
                    await self.next_song(ctx=ctx)
                    return
                if ctx.voice_client is None:
                    return
                if isinstance(self.player[str(ctx.guild.id)], (discord.Message)) or self.player[str(ctx.guild.id)] is None:
                    return await self.next_song(ctx)
                ctx.voice_client.play(self.player[str(ctx.guild.id)], after=lambda _: self.play_next(ctx=ctx))
                playembed = self.get_player_embed(ctx)
                with contextlib.suppress(KeyError, AttributeError, discord.errors.HTTPException, discord.errors.Forbidden):
                    await self.last_message[str(ctx.guild.id)].clear_reactions()
                self.shall_respond_to_reactions[str(ctx.guild.id)] = False
                self.last_message[str(ctx.guild.id)] = await ctx.send(embed=playembed)
                await self.set_btns(ctx=ctx, last_message=self.last_message[str(ctx.guild.id)])
            elif self.loop[str(ctx.guild.id)] and not self.music_is_skipped:
                try:
                    self.player[str(ctx.guild.id)] = MusicSource(
                        discord.FFmpegPCMAudio(
                            ctx.voice_client.source.url, 
                            before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -ss 00', 
                            options=f'-vn -af bass=g={self.bass[str(ctx.guild.id)]}'
                            ), 
                            volume=self.vol[str(ctx.guild.id)], 
                            data=ctx.voice_client.source.data
                        )
                except AttributeError:
                    return await ctx.send(":warning: Error in restarting music! Please try again.`")
                else:
                    prefix = ctx.prefix
                    if ctx.voice_client is None:
                        return
                    ctx.voice_client.play(self.player[str(ctx.guild.id)], after=lambda _: self.play_next(ctx=ctx))
                    await ctx.send(f":repeat: Replayed current song. Use '{prefix}loop' to stop repeating.`", delete_after=3)
                    return await asyncio.sleep(1.5)
        elif len(self.links[str(ctx.guild.id)]) == 0:
            prefix = ctx.prefix
            with contextlib.suppress(AttributeError):
                ctx.voice_client.source.cleanup()
                self.player[str(ctx.guild.id)].cleanup()
                self.player[str(ctx.guild.id)] = None
            with contextlib.suppress(KeyError, AttributeError, discord.errors.HTTPException, discord.errors.Forbidden):
                await self.last_message[str(ctx.guild.id)].clear_reactions()
            self.shall_respond_to_reactions[str(ctx.guild.id)] = False
            await ctx.send(f"`Playlist is over. What's next? Use '{prefix}play <song_name>'`")
            await self.start_counting(ctx=ctx)


    def play_next(self, ctx) -> asyncio.futures:
        if ctx.voice_client is None:
            self.clear_all(ctx)
            return
        next_corou = self.next_song(ctx=ctx)
        fut_next = asyncio.run_coroutine_threadsafe(coro=next_corou, loop=self.client.loop)
        try:
            fut_next.result()
        except Exception as e:
            if ctx.voice_client is None:
                return None 
            dc_corou = ctx.voice_client.disconnect()
            fut_dc = asyncio.run_coroutine_threadsafe(coro=dc_corou, loop=self.client.loop)
            fut_dc.result()
            warn = ctx.send("```\nERROR!\n{0}: {1}\n```".format(e.__class__.__name__, str(e)))
            fut = asyncio.run_coroutine_threadsafe(warn, self.client.loop)
            fut.result()
            raise e


# Below are the functions registered as commands

    @commands.hybrid_command(name="join", aliases=["j", "connect", "come", "fuckon", "fuck-on", "start"], description="Joins the voice channel you are in.")
    @commands.guild_only()
    async def join_voice(self, ctx: commands.Context, invoked_from_play_command: Optional[bool]=False):
        voice = ctx.author.voice
        if voice is None:
            return await ctx.send(":warning: Please connect to a voice channel first!`")
        if ctx.voice_client is not None:
            voice_memb = tuple(mem.id for mem in ctx.voice_client.channel.members if mem.id != self.client.user.id)
            if len(voice_memb) == 0:
                await ctx.voice_client.move_to(voice.channel)
                return await ctx.send(":white_check_mark: Voice channel changed!`")
            else:
                return await ctx.send("\U0000274C `Already connected in a voice channel! `")
        elif ctx.voice_client is None:
            self.start_timer[str(ctx.guild.id)] = time()
            self.player[str(ctx.guild.id)] = None
            self.links[str(ctx.guild.id)] = list()
            self.loop[str(ctx.guild.id)] = False
            self.current_timestamp[str(ctx.guild.id)] = 0
            self.requesters[str(ctx.guild.id)] = list()
            self.last_pause_time[str(ctx.guild.id)] = 0
            self.total_pause_time[str(ctx.guild.id)] = 0
            self.voted_for_skip[str(ctx.guild.id)] = list()
            self.song_queue[str(ctx.guild.id)] = list()
            self.vol[str(ctx.guild.id)] = 0.4
            self.bass[str(ctx.guild.id)] = 2
            self.shall_respond_to_reactions[str(ctx.guild.id)] = False
            self.paginator[str(ctx.guild.id)] = None
            conct_msg = await ctx.send(f"{self.client.infinity_emoji} `Connecting.....`")
            await voice.channel.connect()
            await conct_msg.edit(content=":white_check_mark: Connected to '{0.name}'. Ready to play!`".format(voice.channel))
            await ctx.guild.change_voice_state(channel=voice.channel, self_deaf=True, self_mute=False)
            print("--Voice connected to {0.name}--".format(ctx.guild))
            if invoked_from_play_command:
                return
            else:
                await self.start_counting(ctx)

    @commands.hybrid_command(name="volume", aliases=["vol", "v", "sound"], description="Set the music volume!")
    @commands.guild_only()
    async def change_volume(self, ctx: commands.Context, volume_level: Optional[float] = 40.0):
        if ctx.author.voice is None or ctx.voice_client is None or ctx.voice_client.source is None:
            return await ctx.send("\U0000274C `Please play a song before using music commands.`")
        if ctx.author.voice.channel.id != ctx.voice_client.channel.id:
            return await ctx.send("\U0000274C `You must be connected to the same voice channel to use music commands!`")
        if isinstance(volume_level, str):
            volume_level = float(volume_level.rstrip("%"))
        if not (0 < volume_level < 101):
            return await ctx.send("\U0000274C `Invalid volume level! Valid level is between 1 and 100`")
        else:
            new_vol = volume_level / 100
            if new_vol == self.vol[str(ctx.guild.id)]:
                return await ctx.send(f":x: Volume is already set to {round(self.vol[str(ctx.guild.id)]*100)}%`")
            else:
                self.vol[str(ctx.guild.id)] = new_vol
                ctx.voice_client.source.volume = self.vol[str(ctx.guild.id)]
                return await ctx.send(f":loud_sound: Volume level changed to {round(volume_level)}%`")

    @commands.hybrid_command(name="bassboost", aliases=["bass", "basslevel", "bass-level"], description="Set the bass level!")
    @commands.guild_only()
    async def change_bass(self, ctx, new_bass: Optional[float] = 20.0):
        if ctx.author.voice is None or ctx.voice_client is None or ctx.voice_client.source is None:
            return await ctx.send("\U0000274C `Please play a song before using music commands.`")
        if ctx.author.voice.channel.id != ctx.voice_client.channel.id:
            return await ctx.send("\U0000274C `You must be connected to the same voice channel to use music commands!`")
        if not (0 < new_bass < 151):
            return await ctx.send("\U0000274C `Invalid bass level! Valid level is between 1 and 150`")
        else:
            new_bassboost = new_bass / 10
            if new_bassboost == self.bass[str(ctx.guild.id)]:
                return await ctx.send(f":x: Bass level is already set to {round(self.bass[str(ctx.guild.id)]*10)}%`")
            else:
                self.bass[str(ctx.guild.id)] = new_bassboost
                ctx.voice_client.source = MusicSource(
                    discord.FFmpegPCMAudio(
                        ctx.voice_client.source.url,
                        before_options=f'-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -ss {self.get_current_time(ctx)}', 
                        options=f'-vn -af bass=g={self.bass[str(ctx.guild.id)]}'
                        ), 
                        volume=ctx.voice_client.source.volume, 
                        data=ctx.voice_client.source.data
                    )
                return await ctx.send(f":loudspeaker: Bassboosted upto {round(self.bass[str(ctx.guild.id)]*10)}%`")


    @commands.hybrid_command(name="play", aliases=["p", "pl", "pla"], description="Command for playing a song.")
    @commands.guild_only()
    async def play_(self, ctx: commands.Context, *, url: str = None):
        if ctx.voice_client is None:
            await ctx.invoke(self.join_voice, invoked_from_play_command=True)
        if ctx.author.voice is None or ctx.author.voice.channel.id != ctx.voice_client.channel.id:
            return await ctx.send("\U0000274C `You must be connected to the same voice channel to use music commands!`")
        if len(self.links[str(ctx.guild.id)]) > 0:
            if url is None:
                prefix = ctx.prefix
                if ctx.voice_client.is_paused():
                    await ctx.message.add_reaction("\U0001F90D")
                    await ctx.invoke(self.resume_)
                    return 
                else:
                    await ctx.message.add_reaction("\U0001F90D")
                    await ctx.invoke(self.pause_)
                    return
            else:
                url = str(url)
                successfully_added = await self.add_to_queue(ctx, url)
                if isinstance(successfully_added, discord.Message):
                    return
        elif len(self.links[str(ctx.guild.id)]) <= 0:
            if url is None:
                await ctx.send("\U0000274C `Please try again and provide a song name or a song url along with the command.`")
                return await self.start_counting(ctx)
            else:
                url = str(url)
            if url.startswith(('http://', 'https://')) and not url.startswith(
                ("https://open.spotify.com/track", "http://open.spotify.com/track", "https://www.youtube.com/watch", "http://www.youtube.com/watch", "https://youtu.be", "http://youtu.be")
                ):
                if url.startswith(
                    ("https://open.spotify.com", "http://open.spotify.com", "http://youtube.com/playlist", "https://youtube.com/playlist", "http://www.youtube.com/playlist", "https://www.youtube.com/playlist")):
                    successfully_added = await self.add_to_queue(ctx, url)
                    if isinstance(successfully_added, discord.Message):
                        return
                else:
                    return await ctx.send(":x: Unsupported url! Please provide a YouTube Url or a Spotify track Url or a song name.`")
            else:
                self.requesters[str(ctx.guild.id)].append(ctx.author)
                self.links[str(ctx.guild.id)].append(url)
                self.song_queue[str(ctx.guild.id)].append(url)
            if len(self.links[str(ctx.guild.id)]):
                loading_moji=self.client.inifinity_emoji
                text = await ctx.send(f"{loading_moji} :mag_right: Searching for the given query.....`")
            try:
                self.player[str(ctx.guild.id)] = await MusicSource.create_new_source(
                    url=self.links[str(ctx.guild.id)][0], client=self.client, ctx=ctx, volume=self.vol[str(ctx.guild.id)], bass=self.bass[str(ctx.guild.id)]
                    )
            except youtube_dl.utils.DownloadError:
                with contextlib.suppress(discord.errors.HTTPException, discord.errors.Forbidden): await text.delete()
                await ctx.send(":warning: Access Denied! Please provide the song name.`")
                return await self.next_song(ctx=ctx)
            except IndexError:
                return
            if isinstance(self.player[str(ctx.guild.id)], discord.Message):
                return
            try:
                if ctx.voice_client is None:
                    return
                ctx.voice_client.play(self.player[str(ctx.guild.id)], after=lambda _: self.play_next(ctx=ctx))
            except discord.errors.ClientException:
                await ctx.send(":warning: Please give me one command at a time.`")
            self.current_timestamp[str(ctx.guild.id)] = time()
            playembed = self.get_player_embed(ctx)
            #  Returning a little bit of info about what's being played currently
            self.last_message[str(ctx.guild.id)] = await ctx.send(embed=playembed)
            with contextlib.suppress(discord.errors.Forbidden): await text.delete()
            self.shall_respond_to_reactions[str(ctx.guild.id)] = False
            await self.set_btns(ctx=ctx, last_message=self.last_message[str(ctx.guild.id)])


    @commands.hybrid_command(name='search', aliases=['find', 'searchsong', 'searchyt', 's'], description="Search youtube for a song!")
    @commands.guild_only()
    async def search_yt(self, ctx, *, search_term: str=None):
        if search_term is None:
            return await ctx.send("\U0000274C `Please provide a song name or a song url.`")
        if ctx.voice_client is None:
            await ctx.invoke(self.join_voice, invoked_from_play_command=True)
        if ctx.author.voice is None:
            return
        if ctx.author.voice.channel.id != ctx.voice_client.channel.id:
            return await ctx.send("\U0000274C `You must be connected to the same voice channel to use music commands!`")
        if search_term.lower().startswith(('https://', 'http://')):
            return await ctx.invoke(self.play_, url=search_term)
        searches = await self.yt_client.search(search_term, search_type="video", max_results=10)
        ids = tuple(searches["items"][x]["id"]["videoId"] for x in range(len(searches["items"])))
        titles = tuple(searches["items"][x]["snippet"]["title"] for x in range(len(searches["items"])))
        if len(ids) > 0 and len(titles) > 0: choice_emb = discord.Embed(title=":mag_right: YouTube Search Results", description="\n".join(
            f"`{x+1}` | [{str(titles[x])}](http://youtu.be/{ids[x]})\n" for x in range(len(searches["items"]))), color=discord.Colour.random())
        else: return await ctx.send(":x: Couldn't get any results in Youtube!`")
        choice_emb.set_footer(text=str(self.client.user.name))
        choice_emb.timestamp = discord.utils.utcnow()
        self.last_search[str(ctx.guild.id)] = await ctx.send(embed=choice_emb)
        sent2 = await ctx.send("`Please enter your choice. Or write \"cancel\" to cancel the search session.`")
        try:
            msg = await self.client.wait_for("message", check=lambda msg: msg.author.id == ctx.author.id, timeout=40)
        except asyncio.TimeoutError:
            with contextlib.suppress(discord.errors.Forbidden):
                await sent2.edit(content=":warning: Session timed out!`")
                return
        else:
            ch = msg.content.lstrip(ctx.prefix)
            if not ch.isdigit():
                if msg.content.lower().startswith('-s'):
                    with contextlib.suppress(discord.errors.Forbidden):
                        await sent2.delete()
                elif ch.lower() == "cancel":
                    await sent2.delete()
                    return await ctx.send(":white_check_mark: Session cancelled successfully!`")
            else:
                if int(ch) not in range(1, len(searches["items"])+1):
                    return await ctx.send(":x: Invalid choice! Please search again!`")
                if len(self.links[str(ctx.guild.id)]) > 0:
                    self.links[str(ctx.guild.id)].append(f"http://www.youtube.com/watch?v={ids[int(ch)-1]}/")
                    self.requesters[str(ctx.guild.id)].append(ctx.author)
                    self.song_queue[str(ctx.guild.id)].append(str(titles[int(ch)-1]))
                    return await ctx.send(f":white_check_mark: \"{str(titles[int(ch)-1])}\" added to queue!`")
                else:
                    await ctx.invoke(self.play_, url=f"http://www.youtube.com/watch?v={ids[int(ch)-1]}/")


    @commands.hybrid_command(name='seek', aliases=['fd', 'forward', 'setpos', "set-pos"], description="Forwards a song to the given timestamp")
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    async def seek_(self, ctx: commands.Context, timestamp_in_seconds: Optional[str] = "00"):
        if ctx.author.voice is None:
            return await ctx.send("\U0000274C `Please connect yourself to a voice channel`")
        if ctx.voice_client is None or not ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
            return await ctx.send("\U0000274C `Please play a song to set its timestamp position.`")
        if ctx.author.voice.channel.id != ctx.voice_client.channel.id:
            return await ctx.send("\U0000274C `You must be connected to the same voice channel to use music commands!`")
        try:
            if ":" in timestamp_in_seconds:
                times = timestamp_in_seconds.split(":")
                mins, secs = float(times[0]), float(times[1])
                timestamp_in_seconds = mins*60 + secs
                timestamp = self.format_time(mins=round(mins), secs=round(secs))
            else:
                timestamp_in_seconds = int(timestamp_in_seconds)
                mins, secs = divmod(timestamp_in_seconds, 60)
                timestamp = self.format_time(mins=mins, secs=secs)
        except ValueError:
                return await ctx.send("\U0000274C `Invalid time format! Supported formats are : '1:50' or '110'`")
        if not (1 < timestamp_in_seconds < ctx.voice_client.source.time):
            await ctx.send("\U0000274C `Cannot set that position! Given timestamp is not within the song's duration.`")
            return  # Return a warning if user tries to set timestamp BEYOND the song duration -.- huh!
        try:
            ctx.voice_client.source = MusicSource(
                discord.FFmpegPCMAudio(
                    ctx.voice_client.source.url, 
                    before_options=f'-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -ss {timestamp_in_seconds}', 
                    options=f'-vn -af bass=g={self.bass[str(ctx.guild.id)]}'
                    ), 
                    volume=self.vol[str(ctx.guild.id)], 
                    data=ctx.voice_client.source.data
                )
        except AttributeError:
            return await ctx.send(":warning: Error in forwarding timestamp. Please try again!`")
        prefix = ctx.prefix
        self.current_timestamp[str(ctx.guild.id)] = time() - timestamp_in_seconds
        self.total_pause_time[str(ctx.guild.id)] = 0
        self.last_pause_time[str(ctx.guild.id)] = 0
        return await ctx.send(content=f":fast_forward: Timestamp position is set to {timestamp}. Use '{prefix}replay' to instantly restart the song.`")


    @seek_.error
    async def seek_error(self, ctx: commands.Context, err):
        if isinstance(err, commands.MissingPermissions):
            return await ctx.send("`\U0000274CYou need manage messages permission to set timestamp position of a song!`")
        elif isinstance(err, commands.CheckFailure):
            return
        else:
            await self.client.dm_error_logs(err)

    @commands.hybrid_command(name="loop", aliases=["autoreplay", "autorepeat", "autoloop", "ar"], description="auto-loop switch for the currently playing music.")
    @commands.guild_only()
    async def song_loop(self, ctx: commands.Context):
        if ctx.voice_client is None:
            return await ctx.send(":warning: Not playing any music currently.`")
        prefix = ctx.prefix
        self.loop[str(ctx.guild.id)] = not self.loop[str(ctx.guild.id)]  # Setting the opposite state 
        msg = f":repeat_one: Enabled loop! Use '{prefix}loop' to disable it again.`" if self.loop[str(ctx.guild.id)] else f":ballot_box_with_check: Disabled loop! Use {prefix}loop to enable it again.`"
        return await ctx.send(msg)


    @commands.hybrid_command(name="replay", aliases=["restart", "play-again", "playagain"], description="Instantly restarts the a song.")
    @commands.guild_only()
    async def replay_(self, ctx: commands.Context):
        if ctx.author.voice is None:
            return await ctx.send("`\U0000274CPlease connect to a voice channel first!`")
        if ctx.voice_client is None or not ctx.voice_client.is_playing():
            return await ctx.send(f"`\U0000274CNothing's playing currently! Use {ctx.prefix}play command to play a song.`")
        if ctx.author.voice.channel.id != ctx.voice_client.channel.id:
            return await ctx.send("`\U0000274CYou must be connected to the same voice channel to use music commands!`")
        try:
            ctx.voice_client.source = MusicSource(
                discord.FFmpegPCMAudio(
                    ctx.voice_client.source.url, before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -ss 00', 
                    options=f'-vn -af bass=g={self.bass[str(ctx.guild.id)]}'
                    ), 
                    volume=self.vol[str(ctx.guild.id)], 
                    data=ctx.voice_client.source.data
                )
        except AttributeError:
            return await ctx.send(":warning: Error in restarting music! Please try again.`")
        else:
            prefix = ctx.prefix
            self.current_timestamp[str(ctx.guild.id)] = time()
            self.total_pause_time[str(ctx.guild.id)] = 0
            self.last_pause_time[str(ctx.guild.id)] = 0
            return await ctx.send(f":track_previous: Music has been restarted. Use '{prefix}loop' to enable auto repeat current song.`")


    @commands.hybrid_command(name='queue', aliases=["list", "playlist", 'q'], description="Shows the current playlist.")
    @commands.guild_only()
    async def queue_(self, ctx: commands.Context):
        if ctx.voice_client is None or len(self.links[str(ctx.guild.id)]) == 0 or len(self.song_queue[str(ctx.guild.id)]) == 0 or ctx.voice_client.source is None:
            return await ctx.send(":warning: Currently the playlist is empty!`")
        pager = commands.Paginator(max_size=1966)
        try:
            for x in range(len(self. links[str(ctx.guild.id)])): 
                pager.add_line(f"\t{x+1}. \
{self.song_queue[str(ctx.guild.id)][x].title()}[Requested by: {self.requesters[str(ctx.guild.id)][x]}]") if x else pager.add_line(f"\t{x+1}. {self.player[str(ctx.guild.id)].title} <Now Playing>")
        except IndexError:
            return await ctx.send(":warning: Error! ...`")
        embs = list()
        for p in pager.pages:
            queue_embed = discord.Embed(
                title=":notes: Current Playlist",
                description=p,
                color=ctx.author.color
            )
            queue_embed.set_footer(text=str(self.client.user.name))
            queue_embed.timestamp = discord.utils.utcnow()
            embs.append(queue_embed)
        self.paginator[str(ctx.guild.id)] = pygicord.Paginator(pages=embs, compact=False, has_input=False, timeout=60)
        await self.paginator[str(ctx.guild.id)].start(ctx=ctx)


    @commands.command(name='insert')
    @commands.guild_only()
    @commands.is_owner()  #Available only for me because it needs tests, optimization and also exception handling which will be done later
    async def insert_(self, ctx: commands.Context, index: Optional[int]=0, *, url: str=None):
        if ctx.author.voice is None:
            return await ctx.send("\U0000274C `You are not connected to any voice!`")
        if ctx.voice_client is None or len(self.links[str(ctx.guild.id)]) <= 0:
            return await ctx.send(":o: Currently the playlist is empty!`")
        if ctx.author.voice.channel.id != ctx.voice_client.channel.id:
            return await ctx.send("\U0000274C `You must be connected to the same voice channel to use music commands!`")
        if index is None or index <= 0:
            return await ctx.send("\U0000274C `Invalid index! Please specify the index number of the song in the playlist.`")
        if index == 1:
            return await ctx.send("\U0000274C `Cannot insert before the currently playing song! Index value must be at least 2.`")
        if index > len(self.links[str(ctx.guild.id)]):
            return await ctx.send(f"`Index number must be less than the number of songs in the queue! Use the {ctx.prefix}play command to append a song to the queue.`")
        try:
            if url.startswith(("http://", "https://")) or url.endswith('.com'):
                if url.startswith(("http://youtu.be", "https://youtu.be", "https://www.youtube.com/watch?v=")):
                    #  Showing exact name instead of showing the url
                    self.links[str(ctx.guild.id)].insert(index - 1, url)
                    try:
                        song_name = await MusicSource.get_youtube_track_info(loops=self.client.loop, ctx=ctx, url=url)
                    except youtube_dl.utils.DownloadError:
                        await ctx.send("`\U0000274CThere was a problem while fetching this link! Please provide a song name.`")
                        if ctx.voice_client.is_playing():
                            return ctx.voice_client.stop()
                        else:
                            await self.next_song(ctx=ctx)
                    if isinstance(song_name, discord.Message):
                        return
                elif url.startswith(("https://open.spotify.com/track/", "http://open.spotify.com/track/")):
                    song_name = await MusicSource.get_spotify_track_info(url, True)
                    self.links[str(ctx.guild.id)].append(song_name)
                else:
                    await ctx.send(":x: Unsupported url! Please provide a YouTube Url or a Spotify track Url or a song name.`")
                    return
            else:
                self.links[str(ctx.guild.id)].insert(index - 1, url)
                song_name = url
            self.requesters[str(ctx.guild.id)].insert(index - 1, ctx.author)
            self.song_queue[str(ctx.guild.id)].insert(index - 1, song_name)
        except IndexError:
            return await ctx.send(f"\U0000274C `Index number must be less than or equal to the length of the playlist.`")
        else:
            return await ctx.send(f":white_check_mark: Successfully inserted '{song_name}' at index number {index} of the queue.`")


    @commands.hybrid_command(name="remove", aliases=["rmv", "remv", "delete"], description="Removes a song from the playlist")
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    async def remove_(self, ctx: commands.Context, index: Optional[int] = None):
        if ctx.author.voice is None:
            return await ctx.send("\U0000274C `You are not connected to any voice!`")
        if ctx.voice_client is None or len(self.links[str(ctx.guild.id)]) <= 0:
            return await ctx.send(":o: Currently the playlist is empty!`")
        if ctx.author.voice.channel.id != ctx.voice_client.channel.id:
            return await ctx.send("\U0000274C `You must be connected to the same voice channel to use music commands!`")
        if index is None or index <= 0:
            return await ctx.send("\U0000274C `Invalid index! Please specify the index number of the song in the playlist.`")
        prefix = ctx.prefix
        if index == 1:
            return await ctx.send(f"\U0000274C `Cannot delete currently playing song! You can use '{prefix}skip' to skip this song.`")
        try:
            self.links[str(ctx.guild.id)].pop(index - 1)
            self.requesters[str(ctx.guild.id)].pop(index - 1)
            removed = self.song_queue[str(ctx.guild.id)].pop(index - 1)
        except IndexError:
            return await ctx.send(f"\U0000274C `There's no song at index number {index} of the playlist. Use '{prefix}clearall' to clear whole playlist.`")
        else:
            return await ctx.send(f":white_check_mark: \"{removed}\" has been removed from the playlist. Use '{prefix}clearall' to clear whole playlist.`")

    @remove_.error
    async def remv_error(self, ctx: commands.Context, err):
        if isinstance(err, commands.MissingPermissions):
            return await ctx.send("\U0000274C `You must have manage messages permission to remove a song from the playlist!`")
        elif isinstance(err, commands.CheckFailure):
            return
        else:
            await self.client.dm_error_logs(err)

    @commands.hybrid_command(name="clearall", aliases=["rmvall", "clearplaylist", "remvall", "ra", "clearqueue", "clearq"], description="Deletes the whole playlist.")
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    async def clear_queue(self, ctx: commands.Context):
        if ctx.author.voice is None:
            return await ctx.send("\U0000274C `You are not connected to any voice!`")
        if ctx.voice_client is None or len(self.links[str(ctx.guild.id)]) == 0:
            return await ctx.send(":warning: Currently the playlist is empty!`")
        if ctx.author.voice.channel.id != ctx.voice_client.channel.id:
            return await ctx.send("\U0000274C `You must be connected to the same voice channel to use music commands!`")
        self.loop[str(ctx.guild.id)] = False
        self.clear_all(ctx)
        await ctx.send(":white_check_mark: Successfully cleared the whole playlist!`")
        return ctx.voice_client.stop()

    @clear_queue.error
    async def queue_delete_err(self, ctx: commands.Context, err):
        if isinstance(err, commands.MissingPermissions):
            return await ctx.send("\U0000274C `You must have manage messages permission to delete the whole playlists!`")
        elif isinstance(err, commands.CheckFailure):
            return
        else:
            await self.client.dm_error_logs(err)


    @commands.command(name="lyrics", aliases=["lyric", "ly", "lyrix"], description="Gets lyrics for the currently song!")
    @commands.guild_only()
    async def lyrics_(self, ctx: commands.Context, *, song_name: Optional[str] = ""):
        loop = self.client.loop
        try:
            time_out = (ctx.voice_client.source.time-(self.get_current_time(ctx))) if ctx.voice_client is not None and ctx.voice_client.source is not None and ctx.voice_client.source.time != 0 else 180
        except KeyError:
            time_out = 180
        load_moji = self.client.infinity_emoji
        if not song_name:
            if ctx.voice_client is None or ctx.voice_client.source is None:
                return await ctx.send("\U0000274C `Please provide a song name or play a song to find its lyrics!`")
            if ctx.voice_client.source.second_title is not None:
                song_name = ctx.voice_client.source.second_title + " " + (ctx.voice_client.source.artist).split(',')[0] if ctx.voice_client.source.artist != "unknown" else ctx.voice_client.source.second_title
            else:
                if any(x in self.links[str(ctx.guild.id)][0] for x in ("https://", "http://", "youtu.be", "youtube.", "spotify.", "open.")):
                        words_filter = "official new video song (official video) official music video ( ) { } [ ] | \ / ' \" ; : @ # _ - + 1 2 3 4 5 6 7 8 9 0 ".split()
                        music = str(ctx.voice_client.source.title).lower().split()
                        try:
                            song_name = " ".join(music[x] for x in range(4) if music[x] not in words_filter)
                        except IndexError:
                            song_name = str(ctx.voice_client.source.title)
                else:
                    song_name = " " + self.links[str(ctx.guild.id)][0]
                    song_name = (ctx.voice_client.source.artist).split(',')[0] + song_name if ctx.voice_client.source.artist != "unknown" else song_name
            await ctx.send("{1} `Searching Lyrics for: '{0.title}'......`".format(ctx.voice_client.source, load_moji), delete_after=3)
            part = functools.partial(self.lyricsextractor.search_song, song_name)
            song = await loop.run_in_executor(None, part)
            if song is None:
                return await ctx.send(f"`\U0000274CCould not find lyrics for this song!\nTry {ctx.prefix}lyrics <song_artist and song_name>`", delete_after=5)
        else:
            await ctx.send(f"{load_moji} `Searching Lyrics for: '{song_name}'......`", delete_after=3)
            part = functools.partial(self.lyricsextractor.search_song, song_name)
            song = await loop.run_in_executor(None, part)
            if song is None:
                return await ctx.send(f"`\U0000274CCould not find lyrics for this song!\nTry {ctx.prefix}lyrics <song_artist and song_name>`")
        if song.lyrics.lower() == "[instrumental]" or song.lyrics.lower() == '(instrumental)': return await ctx.send("```\nThis song is instrumental only.\n```")
        else: ly = "**" + song.title + "**" + "\n\n" + str(song.lyrics)
        pager = commands.Paginator(suffix=None, prefix=None, max_size=1980, linesep="\n")
        lines = ly.splitlines()
        for line in lines: pager.add_line(line)
        embs = []
        for page in pager.pages: emb = discord.Embed(title="Lyrics: "+song.title, description=page, colour=ctx.author.color, timestamp=discord.utils.utcnow()); emb.set_footer(text=str(self.client.user.name)); embs.append(emb)
        self.paginator[str(ctx.guild.id)] = pygicord.Paginator(pages=embs, timeout=time_out, compact=False, has_input=False)
        await self.paginator[str(ctx.guild.id)].start(ctx)
    
    @lyrics_.error 
    async def lyrics_search_error(self, ctx, err):
        if isinstance(err, discord.DiscordException):
            with contextlib.suppress(discord.Forbidden, discord.NotFound):
                return await ctx.send(":x: An unknown Error occurred! Please try again later.`")
        else:
            return

    @commands.hybrid_command(name="now-playing", aliases=["now", "np", "nowplaying", "info"], description="Shows some extra info of the currently playing song.")
    @commands.guild_only()
    async def now_playing(self, ctx: commands.Context):
        if ctx.voice_client is None or ctx.voice_client.source is None:
            return await ctx.send("\U0000274C `Nothing is being played at the moment.`")
        total_duration = ctx.voice_client.source.time
        if total_duration > 0:
            crnt_time = self.get_current_time(ctx)
            mins, secs = divmod(crnt_time, 60)
            current_time = self.format_time(mins=round(mins), secs=round(secs))
            try: full_mins, full_secs = divmod(total_duration, 60)
            except (TypeError, ValueError, ZeroDivisionError):
                full_mins = 0
                full_secs = 0
                duration = " :infinity: "
            else: duration = self.format_time(mins=round(full_mins), secs=round(full_secs))
        else: duration = " :infinity: "
        try: pointer_pos = round((crnt_time / total_duration) * 30)
        except ZeroDivisionError: timeline = "🔘"+("▬"*29)
        else: 
            timeline = str()
            for x in range(1, 31): timeline += "▬" if x != pointer_pos else '🔘'
        prefix = ctx.prefix
        name = ctx.voice_client.source.title
        web_link = ctx.voice_client.source.link
        artists = ctx.voice_client.source.artist
        requested_by = self.requesters[str(ctx.guild.id)][0]
        sound = ctx.voice_client.source.volume * 100
        basses = self.bass[str(ctx.guild.id)] * 10
        emoji = self.client.get_emoji(861535416175951872) if web_link.startswith("https://open.spotify.com/track") else self.client.get_emoji(883035973116629033)
        np_embed = discord.Embed(
            title=f"{emoji} Now Playing",
            description=f"**__Currently Playing__**: [{name}]({web_link})",
            color=ctx.author.color
        )
        np_embed.add_field(name="Artists :microphone:", value=f"`{artists}`", inline=True)
        np_embed.add_field(name="Requested by :headphones: ", value=f"`{requested_by}`", inline=True)
        np_embed.add_field(name="Volume :loud_sound:", value=f"`{round(sound)}%`", inline=True)
        np_embed.add_field(name="Bass :loudspeaker: ", value=f"`{round(basses)}%`", inline=True)
        np_embed.add_field(name="Others", value=f"Auto-replay-current-song: {'on' if self.loop[str(ctx.guild.id)] else 'off'}\nAuto-replay-playlist: [Coming Soon]\nUse '{prefix}playlist' to see the whole playlist!`")
        np_embed.add_field(name="Timeline :stopwatch:", value=f"`{timeline}`\n{' ' * 43}{current_time}/{duration}", inline=False)
        np_embed.set_thumbnail(url=ctx.voice_client.source.img)
        np_embed.set_footer(text=f"{self.client.user.name}")
        np_embed.timestamp = discord.utils.utcnow()
        with contextlib.suppress(TypeError, KeyError, discord.errors.HTTPException, discord.errors.Forbidden):
            await self.last_message[str(ctx.guild.id)].clear_reactions()
        self.shall_respond_to_reactions[str(ctx.guild.id)] = False
        self.last_message[str(ctx.guild.id)] = await ctx.send(embed=np_embed)
        await self.set_btns(ctx=ctx, last_message=self.last_message[str(ctx.guild.id)])

    @commands.hybrid_command(name="pause", aliases=["wait", "w8", "pau", "stop", "w"], description="Pause a song.")
    @commands.guild_only()
    async def pause_(self, ctx: commands.Context):
        if ctx.author.voice is None or ctx.voice_client is None:
            return await ctx.send("\U0000274C `Please connect to a voice channel first!`")
        if ctx.author.voice.channel.id != ctx.voice_client.channel.id:
            return await ctx.send("\U0000274C `You must be connected to the same voice channel to use music commands!`")
        prefix = ctx.prefix
        if ctx.voice_client.is_paused():
            return await ctx.send(f"\U000027A0 `Already paused! Use '{prefix}resume' to resume the song.`")
        ctx.voice_client.pause()
        self.last_pause_time[str(ctx.guild.id)] = time()
        await ctx.send(f":pause_button: Music paused! Use '{prefix}resume' to resume the song.`")
        await self.start_counting(ctx)

    @commands.hybrid_command(name="resume", aliases=["continue", "res", "cont", "c", "r"], description="Resume a song")
    @commands.guild_only()
    async def resume_(self, ctx: commands.Context):
        if ctx.author.voice is None or ctx.voice_client is None:
            return await ctx.send("\U0000274C `Please connect to a voice channel first!`")
        if ctx.author.voice.channel.id != ctx.voice_client.channel.id:
            return await ctx.send("\U0000274C `You must be connected to the same voice channel to use music commands!`")
        prefix = ctx.prefix
        if ctx.voice_client.is_playing():
            return await ctx.send(f":warning: Already playing a song! Use '{prefix}pause' to pause the song!`")
        ctx.voice_client.resume()
        self.total_pause_time[str(ctx.guild.id)] += time() - self.last_pause_time[str(ctx.guild.id)]
        self.last_pause_time[str(ctx.guild.id)] = 0
        return await ctx.send(f":arrow_forward: Song resumed. Use '{prefix}pause' to pause the song!`")

    @commands.hybrid_command(name="skip", aliases=["next", "nxt", "voteskip"], description="Vote to skip the currently playing song!")
    @commands.guild_only()
    async def vote_skip(self, ctx: commands.Context):
        if ctx.author.voice is None:
            return await ctx.send("`\U0000274CPlease connect to a voice before using this command!`")
        if ctx.voice_client is None or ctx.voice_client.source is None:
            return await ctx.send("`\U0000274CNothing is being played at the moment!`")
        if ctx.author.voice.channel.id != ctx.voice_client.channel.id:
            return await ctx.send("`\U0000274CYou must be connected to the same voice channel to use music commands!`")
        if ctx.author.id not in self.voted_for_skip[str(ctx.guild.id)]:
            self.voted_for_skip[str(ctx.guild.id)].append(ctx.author.id)
            await ctx.send(f":track_next: {ctx.author} voted to skip the song`")
        else:
            return await ctx.send("\U0000274C `You have already voted for skip!`")
        membs = tuple(mem.id for mem in ctx.voice_client.channel.members if mem.id != self.client.user.id)
        required_votes = len(membs) *(3/4)
        if len(self.voted_for_skip[str(ctx.guild.id)]) >= floor(required_votes):
            await ctx.send(":thumbsup: Skipped the song successfully!`")
            self.voted_for_skip[str(ctx.guild.id)].clear()
            if self.loop[str(ctx.guild.id)]:
                try:
                    self.get_next(ctx)
                except IndexError:
                    self.clear_all(ctx)
                else:
                    self.music_is_skipped = True
            ctx.voice_client.stop()
        else:
            prefix = ctx.prefix
            await ctx.send(f"`Got {len(self.voted_for_skip[str(ctx.guild.id)])} votes. Required {floor(required_votes)} votes! Use '{prefix}forceskip' to forcefully skip a song!`")

    @commands.hybrid_command(name='skipto', aliases=['fsto', 'forceskipto', 'nextto'], description="Skips and plays a song at a given index number!")
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    async def skip_to(self, ctx: commands.Context, indx: Optional[int]=0):
        if ctx.author.voice is None:
            return await ctx.send("\U0000274C `Please connect to a voice before using this command!`")
        if ctx.voice_client is None or ctx.voice_client.source is None:
            return await ctx.send("\U0000274C `Nothing is being played at the moment!`")
        if ctx.author.voice.channel.id != ctx.voice_client.channel.id:
            return await ctx.send("\U0000274C `You must be connected to the same voice channel to use music commands!`")
        if indx <= 0:
            return await ctx.send(":x: Please provide an index number to skip upto that song!`")
        if indx < 2:
            prefix = ctx.prefix
            return await ctx.send(f":x: Index number should be more than or equal to 2 or you can use the {prefix}skip command!`")
        if indx <= len(self.links[str(ctx.guild.id)]):
            if not self.loop[str(ctx.guild.id)]:
                del self.links[str(ctx.guild.id)][:indx-2]
                del self.song_queue[str(ctx.guild.id)][:indx-2]
                del self.requesters[str(ctx.guild.id)][:indx-2]
            else:
                del self.links[str(ctx.guild.id)][:indx-1]
                del self.song_queue[str(ctx.guild.id)][:indx-1]
                del self.requesters[str(ctx.guild.id)][:indx-1]
        else:
            return await ctx.send(":x: Index number can't be more than the playlist length!`")
        self.music_is_skipped = True
        ctx.voice_client.stop()
        return await ctx.send(f":track_next: Skipped upto song no. {indx} of the playlist successfully!\nNow Playing: '{self.song_queue[str(ctx.guild.id)][0] if self.loop[str(ctx.guild.id)] else self.song_queue[str(ctx.guild.id)][1]}'`")

    @skip_to.error
    async def skipto_error(self, ctx: commands.Context, err):
        if isinstance(err, commands.MissingPermissions):
            return await ctx.send("\U0000274C `You need manage messages permission to skipto a song!`")
        if isinstance(err, commands.CheckFailure):
            return
        else:
            await self.client.dm_error_logs(err)

    @commands.hybrid_command(name="forceskip", aliases=["fs", "force-skip"], description="Forcibly Play the next song of the playlist.")
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    async def skip_force(self, ctx: commands.Context):
        if ctx.author.voice is None:
            return await ctx.send("\U0000274C `Please connect to a voice before using this command!`")
        if ctx.voice_client is None or ctx.voice_client.source is None:
            return await ctx.send("\U0000274C `Nothing is being played at the moment!`")
        if ctx.author.voice.channel.id != ctx.voice_client.channel.id:
            return await ctx.send("\U0000274C `You must be connected to the same voice channel to use music commands!`")
        if self.loop[str(ctx.guild.id)]:
            self.voted_for_skip[str(ctx.guild.id)] = list()
            try:
                self.get_next(ctx)
            except IndexError:
                self.clear_all(ctx)
            finally:
                self.music_is_skipped = True
        ctx.voice_client.stop()
        await ctx.message.add_reaction("\U0001F90D")
        return await ctx.send(f":track_next: Music has been forceskipped!`")

    @skip_force.error
    async def skip_error(self, ctx: commands.Context, err):
        if isinstance(err, commands.MissingPermissions):
            prefix = ctx.prefix
            return await ctx.send(f"\U0000274C `Please use {prefix}skip instead of {prefix}forceskip! You must have manage messages permission to forcefully skip a song without votes!`")
        if isinstance(err, commands.CheckFailure):
            return
        else:
            await self.client.dm_error_logs(err)

    @commands.hybrid_command(name='leave', aliases=["dc", "disconnect", "go", "fuck-off", 'fuckoff'], description="Disconnect from a voice channel.")
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    async def leave_(self, ctx: commands.Context):
        if ctx.voice_client is None:
            return await ctx.send(":warning: Not connected to voice!`")
        if ctx.author.voice is None:
            return await ctx.send("\U0000274C `You are not connected to any voice channel!`")
        if ctx.author.voice.channel.id != ctx.voice_client.channel.id:
            return await ctx.send("\U0000274C `You must be connected to the same voice channel to use music commands!`")
        with contextlib.suppress(TypeError, KeyError, discord.errors.HTTPException, discord.errors.Forbidden):
            await self.last_message[str(ctx.guild.id)].clear_reactions()
        await ctx.voice_client.disconnect()
        prefix = ctx.prefix
        self.shall_respond_to_reactions[str(ctx.guild.id)] = False
        self.clear_all(ctx)
        self.loop[str(ctx.guild.id)] = False
        print("--Disconnected vc from {0.name}-- after {1} seconds".format(ctx.guild, round(time()-self.start_timer[str(ctx.guild.id)])))
        return await ctx.send(f":white_check_mark: Disconnected from voice channel successfully! Use '{prefix}clearall' to clear whole playlist!`")

    @leave_.error
    async def dc_error(self, ctx: commands.Context, exception):
        if isinstance(exception, commands.MissingPermissions):
            return await ctx.send("\U0000274C `You need manage messages permission to disconnect me from voice.`")
        else:
            await self.client.dm_error_logs(err=exception)

    @commands.command(name="m:eval", aliases=["m:ev", "m:evaluate"])
    @commands.is_owner()
    async def m_eval(self, ctx, *, cmd:str):
        if "input(" in cmd.lower() or "input (" in cmd.lower():
            return await ctx.send(":x: Cannot Execute input method!`")
        cmd = cmd.strip('`')
        try:
            result = eval(str(cmd))
        except Exception as e:
            result = f"{e.__class__.__name__}: {e}"
        finally:
            cmd_emb = discord.Embed(description=f"{result or '<no output>'}")
            return await ctx.send(embed=cmd_emb)



async def setup(client):
    print("This is old Music commands. This one is disabled permanently!")
    #print("Setting up Music....")
    #await client.add_cog(Music(client))

#async def teardown(client):
    #print("Unloading Music")
    #await client.remove_cog(Music(client))
    
