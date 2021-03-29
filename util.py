import time
import functools
import discord
from discord_slash import cog_ext, SlashContext
import yaml

try:
    with open('config.yml', 'r') as f:
        config = yaml.load(f, Loader=yaml.Loader)
        guild_ids = config.get('guild_ids')
except:
    pass

try:
    with open('settings.yml', 'r') as f:
        settings = yaml.load(f, Loader=yaml.Loader)
except:
    settings = {}

def _write_settings():
    with open('settings.yml', 'w') as f:
        yaml.dump(settings, f)

def enable(guild: int, command: str):
    global settings
    if 'disabled' in settings and guild in settings['disabled'] and command in settings['disabled'][guild]:
        settings['disabled'][guild].remove(command)
        _write_settings()

def disable(guild: int, command: str):
    global settings    
    if 'disabled' not in settings:
        settings['disabled'] = {}

    if guild not in settings['disabled']:
        settings['disabled'][guild] = []

    if command not in settings['disabled'][guild]:
        settings['disabled'][guild].append(command)
        _write_settings()

def cooldown(rate: int, per: float):
    def decorator(func):
        users = {}

        @functools.wraps(func)
        async def wrapper(ref, ctx: SlashContext, *args, **kwargs):            
            nonlocal users

            now = time.time()

            if ctx.author_id not in users:
                users[ctx.author_id] = []

            users[ctx.author_id] = list(filter(lambda x: x > now, users[ctx.author_id]))

            if len(users[ctx.author_id]) == rate:
                try_again = round(users[ctx.author_id][0] - now, 2)
                return await ctx.send(f'You are on cooldown. Try again in {try_again}s', hidden=True)
            else:
                users[ctx.author_id].append(now + per)
                return await func(ref, ctx, *args, **kwargs)

        return wrapper
    return decorator

def command(**kwargs):
    def decorator(func):
        @cog_ext.cog_slash(guild_ids=guild_ids, **kwargs)
        @functools.wraps(func)
        async def wrapper(ref, ctx: SlashContext, *args, **kwargs):
            if 'disabled' in settings and ctx.guild_id in settings['disabled'] and ctx.name in settings['disabled'][ctx.guild_id]:
                return await ctx.send(f'This command is disabled on this server.', hidden=True)
            else:
                return await func(ref, ctx, *args, **kwargs)

        return wrapper
    return decorator

def subcommand(**kwargs):
    def decorator(func):
        @cog_ext.cog_subcommand(guild_ids=guild_ids, **kwargs)
        @functools.wraps(func)
        async def wrapper(ref, ctx: SlashContext, *args, **kwargs):
            if 'disabled' in settings and ctx.guild_id in settings['disabled'] and ctx.name in settings['disabled'][ctx.guild_id]:
                return await ctx.send(f'This command is disabled on this server.', hidden=True)
            else:
                return await func(ref, ctx, *args, **kwargs)

        return wrapper
    return decorator


def is_owner(func):
    @functools.wraps(func)
    async def wrapper(ref, ctx: SlashContext, *args, **kwargs):
        if await ref.bot.is_owner(ctx.author):
            return await func(ref, ctx, *args, **kwargs)
        else:
            return await ctx.send('You cannot use this command because you are not the owner of this bot.', hidden=True)

    return wrapper

def is_admin(func):
    @functools.wraps(func)
    async def wrapper(ref, ctx: SlashContext, *args, **kwargs):
        if ctx.guild and ctx.author.guild_permissions.administrator:
            return await func(ref, ctx, *args, **kwargs)
        else:
            return await ctx.send('You cannot use this command because you are not an admin of this server.', hidden=True)

    return wrapper