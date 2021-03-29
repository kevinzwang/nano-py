from discord.ext import commands
from discord_slash import cog_ext, SlashContext
import aiohttp
import random
import copy
import util

class Random(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _choice(self, func1, func2):
        if random.choice([True, False]):
            func1, func2 = func2, func1

        try:
            try:
                return await func1()
            except:
                return await func2()
        except:
            return None

    async def _randomcat(self):
        async with self.bot.http_session.get('http://aws.random.cat/meow') as response:
            if response.status == 200:
                json = await response.json()
                return json['file']

    async def _thecatapi(self):
        async with self.bot.http_session.get('https://api.thecatapi.com/v1/images/search') as response:
            if response.status == 200:
                json = await response.json()
                return json[0]['url']
    
    async def _nekoslife(self):
        async with self.bot.http_session.get('https://nekos.life/api/v2/img/neko') as response:
            if response.status == 200:
                json = await response.json()
                return json['url']

    async def _nekosmoe(self):
        async with self.bot.http_session.get('https://nekos.moe/api/v1/random/image?nsfw=false') as response:
            if response.status == 200:
                json = await response.json()
                return 'https://nekos.moe/image/' + json['images'][0]['id']


    @util.command(
        name='cat',
        description='Picture of a random cat :3')
    @util.cooldown(3, 10)
    async def cat(self, ctx):
        if img := await self._choice(self._randomcat, self._thecatapi):
            await ctx.send(img)
        else:
            await ctx.send('We\'ve run out of cats! Please check back later :3')

    @util.command(
        name='neko',
        description='Pictuwe of a wandom anime catgiwl uwu')
    @util.cooldown(3, 10)
    async def neko(self, ctx):
        if img := await self._choice(self._nekoslife, self._nekosmoe):
            await ctx.send(img)
        else:
            await ctx.send('Something went wwong, we\'we wewwy sowwy! Pwease check back latew uwu')

    @util.command(
        name='maybecat',
        description='Flips a coin. Heads is cat, tails is catgirl. :3')
    @util.cooldown(3, 10)
    async def maybecat(self, ctx):
        async def cat():
            return await self._choice(self._randomcat, self._thecatapi)

        async def neko():
            return await self._choice(self._nekoslife, self._nekosmoe)

        if img := await self._choice(cat, neko):
            await ctx.send(img)
        else:
            await ctx.send('The cat coin landed on its edge! Something fishy is going on...')

def setup(bot):
    bot.add_cog(Random(bot))