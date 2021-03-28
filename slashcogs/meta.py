import discord
from discord.ext import commands
from discord_slash import cog_ext, SlashContext
import time

class Meta(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @cog_ext.cog_slash()
    async def ping(self, ctx: SlashContext):
        start = time.time()
        msg = await ctx.send('Pong!')
        end = time.time()
        await msg.edit(content=f'Pong! Roundtrip time: {round((end-start)*1000*100)/100}ms')

    @cog_ext.cog_slash()
    async def about(self, ctx):
        app_info = await self.bot.application_info()

        await ctx.send(embed=discord.Embed(
            title='Nano',
            description='Cats, anime, music, Berkeley courses, and more.\nWritten in Python with love <3',
            color=0x8C63D0
        ).add_field(
            name='Owner',
            value=app_info.owner.mention,
            inline=True
        ).add_field(
            name='Server Count',
            value=len(self.bot.guilds),
            inline=True
        ).add_field(
            name='Invite',
            value=f'[Click Here]({discord.utils.oauth_url(self.bot.client_id)})',
            inline=True
        ).add_field(
            name='Source',
            value='https://github.com/kevinzwang/nano-py',
            inline=True
        ).set_thumbnail(url=self.bot.user.avatar_url))

def setup(bot):
    bot.add_cog(Meta(bot))