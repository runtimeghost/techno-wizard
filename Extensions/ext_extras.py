# pylint: disable=bad-indentation
# Some extra features

import calendar
from re import match
import contextlib
from math import ceil
import psutil
from typing import Optional
import better_profanity
from json import loads
import praw
from random import choice, randint
import discord
from discord.ext import commands
import time
from dotenv import load_dotenv
import googletrans
from os import environ
import platform
from endecrypt import encode, decode
import openai
from bot_ui import PageButtons


load_dotenv()

better_profanity.profanity.load_censor_words()
openai.api_key = environ.get("OPENAI_API_KEY")
class Extras(commands.Cog):

	def __init__(self, client):
		self.client = client
		# self.bid = environ.get("brain_id")
		# self.api = environ.get("brain_key")
		self.reddit = praw.Reddit(
			client_id=environ.get('REDDIT_ID'), 
			client_secret=environ.get('REDDIT_SECRET'),
			user_agent=f"script:{environ.get('REDDIT_ID')}:v0.1.0 (by u/snakexenzia01)",
			username="snakexenzia01",
			password=environ.get('REDDIT_PASSWORD')
		)
		self.alpha = """zA<9yB(x8'C[wD@v7E`uF-tG\\6&sH*r,IqJ}p5$KoLn)M>m.Nl%4O~kP?jQi:R3!hS{g+Tf"Ue2/Vd;Wc_1Xb#Y]a0Z"""  # the super secret Algorithm xD
		self.translator = googletrans.Translator()


	@commands.Cog.listener()
	async def on_message(self, msg: discord.Message):
		if msg.author.id == self.client.user.id or msg.author.bot:
			return
		if isinstance(msg.channel, discord.DMChannel):
			if len(msg.content) > 1903:
				return
			else:
				message = str(msg.content)
			if match(pattern="(0|1){1,}", string=message):
				text = decode(message, "binary")
				decoded_emb = discord.Embed(
					title="Decoded Text",
					description=text,
					color=discord.Color.random()
					)
				with contextlib.suppress(discord.errors.Forbidden, discord.errors.HTTPException):
					return await msg.channel.send(embed=decoded_emb)
			else:
				final_string = str()
				key = message[-2:]
				if key.isdigit():
					string = message[:-2]
					if int(key) > 10:
						key=int(key)
						for x in string:
							final_string+=self.alpha[(self.alpha.find(x)-key)%len(self.alpha)] if x in self.alpha else x
						decrypted_emb = discord.Embed(
							title="Decrypted Text",
							description=final_string,
							color=discord.Color.random(),
							timestamp=discord.utils.utcnow()
							)
						decrypted_emb.set_footer(text=self.client.user.name)
						with contextlib.suppress(discord.errors.Forbidden, discord.errors.HTTPException):
							return await msg.channel.send(embed=decrypted_emb)


	@commands.hybrid_command(
		name="meme",
		aliases=['memes', "funpost", "shitpost"],
		usage="meme"
		)
	@commands.guild_only()
	async def memes_reddit(self, ctx: commands.Context):
		"""A random post from reddit."""
		_type_ = "meme"
		subred = self.reddit.subreddit(_type_)
		await ctx.send("Getting some cheesy posts...")
		sub_func = choice((subred.hot, subred.top))
		subs = tuple(sub for sub in sub_func(limit=25))
		meme = choice(subs)
		meme_emb = discord.Embed(
			title=meme.title,
			color=discord.Color.blue()
		)
		meme_emb.set_image(url=meme.url)
		meme_emb.set_footer(text=str(self.client.user.name))
		meme_emb.timestamp = discord.utils.utcnow()
		await ctx.send(embed=meme_emb)


# 	@commands.hybrid_command(name="languages", aliases=["language", "lang", "langs"], description="Shows available languages that a text can be translated to.")
# 	@commands.guild_only()
# 	async def available_langs(self, ctx:commands.Context):
# 		languages = "\n".join(f" {y.title()} = {x.upper()}" for x, y in googletrans.LANGUAGES.items())
# 		lang_emb = discord.Embed(title=":page_with_curl: Available Languages", description=languages, color=discord.Colour.purple())
# 		lang_emb.set_footer(text=str(self.client.user.name))
# 		lang_emb.timestamp=discord.utils.utcnow()
# 		return await ctx.send(embed=lang_emb, delete_after=180)


# 	@discord.app_commands.command(name="translate")
# 	@discord.app_commands.describe(
# 		language_code="The code of the language that we are going to translate to. Use /languages to get code list ",
# 		text="The text we are going to translate.")
# 	@commands.guild_only()
# 	async def translate_(self, ctx: commands.Context, language_code: str=None, *, text: str=None):
# 		if text is None:
# 			return await ctx.send(":x: Please try again providing a text to translate!")
# 		if language_code is None:
# 			return await ctx.send(f":x: Please try again providing a text to translate!\nFor example: {ctx.prefix}translate Ami tomake valobashi")
# 		if better_profanity.profanity.contains_profanity(str(text).lower()):
# 			return await ctx.send(":x: Cannot process indecent words!")
# 		try:
# 			translated = self.translator.translate(text, src="auto", dest=language_code)
# 		except ValueError:
# 			prefix = ctx.prefix
# 			return await ctx.send(f":x: Language not found! Use {prefix}languages to get a list of available languages.")
# 		else:
# 			result = '''Translated from `{0.src}({x[0.src].title()})` to `{0.dest} ({x[translated.dest.lower()].title()})`

# **Actual input**\n`- {1}`

# **Translated output**`
# - {0.text}''.format(
# 				translated,
# 				text,
# 				x=googletrans.LANGUAGES
# 				)
# 			trans_emb = discord.Embed(
# 				title=":u6709: Translate",
# 				description=result,
# 				color=discord.Colour.random(),
# 				timestamp=discord.utils.now()
# 				)
# 			if translated.pronunciation: trans_emb.add_field(name="Pronunciation", value=f"{translated.pronunciation}", inline=False)
# 			trans_emb.set_footer(text=self.client.user.name)
# 			return await ctx.send(embed=trans_emb)


	@commands.hybrid_command(
		name="quotes",
		aliases=["inspire", "inspiration", "quote"],
		usage="quotes"
		)
	@commands.guild_only()
	async def quote_(self, ctx: commands.Context):
		"""Sends a random quote!"""
		# Credit goes to ZenQuotes. Thank you for developing this useful API.
		async with self.client.client_session.get("https://zenquotes.io/api/random") as response:
			formt =  loads(await response.text())
		quote = formt[0]["q"]
		author = formt[0]["a"]
		return await ctx.send(f"```\n{quote}\n{' '*45}-{author}\n```")

	@commands.hybrid_command(
		name="jokes",
		aliases=["fun", "joke"],
		usage="jokes"
		)
	@commands.guild_only()
	async def joke_(self, ctx: commands.Context):
		"""Sends a random joke!"""
		# jokes are taken randomly from official joke API
		async with self.client.client_session.get('https://official-joke-api.appspot.com/random_joke') as resp:
			joke_json = await resp.json()
		joke = f"\n{joke_json['setup']}\n-{joke_json['punchline']}\n"
		return await ctx.send(f"```\n{joke}\n```")

	@commands.hybrid_command(
		name="image",
		aliases=["img", "generate_img", "generate_photo", "photo", "images", "imgs", "illustrate"],
		usage="image <description of your imgaination>"
		)
	@discord.app_commands.describe(
		imagination="Imagine something and give a description of it",
		count="Number of images to generate (maximum 4)"
		)
	@commands.guild_only()
	async def image_illustration(self, ctx: commands.Context, count: Optional[int]=0, *, imagination: str=""):
		"""Generates an image  based on a given description of any imagination!"""
		if not imagination:
			return await ctx.send(":x: Please try again providing a proper description of your imagination!")
		count = ceil(count) or 1
		if not (0 < count < 5):
			count = 1
		imagination = discord.utils.remove_markdown(imagination, ignore_links=True)[:999] #| Generating image by OpenAI (maximum text length is 1000)
		message = await ctx.send("Generating Please wait....")
		try:
			image_info = openai.Image.create(
			prompt=imagination,
			n=count,
			size="1024x1024"
		)
		except openai.InvalidRequestError as err:
			return await message.edit(content=f":x: {str(err)}")
		img_data = image_info["data"]
		img_embeds = []
		x = 0
		for data in img_data:
			x += 1
			img_embeds.append(
				discord.Embed(
					title=f"Generated Image {x}",
					description=f"Requested by {ctx.author.mention}",
					color=discord.Colour.random(),
					timestamp=discord.utils.utcnow()
				).set_image(url=data['url']).set_footer(
						text=f"{self.client.user.name} - Powered by DALL-E of OpenAI.",
						icon_url="https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcStavujZPYSE1sXkTWL9y0pkVClUxU_90wzTQ&usqp=CAU"
					)
			)
		if len(img_embeds) > 1:
			await message.edit(content="Done", embeds=img_embeds)
		else:
			await message.edit(content="Done", embed=img_embeds[0])


	@image_illustration.error
	async def illustration_err(self, ctx, err):
		if isinstance(err, discord.DiscordException):
			await ctx.send("An unknown error occurred! Please try again later ....")
		await self.client.owner.send(err)

	@commands.hybrid_command(
		name="math",
		aliases=["m", "calculate", "calc", "solve", "mathematics"],
		usage="math <description of the mathematical problem>"
	)
	@discord.app_commands.describe(problem="The specific math question.")
	@commands.guild_only()
	async def math_solve(self, ctx: commands.Context, *, problem: str=""):
		"""Solves a given math problem and shows the result!"""
		# Uses OpenAI api to solve any math problem (max text length is 2048)
		if not problem:
			return await ctx.send(":x: Please try again providing a proper description of your math problem!" )
		problem = discord.utils.remove_markdown(problem)[:2047]
		message = await ctx.send("Performing Mathematical operations...` ")
		solved_math = openai.ChatCompletion.create(
			model="gpt-3.5-turbo",
			max_tokens=2048,
			temperature=0.8,
			stop=None,
			n=1,
			messages=[
				{
					'role': 'system',
					'content': 'You are a smart AI math solver and will act like \
a math problem solver that explains solution of a given math problem.'},
				{'role': 'user', 'content': problem}
			]
		)
		math_embed = discord.Embed(
			title="Math Solution",
			description=f"\n```\n{solved_math['choices'][0]['message']['content'][-2000:]}\n```",
			color=discord.Colour.random(),
			timestamp=discord.utils.utcnow()
		)
		math_embed.set_footer(
			text=f"{self.client.user.name} - Powered by OpenAI.",
			icon_url="https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcStavujZPYSE1sXkTWL9y0pkVClUxU_90wzTQ&usqp=CAU"
			)
		await message.edit(content="Done", embed=math_embed)

	@math_solve.error
	async def math_error(self, ctx, error):
		if isinstance(error, discord.DiscordException):
			await ctx.send("There occurred an unknown error. Please wait and try again later.")
		await self.client.owner.send(error)


	@commands.hybrid_command(
		name='ping',
		aliases=['pi', 'lat', 'latency'],
		usage="ping"
		)
	@commands.guild_only()
	async def ping_(self, ctx: commands.Context):
		"""Can be used to check the bot's latency"""
		latency = self.client.latency * 1000
		return await ctx.send(
			embed=discord.Embed(
				title='Ping',
				description=f"Connection latency: {round(latency)}ms\n",
				timestamp=discord.utils.utcnow(),
				color=discord.Colour.random()
				).set_footer(text=self.client.user.name)
			)


	@commands.hybrid_command(
		name="whois",
		aliases=["who", "avatar", "who-is", "userinfo", "memberinfo"],
		usage="whois <user id or mention them>"
		)
	@discord.app_commands.describe(user="The user id or @mention to get info about them")
	@commands.guild_only()
	async def user_info(self, ctx: commands.Context, *, user: discord.User=None):
		"""Shows info about a discord user"""
		if user is None:
			return await ctx.send(
				":x: Please try again and provide a user's name#discriminator or user's id or @mention a member to get info about them"
				)
		if user.id == self.client.user.id:
			desc=f"""Hey! It's me **{user.name}** :wink: 
**I was created at**: {discord.utils.format_dt(user.created_at, style='F')}
**My User ID**: {user.id}\n**__This is a bot account for sure! :woozy_face: __**\n"""
		elif user.id == self.client.owner_id:
			desc=f"""**Name**: {user.name}
**Joined discord at**: {discord.utils.format_dt(user.created_at, style='F')}
**User ID**: {user.id}\n**__The developer of \"{self.client.user.name}\" discord bot! :heart_hands: __**\n"""
		else:
			desc=f"""**Name**: {user.name}
**Joined discord at**: {discord.utils.format_dt(user.created_at, style='F')}
**User ID**: {user.id}\n**__{str(user)} is{' not ' if not user.bot else ' '}a bot account!__**\n"""
		return await ctx.send(embed=discord.Embed(
				title="User Info :bust_in_silhouette:",
				description=desc,
				color=user.accent_color,
				timestamp=discord.utils.utcnow()
					) .set_image(url=user.avatar.url
				).set_footer(text=self.client.user.name)
		)

	@user_info.error
	async def userinfo_error(self, ctx, error):
		if isinstance(error, commands.BadArgument):
			return await ctx.send("Couldn't find a user matching with the given details!")
		else:
			await self.client.dm_error_logs(err=error)


	@commands.hybrid_command(
		name="echo",
		aliases=["say", "ec"],
		usage="echo <text to echo>"
		)
	@commands.guild_only()
	async def echo_(self, ctx: commands.Context, *, text: str):
		"""Repeats a text"""
		if ctx.interaction:
			return await ctx.interaction.response.send_message(content=f"`{text}`")
		with  contextlib.suppress(
			discord.errors.HTTPException,
			discord.errors.Forbidden,
			discord.errors.NotFound
			): await ctx.message.delete()
		return await ctx.send(f"```\n{text}\n\n--{ctx.author}\n```")


	@commands.hybrid_command(
		name="sysinfo",
		aliases=['sys', 'system'],
		usage="sysinfo"
		)
	@commands.guild_only()
	async def system_info(self, ctx):
		"""Shows information about the specs the bot is running."""
		uptime = divmod(round(time.time())-round(self.client.start_time), 60)
		uptime_hours = divmod(uptime[0], 60)
		ram = psutil.virtual_memory()
		used_ram = round(ram.used/pow(1024, 3), 2)
		total_ram = round(ram.total/pow(1024,3), 2)
		info_emb = discord.Embed(
			title="System info",
			description="**{0.name}** is currently running on following specs:".format(self.client.user),
			color=discord.Color.magenta(),
			timestamp=discord.utils.utcnow()
		)
		infos =[
			{
				"name": "OS",
				"value": f"{platform.system()} {platform.release()} |",
				"inline": True
			},
			{
				"name": "Processor",
				"value": f"{platform.processor() or '<unknown>'} | Usage: {psutil.cpu_percent()}%",
				"inline": False
			},
			{
				"name": "RAM usage",
				"value": f"{used_ram} GB / {total_ram} GB",
				"inline": False
			},
			{
				"name": "Executing program with",
				"value": f"Python v{platform.python_version()} {self.client.pymoji}",
				"inline": True
			},
			{
				"name": "Discord Library",
				"value": f"Discord.py v{discord.__version__}",
				"inline": True
			},
			{
				"name": "Uptime",
				"value": f"{uptime_hours[0]} hours {uptime_hours[1]} mins {uptime[1]} seconds",
				"inline": False
			}
		]
		for item in infos:
			info_emb.add_field(**item)
		info_emb.set_footer(text=self.client.user.name)
		info_emb.timestamp = discord.utils.utcnow()
		await ctx.send(embed=info_emb)


	@commands.hybrid_command(
		aliases=["calen", "calend", "year"],
		usage="calendar <year>"
		)
	@discord.app_commands.describe(year="The year to show calendar of")
	@commands.guild_only()
	async def calendar(self, ctx, year: Optional[int]=None):
		"""See a calendar from future or past"""
		if not year:
			year = discord.utils.utcnow().year
		embs = [
			discord.Embed(
				title=f"The Calendar of {year}",
				description=f"```\n{calendar.month(theyear=year, themonth=m)}\n```",
				colour=discord.Colour.random(),
				timestamp=discord.utils.utcnow()
			).set_footer(text=self.client.user.name)
			for m in range(1, 13)
		]
		return await ctx.send(
			embed=embs[0],
			view=PageButtons(embeds=embs, timeout=180)
			)


	@commands.hybrid_command(
		name="binary",
		aliases = ["bin"],
		usage="binary <the text to convert>"
		)
	@discord.app_commands.describe(text="The text that we are going to convert. DM the code to decode")
	@commands.guild_only()
	async def convert_to_binary(self, ctx, *, text: str=None):
		"""Converts a given text into binary."""
		if not ctx.interaction:
			try:
				await ctx.message.delete()
			except (discord.errors.HTTPException, discord.errors.Forbidden):
				await ctx.send(":x: I need Manage Messages Permission to delete your message!")
		if text is None:
			return await ctx.send(":x: Please try again providing a text to convert!")
		if len(text) > 1900:
			return await ctx.send(":x: Please make sure that your text doesn't contain more than 1900 characters!")
		else:
			if better_profanity.profanity.contains_profanity(text.lower()):
				warn_msg=":x: Contains words thats aren't allowed to convert!"
				return await ctx.interaction.response.send_message(content=warn_msg)
			else:
				converted_text = encode(text, "binary")
				info = f"{ctx.author.mention} `DM the following binary code to decode it!"
				enc_emb = discord.Embed(title="Text Encoding", description=converted_text, color=discord.Color.random())
			if ctx.interaction:
				return await ctx.interaction.response.send_message(content=info, embed=enc_emb, ephemeral=True)
			else:
				try:
					await ctx.author.send(info, embed=enc_emb)
				except (discord.errors.HTTPException, discord.errors.Forbidden):
					return await ctx.send(":x: Please make sure you have enabled 'Direct Messages' from server members!", delete_after=10)
				else:
					await ctx.send(":white_check_mark: Check DM please.", delete_after=5)


	@commands.hybrid_command(
		name="encrypt",
		aliases=["encode", "enc"],
		usage="encrypt <the text to encrypt>"
		)
	@discord.app_commands.describe(text="The text that is going to be encrypted")
	@commands.guild_only()
	async def cryptography_(self, ctx: commands.Context, *, text: str=None):
		"""Encrypts and transforms a given text into a secret code."""
		if not ctx.interaction:
			try:
				await ctx.message.delete()
			except (discord.errors.HTTPException, discord.errors.Forbidden):
				await ctx.send(":x: I need Manage Messages Permission to delete your message!", delete_after=6)
		if text is None:
			return await ctx.send(":x: Please try again providing the text you want to encrypt!", delete_after=7)
		if len(text) > 1900:
			return await ctx.send(":x: Please make sure that your text doesn't contain more than 1900 characters!", delete_after=8)
		if better_profanity.profanity.contains_profanity(text.lower()):
			await ctx.send(":warning: Please do not use bad words!")
			return
		final_str=str()
		key = randint(11, 98)
		for x in text:
			final_str+=self.alpha[(self.alpha.find(x)+key)%len(self.alpha)] if x in self.alpha else x
		encrypted = final_str+str(key)
		enc_emb = discord.Embed(title="Text Encryption", description=encrypted, color=discord.Color.random())
		if ctx.interaction:
			return await ctx.interaction.response.send_message(content=f"{ctx.author.mention} DM me the following encrypted text to decrypt it: ", embed=enc_emb, ephemeral=True)
		else:
			try:
				await ctx.author.send(f"{ctx.author.mention} `DM me the following encrypted text to decrypt it. : ")
				await ctx.author.send(embed=enc_emb)
			except (discord.errors.HTTPException, discord.errors.Forbidden):
				return await ctx.send(":x: Please make sure you have enabled 'Direct Messages from server members'! Or you can use the slash command instead.", delete_after=10)
			else:
				await ctx.send(":white_check_mark: Check DM please.", delete_after=5)

	@commands.hybrid_command(
		name='invite',
		aliases=['add', 'link', 'links'],
		usage="invite"
		)
	@commands.guild_only()
	async def invitation(self, ctx):
		"""Get a link to invite me :)"""
		inv_embed = discord.Embed(
			title="Invite me",
			description="""I'm so happy that you wanted to invite me :D!
To invite me to your server just click the invite button \U0001F90D""",
			color=discord.Color.blue(),
			timestamp=discord.utils.utcnow()
			)
		invite_url = discord.utils.oauth_url(
			self.client.user.id,
			permissions=discord.Permissions(administrator=True)
			)
		inv_embed.set_thumbnail(url=self.client.user.avatar.url)
		inv_embed.set_footer(text=self.client.user.name)
		view = discord.ui.View(timeout=None)
		view.add_item(discord.ui.Button(label="invite", url=invite_url))
		await ctx.send(embed=inv_embed, view=view)


async def setup(client):
    print("Setting up Extras....")
    await client.add_cog(Extras(client))

async def teardown(client):
    print("Unloading Extras....")
    await client.remove_cog(client.cogs['Extras'])
