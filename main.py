# pylint: disable=bad-indentation,used-before-assignment,unspecified-encoding,broad-exception-caught,exec-used,eval-used,arguments-differ

# |Techno-wizard|


"""
####################################################################################################
####################################################################################################
##                       The important thing is not to stop questioning.                          ##
##                       Because curiosity has its own reason for existing.                       ##
##                                                                             -Albert Einstein   ##
####################################################################################################
####################################################################################################
"""


# Modules initialization

import aiohttp
from bot_ui import PageButtons
import traceback
from time import time
import math
from os import environ, listdir, chdir, path, name as kernel
import typing
from json import load,  dump
import discord
from discord.ext import commands
import io
from dotenv import load_dotenv
import contextlib
from textwrap import indent
import logging
from asyncio import sleep as asleep, set_event_loop_policy, WindowsSelectorEventLoopPolicy
# import subprocess
# from threading import Thread

if kernel=='nt':
	set_event_loop_policy(WindowsSelectorEventLoopPolicy())

load_dotenv()

dirpath = path.dirname(path.realpath(__file__))
chdir(dirpath)

# Setting up logger
handler = logging.FileHandler(
		filename='program_logs.log',
		encoding='utf-8',
		mode='w'
	)
formatter = logging.Formatter(
	'%(asctime)s:%(levelname)s:%(name)s: %(message)s'
	)

handler.setFormatter(formatter)
discord.utils.setup_logging(
	handler=handler,
	level=logging.INFO,
	formatter=formatter,
	root=True
	)


TOKEN = environ.get("SECRET_TOKEN_VAR")


cogs = [cog[:-3] for cog in listdir("Extensions/") if cog.startswith("ext") and cog.endswith(".py")]

class TechnoWizard(commands.Bot):
# The Bot class, But I have added extra methods so that I can use them globally across all files of the project
	def __init__(self, **options):
		self.client_session = None
		self.start_time = time()
		self.test_guild = None
		self.pymoji = None
		self.infinity_emoji = None
		self.owner = None
		self.note_channel = None

		super(TechnoWizard,
			self
		).__init__(
			command_prefix=self.server_prefix,
			strip_after_prefix=True,
			case_insensitive=True,
			description=None,
			intents=discord.Intents.all(),
			root_logger=False,
			help_command=None,
			**options
		)

	# def b4exit(self):
	# 	print()
	# 	self.loop.create_task(self.close())

	async def setup_hook(self):
		self.test_guild = await self.fetch_guild(932683373137240154)
		# self.loop.add_signal_handler(signal.SIGINT, self.b4exit)
		# self.loop.add_signal_handler(signal.SIGTERM, self.b4exit)
		with contextlib.suppress(discord.errors.NotFound):
			self.pymoji = await self.test_guild.fetch_emoji(1077662671551348976)
			self.infinity_emoji = await self.test_guild.fetch_emoji(1078021826229325904)
		self.client_session = aiohttp.ClientSession()
		self.owner = await self.fetch_user(self.owner_id)
		self.note_channel = await self.fetch_channel(1081508205055717406)
		for cog in cogs:
			await self.load_extension(f"Extensions.{cog}")

	async def get_server_prefix(self, ctx_or_message: typing.Union[commands.Context, discord.Message]):
		# This coroutine reads the database files and returns the prefix dedicated for the current server.
		# Also writes the default server prefix in the database if not available
		with open("./database/prefixes.json", 'r') as prefix_file:
			prefix = load(prefix_file)
		try:
			return prefix[str(ctx_or_message.guild.id)]
		except KeyError:
			prefix[str(ctx_or_message.guild.id)] = "-"
			with open("./database/prefixes.json", "w") as prefix_file:
				dump(prefix, prefix_file, indent=8)
			return prefix[str(ctx_or_message.guild.id)]

	async def server_prefix(self, *args):
		# This coroutine takes the prefix from the above coroutine and returns a callable which is passed to the commands_prefix argument of the Bot instance
		_prefixes_ = await self.get_server_prefix(args[1])
		servers_prefix = commands.when_mentioned_or(_prefixes_)
		return servers_prefix(args[0], args[1])

	async def send_self_embed(self, ctx):
		# A coroutine that sends an embed containing details about the bot
		prefix = await self.get_server_prefix(ctx)
		selfembed = discord.Embed(
			title='About Me.',
			description=f"""```\nHi :D. My name is {self.user.name}! A simple multi-purpose Discord bot.\nI'm more like a music \
	bot but I have some moderation commands too. Type \"{prefix}help\" for a list of available \
	commands\n\n----- It's XENON learning to Code :) -----\n#Peace\n```\n\U0001F90D""",
			color=self.user.color,
			timestamp=discord.utils.utcnow()
		)
		selfembed.set_author(
			name=f'{self.user.name}', icon_url=self.user.avatar.url)
		selfembed.set_image(url=self.user.avatar.url)
		selfembed.add_field(
			name='Developer:', value='`MD Rimel Hossain\n{0.name}#{0.discriminator} `'.format(self.owner), inline=True)
		selfembed.set_footer(
			text=f'{self.user.name}', icon_url=self.user.avatar.url)
		return await ctx.send(embed=selfembed)

	async def dm_error_logs(self, err):
		try:
			raise err
		except Exception as e:
			logging.exception("ERROR")
			await self.owner.send(
				embed=discord.Embed(
					title="Error!",
					description=f"```py\n{traceback.format_exc()}\n```",
					color=discord.Colour.red(),
					timestamp=discord.utils.utcnow()
				)
			)
			print(e.__class__.__name__, ':', str(e))


	async def on_ready(self):
		await self.tree.sync()
		await self.change_presence(status=discord.Status.idle, activity=discord.Activity(type=discord.ActivityType.listening, name="Your commands :)"))
		await self.owner.send(":green_circle: --------I'm online!--------`:green_circle:")
		# Printing in the console and sending the owner a Dm that the bot has successfully logged in.
		print(
			f"Logged in as {self.user.name}#{self.user.discriminator} (id: {self.user.id})"
		)
		print("Bot is Online!\n")

	async def on_guild_join(self, server: discord.Guild):
		# Printing the new server name in the comsole, sending DM to the owner and Sending Thank you message in the system channel of the server when the bot joins a new server
		join_embed = discord.Embed(
			title='Thanks',
			description='''Thanks a lot for inviting me!\nMy default prefix is **"-"**
		\nType "-help" for a list of available commands.
		Mention me anytime to know my prefix. (Useful when you forget the prefix.)''',
			color=discord.Colour.from_rgb(238, 181, 217)
		)
		join_embed.add_field(name='Joined server:',
								value=server.name, inline=False)
		join_embed.set_image(
			url='https://i.pinimg.com/originals/66/e6/4e/66e64edb3c4519f8f248cfe73496b55d.jpg')
		join_embed.set_footer(text=self.user.name,
								icon_url=self.user.avatar.url)
		join_embed.timestamp = discord.utils.utcnow()
		channel = server.system_channel
		with open("./database/prefixes.json", 'r') as prefix_file:
			prefix = load(prefix_file)
		prefix[str(server.id)] = "-"
		with open("./database/prefixes.json", "w") as prefix_file:
			dump(prefix, prefix_file, indent=8)
		await self.owner.send("----Joined a new server: {0.name}----".format(server))
		print(f"Joined new server: \"{server.name}\"")
		return await channel.send(embed=join_embed)

	async def on_guild_remove(self, server: discord.Guild):
		# Printing the name of server from where the bot has been removed
		with open("./database/prefixes.json", "r") as prefix_file:
			prefix = load(prefix_file)
		with contextlib.suppress(KeyError):
			del prefix[str(server.id)]
		with open("./database/prefixes.json", 'w') as prefix_file:
			dump(prefix, prefix_file, indent=8)
		await self.owner.send("----Got removed from {0.name}----".format(server))
		print(f"Got removed from \"{server.name}\"")

	async def on_command_error(self, ctx, err):
		# return await ctx.send(err.message)
		if isinstance(err, commands.BotMissingPermissions):
			return await ctx.send(":x: I don't have enough permission to perform this task!")
		elif isinstance(err, commands.NoPrivateMessage):
			await ctx.send(":x: Please use commands in server channels only!")
		elif isinstance(err, commands.NotOwner):
			return await ctx.send(":warning: :x: This command is available for the owner only!")
		elif isinstance(err, (discord.errors.HTTPException)):
			if err.status not in (403, 440):
				raise err
			else:
				return None
		elif isinstance(err, commands.CommandOnCooldown):
			return await ctx.send(f"\U0000274C `This command is on cooldown. Please try again after {math.ceil(err.retry_after)} seconds!")
		elif isinstance(
			err,
			(
				commands.MissingPermissions,
				commands.MemberNotFound,
				commands.CommandNotFound,
				commands.CheckFailure,
				discord.NotFound,
				discord.errors.Forbidden,
				commands.MissingRequiredArgument,
				commands.BadArgument
			)
			):
			return None
		else:
			await self.dm_error_logs(err=err)
			await ctx.send(":warning: An unknown error occurred. The owner has been informed about the error!")


# Creating the Bot object
client = TechnoWizard(owner_id=425590285943439362)

@client.check
# A check whether the author is blocked by any moderator
async def not_is_blocked(ctx: commands.Context):
	if isinstance(ctx.channel, discord.DMChannel):
		return True
	with open('./database/blacklist.json', 'r') as blocked:
		blocks = load(blocked)
	try:
		if str(ctx.author.id) in blocks[str(ctx.guild.id)] and ctx.author.id != client.owner_id and ctx.author.id != ctx.guild.owner_id:
			await ctx.send(":warning: You are blocked by a moderator! Cannot take your commands.")
			return False
		else:
			return True
	except KeyError:
		blocks[str(ctx.guild.id)] = list()
		with open('./database/blacklist.json', 'w') as blocked:
			dump(blocks, blocked, indent=8)
		return True


@client.check
# A check whether the bot is under maintenance
async def not_is_off(ctx: commands.Context):
	with open("./database/owners_db.json", 'r') as current_state:
		state = load(current_state)
	if (state['bot_is_off'] and ctx.author.id != client.owner_id):
		await ctx.send(":warning: The bot is currently under maintenance! Please try again after 30 mins (approx.)")
		return False
	return True

#| Moderation context Menus
@client.tree.context_menu(name="Kick")
@discord.app_commands.checks.has_permissions(kick_members=True)
@discord.app_commands.checks.bot_has_permissions(kick_members=True)
async def context_kick(interaction, member: discord.Member):
	try:
		member_name = member.name
		await member.kick(reason='Unknown Reason')
	except discord.Forbidden:
		return await interaction.response.send_message("**Any one of us Missing Required Permissions!**", ephemeral=True)
	else:
		return await interaction.response.send_message(
			embed=discord.Embed(
				title='Kick',
				description=f':white_check_mark: Successfully Kicked out {member_name}',
				timestamp=discord.utils.utcnow(),
				color=discord.Color.random()
				)
			)

@client.tree.context_menu(name="Ban")
@discord.app_commands.checks.has_permissions(ban_members=True)
@discord.app_commands.checks.bot_has_permissions(ban_members=True)
async def context_ban(interaction, member: discord.Member):
	try:
		member_name = member.name
		await member.ban(reason='Unknown Reason')
	except discord.Forbidden:
		return await interaction.response.send_message("**Any one of us Missing Required Permissions!**", ephemeral=True)
	else:
		return await interaction.response.send_message(
			embed=discord.Embed(
				title='Ban',
				description=f':white_check_mark: Successfully Banned {member_name}',
				timestamp=discord.utils.utcnow(),
				color=discord.Color.random()
				)
			)


# @client.command()
# @commands.is_owner()
# async def test(ctx):
# 	raise discord.DiscordException

@client.event
async def on_message(text: discord.Message):
	if not isinstance(text.channel, discord.DMChannel) or text.author.bot:
		if client.user.mentioned_in(text):
			prefix = await client.get_server_prefix(text)
			await text.channel.send(
				f"My prefix in this server is: {prefix} \nType '{prefix}help' to get commands list."
				)
		return await client.process_commands(text)
	else:
		return None


@client.command(name="sl", aliases=["s-l", "servers", "server-list"], hidden=True)
@commands.guild_only()
@commands.is_owner()
async def servers(ctx):
	count = len(client.guilds)
	pager = commands.Paginator()
	x = 0
	for line in client.guilds:
		x += 1
		next_line = f"__{x}__| {str(line.name)}" if line.id != ctx.guild.id else f"__{x}__| {str(line.name)} <This_Server>"
		pager.add_line(next_line)
	embs = [
		discord.Embed(
			title='Servers',
			description=f"Total {count} servers:\n\n{p}",
			color=discord.Colour.random(),
			timestamp=discord.utils.utcnow()
		).set_footer(text=client.user.name) for p in pager.pages
	]
	await ctx.send(
		view=PageButtons(embeds=embs) if len(embs) > 1 else None
	)


@client.command(aliases=["announce", "anc"])
@commands.is_owner()
async def announcement(ctx, *, msg: str=""):
	if not msg:
		return await ctx.send(":x: Message field is empty!")
	status = {}
	mymsg = await ctx.send(f"{client.infinity_emoji} `Trying to Send this message to any one channel in each server.")
	for server in client.guilds:
		status[server.name] = "Could not perform action"
		channels = [channel for channel in server.channels if isinstance(channel, discord.TextChannel)]
		for chann in channels:
			try:
				await chann.send(msg)
			except discord.DiscordException:
				continue
			else:
				status[server.name] = "success"
				await asleep(2) #| An unsure rate limit handling
				break
	await mymsg.edit(content=f"```py\n{status}\n``")


@client.command(name='dc-useless-vc', aliases=['dc-u', 'dcu'])
@commands.guild_only()
@commands.is_owner()
async def auto_dc_by_owner(ctx: commands.Context):
	count = 0
	msg = await ctx.send("Disconnecting useless vcs.....")
	for vc in client.voice_clients:
		if vc is not None and not vc.is_playing:
			membs = tuple(
				mem.id for mem in vc.channel.members if mem.id != client.user.id)
			if len(membs) == 0:
				await vc.disconnect()
				count += 1
				if vc.guild.system_channel is not None:
					await asleep(0.5)
	if count:
		with contextlib.suppress(discord.NotFound):
			await msg.delete()
		await ctx.channel.send(f"{count} voice clients disconnected successfully.....")


@client.command(name='restart-bot', aliases=['restart_bot', 'reload', 'restart-client', 'reboot'], description='For owner only!')
@commands.is_owner()
async def restart_client(ctx):
	await ctx.send("Restarting....")
	for vc in client.voice_clients:
		server = vc.guild
		try:
			await vc.disconnect()
			await server.system_channel.send(":warning: The bot has been restarted by it's owner! Maybe a minor update has been pushed!")
			print("--Disconnected vc from {0.name}".format(vc.guild))
		except AttributeError:
			continue
	for filename in cogs:
		try:
			await client.reload_extension(f'Extensions.{filename}')
		except Exception as e:
			await ctx.send(f":warning: Error occurred while reloading {filename}\n{e.__class__.__name__}: {e}")
			print("Error while unloading", filename)
	await client.tree.sync()
	await ctx.send("Extensions and commmand tree reloaded successfully!")


@client.command(name="on", aliases=['turnon', "wakeup", "wake"])
@commands.guild_only()
@commands.is_owner()
async def turn_on(ctx):
	for filename in cogs:
		try:
			await client.load_extension(f'Extensions.{filename}')
		except Exception as e:
			print(e)
			await ctx.send(f"\U0000274CError occurred while loading {filename}")
	await ctx.send("Changing state from down to up.....\nTurning on!")
	with open("./database/owners_db.json", 'w') as bot_state:
		dump({'bot_is_off': False}, bot_state, indent=4)
	await client.change_presence(status=discord.Status.idle, activity=discord.Activity(type=discord.ActivityType.listening, name="Your commands :)"))
	await ctx.send("I'm back online again!")


@client.command(name='shutdown', aliases=['turnoff', 'off', "sleep"])
@commands.guild_only()
@commands.is_owner()
async def shutdown_bot(ctx):
	for vc in client.voice_clients:
		server = vc.guild
		with contextlib.suppress(discord.DiscordException):
			await vc.disconnect()
			await server.system_channel.send(":warning: The bot has been taken under maintainance by the owner! Please try again after it's online again.")
		print("--Disconnected vc from {0.name}".format(vc.guild))
	for filename in cogs:
		try:
			await client.unload_extension(f'Extensions.{filename}')
		except Exception as e:
			print(e)
			await ctx.send(f"\U0000274CError occurred while unloading {filename}")
	await ctx.send("Changing state from up to down.....\nShutting down!")
	with open("./database/owners_db.json", 'w') as z:
		dump({'bot_is_off': True}, z, indent=4)
	await client.change_presence(status=discord.Status.do_not_disturb, activity=discord.Activity(type=discord.ActivityType.listening, name="Owner's Commands"))


@client.command(name='x:eval', aliases=['x:evaluate', "x:ev"])
@commands.guild_only()
@commands.is_owner()
async def x_evaluate(ctx, *, cmd):
	if "input(" in cmd.lower() or "input (" in cmd.lower():
		return await ctx.send(":x: Cannot Execute input method!")
	cmd = cmd.strip('`')
	try:
		res = eval(cmd)
	except Exception as e:
		return await ctx.send("\U0000274CFailed!\n{0.__class__.__name__}: {0}".format(e))
	else:
		ev_emb = discord.Embed(
			description=f'{res}', color=discord.Color.green())
		return await ctx.send(embed=ev_emb)


@client.command(name="x:exec", aliases=["x:execute", "x:exc"])
@commands.guild_only()
@commands.is_owner()
async def x_execute(ctx, *, cmd: str):
	if "input(" in cmd.lower() or "input (" in cmd.lower():
		return await ctx.send(":x: Cannot Execute input method!")
	if cmd.startswith("``") and cmd.endswith("``"):
		cmd = ("\n".join(cmd.split("\n")[1:])).rstrip('`')
	local_vars = {
		'discord': discord,
		'commands': commands,
		'client': client,
		'ctx': ctx
	}
	no_error = True
	output = io.StringIO()
	try:
		with contextlib.redirect_stdout(output):
			exec(f"async def eval_func():\n{indent(cmd, '    ')}", local_vars)
			returned_val = await local_vars['eval_func']()
			result = f"**\U00002705Output**\n\n{output.getvalue()}\n\n`Returned value: {returned_val}`"
	except Exception as e:
		result = f"**\U0000274CFailed to Execute!**\n{e.__class__.__name__}: {e}"
		no_error = False
	finally:
		eval_emb = discord.Embed(title="Code Execution", description=result,
									color=discord.Color.green() if no_error else discord.Color.dark_red())
		eval_emb.set_footer(text=str(client.user.name))
		eval_emb.timestamp = discord.utils.utcnow()
		await ctx.send(embed=eval_emb)


if __name__ == '__main__':
	# def start_lava():
	# 	subprocess.run(["java", "-jar", "Lavalink.jar"], stdout=open("lavalogs.log", "w"))
	# client.lavalink = Thread(target=start_lava)
	# client.lavalink.start()
	# sleep(10.0) #| Waiting for the lavalink server to start

	client.run(TOKEN)

