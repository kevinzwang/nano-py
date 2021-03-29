from discord.ext import commands
from discord_slash import SlashContext
from discord_slash.utils.manage_commands import create_option
import util

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @util.command(
        name='quit',
        description='[OWNER ONLY] Quits the bot')
    @util.is_owner
    async def quit(self, ctx: SlashContext):
        await ctx.send('gn')
        await self.bot.close()

    @util.subcommand(
        base='settings',
        name='enable',
        description='[ADMIN ONLY] Enable a command on this server',
        options=[
            create_option(
                name='command',
                description='Command to enable',
                option_type=3,
                required=True
            )
        ])
    @util.is_admin
    async def enable(self, ctx: SlashContext, command):
        util.enable(ctx.guild_id, command)
        await ctx.send(f'Successfully enabled command `{command}`')

    @util.subcommand(
        base='settings',
        name='disable',
        description='[ADMIN ONLY] Disable a command on this server',
        options=[
            create_option(
                name='command',
                description='Command to disable',
                option_type=3,
                required=True
            )
        ])
    @util.is_admin
    async def disable(self, ctx: SlashContext, command):
        util.disable(ctx.guild_id, command)
        await ctx.send(f'Successfully disabled command `{command}`')

def setup(bot):
    bot.add_cog(Admin(bot))