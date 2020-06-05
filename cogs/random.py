from discord.ext import commands
import aiohttp
import random

class Random(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(help='Picture of a random cat :3')
    @commands.cooldown(3, 10, commands.BucketType.user)
    async def cat(self, ctx):
        async def randomcat():
            async with self.bot.http_session.get('http://aws.random.cat/meow') as response:
                    if response.status == 200:
                        json = await response.json()
                        return json['file']
        
        async def thecatapi():
            async with self.bot.http_session.get('http://thecatapi.com/api/images/get') as response:
                    if response.status == 200:
                        return response.url

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

    @commands.command(aliases=['catgirl'], help='Pictuwe of a wandom anime catgiwl uwu', enabled=False)
    @commands.cooldown(3, 10, commands.BucketType.user)
    async def neko(self, ctx):
        async def nekoslife():
            async with self.bot.http_session.get('https://nekos.life/api/v2/img/neko') as response:
                    if response.status == 200:
                        json = await response.json()
                        return json['url']
        
        async def nekosmoe():
            async with self.bot.http_session.get('https://nekos.moe/api/v1/random/image?nsfw=false') as response:
                    if response.status == 200:
                        json = await response.json()
                        return 'https://nekos.moe/image/' + json['images'][0]['id']

        if (random.choice([True, False])):
            neko1 = nekoslife
            neko2 = nekosmoe
        else:
            neko1 = nekosmoe
            neko2 = nekoslife
        
        if img1 := await neko1():
            await ctx.send(img1)
        elif img2 := await neko2():
            await ctx.send(img2)
        else:
            await ctx.send('Something went wwong, we\'we wewwy sowwy! Pwease check back latew uwu')
    
def setup(bot):
    bot.add_cog(Random(bot))