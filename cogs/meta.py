from discord.ext import commands
import time

class Meta(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def ping(self, ctx):
        start = time.time()
        msg = await ctx.send('Pong!')
        end = time.time()
        await msg.edit(content=f'Pong! Roundtrip time: {round((end-start)*1000*100)/100}ms')

def setup(bot):
    bot.add_cog(Meta(bot))