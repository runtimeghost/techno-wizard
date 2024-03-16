

import discord
from asyncio import TimeoutError
from random import randrange
from discord.ext import commands
from bot_ui import RPSChoice


class Game(commands.Cog):
    def __init__(self, client):
        self.client = client


    @commands.hybrid_command(
        name="random-number-guessing-game",
        aliases=["randomnumberguessinggame", "random", "rngg"],
        usage="rngg"
        )
    @commands.guild_only()
    async def rng_game(self, ctx: commands.Context):
        """Let's see if your random guess matches with mine ;)"""
        num = randrange(1, 21)
        chances_are_left = 0
        await ctx.send("Guess any number between 1 and 20 within 3 chances!")
        chances_are_left = 3
        author_could_not_say_the_correct_number = True
        time_is_not_up = True
        while chances_are_left:
            try:
                guess = await self.client.wait_for(
                    'message',
                    check=lambda txt: txt.author.id==ctx.author.id,
                    timeout=20
                    )
            except TimeoutError:
                await ctx.send(f"Time's up! The number is {num}")
                time_is_not_up = False
                break
            else:
                try:
                    user_choice = float(guess.content)
                except ValueError:
                    await ctx.send("\U0000274CPlease choose a number, not a word.")
                    chances_are_left+=1
                else:
                    if user_choice == float(num):
                        await ctx.send(
                            f":partying_face: Whoa! {ctx.author.name}, \
You are absolutely Correct! The number is {num}")
                        author_could_not_say_the_correct_number = False
                        break
                    elif user_choice > float(num):
                        if chances_are_left > 1:
                            await ctx.send(f"\U0000274COops! Try lower values!")
                    elif user_choice < float(num):
                        if chances_are_left > 1:
                            await ctx.send(f"\U0000274COops! Try higher values!")
            finally:
                chances_are_left -= 1
        if author_could_not_say_the_correct_number and time_is_not_up:
            return await ctx.send(f"\U0000274CChances are over! The number is {num}")


    @commands.hybrid_command(
        name="rock-paper-scissor",
        aliases=["rps"],
        usage="rps")
    @commands.guild_only()
    async def rock_paper_scissor(self, ctx=commands.Context):
        """Let's play Rock paper scissor"""
        embd = discord.Embed(
				title="Rock Paper Scissor",
				description="**Choose any one from below: **",
				colour=discord.Color.random(),
				timestamp=discord.utils.utcnow()
        	)
        embd.set_footer(text=self.client.user.name)
        return await ctx.send(embed=embd, view=RPSChoice(embed=embd, timeout=30))

async def setup(client):
    print("Setting up Game....")
    await client.add_cog(Game(client))

async def teardown(client):
    print("Unloading Game....")
    await client.remove_cog(client.cogs['Game'])
