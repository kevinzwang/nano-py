from discord.ext import commands
from discord_slash import cog_ext, SlashContext
import aiohttp
import random
import copy
import util

class Random(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @cog_ext.cog_slash(
        name='cat',
        description='Picture of a random cat :3')
    @util.cooldown(3, 10)
    async def cat(self, ctx):
        async def randomcat():
            try:
                async with self.bot.http_session.get('http://aws.random.cat/meow') as response:
                        if response.status == 200:
                            json = await response.json()
                            return json['file']
            except:
                return None
        
        async def thecatapi():
            try:
                async with self.bot.http_session.get('https://api.thecatapi.com/v1/images/search') as response:
                        if response.status == 200:
                            json = await response.json()
                            return json[0]['url']
            except:
                return None

        if (random.choice([True, False])):
            cat1 = randomcat
            cat2 = thecatapi
        else:
            cat1 = thecatapi
            cat2 = randomcat
        
        if img1 := await cat1():
            await ctx.send(img1)
        elif img2 := await cat2():
            await ctx.send(img2)
        else:
            await ctx.send('We\'ve run out of cats! Please check back later :3')

def setup(bot):
    bot.add_cog(Random(bot))