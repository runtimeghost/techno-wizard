# pylint: disable=bad-indentation,used-before-assignment,unspecified-encoding,wildcard-import,unused-wildcard-import,eval-used,broad-exception-caught,invalid-overridden-method,subprocess-run-check
#| Same music commands from old music extension but totally rewritten
#| Needs java in this environment to run Lavalink.jar
#| To download Lavalink.jar, open a terminal on the home directory of this project and
#| run the following command in terminal
#| wget "https://github.com/freyacodes/Lavalink/releases/download/3.7.3/Lavalink.jar"

#| Alternative way is to download Lavalink.jar from official github repository
#| and move it to the home directory of this project

#| without java in the environment we may use already hosted lavalink servers

# from icecream import ic #debugging purpose

from dotenv import load_dotenv
import json
from discord.ext import commands
import wavelink
from aiohttp.web_exceptions import HTTPError
import discord
from os import environ
import typing
from bot_ui import *
# import lyricsgenius
from contextlib import suppress
import re
from yt_dlp import YoutubeDL
import datetime


#| Setting up environment Variables
load_dotenv()


async def voice_state(ctx):
	if isinstance(ctx, discord.Interaction):
		ctx = commands.Context.from_interactio(ctx)
	if ctx.author.voice is None:
		await ctx.send(":x: You are not connected to any voice channel!")
		return False
	if ctx.voice_client is None:
		await ctx.send(":x: I'm not connected to any voice channel currently!")
		return False
	if ctx.author.voice.channel != ctx.voice_client.channel:
		await ctx.send(":warning: We are not in the same voice channel!")
		return False
	return True


class Music(commands.Cog):

	wavenode: wavelink.Node
	client: commands.Bot

	def __init__(self, client: commands.Bot):
		self.client = client
		# self.lyrics_searcher = lyricsgenius.Genius(
		# 	access_token=environ.get("LYRICS_API"),
		# 	timeout=20,
		# 	verbose=False,
		# 	response_format='plain'
		# )
		self.queue = wavelink.Queue()
		self.ytdl_client = YoutubeDL(
			{
				'quiet': True,
				'noplaylist': True,
				'youtube_include_dash_manifest': False,
				'youtube_include_hls_manifest': False,
				'format': 'bestaudio/best'
			}
		)
		self.vcs: dict = {}
		self.BASE_URL = re.compile('https?://(?:www\\.)?.+')
		self.SOUNDCLOUD_URL = re.compile('((?:https?:)?\\/\\/)?((?:www|m)\\.)?soundcloud.com\\/.*/.*')
		self.SPOTIFY_URL = re.compile('https?://open.spotify.com/(?P<type>album|playlist|track|artist)/(?P<id>[a-zA-Z0-9]+)')
		self.YOUTUBE_PLAYLIST_URL = re.compile('^((?:https?:)?\\/\\/)?((?:www|m)\\.)?((?:youtube\\.com|youtu.be))/playlist\\?list=.*')
		self.YOUTUBE_URL = re.compile('^((?:https?:)?\\/\\/)?((?:www|m)\\.)?((?:youtube\\.com|youtu.be))(\\/(?:[\\w\\-]+\\?v=|embed\\/|v\\/)?)([\\w\\-]+)(\\S+)?$')
		# self.AM_URL = re.compile('https?://music.apple.com/(?P<country>[a-zA-Z]{2})/(?P<type>album|playlist|song|artist)/(?P<name>.+)/(?P<id>[^?]+)')


	async def cog_command_error(self, ctx, error):
		if isinstance(error, commands.errors.MissingPermissions):
			return await ctx.send(f":x: {str(error)}")
		elif isinstance(error, AttributeError):
			return await ctx.send(":x: Error while processing command!")
		elif isinstance(error, HTTPError):
			if error.status==403:
				return await ctx.send(":x: Error: 403 client error!")
		else:
			return None

	async def connect_voice_node(self):
		self.wavenode = await wavelink.Pool.connect(
			nodes=[
				wavelink.Node(
					uri=environ.get("LAVALINK_URL"),
					password="youshallnotpass",
				)
			],
			client=self.client,
			cache_capacity=None
			)

	# A check whether the member has a dj role
	async def cog_check(self, ctx: commands.Context, member: discord.Member=None) -> bool:
		member = member or ctx.author
		if member.id == self.client.user.id:
			return False
		with open("./database/djonly_role_id.json", "r") as dj_roles:
			djrole = json.load(dj_roles)
		try:
			if djrole[str(ctx.guild.id)] is None:
				return True
			else:
				ids = tuple(str(role.id) for role in member.roles)
				if djrole[str(member.guild.id)] not in ids and ctx.guild.owner_id != member.id:
					await ctx.send(":warning: I am currently in DJ only mode!")
					return False
				else:
					return True
		except KeyError:
			djrole[str(ctx.guild.id)] = None
			with open("./database/djonly_role_id.json", "w") as dj_roles:
				json.dump(djrole, dj_roles, indent=8)
			return True

	def unformatted_time(self, time: typing.Union[str, float]):
		if isinstance(time, float):
			return int(time*1000)
		else:
			try:
				if ":" in str(time):
					times = str(time).split(":")
					mins, secs = int(times[0]), int(times[1])
				else:
					return int(time) * 1000
			except ValueError:
				return 0
			else:
				return (mins*60 + secs)*1000

	async def add_next(self, ctx: commands.Context, source: typing.Union[wavelink.Playlist, wavelink.Playable]) -> str|None:
		vc = ctx.voice_client
		if not source:
			return None
		if isinstance(source, wavelink.Playlist):
			for song in source:
				song.extras = wavelink.ExtrasNamespace({"requester": str(ctx.author), "skips": list(), "channel_id": ctx.channel.id})
			count = vc.queue.put(source)
			await ctx.channel.send(
				f":white_check_mark: Added {count} songs to the playlist! Requested by: {ctx.author.mention}"
				)
		else:
			song: wavelink.Playable = source[0]
			song.extras = wavelink.ExtrasNamespace({"requester": str(ctx.author), "skips": list(), "channel_id": ctx.channel.id})
			vc.queue.put(song)
			if vc.playing:
				if vc.current == song:
					return False
				await ctx.channel.send(f":white_check_mark: Added '{song.title}' to the playlist! Requested by: {ctx.author.mention}")
			if not vc.playing:
				first_song = vc.queue.get()
				await vc.play(first_song, replace=False, add_history=False)
		return True


	async def send_player_embed(self, vc: wavelink.Player):
		track = vc.current
		song_desc = f"""**Title: [{discord.utils.remove_markdown(track.title)}]({track.uri})**
Duration: {formatted_time(track.length)} || Volume: {vc.volume}%"""
		play_embd = discord.Embed(
			title="|Play Music|",
			description=song_desc,
			color=discord.Colour.random(),
			timestamp=discord.utils.utcnow()
		)
		play_embd.add_field(name="Requested by", value=track.extras.requester)
		play_embd.set_image(url=track.artwork)
		play_embd.set_footer(text=self.client.user.name)
		try:
			channel = self.client.get_channel(track.extras.channel_id)
		except AttributeError:
			channel = vc.ctx.channel
		vc.controller = await channel.send(embed=play_embd, view=PlayerButtons(player=vc, timeout=None))

	async def clean_up(self, vc: wavelink.Player, stop: bool=False, destroy: bool=False):
		with suppress(AttributeError):
			view = discord.ui.View.from_message(vc.controller)
			if view:
				for item in view.children:
					item.style = discord.ButtonStyle.secondary
					item.disabled = True
				view.stop()
			with suppress(discord.errors.NotFound):
				await vc.controller.edit(view=view)
		if chanl:=vc.channel:
			destroy = destroy or len(chanl.members) < 2
			if stop:
				with suppress(AttributeError):
					vc.current.extras.skips.clear()
				await vc.skip(force=True)
			if destroy:
				vc.queue.mode = wavelink.QueueMode.normal
				await vc.disconnect()

	@commands.Cog.listener()
	async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
		print(f"Successfully connected Wavelink {payload.node.identifier}")

	@commands.Cog.listener()
	async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):
		player = payload.player
		if not player:
			return None
		if player.queue.mode == wavelink.QueueMode.normal:
			await self.send_player_embed(player)

	@commands.Cog.listener()
	async def on_wavelink_track_exception(self, payload: wavelink.TrackExceptionEventPayload):
		player = payload.player
		if not player:
			return None

		await self.clean_up(player, stop=True, destroy=True)
		await self.client.owner.send(
			f"on_wavelink_Track_Exception triggered,\n{payload.exception}\n\n{player}\n{payload.track}"
			)

	@commands.Cog.listener()
	async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
		player = payload.player
		if not player:
			return None
		try:
			if len(player.channel.members) < 2:
				await self.clean_up(player, stop=True, destroy=True)
			else:
				next_song = player.queue.get()
				await player.play(next_song, replace=False, add_history=False)
				if player.queue.mode == wavelink.QueueMode.loop and payload.reason!='finished':
						await self.send_player_embed(player)
		except wavelink.QueueEmpty:
			player.queue.mode = wavelink.QueueMode.normal
			await self.clean_up(player)

	@commands.hybrid_command(
			name="join",
			aliases=["connect", "j"],
			usage='join'
			)
	async def join_voice(self, ctx: commands.Context):
		"""Joins the voice channel you're connected to."""
		if ctx.author.voice is None:
			return await ctx.send(":warning: Connect yourself to a voice channel first!")
		if ctx.voice_client is None:
			channel = ctx.author.voice.channel
			await channel.connect(cls=wavelink.Player, self_deaf=True)
			vc: wavelink.Player = ctx.voice_client
			vc.inactive_timeout = 300
			vc.auto_queue = wavelink.AutoPlayMode.disabled
			vc.ctx = ctx
			vc.controller = None
			vc.autoplay = wavelink.AutoPlayMode.disabled

			await vc.set_volume(75)

			await ctx.send(f":white_check_mark: Connected to voice channnel {channel.name}")
		else:
			if len(ctx.voice_client.channel.members) == 1 and not ctx.voice_client.playing:
				await ctx.voice_client.move_to(ctx.author.voice.channel)
				return await ctx.send(f":ballot_box_with_check: Shifted to {ctx.author.voice.channel.name}")
			else:
				return await ctx.send(f":x: Already connected to {ctx.voice_client.channel.name}")


	@commands.hybrid_command(
			aliases=["p", "song", "yt", "youtube", "spotify"],
			usage='play <song title or url>'
			)
	@discord.app_commands.describe(
		song="The title or the url of the song (Spotify & SoundCloud urls are also supported)"
		)
	@commands.check(voice_state)
	async def play(self, ctx: commands.Context, *, song: str=""):
		"""Play a song from YouTube or spotify"""
		if not song:
			if ctx.voice_client.playing and ctx.voice_client.paused:
				await ctx.voice_client.pause(False)
				return await ctx.send(":arrow_forward: Resumed the song!")
			return await ctx.send(":warning: Please try again providing a song name with the command!")

		if ctx.interaction:
			await ctx.interaction.response.send_message(
				f"{self.client.infinity_emoji} Getting item from YouTube...",
				delete_after=5
				)
		else:
			await ctx.typing()
		try:
			tracks: wavelink.Search = await wavelink.Playable.search(song, source=wavelink.TrackSource.YouTube)
		except wavelink.LavalinkLoadException as e:
			return await ctx.send(":x: " + str(e))
		track_added = await self.add_next(ctx, tracks)
		if track_added is None:
			return await ctx.send(
				f":warning: No song found '{song}'!"
			)
		elif not track_added:
			return await ctx.send(
				f":x: Already playing this song! Use '{ctx.prefix}loop' to start looping over current song!"
			)

	## Neeeds fix
	@commands.hybrid_command(
		aliases=[
		'playfavs', 'playfav', 'playstarred',
		'pfav', 'pfavs', 'playfavorites'
		],
		usage="playfavs [item index from your favourite list]"
	)
	@commands.check(voice_state)
	async def playfavourites(self, ctx, index: typing.Optional[int]=0):
		"""Play songs from your favourites"""
		with open('./database/favourite_tracks.json', 'r') as favfile:
			favs = json.load(favfile)
		failed = []
		try:
			if not favs[str(ctx.author.id)]:
				return await ctx.send(":x: You have no songs in your favourites list!")
		except KeyError:
			return await ctx.send(":x: Your Favourites list is empty!")
		else:
			if inter:=ctx.interaction:
				await inter.response.send_message(f"{self.client.infinity_emoji} `Getting your favourite tracks...", delete_after=3)
			else:
				await ctx.typing()
			if index <= 0:
				for track in favs[str(ctx.author.id)]:
					try:
						song = wavelink.Playable(track["data"])
						song.extras = wavelink.ExtrasNamespace({"requester": str(ctx.author), "skips": list(), "channel_id": ctx.channel.id})
					except wavelink.LavalinkException:
						failed.append(track)
						continue
					else:
						if ctx.voice_client.playing and (track["data"]==ctx.voice_client.current.raw_data or any(s.raw_data==track["data"] for s in ctx.voice_client.queue)):
							continue
						else:
							ctx.voice_client.queue(song)
				if ctx.voice_client.playing:
					await ctx.channel.send(':white_check_mark: Added your favourite songs to the playlist!')
				else:
					with suppress(wavelink.QueueEmpty):
						await ctx.voice_client.play(ctx.voice_client.queue.get(), add_history=False)
			else:
				try:
					song = favs[str(ctx.author.id)][index-1]
					track = wavelink.Playable(song['data'])
					track.extras = wavelink.ExtrasNamespace({"requester": str(ctx.author), "skips": list(), "channel_id": ctx.channel.id})
				except IndexError:
					return await ctx.channel.send(f":x: No song at index {index} of your favourites list!")
				except wavelink.LavalinkException:
					failed.append(song)
				else:
					if ctx.voice_client.playing and (ctx.voice_client.current.raw_data==song['data'] or any(song['data']==t.raw_data for t in ctx.voice_client.queue)):
						return await ctx.send(":x: Already in the playlist!")
					ctx.voice_client.queue(track)
					if ctx.voice_client.playing:
						await ctx.channel.send(f":white_check_mark: Added '{track.title}' to the playlist!")
					else:
						await ctx.voice_client.play(ctx.voice_client.queue.get(), add_history=False)
			if failed:
				tracks = []
				for item in failed:
					result = await wavelink.YouTubeTrack.search(item['title'])
					if not result:
						continue
					track = result[0]
					tracks.extras = wavelink.ExtrasNamespace({"requester": str(ctx.author), "skips": list(), "channel_id": ctx.channel.id})
					if ctx.voice_client.playing and (track==ctx.voice_client.current or track in ctx.voice_client.queue):
						continue
					else:
						ctx.voice_client.queue(track)
					if not ctx.voice_client.playing:
						await ctx.voice_client.play(ctx.voice_client.queue.get(), add_history=False)
					else:
						await ctx.channel.send(":white_check_mark: Finished appending all Tracks!")
				else:
					return await ctx.channel.send(":warning: One or more songs failed to get added! Possible cause: Already in playlist or No results found on YouTube!")


	@commands.hybrid_command(
		aliases=["s", "search", "syt", "ytsearch"],
		usage="searchyt <search term>"
		)
	@discord.app_commands.describe(search_term="The term to search in YouTube")
	@commands.check(voice_state)
	async def searchyt(self, ctx, *, search_term: str=""):
		"""Search the given term in YouTube and let you choose a song"""
		if not search_term:
			return await ctx.send(":x: Please try again providing a term to search in YouTube!")
		if self.BASE_URL.match(string=search_term):
			return await ctx.invoke(self.play, song=search_term)
		if ctx.interaction:
			await ctx.interaction.response.send_message(
				f"{self.client.infinity_emoji} Searching for '{search_term}' in Youtube....",
				delete_after=5
				)
		else:
			await ctx.typing()
		try:
			yttracks: wavelink.Search = await wavelink.Playable.search(search_term, source=wavelink.TrackSource.YouTube)
		except wavelink.LavalinkLoadException as e:
			return await ctx.send(f":x: {e}")
		if not yttracks:
			return await ctx.channel.send(":warning: No results found!")
		choice_embed = discord.Embed(
					title="YouTube Search Results :mag_right:",
					description=f"**The followings are the search results from YouTube matching with `{search_term}`**",
					color=discord.Color.random(),
					timestamp=discord.utils.utcnow()
				)
		choice_view = SearchChoice(
			user=ctx.author,
			timeout=240,
			track_titles=[{'title': track.title, 'channel': track.author} for track in yttracks]
		)
		choice_msg = await ctx.channel.send(embed=choice_embed, view=choice_view)
		await choice_view.wait()
		if choice_view.choice is None:
			for item in choice_view.children:
				item.disabled = True
			await choice_msg.edit(view=choice_view)
			return await ctx.channel.send("Time is up for making a choice. Search again!")
		elif choice_view.choice == "cancel":
			return await ctx.channel.send(":ballot_box_with_check: Search session cancelled.")
		else:
			if ctx.voice_client is None:
				return
			track = yttracks[int(choice_view.choice)]
			track.extras = {"requester": str(ctx.author), 'skips': list(), "channel_id": ctx.channel.id}
			if ctx.voice_client.current is not None and ctx.voice_client.current == track:
				return await ctx.send(f":x: Already playing this song! Use `{ctx.prefix}loop` to start looping over current song!")
			ctx.voice_client.queue.put(track)
			if ctx.voice_client.playing:
				return await ctx.channel.send(f":white_check_mark: Added **'{discord.utils.remove_markdown(track.title)}'** to the playlist!")
			else:
				await ctx.voice_client.play(ctx.voice_client.queue.get(), add_history=False)


	@commands.hybrid_command(
			aliases=["restartsong", "replaysong", "r", "restart"],
			usage="replay"
			)
	@commands.check(voice_state)
	@commands.has_guild_permissions(manage_messages=True)
	async def replay(self, ctx):
		"""Instantly restart the currently playing song"""
		if not ctx.voice_client.playing:
			return await ctx.send(":x: Nothing is being played currently!")
		await ctx.voice_client.seek()
		await ctx.send(":rewind: Restarted current song!")


	@commands.hybrid_command(
			aliases=['setpos', 'pos', 'timestamp', 'settimestamp'],
			usage="seek <min:sec>"
			)
	@discord.app_commands.describe(timestamp="The position of the timestamp to set. e.g: 01:53")
	@commands.check(voice_state)
	@commands.has_guild_permissions(manage_messages=True)
	async def seek(self, ctx, *, timestamp=None):
		"""Seek forward to a given timestamp position of a song"""
		if not ctx.voice_client.playing:
			return await ctx.send(":x: Currently no song is being played!")
		if not timestamp:
			return await ctx.send(":x: Please try again and provide the position of the song in this format -> mins:secs \nExample: seek 2:34")
		pos = self.unformatted_time(timestamp)
		if pos is None:
			return await ctx.send(f":x: Invalid position format! Supported format -> mins:secs \n Example: **{ctx.prefix}seek 2:14**")
		if pos <= 10000:
			return await ctx.send(f":x: Cannot to a position less than 11 seconds! Use the '{ctx.prefix}replay' command instead.")
		if pos >= ctx.voice_client.current.length:
			return await ctx.send(":x: Cannot seek to a position greater than the song length!")
		await ctx.voice_client.seek(pos)
		return await ctx.send(f":fast_forward: Song position set to {formatted_time(pos)}")


	# @commands.hybrid_command(
	# 		aliases=["ins"],
	# 		usage="insert <position in the playlist to put the song at> <song url>")
	# @discord.app_commands.describe(
	# 	index="The position in the playlist in which we're going to insert the song.",
	# 	song_name="The url or title of the song"
	# 	)
	# @commands.check(voice_state)
	# async def insert(self, ctx, index: int=0, *, song_name: str=""):
	# 	"""Inserts a song at a given index of the playlist"""
	# 	if not index:
	# 		return await ctx.send(":x: Index must be greater than 0. Please specify an index number before the song name!")
	# 	if not song_name:
	# 		return await ctx.send(":x: Provide a song name and try again!")
	# 	# if ctx.voice_client.queue.is_full:
	# 	# 	return await ctx.send(":x: Playlist is full! Please wait for some songs to finish.")
	# 	if not ctx.voice_client.queue or not ctx.voice_client.playing:
	# 		return await ctx.invoke(self.play, song=song_name)
	# 	if not ctx.interaction:
	# 		await ctx.typing()
	# 	try:
	# 		result = await wavelink.Playable.search(song_name, source=wavelink.TrackSource.YouTube)
	# 	except wavelink.LavalinkLoadException as e:
	# 		return await ctx.send(f":x: {e}")
	# 	if not result:
	# 		return await ctx.channel.send(":warning: No results found!")
	# 	track = result[0]
	# 	track.extras = {"requester": str(ctx.author), "skips": list()}
	# 	if ctx.voice_client.current == track:
	# 		return await ctx.send(f":x: Already playing this song! Use '{ctx.prefix}loop' to start looping over current song!")
	# 	if index > len(ctx.voice_client.queue):
	# 		ctx.voice_client.queue.put(track)
	# 	else:
	# 		ctx.voice_client.queue.insert(index-2, track)
	# 	return await ctx.send(f":white_check_mark: Inserted **{discord.utils.remove_markdown(track.title)}** - at {index}")


	## Needs Fixing
	@commands.hybrid_command(
			aliases=["ly", "lyrix"],
			usage="lyrics [song title]"
			)
	#@discord.app_commands.describe(song="The name of ths song to search lyrics for (not url/link)")
	#@commands.check(voice_state)
	async def lyrics(self, ctx): #, *, song: str=""):
		"Search lyrics for the given song"
		return await ctx.send(":x: This command is currently broken! (Will be fixed very soon)")
		# if re.match(pattern=wavelink.URLRegex.BASE_URL, string=song) :
		# 	return await ctx.send(":x: Only song titles are supported, not urls or links.")
		# if ctx.interaction:
		# 	await ctx.interaction.response.send_message(f"{self.client.infinity_emoji} `Searching lyrics please wait....", delete_after=5)
		# if not song_name:
		# 	song_name = ctx.voice_client.current.title.lower().replace(("("))
		# song = self.lyrics_searcher.search_song(song_name)
		# if not song:
		# 	return await ctx.channel.send(":warning: Could not find lyrics for this song!", delete_after=5)
		# pager = commands.Paginator()
		# for line in song.lyrics.splitlines():
		# 	pager.add_line(line)
		# embeds = [
		# 	discord.Embed(
		# 		title=f"Lyrics for {song.title}",
		# 		description=page,
		# 		color=discord.Color.random(),
		# 		timestamp=discord.utils.utcnow()
		# 	).set_footer(text=self.client.user.name) for page in pager.pages
		# ]
		# return await ctx.channel.send(
		# 	embed=embeds[0],
		# 	view=PageButtons(embeds=embeds, timeout=300) if len(embeds) > 1 else discord.utils.MISSING
		# 	)


	@commands.hybrid_command(
			aliases=["stop"],
			usage="pause"
			)
	@commands.check(voice_state)
	async def pause(self, ctx):
		"""Pause the currently playing song"""
		if not ctx.voice_client.playing:
			return await ctx.send(":x: Nothing playing currently!")
		if not ctx.voice_client.paused:
			await ctx.voice_client.pause(True)
			return await ctx.send(":pause_button: Paused the currently playing song.")
		else:
			return await ctx.send(":warning: Already paused!")


	@commands.hybrid_command(
			aliases=["resum", "res", "cont", "continue"],
			usage="resume")
	@commands.check(voice_state)
	async def resume(self, ctx):
		"""Resume the paused song!"""
		if not ctx.voice_client.playing:
			return await ctx.send(":x: Nothing playing currently!")
		if not ctx.voice_client.paused:
			return await ctx.send(":warning: Already playing!")
		else:
			await ctx.voice_client.pause(False)
			return await ctx.send(":arrow_forward: Resumed the song!")


	@commands.hybrid_command(
			aliases=["np", "now", "timeline", "current"],
			usage="nowplaying"
			)
	async def nowplaying(self, ctx: commands.Context):
		"""Shows position of the timeline of the currently playing song"""
		if ctx.voice_client is None or not ctx.voice_client.playing:
			return await ctx.send(":x: Nothing playing now!")
		pointer_pos = round((ctx.voice_client.position/ctx.voice_client.current.length)*30)
		timeline = "".join("▬" if x != pointer_pos else "🔘" for x in range(1, 31))
		current_pos = formatted_time(int(ctx.voice_client.position))
		totaltime = formatted_time(int(ctx.voice_client.current.length))
		np_embed = discord.Embed(
			title="Now Playing :musical_note:",
			description=f"Title: **[{discord.utils.remove_markdown(ctx.voice_client.current.title)}]({ctx.voice_client.current.uri})**",
			color=discord.Color.random(),
			timestamp=discord.utils.utcnow()
		)
		looping = ctx.voice_client.queue.mode == wavelink.QueueMode.loop
		np_fields = [
			{
				"name": "Author",
				"value": ctx.voice_client.current.author,
				"inline": True
			},
			{
				"name": "Volume",
				"value": f"{ctx.voice_client.volume}%",
				"inline": True
			},
			{
				"name": "Loop",
				"value": "Enabled" if looping else "Disabled",
				"inline": False
			},
			{
				"name": "Timeline Position",
				"value": f"**{current_pos}** `{timeline}` **{totaltime}**",
				"inline": False
			},
		]
		for item in np_fields:
			np_embed.add_field(**item)
		np_embed.set_thumbnail(url=ctx.voice_client.current.artwork)
		np_embed.set_footer(text=self.client.user.name)
		await self.clean_up(ctx.voice_client, stop=False, destroy=False)
		ctx.voice_client.controller = await ctx.send(embed=np_embed, view=PlayerButtons(player=ctx.voice_client))


	@commands.hybrid_command(
			aliases=["playlist", "q", "songlist", "songs", "list"],
			usage="queue"
			)
	async def queue(self, ctx):
		"""Display what's next in the song queue"""
		if not ctx.voice_client.queue:
			if ctx.voice_client.playing:
				duration = formatted_time(ctx.voice_client.current.length)
				emb = discord.Embed(
					title="Playlist :notes:",
					description=f"**Now Playing**\n\n1| {discord.utils.remove_markdown(ctx.voice_client.current.title)} ({duration})",
					color=discord.Color.random(),
					timestamp=discord.utils.utcnow()
				)
				emb.set_footer(text=self.client.user.name)
				return await ctx.send(embed=emb)
			else:
				return await ctx.send(":warning: Playlist is empty!")
		else:
			pager = commands.Paginator(suffix=None, prefix=None, max_size=1980, linesep='\n')
			duration = formatted_time(ctx.voice_client.current.length)
			current_song = f"**Now Playing**\n\n1| {discord.utils.remove_markdown(ctx.voice_client.current.title)} ({duration})\n\n**Up Next:**\n"
			pager.add_line(current_song)
			for x, track in enumerate(ctx.voice_client.queue): pager.add_line(f"{x+2}| {discord.utils.remove_markdown(track.title)}")
			embeds = [
				discord.Embed(
					title="Playlist :notes:",
					description=page,
					color=discord.Color.random(),
					timestamp=discord.utils.utcnow()
				).set_footer(text=self.client.user.name) for page in pager.pages]
			await ctx.send(
				embed=embeds[0],
				view=PageButtons(
					embeds=embeds
					) if len(embeds) > 1 else discord.utils.MISSING
				)


	@commands.hybrid_command(
			aliases=["shuffleq", "shuffle", "shuffleplaylist"],
			usage="shuffleq"
			)
	@commands.check(voice_state)
	@commands.has_guild_permissions(manage_messages=True)
	async def shufflequeue(self, ctx):
		"""Shuffle the whole song playlist (This can't be undone!)"""
		if not ctx.voice_client.playing:
			return await ctx.send(":x: Playlist is empty!")
		if not ctx.voice_client.queue or len(ctx.voice_client.queue) < 3:
			return await ctx.send(":x: At least 3 songs are required to shuffle the Playlist!")
		ctx.voice_client.queue.shuffle()
		return await ctx.send(f"Playlist shuffled by {ctx.author.mention}!")


	@commands.hybrid_command(
			aliases=['rmv', 'rm'],
			usage="remove <index number from song queue>"
			)
	@discord.app_commands.describe(
		index="Use /queue to know the index of the song you want to remove"
		)
	@commands.check(voice_state)
	@commands.has_guild_permissions(manage_messages=True)
	async def remove(self, ctx, index: typing.Optional[int]=None):
		"""Remove a song corresponding to the given index from the playlist"""
		if not ctx.voice_client.playing:
			return await ctx.send(":x: Nothing playing and playlist is empty!")
		if not ctx.voice_client.queue:
			return await ctx.send(":x: Only one song in the playlist!")
		if index is None:
			return await ctx.send(f":x: Please try again specifying the index number of the song. \
Use {ctx.prefix}queue to know the index of the song that you want to remove!")
		if index < 2:
			return await ctx.send(":x: Can't remove the song currently being played!")
		try:
			track_title = await ctx.voice_client.queue.delete(index-2)
		except (ValueError, IndexError):
			return await ctx.send(f':x: No song at index {index} in the playlist!')
		else:
			return await ctx.send(f":white_check_mark: Removed '{track_title}' from the playlist!")


	@commands.hybrid_command(
			aliases=["clearq", "clearsongs", "clearall", "cq", "clearplaylist"],
			usage="clearqueue"
			)
	@commands.check(voice_state)
	@commands.has_guild_permissions(manage_messages=True)
	async def clearqueue(self, ctx):
		"""Clears the whole song queue"""
		if not ctx.voice_client.playing:
			return await ctx.send(":x: Playlist is already empty!")
		if not ctx.voice_client.queue:
			await ctx.invoke(self.forceskip)
		else:
			ctx.voice_client.queue.reset()
			await ctx.send(":white_check_mark: Cleared the playlist!")
			return await self.clean_up(ctx.voice_client)


	@commands.hybrid_command(
			aliases=['vol', 'sound', 'v'],
			usage="volume <any number from 1 to 100>"
			)
	@discord.app_commands.describe(level="The volume level (should be between 1 and 100)")
	@commands.check(voice_state)
	async def volume(self, ctx, level: str="75"):
		"""Set the volume level for songs"""
		try:
			if "%" in level:
				level = level.strip("% ")
			level = float(level)
		except ValueError:
			return await ctx.send(":x: Please try again providing a valid volume level!")
		if level > 100:
			vol = 100
		elif level < 1:
			vol = 1
		else:
			vol = int(level)
		if vol == ctx.voice_client.volume:
			return await ctx.send(f":loud_sound: Volume is already set to {vol}%")
		await ctx.voice_client.set_volume(vol)
		return await ctx.send(f":loud_sound: Volume has been set to {vol}%")


	@commands.hybrid_command(
			aliases=["bass", "boost"],
			usage="bassboost"
			)
	@commands.check(voice_state)
	async def bassboost(self, ctx):
		"""Toggles the equalizer to bassboost mode"""
		if not ctx.voice_client.playing:
			return await ctx.send(":x: No song is playing currently!")
		await ctx.voice_client.set_filter(wavelink.Filter(equalizer=wavelink.Equalizer.boost()))
		return await ctx.send(":white_check_mark: Enabled bassboost!")


	@commands.hybrid_command(
			aliases=["fav", "favorite", "star", "addfav"],
			usage="favourite"
			)
	@commands.check(voice_state)
	async def favourite(self, ctx):
		"""Add the currently playing song to your favourites list"""
		if not ctx.voice_client.playing:
			return await ctx.send(":x: Nothing is playing currently!")
		with open('./database/favourite_tracks.json', 'r') as favfile:
			favs = json.load(favfile)
		try:
			if len(favs[str(ctx.author.id)]) >= 20:
				return await ctx.send(":x: Max 20 songs can be added to the favourites!")
			if any(ctx.voice_client.current.raw_data == item['data'] for item in favs[str(ctx.author.id)]):
				return await ctx.send(":ballot_box_with_check: Current song is already in your favourites!")
			favs[str(ctx.author.id)].append(
				{'title': discord.utils.remove_markdown(ctx.voice_client.current.title[:90]), "data": ctx.voice_client.current.raw_data}
				)
		except KeyError:
			favs[str(ctx.author.id)] = []
			favs[str(ctx.author.id)].append(
				{"title": discord.utils.remove_markdown(ctx.voice_client.current.title[:90]), "data": ctx.voice_client.current.raw_data}
				)
		finally:
			with open('./database/favourite_tracks.json', 'w') as favfile:
				json.dump(favs, favfile, indent=4)
		return await ctx.send(":star: Added current track to your favourites!")


	@commands.hybrid_command(
			aliases=['rmfav', 'removefav', 'unstar', 'unfav', 'removefavorite'],
			usage="rmfav <index number of the song from your favourites list>"
			)
	@discord.app_commands.describe(index="The index no. of the song from your favourites (`index = -1` means remove all)")
	async def removefavourite(self, ctx, index: int=0):
		"""Remove a song from your favourites"""
		return await ctx.send("This command is broken and will be fixed soon.")
		# if index < -1 or index == 0:
		# 	return await ctx.send(
		# 	f"Please provide a valid index number. Use `{ctx.prefix}favourites` to know the index numbers"
		# )
		# with open('./database/favourite_tracks.json') as favfile:
		# 	favs = json.load(favfile)
		# try:
		# 	if index == -1:
		# 		favs.clear()
		# 	else:
		# 		rmvd = favs[str(ctx.author.id)].pop(index-1)
		# except (IndexError, KeyError):
		# 	return await ctx.send(f":x: No song at index {index} of your favourites!")
		# else:
		# 	with open('./database/favourite_tracks.json', 'w') as favfile:
		# 		json.dump(favs, favfile, indent=4)
		# 	if index > 0:
		# 		msg = f':ballot_box_with_check: Removed \'{rmvd["title"]}\' from your favourites!'
		# 	else:
		# 		msg = "Cleared all songs from your favourites"
		# 	return await ctx.channel.send(msg)


	@commands.hybrid_command(
			aliases=['favs', 'starred', 'stars', 'favlist', 'favorites'],
			usage='favourites'
			)
	async def favourites(self, ctx):
		"""See what's in your favourite list"""
		return await ctx.send("This command is broken and will be fixed soon.")
		# with open('./database/favourite_tracks.json') as favfile:
		# 	favs = json.load(favfile)
		# try:
		# 	if not favs[str(ctx.author.id)]:
		# 		return await ctx.send(":warning: You have nothing in your favourites!")
		# except KeyError:
		# 	return await ctx.send(":warning: Your favourite songs list is empty!")
		# else:
		# 	pager = commands.Paginator(
		# 				prefix=f'{ctx.author.name}, the following songs are in your favourites:\n',
		# 				suffix=None,
		# 				max_size=1900,
		# 				linesep='\n'
		# 			)
		# 	for x, song in enumerate(favs[str(ctx.author.id)]):
		# 		pager.add_line(f'__{x+1}__| {song["title"]}')
		# 	embs = [
		# 		discord.Embed(
		# 			title='Favourites \U0001F31F',
		# 			description=page,
		# 			color=discord.Color.random(),
		# 			timestamp=discord.utils.utcnow()
		# 			).set_footer(text=self.client.user.name) for page in pager.pages
		# 			]
		# 	return await ctx.send(
		# 			embed=embs[0],
		# 			view=PageButtons(
		# 				embeds=embs,
		# 				timeout=240
		# 				) if len(embs) > 1 else discord.utils.MISSING
		# 		)


	@commands.hybrid_command(
			aliases=["autoreplay"],
			usage='loop'
			)
	@commands.check(voice_state)
	async def loop(self, ctx):
		"""Toggles the "auto repeat current song" switch"""
		if ctx.voice_client.playing:
			if ctx.voice_client.queue.mode == wavelink.QueueMode.normal:
				ctx.voice_client.queue.mode = wavelink.QueueMode.loop
				await ctx.send(":repeat_one: Current song will be looped!")
			else:
				ctx.voice_client.queue.mode = wavelink.QueueMode.normal
				await ctx.send(":ballot_box_with_check: Disabled loop!")
		else:
			return await ctx.send(":x: Not playing any song currently!")


	@commands.hybrid_command(
			name='ytdownload',
			aliases=['savetodisk', 'download', 'dl', 'ytdl'],
			usage="ytdownload [song url from YouTube]"
			)
	@discord.app_commands.describe(url="Url of the video from YouTube")
	async def send_audio_video_url(self, ctx: commands.Context, *, url: typing.Optional[str]=None):
		"""Try to download an audio from YouTube and send it to this channel"""
		return await ctx.send("This command is broken and will be fixed soon.")
# 		if url is None:
# 			if not ctx.voice_client or not ctx.voice_client.playing:
# 				return await ctx.send(":x: Please play a song or try again providing a youtube video url!")
# 			else:
# 				url = ctx.voice_client.current.uri
# 		if self.YOUTUBE_URL.match(url):
# 			emb = discord.Embed(
# 				title="Downloading from YouTube",
# 				description=f"{self.client.infinity_emoji} Trying to download `{url}`",
# 				colour=discord.Colour.blue(),
# 				timestamp=discord.utils.utcnow()
# 				)
# 			emb.set_footer(text=self.client.user.name)
# 			msg = await ctx.send(embed=emb)
# 		elif self.YOUTUBE_PLAYLIST_URL.match(url):
# 			return await ctx.send(":x: Youtube playlist url is not supported! Try again providing a video url.")
# 		else:
# 			return await ctx.send(":x: The url is not a YouTube video Url!")
# 		try:
# 			info = self.ytdl_client.extract_info(url, download=False, process=False)
# 			if info is None or all('format_id' not in item for item in info['formats']):
# 				emb.title = "Not found!"
# 				emb.description = ":warning: The given url doesn't seem to return any result from Youtube!"
# 				return await msg.edit(embed=emb)
# 			else:
# 				emb.title = "Media type!"
# 				emb.description = "Choose a media type from the followings"
# 			view = SelectResolution(timeout=30, author=ctx.author)
# 			await msg.edit(embed=emb, view=view)
# 			await view.wait()
# 			if view.itag_value not in ('140', '22'):
# 				emb.title = "Failed"
# 				emb.description = "**You did not select any choice!**"
# 				emb.color = discord.Colour.red()
# 				for item in view.children:
# 					item.style = discord.ButtonStyle.grey
# 					item.disabled = True
# 				return await msg.edit(embed=emb, view=view)
# 			vid = next(item for item in info['formats'] if item['format_id']==view.itag_value)
# 		except (KeyError, StopIteration):
# 			emb.title = "Item not found!"
# 			emb.description = ":x: Can't find this item in YouTube!"
# 			emb.colour = discord.Colour.red()
# 			await msg.edit(embed=emb)
# 		else:
# 			emb.title = "Downloaded item from YouTube"
# 			emb.description = f"""
# :white_check_mark: {ctx.author.mention} Successfully Downloaded `{info["title"]}`\n
# **Click [here]({vid['url']}) to open it in browser and then click on the `three dots` menu \
# besides the :loud_sound: icon to get download option.**\n
# Links expire {discord.utils.format_dt(datetime.datetime.now()+datetime.timedelta(hours=5), style='R')} from now."""
# 			emb.colour = discord.Colour.green()
# 			emb.set_thumbnail(url=info['thumbnails'][-1]['url'])
# 			try:
# 				await msg.edit(embed=emb)
# 			except discord.errors.NotFound:
# 				await ctx.channel.send(embed=emb)


	@commands.hybrid_command(
			name="stereo",
			aliases=["threed", "3d", "stereo-mode"],
			usage="stereo"
			)
	@commands.check(voice_state)
	async def stereo_mode(self, ctx):
		"""Toggles the 3D effect"""
		if not ctx.voice_client.playing:
			return await ctx.send(":x: Not playing any song currently!")
		await ctx.voice_client.set_filter(wavelink.Filter(rotation=wavelink.Rotation(0.75)))
		return await ctx.send(":white_check_mark: Enabled stereo mode!")


	@commands.hybrid_command(
			aliases=['rf', 'nofilters', 'disablefilters'],
			usage='resetfilters'
			)
	@commands.check(voice_state)
	async def resetfilters(self, ctx):
		"""Reset all the applied audio filters"""
		if not ctx.voice_client.playing:
			return await ctx.send(":x: No song is playing right now!")
		if ctx.voice_client.filters:
			await ctx.voice_client.set_filter(None)
			return await ctx.send(":ballot_box_with_check: Reset all filters successfully!")
		else:
			return await ctx.send(":warning: No filters applied currently!")


	@commands.hybrid_command(
			aliases=["vskip", "next", "vnext", "voteskip"],
			usage='skip'
			)
	@commands.check(voice_state)
	async def skip(self, ctx):
		"""Vote to skip the current song"""
		if not ctx.voice_client.playing:
			return await ctx.send(":x: Not playing any music currently!")
		if str(ctx.author.id) in ctx.voice_client.current.extras.skips:
			return await ctx.send(":x: You have already voted to skip current song!")
		ctx.voice_client.current.extras.skips.append(str(ctx.author.id))
		required_votes = round((len(ctx.voice_client.channel.members) - 1)/3)
		number_of_votes = len(ctx.voice_client.current.extras.skips)
		skip_msg = f"{ctx.author} voted to skip the song!"
		if number_of_votes < required_votes:
			return await ctx.send(f":track_next: {skip_msg} Need {required_votes-number_of_votes} more to skip.")
		await ctx.send(f":track_next: {skip_msg} Skipping...")
		await self.clean_up(ctx.voice_client, stop=True)


	@commands.hybrid_command(
			aliases=["playskip", "fsto", "jump", "jumpto"],
			usage="skipto <index number from the song queue>"
			)
	@discord.app_commands.describe(
		index="Use /queue to know the index of the song you want to skip upto"
		)
	@commands.check(voice_state)
	@commands.has_guild_permissions(manage_messages=True)
	async def skipto(self, ctx, index: typing.Optional[int]=None):
		"""Skip upto the song corresponding to given index from the the playlist"""
		if not ctx.voice_client.playing:
			return await ctx.send(":x: Nothing playing and playlist is empty!")
		if index is None:
			return await ctx.send(":x: Please try again specifying the index number of the song. \
Use /queue to know the index of the song that you want to skip upto!")
		if index < 2:
			return await ctx.invoke(self.forceskip)
		try:
			del ctx.voice_client.queue[:index-2]
		except (ValueError, IndexError):
			return await ctx.send(f':x: No song at index {index} in the playlist!')
		else:
			await self.clean_up(ctx.voice_client, stop=True)



	@commands.hybrid_command(
			aliases=["fs", "forcenext", "fnext", "fskip"],
			usage='forceskip'
			)
	@commands.check(voice_state)
	@commands.has_guild_permissions(manage_messages=True)
	async def forceskip(self, ctx):
		"""Forcibly play the next song"""
		if ctx.voice_client.playing:
			await self.clean_up(ctx.voice_client, stop=True)
			if ctx.interaction:
				await ctx.send(":thumbsup: Force Skipped!")
			else:
				await ctx.message.add_reaction("🆗")
		else:
			await ctx.send(":x: Not playing any song currently!")

	# @forceskip.error
	# async def fs_error(self, ctx, error):
	# 	if isinstance(error, commands.MissingPermissions):
	# 		return await ctx.send(":x: This command requires you to have manage messages permission in this server.")


	@commands.hybrid_command(
			name="leave",
			aliases=["dc", "disconnect"],
			usage='leave'
			)
	@commands.has_guild_permissions(manage_messages=True)
	@commands.check(voice_state)
	async def leave_vc(self, ctx: commands.Context):
		"""Disconnect from the connected voice channel"""
		channel = ctx.voice_client.channel.name
		await self.clean_up(ctx.voice_client, stop=True, destroy=True)
		await ctx.send(f":white_check_mark: Diconnected from '{channel}' successfully!")


	@commands.command(name="m:eval", aliases=["m:ev", "m:evaluate"], hidden=True)
	@commands.is_owner()
	async def m_eval(self, ctx, *, cmd:str):
		if "input(" in cmd.lower() or "input (" in cmd.lower():
			return await ctx.send(":x: Cannot Execute input method!")
		cmd = cmd.strip('`')
		try:
			result = eval(str(cmd))
		except Exception as e:
			result = f"{e.__class__.__name__}: {e}"
		cmd_emb = discord.Embed(description=f"{result or '<no output>'}")
		return await ctx.send(embed=cmd_emb)


async def setup(bot):
	print("Setting up Music v2!...")
	cog = Music(bot)
	await cog.connect_voice_node()
	await bot.add_cog(cog)

async def teardown(bot):
	# await wavelink.NodePool.disconnect()
	print("Unloading Music v2!...")
	# bot.lavalink.exit()
	await bot.remove_cog(bot.cogs['Music'])
