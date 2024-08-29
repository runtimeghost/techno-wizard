# pylint: disable=exec-used,eval-used.wrong-import-order,broad-exception-caught

#This Extension is Only for owner :P
#For executing codes in realtime

import math
import threading
import asyncio
import typing
import functools
import logging
import time
import json
import discord
import lyricsgenius
import os
import contextlib
import io
import textwrap
import random
import sys
import psutil
import aiohttp
import googletrans
import wavelink
# Above are the Libraries
from Extensions import *

class ExecCmd(discord.ext.commands.Cog):

    def __init__(self, client):
        self.client = client
        self.local_vars = {
            "self": self,
            "discord": discord,
            "commands": discord.ext.commands,
            "math": math,
            "threading": threading,
            "asyncio": asyncio,
            "typing": typing,
            "functools": functools,
            "logging": logging,
            "time": time,
            "json": json,
            "lyricsgenius": lyricsgenius,
            "os": os,
            "contextlib": contextlib,
            "io": io,
            "textwrap": textwrap,
            "random": random,
            "sys": sys,
            "psutil": psutil,
            "aiohttp": aiohttp,
            "googletrans": googletrans,
            "wavelink": wavelink,
            "music": ext_music2,
            "mirrors": ext_mirrorlinks2,
            "games": ext_game,
            "extras": ext_extras,
            "moderations": ext_moderations,
            "settings": ext_settings,
            'helps': ext_help
        }


    @discord.ext.commands.command(name='ownerhelp', aliases=['ownershelp'], hidden=True)
    @discord.ext.commands.guild_only()
    @discord.ext.commands.is_owner()
    async def owner_help(self, ctx):
        emb = discord.Embed(
            title="Owner's Commands",
            description="__1__| x:eval\n__2__| x:exec\n__3__| m:eval\n__4__|\
     eval\n__5__| exec\n__6__| fileemoji\n__7__| urlemoji\n__8__| serverlist\n__9__| dcu\
    \n__10__| reload\n__11__| wakeup\n__12__| shutdown",
    color=discord.Colour.purple(),
    timestamp=discord.utils.utcnow()
    )
        emb.set_footer(text=self.client.user.name)
        await ctx.send(embed=emb, delete_after=30)


    @discord.ext.commands.command(name="fileemoji", hidden=True)
    @discord.ext.commands.guild_only()
    @discord.ext.commands.is_owner()
    async def emoji_from_file(self, ctx, filename, name):
        if filename in os.listdir("./"):
            with open(filename, "rb") as x:
                y = x.read()
        else:
            return await ctx.send(f"FileNotFoundError: No file/folder named '{filename}'")
        em = await ctx.guild.create_custom_emoji(image=y, name=str(name))
        return await ctx.send(f"{em.id}: {em}")


    @discord.ext.commands.command(name="urlemoji", hidden=True)
    @discord.ext.commands.guild_only()
    @discord.ext.commands.is_owner()
    async def get_moji(self, ctx: discord.ext.commands.Context, url: str="", *, name):
        if not url:
            return await ctx.send(":x: Url undefined!")
        async with self.client.client_session.get(url) as b:
            x = io.BytesIO(await b.read())
        byts = x.getvalue()
        em = await ctx.guild.create_custom_emoji(image=byts, name=str(name))
        return await ctx.send(f"{em.id}: {em}")

    @discord.ext.commands.command(name="exec", aliases=["execute", "exc", "ex"], hidden=True)
    @discord.ext.commands.guild_only()
    @discord.ext.commands.is_owner()
    async def exec_code(self, ctx: discord.ext.commands.Context, *, cmd: str):
        if "input(" in cmd.lower() or "input (" in cmd.lower():
            return await ctx.send(":x: Cannot Execute input method!")
        if cmd.startswith("```") and cmd.endswith("```"):
            cmd = "\n".join(cmd.splitlines()[1:])
        if cmd.endswith("`"):
            cmd = cmd.rstrip("`")
        no_err = True
        self.local_vars["ctx"] = ctx
        output = io.StringIO()
        code=f'''async def virtual_code():\n{textwrap.indent(cmd, "    ")}'''
        result: str=""
        print(code)
        try:
            with contextlib.redirect_stdout(output):
                exec(code, self.local_vars)
                return_value = await self.local_vars["virtual_code"]()
                result = f"\n**\U00002705Output:**\n{str(output.getvalue())}\n\n```\nReturned: {str(return_value)}\n```"
        except Exception as e:
            result = f"**\U0000274CFalied to execute!**\n{e.__class__.__name__}: {e}"
            no_err = False
        finally:
            try:
                exec_emb = discord.Embed(
                    title="Code Execution",
                    description=f"{result}",
                    color=discord.Color.green() if no_err else discord.Color.dark_red(),
                    timestamp = discord.utils.utcnow()
                    )
                exec_emb.set_footer(text=str(self.client.user.name))
                await ctx.send(embed=exec_emb)
            except discord.errors.HTTPException:
                exec_emb = discord.Embed(title="Code Execution", description=f"{str(result)[-1998:]}", color=discord.Color.green() if no_err else discord.Color.dark_red())
                exec_emb.set_footer(text=str(self.client.user.name))
                exec_emb.timestamp = discord.utils.utcnow()
                await ctx.send(embed=exec_emb)

    @discord.ext.commands.command(name='eval', aliases=['evaluate', "ev"], hidden=True)
    @discord.ext.commands.guild_only()
    @discord.ext.commands.is_owner()
    async def eval(self, ctx: discord.ext.commands.Context, *, cmd: str):
        if "input(" in cmd.lower() or "input (" in cmd.lower():
            return await ctx.send(":x: Cannot Execute input method!")
        cmd = cmd.strip('`')
        try:
            res = eval(cmd)
        except Exception as e:
            return await ctx.send("\U0000274C Eval job failed!\n{0.__class__.__name__}: {0}".format(e))
        else:
            try:
                ev_emb = discord.Embed(description=f'{res or "<no_output>"}', color=discord.Color.dark_purple())
                return await ctx.send(embed=ev_emb)
            except discord.errors.HTTPException:
                ev_emb = discord.Embed(description=f'{str(res)[-1998:]}', color=discord.Color.dark_purple())
                return await ctx.send(embed=ev_emb)

    @discord.ext.commands.command(aliases=['notes', 'addnote'], hidden=True)
    @discord.ext.commands.is_owner()
    async def note(self, ctx: discord.ext.commands.Context, *, text: str=""):
        if not text:
            return await ctx.send(":x: Cannot create empty note!")
        with contextlib.suppress(
            discord.errors.HTTPException,
            discord.errors.NotFound,
            discord.errors.Forbidden
            ):
            await ctx.message.delete()

        channel = self.client.note_channel
        emb = discord.Embed(
            title="Note",
            description=text,
            colour=discord.Colour.random(),
            timestamp=discord.utils.utcnow()
        )
        emb.set_footer(text=self.client.user.name)
        await channel.send(embed=emb)
        await ctx.channel.send(":white_check_mark: Note added!", delete_after=2)


async def setup(client):
    print("Setting up Execution....")
    await client.add_cog(ExecCmd(client))

async def teardown(client):
    print("Unloading Execution....")
    await client.remove_cog(client.cogs['ExecCmd'])
