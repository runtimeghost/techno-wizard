# pylint: disable=bad-indentation

from bot_ui import PageButtons
import discord
from discord.ext import commands


class Help(commands.Cog):
    
	def __init__(self, bot: commands.Bot):
		self.client: commands.Bot = bot


	@commands.command(name="help", aliases=["h"], usage="help")
	@commands.guild_only()
	async def helper_command(self, ctx):
		"""Get list of Commands"""

		if self.client.user.mentioned_in(ctx.message):
			prefix = await self.client.get_server_prefix(ctx)
		else:
			prefix = ctx.prefix
		all_pages = []
		for cog in self.client.cogs:
			if cog == "ExecCmd":
				continue
			pager = commands.Paginator(max_size=4000, suffix=None, prefix=None)
			for cmd in self.client.cogs[cog].walk_commands():
				if cmd.hidden:
					continue
				pager.add_line(
					f"""
{prefix}{str(cmd.parent)+' ' if cmd.parent else ''}{cmd.name}
    Description: {cmd.short_doc}
    Aliases: {cmd.aliases}
	{f'Usage: {prefix}{cmd.usage}'if cmd.usage else ''}
					"""
				)
			embs = [
				discord.Embed(
				title=cog,
				description=page,
				colour=discord.Colour.random(),
				timestamp=discord.utils.utcnow()
				) for page in pager.pages
			]
			all_pages += embs

		await ctx.send(
			"""
Here's the whole list of all the commands available in this bot.
The required arguments for a command are mentioned in it's Usage.
Arguments that are mentioned inside '<>' this bracket are required \
for the command to work! On the other hand, those which are mentioned inside \
'[]' this bracket are optional.

Make sure you use proper prefix and don't use these '<>' '[]' brackets while excuting commands.
I have used them here just to separate the optional and required arguments!
**If you find this too complicated, please use '/slash commands'**
**But in case of slash commands, full command name must be used \
i.e. Aliases A.K.A short forms are not supported in slash commands!**
			""",
			embed=all_pages[0],
			view=PageButtons(
			embeds=all_pages,
			timeout=15*60) # I guess 15 minutes is enough to go through the help command
			)


async def setup(bot):
	print("Setting up Help....")
	await bot.add_cog(Help(bot))

async def teardown(bot):
	print("Unloading Help....")
	await bot.remove_cog(bot.cogs['Help'])
