# pylint: disable=unspecified-encoding
# Help and Settings are taken from here



from discord.ext import commands
import discord
from json import dump, load
import better_profanity


class Settings(commands.Cog):

    def __init__(self, bot):
        self.client = bot

    @commands.group(
        name='settings', aliases=['setting', 'preferences', 'personalisation', 'personalization', 'set'],
        invoke_without_command=True, case_insensitive=True
    )
    @commands.guild_only()
    async def bots_settings(self, ctx):
        """Settings for bot"""
        prefix = ctx.prefix
        sett_embed = discord.Embed(
            title="Settings",
            description=f"Usage: {prefix}settings <option>",
            color=ctx.author.color
        )
        sett_embed.add_field(name="Moderation Settings",
                             value=f"{prefix}settings swp")
        sett_embed.add_field(name="Prefix settings",
                             value=f"{prefix}settings prefix", inline=False)
        sett_embed.add_field(
            name="Music settings", value=f"""{prefix}settings djrole\n{prefix}settings removedj""")
        sett_embed.add_field(name='Blacklist settings',
                             value=f'{prefix}settings block\n{prefix}settings unblock')
        sett_embed.set_author(name=f"{self.client.user.name}")
        sett_embed.set_footer(text=f"{self.client.user.name}")
        sett_embed.timestamp = discord.utils.utcnow()
        return await ctx.send(embed=sett_embed)

    @bots_settings.command(name="swp", aliases=["cursedwordsprotection", "swearwordsprotection", "betterprofanity"])
    @commands.has_guild_permissions(manage_guild=True)
    async def better_profanity_switch(self, ctx, *, state: str = None):
        """Enable or disable Swear words protection"""
        if state is None:
            prefix = ctx.prefix
            return await ctx.send(f"```\nUsage: {prefix}settings swp <on/off>\nDescription: SWP(SwearWords Protection) can be used to detect bad words in a message and instantly delete it. \
	That is, when it's turned on, if someone sends any bad word, the bot detects that bad word automatically and deletes it!\nAliases: 'cursedwordsprotection', 'swearwordsprotection', \
'betterprofanity'\n```")
        with open("database/better_profanity.json", "r") as bp:
            bp_servers = load(bp)
        if str(state).lower() == "on":
            if str(ctx.guild.id) not in bp_servers["server_ids"]:
                bp_servers["server_ids"].append(str(ctx.guild.id))
                with open("database/better_profanity.json", "w") as bp:
                    dump(bp_servers, bp, indent=8)
                return await ctx.send(":white_check_mark: Enabled SwearWords Protection for this server.")
            else:
                return await ctx.send(":x: SwearWords Protection already enabled for this server!")
        elif str(state).lower() == "off":
            try:
                bp_servers["server_ids"].remove(str(ctx.guild.id))
            except ValueError:
                return await ctx.send(":x: SwearWords Protection is not enabled for this server yet!")
            else:
                with open("database/better_profanity.json", "w") as bp:
                    dump(bp_servers, bp, indent=8)
                return await ctx.send(":warning: Disabled SwearWords Protection for this server.")
        else:
            return await ctx.send(":x: Invalid switch state! Valid options are 'on' and 'off'!")

    @better_profanity_switch.error
    async def profanity_detection_err(self, ctx: commands.Context, err):
        if isinstance(err, commands.MissingPermissions):
            return await ctx.send("\U0000274CYou need manage server permission to toggle SWP switch!")
        elif isinstance(err, commands.CheckFailure):
            return
        else:
            await self.client.dm_error_logs(err=err)

    @bots_settings.command(name="changeprefix", aliases=['c-p', 'prefix', 'cp', 'new-prefix'], description='Used to change prefix')
    @commands.has_permissions(manage_channels=True)
    async def change_prefix(self, ctx, new_prefix: str|None = None):
        """Change the bot's prefix"""
        if new_prefix is None:
            prefix = ctx.prefix
            return await ctx.send(f"""```\nUsage: {prefix}settings prefix <new_prefix>\nDescription: Used to change prefix \
for the bot!\nAliases: 'changeprefix', 'cp', 'c-p'\n```""")
        if better_profanity.profanity.contains_profanity(ctx.message.content):
            return
        if not len(new_prefix) > 5:
            with open("./database/prefixes.json", 'r') as prefix_file:
                prefix = load(prefix_file)
            prefix[str(ctx.guild.id)] = new_prefix
            with open("./database/prefixes.json", 'w') as prefix_file:
                dump(prefix, prefix_file, indent=8)
            return await ctx.send(f":white_check_mark: Prefix set to: {new_prefix}")
        else:
            return await ctx.send(":warning: Prefix length cannot be more than 5 characters!")


    @change_prefix.error
    async def prefix_change_error(self, ctx, err):
        if isinstance(err, commands.MissingPermissions):
            return await ctx.send("\U0000274CYou need manage channels permission to change the prefix! ")
        elif isinstance(err, commands.CheckFailure):
            return
        else:
            await self.client.dm_error_logs(err=err)


    @bots_settings.command(
            name='set-dj-role',
            aliases=['dj', 'set-dj', 'setdj', 'setdjrole', 'djrole', 'dj-role'],
            )
    @commands.has_guild_permissions(manage_roles=True)
    async def set_dj_role(self, ctx, role_name: discord.Role = None):
        """Set a role make the bot accept music commands only from that role"""
        if role_name is None:
            prefix = ctx.prefix
            return await ctx.send(f"""```\nUsage: {prefix}settings djrole <@mention_role>.\nDescription: Sets a role a DJ Role and bot \
takes command only from those who belong to this role!\nAliases: 'dj', 'set-dj', 'setdj', 'setdjrole', 'djrole', 'dj-role'\n```""")
        with open("./database/djonly_role_id.json", 'r') as djs:
            dj_role = load(djs)
        if dj_role[str(ctx.guild.id)] is not None:
            if dj_role[str(ctx.guild.id)] != str(role_name.id):
                dj_role[str(ctx.guild.id)] = str(role_name.id)
                with open("./database/djonly_role_id.json", 'w') as djs:
                    dump(dj_role, djs, indent=8)
                return await ctx.send(f"\U00002705 'DJ role has been changed to {role_name}'")
            else:
                return await ctx.send(":warning: '{0.name}' is already set as DJ role!`".format(role_name))
        else:
            dj_role[str(ctx.guild.id)] = str(role_name.id)
            with open("./database/djonly_role_id.json", 'w') as djs:
                dump(dj_role, djs, indent=8)
            return await ctx.send(f':white_check_mark: {role_name} is set as DJ role.')

    @set_dj_role.error
    async def dj_err(self, ctx, err):
        if isinstance(err, commands.MissingPermissions):
            return await ctx.send("\U0000274CThis action requires you to have Manage Roles permission!")
        elif isinstance(err, commands.CheckFailure):
            return
        elif isinstance(err, commands.RoleNotFound):
            return await ctx.send("Role not found! Try mentioning the role with an '@'")
        else:
            await self.client.dm_error_logs(err=err)

    @bots_settings.command(name='remove-dj', aliases=['removedj', 'remove-dj-role', 'removedjrole', 'rmvdj', 'remvdj', 'rmv-dj', 'rmdj'])
    @commands.has_guild_permissions(manage_roles=True)
    async def remove_dj(self, ctx, djrole: discord.Role = None):
        """Remove a role from dj role"""
        try:
            with open('./database/djonly_role_id.json', 'r') as djs:
                dj_role = load(djs)
            if djrole is None:
                if dj_role[str(ctx.guild.id)] is None:
                    prefix = ctx.prefix
                    return await ctx.send(f"```\nUsage: {prefix}settings remove-dj <@mention_current_djrole>\nDescription: Removes a role from DJ role \
list\nAliases: 'removedj', 'remove-dj-role', 'removedjrole', 'rmvdj', 'remvdj', 'rmv-dj', 'rmdj'\n```")
                return await ctx.send(":x: Please mention the current dj role to remove it from dj role!")
            elif dj_role[str(ctx.guild.id)] != str(djrole.id):
                return await ctx.send(f":x: '{djrole.name}' is not a dj role!")
            elif dj_role[str(ctx.guild.id)] == str(djrole.id):
                dj_role[str(ctx.guild.id)] = None
            with open('./database/djonly_role_id.json', 'w') as djs:
                dump(dj_role, djs, indent=8)
            return await ctx.send(f":white_check_mark: Successfully removed {djrole.name} as the dj role.")
        except (KeyError, ValueError):
            prefix = ctx.prefix
            return await ctx.send(f"```\nUsage: {prefix}settings remove-dj <@mention_current_djrole>\nDescription: Removes a role from DJ role \
list\nAliases: 'removedj', 'remove-dj-role', 'removedjrole', 'rmvdj', 'remvdj', 'rmv-dj', 'rmdj'\n```")

    @remove_dj.error
    async def remove_dj_err(self, ctx, err):
        if isinstance(err, commands.MissingPermissions):
            return await ctx.send("\U0000274C You must have manage roles permission to remove a dj role!")
        elif isinstance(err, commands.RoleNotFound):
            return await ctx.send(":x: Couldn't find the Role you are trying to remove! Try again Mentioning the role aith an '@'")
        elif isinstance(err, commands.CheckFailure):
            return
        else:
            await self.client.dm_error_logs(err=err)

    @bots_settings.command(name='blacklist', aliases=['black', 'block', 'blocklist', 'blk'])
    @commands.has_guild_permissions(manage_roles=True)
    async def blacklist_(self, ctx, member: discord.Member=None):
        """Put a member in blacklist"""
        if member is None:
            prefix = ctx.prefix
            return await ctx.send(f"""```\nUsage: {prefix}settings blacklist <@mention_the_member>.\nDescription: Puts a member \
in blacklist! I will not take command from a blacklisted member.\nAliases: 'black', 'block', 'blocklist', 'blk'\n```""")
        if member.id == ctx.author.id:
            return await ctx.send("\U0000274C You cannot block yourself!")
        if ctx.author.top_role <= member.top_role or member.id == ctx.guild.owner_id:
            return await ctx.send(":x: You cannot put someone to blacklist if your role is not in higher rank than their role!")
        with open('./database/blacklist.json', 'r') as blocked:
            blocked_users = load(blocked)
        try:
            if str(member.id) in blocked_users[str(ctx.guild.id)]:
                return await ctx.send(f"\U0000274C {member.name}#{member.discriminator} is already in blacklist!")
            blocked_users[str(ctx.guild.id)].append(str(member.id))
        except KeyError:
            blocked_users[str(ctx.guild.id)] = list()
            blocked_users[str(ctx.guild.id)].append(str(member.id))
        finally:
            with open('./database/blacklist.json', 'w') as blocked:
                dump(blocked_users, blocked, indent=8)
            await ctx.send(f":white_check_mark: {member} has been put to blacklist!")

    @blacklist_.error
    async def block_err(self, ctx, err):
        if isinstance(err, commands.MissingPermissions):
            return await ctx.send("\U0000274CYou must have manage roles permission to block a member!")
        elif isinstance(err, commands.MemberNotFound):
            return await ctx.send("\U0000274CMember not found in ther server! Try mentioning the member with an '@'.")
        elif isinstance(err, commands.CheckFailure):
            return
        else:
            await self.client.dm_error_logs(err=err)

    @bots_settings.command(name='remove-blacklist', aliases=['remv-block', 'unblock', 'rmv-blk', 'remvblk', 'removeblacklist', 'remove-block', 'removeblock'])
    @commands.has_guild_permissions(manage_roles=True)
    async def remv_block(self, ctx, member: discord.Member = None):
        """Remove a member from blocklist"""
        if member is None:
            prefix = ctx.prefix
            return await ctx.send(f"""```\n{prefix}settings unblock <@mention_the_member>.\nRemoves a member from blocklist and bot starts taking command from that member \
again!\nAliases: 'unblock', 'rmv-blk', 'remvblk', 'removeblacklist', 'remove-block', 'removeblock', 'remove-blacklist'\n```""")
        if ctx.author.top_role <= member.top_role or member.id == ctx.guild.owner_id:
            return await ctx.send(":x: You cannot remove someone from blacklist if your role is not in higher rank than their role!")
        with open("./database/blacklist.json", 'r') as blocks:
            blocked_user = load(blocks)
        try:
            del blocked_user[str(ctx.guild.id)][blocked_user[str(
                ctx.guild.id)].index(str(member.id))]
        except (KeyError, ValueError):
            return await ctx.send(":warning: Mentioned member is not in the blocklist! Try mentioning the member with an '@'")
        else:
            with open('./database/blacklist.json', 'w') as blocks:
                dump(blocked_user, blocks, indent=8)
            return await ctx.send(f":white_check_mark: {member} has been removed from blacklist!")

    @remv_block.error
    async def remvblk_err(self, ctx, err):
        if isinstance(err, commands.MissingPermissions):
            return await ctx.send("\U0000274CYou must have manage roles permission to remove a member from blocklist!")
        elif isinstance(err, commands.MemberNotFound):
            return await ctx.send("\U0000274CMember not found in the server! Try mentioning the member with an '@'.")
        elif isinstance(err, commands.CheckFailure):
            return
        else:
            await self.client.dm_error_logs(err=err)


async def setup(client):
    print("Setting up Settings....")
    await client.add_cog(Settings(client))


async def teardown(client):
    print("Unloading Help Settings....")
    await client.remove_cog(client.cogs['Settings'])
