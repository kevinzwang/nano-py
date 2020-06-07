import discord
from discord.ext import commands
from discord.ext.commands.errors import CheckFailure
import yaml
import inspect

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.add_check(self.perms_check)
        self.embed_color = 0x8C63D0

        try:
            with open('settings.yml', 'r') as f:
                self.settings = yaml.load(f, Loader=yaml.Loader)
        except:
            self.settings = {}

    def _write_settings(self):
        try:
            with open('settings.yml', 'w') as f:
                yaml.dump(self.settings, f)
        except:
            print('Error writing to settings file.')

    async def perms_check(self, ctx):
        if await self.bot.is_owner(ctx.author): return True

        if 'blacklist' in self.settings and ctx.author.id in self.settings['blacklist']:
            blacklisted = self.settings['blacklist'][ctx.author.id]
            if '*' in blacklisted or ctx.command.name in blacklisted:
                raise CheckFailure('You are not allowed to use this command.')

        if 'disabled' in self.settings:
            if 'global' in self.settings['disabled'] and ctx.command.name in self.settings['disabled']['global']:
                raise CheckFailure('This command is disabled.')
            if ctx.guild:
                if ctx.guild.id in self.settings['disabled'] and ctx.command.name in self.settings['disabled'][ctx.guild.id]:
                    raise CheckFailure('This command is disabled in this server.')
            else:
                if ctx.command.name in self.settings['disabled']['dm']:
                    raise CheckFailure('This command is disabled in DMs.')

        return True

    @commands.command(aliases=['exit', 'shutdown', 'q'])
    @commands.is_owner()
    async def quit(self, ctx):
        await ctx.send('gn')
        await self.bot.close()

    @commands.command(aliases=['eval', 'exec'])
    @commands.is_owner()
    async def debug(self, ctx, *, args):
        result = eval(args)
        if inspect.isawaitable(result):
            result = await result

        await ctx.send(f'```{result}```')

    @commands.command()
    @commands.is_owner()
    async def disable(self, ctx, *args):
        guild_id = ctx.guild.id
        if len(args) > 0 and (args[0] == 'global' or args[0] == 'dm'):
            guild_id = args[0]
            args = args[1:]

        if 'disabled' not in self.settings:
            self.settings['disabled'] = {}

        if len(args) == 0:
            disabled_commands = self.settings['disabled'][guild_id] if guild_id in self.settings['disabled'] else []
            return await ctx.send(embed=discord.Embed(
                title='Disabled Commands',
                description=', '.join(disabled_commands),
                color=self.embed_color
            ))
        else:
            bot_commands = [c.name for c in self.bot.commands]
            if guild_id not in self.settings['disabled']:
                self.settings['disabled'][guild_id] = []
            
            success = True

            for command in args:
                if command in bot_commands:
                    if command in self.settings['disabled'][guild_id]:
                        success = False
                    else:
                        self.settings['disabled'][guild_id].append(command)
                else:
                    success = False 

            try:
                self._write_settings()
            except:
                success = False

            if success:
                return await ctx.send(f'Successfully disabled {len(args)} {"commands" if len(args) > 1 else "command"}.') 
            else:
                return await ctx.send(f'Something went wrong while disabling commands.') 

    @commands.command()
    @commands.is_owner()
    async def enable(self, ctx, *args):
        guild_id = ctx.guild.id

        if len(args) > 0 and (args[0] == 'global' or args[0] == 'dm'):
            guild_id = args[0]
            args = args[1:]

        if len(args) == 0:
            disabled_commands = self.settings['disabled'][guild_id] if guild_id in self.settings['disabled'] else []
            enabled_commands = [c.name for c in self.bot.commands if c.name not in disabled_commands]
            return await ctx.send(embed=discord.Embed(
                title='Enabled Commands',
                description=', '.join(enabled_commands),
                color=self.embed_color
            ))
        else:            
            success = True

            if 'disabled' in self.settings and guild_id in self.settings['disabled']:
                for command in args:
                    if command in self.settings['disabled'][guild_id]:
                        self.settings['disabled'][guild_id].remove(command)
                    else:
                        success = False 
            else:
                success = False

            try:
                self._write_settings()
            except:
                success = False

            if success:
                return await ctx.send(f'Successfully enabled {len(args)} {"commands" if len(args) > 1 else "command"}.')  
            else:
                return await ctx.send(f'Something went wrong while enabling commands.') 

    @commands.group(invoke_without_command=True)
    @commands.is_owner()
    async def blacklist(self, ctx):
        users = self.settings['blacklist'] if 'blacklist' in self.settings else {}
        await ctx.send(embed=discord.Embed(
            title='Blacklisted users',
            description='\n'.join([f'{self.bot.get_user(user_id).mention}: {", ".join(blacklisted)}' for user_id, blacklisted in users.items()]),
            color=self.embed_color
        ))

    @blacklist.command()
    async def add(self, ctx, user: discord.User, *args):
        bot_commands = [c.name for c in self.bot.commands]
        if 'blacklist' not in self.settings:
            self.settings['blacklist'] = {}
        if user.id not in self.settings['blacklist']:
            self.settings['blacklist'][user.id] = []

        success = True
        if len(args) == 0 or '*' in self.settings['blacklist'][user.id]:
            self.settings['blacklist'][user.id] = ['*']
        else:
            for command in args:
                if command in bot_commands:
                    if command not in self.settings['blacklist'][user.id]:
                        self.settings['blacklist'][user.id].append(command)
                else:
                    success = False

        try:
            self._write_settings()
        except:
            success = False

        if success:
            return await ctx.send('Successfully added to blacklist!')
        else:
            return await ctx.send('Something went wrong while adding to the blacklist.')

    @blacklist.command()
    async def remove(self, ctx, user: discord.User, *args):
        success = True
        if 'blacklist' in self.settings and user.id in self.settings['blacklist']:
            if len(args) == 0:
                del self.settings['blacklist'][user.id]
            else:
                if '*' in self.settings['blacklist'][user.id]:
                    success = False
                else:
                    for command in args:
                        if command in self.settings['blacklist'][user.id]:
                            self.settings['blacklist'][user.id].remove(command)
                        else:
                            success = False
        else:
            success = False

        try:
            self._write_settings()
        except:
            success = False
            
        if success:
            return await ctx.send('Successfully removed from blacklist!')
        else:
            return await ctx.send('Something went wrong while removing from the blacklist.')

def setup(bot):
    bot.add_cog(Admin(bot))