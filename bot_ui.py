# pylint: disable=bad-indentation,arguments-differ,arguments-renamed

from contextlib import suppress
import discord
from random import choice

from wavelink import QueueMode


def formatted_time(time):
    mins, secs = divmod(round(time/1000), 60)
    return f"{int(mins):0>2}:{int(secs):0>2}"


class CancelMirror(discord.ui.View):

	def __init__(self, file_obj, timeout=None):
		super().__init__(timeout=timeout)
		self.file = file_obj

	@discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
	async def cancel_task(self, inter: discord.Interaction, button):
		if inter.user not in (self.file.ctx.author, inter.client.owner, inter.guild.owner):
			await inter.response.send_message("**:x: You are not the one who started this mirror task!**", ephemeral=True)
		else:
			button.disabled = True
			await inter.response.edit_message(view=self)
			await self.file.cancel()


class ConfirmButtons(discord.ui.View):
	"""Are you sure? :/"""
	
	def __init__(self, timeout=40):
		super().__init__(timeout=timeout)

		self.value = None

	@discord.ui.button(label="✓", custom_id="yes_button", style=discord.ButtonStyle.success)
	async def confirm(self, inter: discord.Interaction, button):
		for child in self.children:
			child.disabled = True
		button.style = discord.ButtonStyle.primary
		self.value = True
		await inter.response.edit_message(view=self)
		self.stop()

	@discord.ui.button(label="x", custom_id="!yes_button", style=discord.ButtonStyle.danger)
	async def reject(self, inter: discord.Interaction, button):
		for item in self.children:
			item.disabled = True
		button.style = discord.ButtonStyle.primary
		self.value = False
		await inter.response.edit_message(view=self)
		self.stop()

# class ButtonFHD(discord.ui.Button):
# 	def __init__(self):
# 		super().__init__(
# 			style=discord.ButtonStyle.primary,
# 			custom_id='1080p', label='1080p HD video'
# 			)
# 	async def callback(self, interaction):
# 		self.style = discord.ButtonStyle.success
# 		for item in self.view.children:
# 			item.disabled = True
# 		self.view.itag_value = 248
# 		await interaction.response.edit_message(view=self.view)
# 		self.view.stop()

class SelectResolution(discord.ui.View):
	def __init__(self, *, author, timeout: float = 30):
		super().__init__(timeout=timeout)
		self.itag_value = None
		self.author = author

	async def interaction_check(self, interaction):
		return self.author == interaction.user
	
	@discord.ui.button(label="720p Video", custom_id='video', style=discord.ButtonStyle.primary)
	async def video_button(self, inter, button):
		button.style = discord.ButtonStyle.success
		for item in self.children:
			item.disabled = True
		self.itag_value = '22'
		await inter.response.edit_message(view=self)
		self.stop()
	
	@discord.ui.button(label="128kbps Audio", custom_id='audio', style=discord.ButtonStyle.primary)
	async def audio_button(self, inter, button):
		button.style = discord.ButtonStyle.success
		for item in self.children:
			item.disabled = True
		self.itag_value = '140'
		await inter.response.edit_message(view=self)
		self.stop()


class SearchChoiceSelect(discord.ui.Select):

	def __init__(self, track_titles):
		self.titles = track_titles
		opts = [
			discord.SelectOption(
				label=self.titles[x]['title'][:95],
				description=self.titles[x]['channel'],
				value=x
				) for x in range(len(track_titles))
			]
		super().__init__(
			placeholder="Click here to view the list and select",
			custom_id='search_results',
			max_values=1,
			min_values=1,
			options=opts,
			row=0
			)

	async def callback(self, inter):
		user_choice = int(self.values[0])
		self.placeholder = self.titles[user_choice]['title']
		for item in self.view.children:
			item.disabled = True
		self.view.choice = user_choice
		self.view.stop()
		return await inter.response.edit_message(view=self.view)

class SearchChoice(discord.ui.View):

	choice = None

	def __init__(self, track_titles, user, timeout=30):
		super().__init__(timeout=timeout)
		self.track_titles = track_titles
		self.author = user

		self.add_item(SearchChoiceSelect(track_titles=self.track_titles))

	async def on_error(self, inter, error, item):
		item.disabled = True
		try:
			raise error
		except discord.DiscordException as e:
			await inter.channel.send(e)
		await inter.response.edit_message(view=self)

	async def interaction_check(self, inter):
		return self.author == inter.user

	@discord.ui.button(label="Cancel", custom_id="cancel", style=discord.ButtonStyle.danger, row=1)
	async def cancel_search(self, inter, button: discord.ui.Button):
		button.label = "Cancelled"
		for item in self.children:
			item.disabled = True
		self.choice = "cancel"
		self.stop()
		await inter.response.edit_message(view=self)

class RPSChoice(discord.ui.View):
	def __init__(self, embed, timeout):
		super().__init__(timeout=timeout)
		self.emb = embed

	@discord.ui.button(label="Rock", emoji="👊", style=discord.ButtonStyle.primary)
	async def rock_choice(self, inter, button):
		bots_choice = choice(["r", "p", "s"])
		if bots_choice == "r":
			self.emb.description = "Phew!! What a close call! Both of us have choosen Rock. It's a tie."
		elif bots_choice == "s":
			self.emb.description = "Congo buddy! I have choosen Scissor and you have choosen rock. The Rock wins"
			button.style = discord.ButtonStyle.success
		elif bots_choice == "p":
			self.emb.description = "Aaha! You loose buddy! You've choosen Rock and I have choosen Paper. And Paper wins against Rock. :)"
			button.style = discord.ButtonStyle.danger
		for item in self.children:
			if item != button:
				item.style = discord.ButtonStyle.grey
			item.disabled = True
		self.stop()
		await inter.response.edit_message(embed=self.emb, view=self)

	@discord.ui.button(label="Paper", emoji="✋", style=discord.ButtonStyle.primary)
	async def paper_choice(self, inter, button):
		bots_choice = choice(["r", "p", "s"])
		if bots_choice == "p":
			self.emb.description = "Pheww!! What a close call! Both of us have choosen Paper. It's a tie."
		elif bots_choice == "r":
			self.emb.description = "Congo buddy! I have choosen Rock and you have choosen Paper. The Paper wins"
			button.style = discord.ButtonStyle.success
		elif bots_choice == "s":
			self.emb.description = "Aaha! You loose buddy! You've choosen Paper and I have choosen Scissor. And Scissor wins against Paper. :)"
			button.style = discord.ButtonStyle.danger
		for item in self.children:
			if item != button:
				item.style = discord.ButtonStyle.grey
			item.disabled = True
		self.stop()
		await inter.response.edit_message(embed=self.emb, view=self)

	@discord.ui.button(label="Scissor", emoji="✌️", style=discord.ButtonStyle.primary)
	async def scissor_choice(self, inter, button):
		bots_choice = choice(["r", "p", "s"])
		if bots_choice == "s":
			self.emb.description = "Pheww!! What a close call! Both of us have choosen Scissor. It's a tie."
		elif bots_choice == "p":
			self.emb.description = "Congo buddy! I have choosen Paper and you have choosen Scissor. The Scissor wins"
			button.style = discord.ButtonStyle.success
		elif bots_choice == "r":
			self.emb.description = "Aaha! You loose buddy! You've choosen Scissor and I have choosen Rock. And Rock wins against Scissor. :)"
			button.style = discord.ButtonStyle.danger
		for item in self.children:
			if item != button:
				item.style = discord.ButtonStyle.grey
			item.disabled = True
		self.stop()
		await inter.response.edit_message(embed=self.emb, view=self)

	@discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
	async def cancel_rps(self, interact, item):
		item.style = discord.ButtonStyle.grey
		self.emb.description = ":white_check_mark: **Cancelled!**"
		for button in self.children: button.disabled = True
		self.stop()
		await interact.response.edit_message(embed=self.emb, view=self)


class PageButtons(discord.ui.View):
	def __init__(self, embeds, timeout=240):
		super().__init__(timeout=timeout)

		self.embeds = embeds
		self.current_page = 0

	async def on_error(self, interaction, error, item):
		item.label = "Error"
		item.style = discord.ButtonStyle.danger
		item.disabled = True
		await interaction.response.edit_message(view=self)
		print(error.__class__.__name__, ":", str(error))

	@discord.ui.button(emoji='\U00002B05', custom_id="page_previous", style=discord.ButtonStyle.primary)
	async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
		button.style = discord.ButtonStyle.secondary if button.style == discord.ButtonStyle.primary else discord.ButtonStyle.primary
		self.current_page -= 1
		if self.current_page < 0:
			self.current_page = len(self.embeds)-1
		await interaction.response.edit_message(embed=self.embeds[self.current_page])

	@discord.ui.button(emoji="\U000023F9", custom_id="stop_embeds", style=discord.ButtonStyle.primary)
	async def stop_embs(self, interaction: discord.Interaction, button: discord.ui.Button):
		for item in self.children:
			if item != button:
				item.style = discord.ButtonStyle.grey
			item.disabled = True
		self.stop()
		await interaction.response.edit_message(view=self)
		await interaction.message.delete(delay=15)

	@discord.ui.button(emoji='\U000027A1', custom_id="page_next", style=discord.ButtonStyle.primary)
	async def next_page(self, interaction: discord.Interaction, button: discord.Button):
		button.style = discord.ButtonStyle.secondary if button.style == discord.ButtonStyle.primary else discord.ButtonStyle.primary
		self.current_page += 1
		if self.current_page+1 > len(self.embeds):
			self.current_page = 0
		await interaction.response.edit_message(embed=self.embeds[self.current_page])


class PlayerButtons(discord.ui.View):

	def __init__(self, player, timeout=None):
		super(PlayerButtons, self).__init__(timeout=timeout)

		self.player = player

	async def clean_up(self):
		vc = self.player
		with suppress(AttributeError):
			view = discord.ui.View.from_message(vc.controller)
			if view:
				for item in view.children:
					item.style = discord.ButtonStyle.secondary
					item.disabled = True
				view.stop()
			with suppress(discord.errors.NotFound):
				await vc.controller.edit(view=view)
		vc.current.extras.skips.clear()
		await vc.skip(force=True)


	@classmethod
	async def renew(cls, player):
		return cls(player=player)

	async def on_error(self, interaction: discord.Interaction, error, item):
		print(item.custom_id)
		print(error.__class__.__name__, ":", str(error))
		item.label = "Error!"
		item.style = discord.ButtonStyle.danger
		await interaction.response.edit_message(view=self)

	@discord.ui.button(emoji='\U000023F8', custom_id='pause_button', style=discord.ButtonStyle.success)
	async def interactive_play_pause(self, interaction: discord.Interaction, button: discord.ui.Button):
		if self.player.paused:
			await self.player.pause(False)
			button.emoji = "\U000023F8"
			button.style = discord.ButtonStyle.success
			await interaction.response.edit_message(view=self)
			await interaction.channel.send(f":arrow_forward: Resumed by {interaction.user}!")
		else:
			await self.player.pause(True)
			button.emoji = "\U000025B6"
			button.style = discord.ButtonStyle.primary
			await interaction.response.edit_message(view=self)
			await interaction.channel.send(f":pause_button: Paused by {interaction.user}!")


	@discord.ui.button(emoji='\U000023ED', custom_id='skip_button', style=discord.ButtonStyle.success)
	async def interactive_skip(self, interaction: discord.Interaction, button: discord.ui.Button):
		track = self.player.current
		if str(interaction.user.id) in track.extras.skips:
			return await interaction.response.send_message(":warning: You have already voted!", ephemeral=True)
		else:
			track.extras.skips.append(str(interaction.user.id))
			skip_msg = f":track_next: {interaction.user} voted to skip the song!"
			required = round((len(self.player.channel.members) - 1) / 3)
			current = len(track.extras.skips)
			if required:
				button.label = f"{current}/{required}"
			await interaction.response.edit_message(view=self)
			if current < required:
				await interaction.channel.send(
					f"{skip_msg} Need {required-current} more to skip."
					)
			else:
				await interaction.channel.send(f"{skip_msg} Skipping...")
				await self.clean_up()


	@discord.ui.button(emoji="\U000023EA", custom_id='repeat_button', style=discord.ButtonStyle.success)
	async def interactive_repeat(self, interaction: discord.Interaction, button: discord.ui.Button):
		await self.player.seek()
		button.style = discord.ButtonStyle.success if button.style == discord.ButtonStyle.primary else discord.ButtonStyle.primary
		await interaction.response.edit_message(view=self)
		await interaction.channel.send(f":rewind: Restarted current song by {interaction.user}")

	# @discord.ui.button(emoji="\U0001F502", custom_id="loop_button", style=discord.ButtonStyle.success)
	# async def interactive_loop(self, interaction: discord.Interaction, button: discord.ui.Button):
	# 	self, player.loop = self.player.current if self.player.loop is None else None
	# 	if self.player.loop:
	# 		state = "turned on"
	# 		button.style = discord.ButtonStyle.primary
	# 	else:
	# 		state = "turned off"
	# 		button.style = discord.ButtonStyle.success
	# 	await interaction.response.edit_message(view=self)
	# 	await interaction.channel.send(f":repeat_one: Auto replay {state} by {interaction.user}")

	@discord.ui.button(emoji='\U0001F3B6', custom_id='queue_button', style=discord.ButtonStyle.success)
	async def interactive_queue(self, interaction: discord.Interaction, button):
		button.style = discord.ButtonStyle.primary if button.style==discord.ButtonStyle.success else discord.ButtonStyle.success
		await interaction.response.edit_message(view=self)
		if not self.player.queue:
			duration = formatted_time(self.player.current.length)
			emb = discord.Embed(
				title="Playlist :notes:",
				description=f"**Now Playing**\n\n1| {self.player.current.title} ({duration})",
				color=discord.Color.random(),
				timestamp=discord.utils.utcnow()
			)
			emb.set_footer(text=self.player.client.user.name)
			await interaction.channel.send(embed=emb)
		else:
			pager = discord.ext.commands.Paginator(suffix=None, prefix=None, max_size=1980, linesep='\n')
			duration =formatted_time(self.player.current.length)
			current_song = f"**Now Playing**\n1| {self.player.current.title} ({duration})\n\n**Up Next:**\n"
			pager.add_line(current_song)
			for x, track in enumerate(self.player.queue): pager.add_line(f"{x+2}| {track.title}")
			embeds = [
				discord.Embed(
					title="Playlist :notes:",
					description=page,
					color=discord.Color.random(),
					timestamp=discord.utils.utcnow()
				).set_footer(text=self.player.client.user.name) for page in pager.pages]
			await interaction.channel.send(
				embed=embeds[0],
				view=PageButtons(
					embeds=embeds
					) if len(embeds) > 1 else discord.utils.MISSING
				)

	@discord.ui.button(emoji="\U0001F3B5", custom_id="nowplay_button", style=discord.ButtonStyle.success)
	async def interactive_np(self, interaction: discord.Interaction, button: discord.ui.Button):
		pointer_pos = round((self.player.position/self.player.current.length)*30)
		timeline = "".join("▬" if x not in (0, pointer_pos) else "🔘" for x in range(1, 31))
		current_pos = formatted_time(int(self.player.position))
		totaltime = formatted_time(int(self.player.current.length))
		np_embed = discord.Embed(
			title="Now Playing :musical_note:",
			description=f"Title: **[{self.player.current.title}]({self.player.current.uri})**",
			color=discord.Color.random(),
			timestamp=discord.utils.utcnow()
		)
		looping = self.player.queue.mode == QueueMode.loop
		np_fields = [
			{
				"name": "Author",
				"value": self.player.current.author,
				"inline": True
			},
			# {
			# 	"name": "Requested by",
			# 	"value": ctx.voice_client.current.requester,
			# 	"inline": True
			# },
			{
				"name": "Volume",
				"value": f"{self.player.volume}%",
				"inline": True
			},
			{
				"name": "Loop",
				"value": "Enabled" if looping else "Disabled",
			},
			{
				"name": "Timeline Position",
				"value": f"**{current_pos}** `{timeline}` **{totaltime}**",
				"inline": False
			},
		]
		for item in np_fields:
			np_embed.add_field(**item)
		np_embed.set_thumbnail(url=self.player.current.artwork)
		np_embed.set_footer(text=self.player.client.user.name)
		for item in self.children:
			item.disabled = True
			if item!=button:
				item.style = discord.ButtonStyle.gray
		new_view = await self.renew(player=self.player)
		with suppress(discord.NotFound):
			await interaction.response.edit_message(view=self)
		self.player.controller = await interaction.channel.send(
			embed=np_embed, view=new_view
			)
