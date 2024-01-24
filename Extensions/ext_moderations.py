# pylint: disable=unspecified-encoding,broad-exception-caught

# Moderation features of "Melodies'O Arts"


import json
from typing import Optional
import contextlib
from discord.ext import commands
import discord
from bot_ui import ConfirmButtons
import better_profanity

better_profanity.profanity.load_censor_words()


class Moderations(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_message(self, msg):
        if msg.author.id == self.client.user.id or msg.author.bot:
            return
        if not isinstance(msg.channel, discord.DMChannel):
            with open("database/better_profanity.json", "r") as bp:
                swearwords_protected_servers = json.load(bp)
            if str(msg.guild.id) in swearwords_protected_servers["server_ids"]:
                if better_profanity.profanity.contains_profanity(str(msg.content).lower()):
                    try:
                        await msg.delete()
                    except discord.errors.NotFound as e:
                        if e.status == 404:
                            return
                    await msg.channel.send(":warning: Please avoid using bad words!")
            return

    @commands.hybrid_command(
        name='kick',
        aliases=['k', 'ki', 'kic'],
        usage="kick <mention a single or members>"
        )
    @commands.guild_only()
    @commands.has_permissions(kick_members=True)
    async def kick_(self, ctx: commands.Context, members: commands.Greedy[discord.Member]=None, *, cause='<Reason not provided>'):
        """Kick one or more members"""
        if not ctx.interaction:
            with contextlib.suppress(discord.errors.Forbidden):
                await ctx.message.delete()
        if members is None:
            return await ctx.send("\U0000274C `Please try again mentioning at least one member you're trying to kick out!")
        success = []
        failed = []
        for member in members:
            if member.id == self.client.user.id:
                continue
            if ctx.author.top_role > member.top_role or ctx.author == ctx.guild.owner:
                try:
                    await member.kick(reason=cause)
                except discord.errors.Forbidden:
                    failed.append(str(member))
                else:
                    if not member.bot:
                        with contextlib.suppress(discord.errors.Forbidden):
                            await member.send(f"```\nYou have been kicked you out from {ctx.guild.name}!\nReason: {cause}\n``")
                    success.append(str(member))
            else:
                failed.append(str(member))
        kick_embed = discord.Embed(
            title='Kick Out',
            description=f'{":white_check_mark:" if success else ":x:"} `Kicked out: {", ".join(success)} \nReason: {cause}`',
            colour=ctx.author.color,
            timestamp=discord.utils.utcnow()
        )
        if failed: kick_embed.description += f'\n:warning: Failed to kick: {", ".join(failed)}\nPossible cause: Higher Role!'
        kick_embed.set_footer(text='{0.name}'.format(self.client.user))
        return await ctx.send(embed=kick_embed)

    @kick_.error
    async def kick_error(self, ctx, exception):
        if isinstance(exception, commands.MissingPermissions):
            await ctx.send("\U0000274C `You don't have enough permission to kick a member. ")
        elif isinstance(exception, commands.MemberNotFound):
            await ctx.send("\U0000274C `Could not find the member you are trying to kick out!")
        elif isinstance(
            exception,
            (commands.MissingRequiredArgument, commands.CheckFailure, commands.BadArgument)
            ):
            return None
        else:
            await self.client.dm_error_logs(err=exception)


    @commands.hybrid_command(
        name='ban',
        aliases=['b', 'ba'],
        usage="ban <mention a single or multiple members>")
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    async def ban_(
        self, 
        ctx: commands.Context, members: commands.Greedy[discord.Member]=None, *,
        cause: Optional[str]='<Reason not provided>'
        ):
        """Ban one or more members"""
        if not ctx.interaction:
            with contextlib.suppress(discord.errors.Forbidden):
                await ctx.message.delete()
        if members is None:
            return await ctx.send("\U0000274C `Please try again mentioning the member you are trying to ban!")
        success = []
        failed = []
        for member in members:
            if member.id == self.client.user.id:
                continue
            if ctx.author.top_role > member.top_role or ctx.author == ctx.guild.owner:
                try:
                    await member.ban(reason=cause)
                except discord.errors.Forbidden:
                    failed.append(str(member))
                else:
                    if not member.bot:
                        with contextlib.suppress(discord.errors.Forbidden):
                            await member.send(f"```\nYou have been banned from {ctx.guild.name}!\nReason: {cause}\n``")
                    success.append(str(member))
            else:
                failed.append(str(member))
        ban_embed = discord.Embed(
            title='Ban',
            description=f'{":white_check_mark:" if success else ":x:"} `Banned: {", ".join(success)} \nReason: {cause}`',
            colour=ctx.author.color,
            timestamp=discord.utils.utcnow()
        )
        if failed: ban_embed.description += f'\n:warning: Failed to ban: {", ".join(failed)}\nPossible cause: Higher Role!'
        ban_embed.set_footer(text='{0.name}'.format(self.client.user))
        return await ctx.send(embed=ban_embed)


    @ban_.error
    async def ban_error(self, ctx: commands.Context, exception):
        if isinstance(exception, commands.MissingPermissions):
            await ctx.send("\U0000274CYou don't have enough permission to ban a member. ")
        elif isinstance(exception, commands.MemberNotFound):
            await ctx.send("\U0000274CCould not find the member you are trying to ban out!")
        elif isinstance(exception, commands.MissingRequiredArgument) or isinstance(exception, commands.BadArgument) or isinstance(exception, commands.CheckFailure):
            return None
        else:
            await self.client.dm_error_logs(err=exception)


    @commands.hybrid_command(
        name="selfleave",
        aliases=["leaveserver", "leaveguild", "leave-guild", "leave-server"],
        description="Bot leaves the server itself :(",
        usage="selfleave"
        )
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def self_leave(self, ctx):
        if not ctx.interaction:
            with contextlib.suppress(discord.errors.Forbidden):
                await ctx.message.delete()
        confirmation_embed = discord.Embed(
            title="Leave",
            description="Do you really want me to leave this server? :(",
            colour=discord.Colour.red(),
            timestamp=discord.utils.utcnow()
            )
        confirmation_embed.set_footer(text=self.client.user.name)
        confirm_view = ConfirmButtons(timeout=40)
        confirmation_message = await ctx.send(embed=confirmation_embed, view=confirm_view)
        await confirm_view.wait()
        if confirm_view.value is None:
            return await confirmation_message.delete()
        elif confirm_view.value == False:
            return await ctx.send("Thank you. I will try not to disappoint you :)")
        else:
            await ctx.send(f"I'm sorry if I've disappointed you! To report any bugs DM {self.client.owner}")
            return await ctx.guild.leave()


    @self_leave.error
    async def leave_server_error(self, ctx: commands.Context, err):
        if isinstance(err, commands.MissingPermissions):
            await ctx.send("\U0000274C `You must have manage server permission to add me or to remove me from this server. ")
        elif isinstance(err, discord.errors.Forbidden):
            if err.status == 403:
                return
            else: raise err
        else:
            await ctx.send(":warning: Error while leaving the server! Please kick me out manually!")
            await self.client.dm_error_logs(err=err)

    @commands.hybrid_command(
        name="mute",
        aliases=['shutup'],
        description="Mute a member!",
        usage="mute <@mention or member id>"
        )
    @commands.guild_only()
    @commands.has_guild_permissions(manage_roles=True)
    async def mute_member(self, ctx: commands.Context, member: discord.Member=None, *, reason: Optional[str]=""):
        if not ctx.interaction:
            with contextlib.suppress(discord.errors.Forbidden):
                await ctx.message.delete()
        if member is None:
            await ctx.send("\U0000274CPlease try again mentioning the member you are trying to mute!")
        if member.id == ctx.author.id:
            return await ctx.send(":x: You cannot mute yourself!")
        if member.id == self.client.user.id:
            return await ctx.send(":warning: I won't be able to process commands if I am muted!")
        if ctx.author.top_role <= member.top_role and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send(":x: Your top role must be in higher position than the member's top role whom you're trying to mute!")
        muted_role = discord.utils.get(ctx.guild.roles, name="MUTED")
        if muted_role is None:
            loading = self.client.infinity_emoji
            txt = await ctx.send(f"{loading} `Initializing for the first time.... ")
            try:
                muted_role = await ctx.guild.create_role(name="MUTED")
            except (discord.errors.Forbidden, discord.errors.HTTPException):
                return await ctx.send("\U0000274C `Failed to initialize! I need permission to manage roles.")
            else:
                try:
                    for channel in ctx.guild.channels:
                        await channel.set_permissions(
                            muted_role,
                            change_nickname=False, 
                            send_messages=False,
                            use_external_emojis=False, 
                            connect=False, speak=False,
                            read_message_history=False,
                            read_messages=False,
                            view_channel=True)
                except (discord.errors.Forbidden, discord.errors.HTTPException):
                    return await ctx.send("\U0000274C `Failed to initialize! I need permission to manage permissions for a channel.")
                finally: await txt.delete()
        roles = [rol.id for rol in member.roles]
        if muted_role.id in roles:
            return await ctx.send(":warning: The mentioned member is already muted!")
        await member.add_roles(muted_role, reason=reason)
        mute_embed = discord.Embed(
            title="Mute", 
            description=f":lock: {member.name}#{member.discriminator} has been muted | **{reason}**",
            colour=discord.Color.purple()
            )
        mute_embed.set_footer(text=str(self.client.user.name))
        mute_embed.timestamp = discord.utils.utcnow()
        await ctx.send(embed=mute_embed)
        if not member.bot:
            with contextlib.suppress(discord.errors.HTTPException, discord.errors.Forbidden):
                await member.send(f"You have been muted in server: '{ctx.guild.name}'")

    @mute_member.error
    async def mute_err(self, ctx:commands.Context, error):
        if isinstance(error, commands.MissingPermissions):
            return await ctx.send("\U0000274C `You must have manage roles permission to mute a member!")
        elif isinstance(error, discord.errors.Forbidden):
            if error.status == 403:
                return await ctx.send("\U0000274C `I don't have permission to mute that member!")
        elif isinstance(error, commands.MemberNotFound):
            return await ctx.send("\U0000274C `Could not find the member you are trying to mute! Try again mentioning them with an '@'")
        elif isinstance(error, commands.MissingRequiredArgument) or isinstance(error, commands.BadArgument) or isinstance(error, commands.CheckFailure):
            return
        else:
            await self.client.dm_error_logs(err=error)

    @commands.hybrid_command(
        name="unmute",
        description="Unmute a member!",
        usage="unmute <@mention member or member id>"
        )
    @commands.guild_only()
    @commands.has_guild_permissions(manage_roles=True)
    async def unmute_member(self, ctx: commands.Context, member: discord.Member=None, *, reason: Optional[str]=''):
        if not ctx.interaction:
            with contextlib.suppress(discord.errors.Forbidden):
                await ctx.message.delete()
        if member is None:
            return await ctx.send("\U0000274C `Please try again mentioning the member you are trying to unmute!")
        if member.id == self.client.user.id:
            return await ctx.send(":warning: I am not muted!")
        if ctx.author.top_role <= member.top_role and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send(":x: Your top role must be in higher position than that of the member you're trying to unmute!")
        muted_role = discord.utils.get(ctx.guild.roles, name="MUTED")
        roles = tuple(rol.id for rol in member.roles)
        if muted_role is None or muted_role.id not in roles:
            return await ctx.send(":warning: The mentioned member has not been muted yet!")
        else:
            await member.remove_roles(muted_role)
        unmute_emb = discord.Embed(
            title="Unmute",
            description=f":unlock: {member.mention} has been unmuted | {reason}",
            color=discord.Color.purple()
        )
        unmute_emb.set_footer(text=str(self.client.user.name))
        unmute_emb.timestamp = discord.utils.utcnow()
        await ctx.send(embed=unmute_emb)

    @unmute_member.error
    async def unmute_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingPermissions):
            return await ctx.send("\U0000274C `You must have manage roles permission to unmute a member!")
        elif isinstance(error, commands.MemberNotFound):
            return await ctx.send("\U0000274C `Could not find the member you are trying to unmute!")
        elif isinstance(error, commands.MissingRequiredArgument) or isinstance(error, commands.BadArgument) or isinstance(error, commands.CheckFailure):
            return
        else:
            await self.client.dm_error_logs(err=error)


    @commands.hybrid_command(
        name="vckick", aliases=["kickvc", "voicekick", "kickvoice"],
        description="Remove a member from any voice channel!",
        usage="vckick <@mention or member id of one or more members>"
        )
    @commands.guild_only()
    @commands.has_guild_permissions(move_members=True)
    async def voice_kick(self, ctx: commands.Context, members: commands.Greedy[discord.Member]=None, *, reason: Optional[str]="<reason not provided>"):
        if members is None:
            return await ctx.send(":x: Please try again @mentioning at least one member you're trying to kick from voice!")
        success = []
        failed = []
        for member in members:
            if member.id == self.client.user.id:
                continue 
            if (member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id) or member.voice is None:
                failed.append(str(member))
                continue
            try: await member.move_to(channel=None, reason=reason)
            except discord.errors.Forbidden: failed.append(str(member))
            else: success.append(str(member))
        vc_kick_emb = discord.Embed(title="VoiceKick", description=str(), color=discord.Colour.random(), timestamp=discord.utils.utcnow())
        if success:
            vc_kick_emb.description += f":white_check_mark: **Kicked out from voice channel:**\n```{', '.join(success)}\n\nReason: {reason}```\n\n"
        if failed:
            vc_kick_emb.description += f":x: **Failed to kick:**\n```{', '.join(failed)}\n\n*Possible Reason: Lower role or missing permissions or the member is not connected to voice*```"
        vc_kick_emb.set_footer(text=self.client.user.name)
        return await ctx.send(embed=vc_kick_emb)

    @voice_kick.error
    async def vckick_err(self, ctx: commands.Context, err: discord.DiscordException):
        if isinstance(err, commands.MemberNotFound):
            return await ctx.send(":x: Member not found please try again @mentioning the member you're trying to kick from voice!")
        if isinstance(err, commands.MissingPermissions):
            return await ctx.send(":x: You must have 'Move members' Permission to use this command!")
        else:
            await self.client.dm_error_logs(err)


    @commands.hybrid_command(
        name='status',
        aliases=['stat', 'stats', 'members', 'statuses'],
        description="Command for getting how many members are online",
        usage="status"
        )
    @commands.guild_only()
    async def status_(self, ctx: commands.Context):
        online = 0
        offline = 0
        idle = 0
        dnd = 0
        others = 0
        for members in ctx.guild.members:
            if members.status == discord.Status.online:
                online += 1
            elif members.status == discord.Status.offline:
                offline += 1
            elif members.status == discord.Status.idle:
                idle += 1
            elif members.status == discord.Status.dnd or members.status == discord.Status.do_not_disturb:
                dnd += 1
            else:
                others += 1
        stat_embed = discord.Embed(
            title="Member Status",
            description=f"**Total: {len(ctx.guild.members)}**",
            colour=ctx.author.color
        )
        stat_embed.add_field(name="Online:", value=f"{online} members")
        stat_embed.add_field(name="Offline/Invisible:", value=f"{offline} members")
        stat_embed.add_field(name="Idle:", value=f"{idle} members")
        stat_embed.add_field(name="DND:", value=f"{dnd} members")
        if others: stat_embed.add_field(name="Others", value=f"{others} members")
        stat_embed.set_footer(text=f"{self.client.user.name}")
        stat_embed.timestamp = discord.utils.utcnow()
        if ctx.interaction:
            return await ctx.interaction.response.send_message(embed=stat_embed, ephemeral=True)
        return await ctx.send(embed=stat_embed)

    @commands.hybrid_command(
            name='clear',
            aliases=['cl', 'clr', 'cls', 'erase', 'cleartexts', 'clearmessages'],
            description="Clear given amount of messages",
            usage="clear <Number of messages to clear>"
            )
    @commands.guild_only()
    @commands.cooldown(rate=5, per=50, type=commands.cooldowns.BucketType.channel)
    @commands.has_permissions(manage_messages=True)
    async def clear_messages(self, ctx, amount: Optional[int]=0):
        if amount < 1:
            return await ctx.send("\U0000274C `Please specify a valid amount of messages to be cleared!")
        if amount > 50:
            return await ctx.send("\U0000274C `Currently I am allowed to clear Maximum 50 messages per command in a channel every 50 seconds!")
        final_amount = amount 
        try:
            if ctx.interaction:
                await ctx.interaction.response.send_message(content="Clearing message...")
                final_amount += 1
            await ctx.channel.purge(limit=final_amount+1)
        except (discord.errors.HTTPException, discord.errors.Forbidden):
            await ctx.send("\U0000274C `I don't have the manage messages permission! Can't Clear Messages.")
        else:
            return await ctx.channel.send(f":white_check_mark: Cleared out {amount} messages from this channel!", delete_after=5)

    @clear_messages.error
    async def clear_error(self, ctx, exception):
        if isinstance(exception, commands.MissingPermissions):
            await ctx.send("\U0000274C `You must have manage messages permission to clear messages! ")
        elif isinstance(exception, commands.CheckFailure) or isinstance(exception, commands.CommandOnCooldown):
            return
        else:
            await self.client.dm_error_logs(err=exception)

    @commands.hybrid_command(
        name="changenickname", 
        aliases=["setnick", "nickname", "changename", "changenick", "nick", "resetnick", "resetnickname"], 
        description="Change nickname of a member.",
        usage="setnick <@mention the member or member id> <new nickname>"
        )
    @commands.guild_only()
    @commands.has_permissions(change_nickname=True)
    async def change_member_nick(self, ctx: commands.Context, member: discord.Member=None, *, new_nickname: Optional[str]=None):
        if not ctx.interaction:
            with contextlib.suppress(discord.errors.NotFound):
                await ctx.message.delete()
        if member is None:
            return await ctx.send("\U0000274C `Please try again mentioning the member you are trying to set nickname!")
        if new_nickname is None or better_profanity.profanity.contains_profanity(new_nickname): 
            return await ctx.send("\U0000274C `Please provide a proper nickname of the member!")
        if new_nickname.lower() == "none":
            await member.edit(nick=None)
            if inter:=ctx.interaction:
                await inter.response.send_message(f":white_check_mark: Cleared the nickname of {member.name}", ephemeral=True)
            else:
                await ctx.channel.send(f":white_check_mark: Cleared the nickname of {member.name}")
        else:
            await member.edit(nick=new_nickname)
            if inter:=ctx.interaction:
                await inter.response.send_message(f":white_check_mark: Nickname of {member.name} has been changed to {member.display_name}", ephemeral=True)
            else:
                await ctx.send(f":white_check_mark: Nickname of {member.name} has been changed to {new_nickname}")

    @change_member_nick.error
    async def name_change_error(self, ctx, exception):
        if isinstance(exception, commands.MemberNotFound):
            return await ctx.send("\U0000274C `There is no member in our server with this name. Try mentioning the member with an '@'")
        elif isinstance(exception, commands.MissingPermissions):
            return await ctx.send("\U0000274C `You don't have enough permissions to change nicknames!")
        elif isinstance(exception, discord.errors.Forbidden):
            return await ctx.send(":warning: I don't have permission to change nickname for this member!")
        elif isinstance(exception, (commands.MissingRequiredArgument, commands.CheckFailure)):
            return
        else:
            await self.client.dm_error_logs(err=exception)

    @commands.hybrid_command(
            name="dm",
            aliases=["directmessage", "direct-message", "d-m", "message", "sendmessage"],
            description="Sends DM to the mentioned members!",
            usage="dm <member id of a single or multiple members> <The message to send in DM>"
            )
    @commands.guild_only()
    @commands.has_guild_permissions(manage_roles=True)
    async def direct_message(self, ctx: commands.Context, members: commands.Greedy[discord.Member], *, message: str):
        if not ctx.interaction:
            with contextlib.suppress(discord.errors.Forbidden):
                await ctx.message.delete()
        success = []
        failed_coz_its_a_bot = []
        turned_off_dms = []
        failed = []
        for member in members:
            if member.bot:
                failed_coz_its_a_bot.append(f"{member.name}#{member.discriminator}")
                continue
            try:
                await member.send(f"```\nMessage:\n\n{message}\n\nFrom: {ctx.author}\nServer: {ctx.guild.name}\n```")
                success.append(f"{member.name}#{member.discriminator}")
            except (discord.errors.HTTPException, discord.errors.Forbidden):
                turned_off_dms.append(f"{member.name}#{member.discriminator}")
            except Exception:  # type: ignore
                failed.append(f"{member.name}#{member.discriminator}")
        try:
            dm_emb = discord.Embed(title="Direct Message", color=ctx.author.color, timestamp=discord.utils.utcnow())
            if len(success) > 0: dm_emb.add_field(name="Successfully sent to:", value=",".join(success), inline=False)
            if len(turned_off_dms) > 0: dm_emb.add_field(name="Failed to send to the following because they've turned off DM:", value=",".join(turned_off_dms), inline=False)
            if len(failed_coz_its_a_bot) > 0: dm_emb.add_field(name="Falied to send to the following because they're bots:", value=",".join(failed_coz_its_a_bot), inline=False)
            if len(failed) > 0: dm_emb.add_field(name="Failed for unknown reason", value=", ".join(failed), inline=False)
            dm_emb.set_footer(text=str(self.client.user.name))
            if ctx.interaction:
                return await ctx.interaction.response.send_message(embed=dm_emb, ephemeral=True)
            await ctx.send(embed=dm_emb)
        except discord.DiscordException:
            await ctx.send(f"{':white_check_mark: Direct Message done!' if success else ':x: Could not DM any of the members you have mentioned!'}", delete_after=5)

    @direct_message.error
    async def dm_send_err(self, ctx: commands.Context, err):
        if isinstance(err, commands.MissingPermissions):
            return await ctx.send("\U0000274C `You must have manage roles permission to DM a server member through me!")
        elif isinstance(err, commands.MemberNotFound):
            return await ctx.send("\U0000274C `Member not found in this server! Try mentioning the member with an '@'")
        elif isinstance(err, commands.CheckFailure) or isinstance(err, commands.MissingRequiredArgument):
            return
        else:
            await self.client.dm_error_logs(err)


async def setup(client):
    print("Setting up Moderations....")
    await client.add_cog(Moderations(client))

async def teardown(client):
    print("Unloading Moderations....")
    await client.remove_cog(client.cogs['Moderations'])
