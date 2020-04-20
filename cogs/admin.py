from discord.ext import commands

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['exit', 'shutdown'])
    @commands.is_owner()
    async def quit(self, ctx):
        await ctx.send('gn')
        await self.bot.logout()

def setup(bot):
    bot.add_cog(Admin(bot))