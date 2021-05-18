from discord.ext import commands
from discord_slash import cog_ext, SlashContext
import aiohttp
import random
import copy
import util

class Random(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _choose(self, *choices):
        if len(choices) > 0:
            func = random.choice(choices)
            try:
                return await func()
            except:
                return self._choose([c for c in choices if c != func])
        else:
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
    
    async def _nekolove(self):
        async with self.bot.http_session.get('https://neko-love.xyz/api/v1/neko') as response:
            if response.status == 200:
                json = await response.json()
                return json['url']


    @util.command(
        name='cat',
        description='Picture of a random cat :3')
    @util.cooldown(3, 10)
    async def cat(self, ctx):
        if img := await self._choose(self._randomcat, self._thecatapi):
            await ctx.send(img)
        else:
            await ctx.send('We\'ve run out of cats! Please check back later :3')

    @util.command(
        name='neko',
        description='Pictuwe of a wandom anime catgiwl uwu')
    @util.cooldown(3, 10)
    async def neko(self, ctx):
        if img := await self._choose(self._nekoslife, self._nekosmoe, self._nekolove):
            await ctx.send(img)
        else:
            await ctx.send('Something went wwong, we\'we wewwy sowwy! Pwease check back latew uwu')

    @util.command(
        name='maybecat',
        description='Flips a coin. Heads is cat, tails is catgirl. :3')
    @util.cooldown(3, 10)
    async def maybecat(self, ctx):
        async def cat():
            return await self._choose(self._randomcat, self._thecatapi)

        async def neko():
            return await self._choose(self._nekoslife, self._nekosmoe, self._nekolove)

        if img := await self._choose(cat, neko):
            await ctx.send(img)
        else:
            await ctx.send('The cat coin landed on its edge! Something fishy is going on...')

def setup(bot):
    bot.add_cog(Random(bot))