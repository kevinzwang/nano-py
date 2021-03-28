import time
import functools
from discord_slash import SlashContext

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