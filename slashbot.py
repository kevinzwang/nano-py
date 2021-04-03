import discord
from discord.ext import commands
from discord_slash import SlashCommand, SlashContext
import yaml
import aiohttp

extensions = (
    'slashcogs.admin',
    # 'slashcogs.animu',
    'slashcogs.meta',
    'slashcogs.random',
    'slashcogs.weeb',
    'slashcogs.berkeley',
)

def main():
    bot = commands.Bot(command_prefix='/', help_command=None)
    slash = SlashCommand(bot, sync_commands=True)

    try:
        with open('config.yml', 'r') as f:
            config = yaml.load(f, Loader=yaml.Loader)
            bot.token = config['token']
            bot.client_id = config['client_id']
    except:
        print('Something went wrong. Do you have your bot `token` and `client_id` in a `config.yml` file?')

    for ext in extensions:
        bot.load_extension(ext)

    @bot.command()
    async def help(ctx: commands.Context):
        await ctx.send("Nano uses slash commands!\nCheck out my available commands by typing `/`.")

    @bot.event
    async def on_ready():
        bot.command_prefix = (f'<@!{bot.user.id}> ', f'<@{bot.user.id}> ')
        await bot.change_presence(activity=discord.Game('/cat'))

        bot.http_session = aiohttp.ClientSession()
        print(f'{bot.user} is connected!')

    @bot.event
    async def close():
        await super(type(bot), bot).close()
        await bot.http_session.close()

    @bot.event
    async def on_slash_command_error(ctx: SlashContext, ex: Exception):
        app_info = await bot.application_info()
        await ctx.send(f'An exception occured when trying to run the command:\n```{str(ex)}```\nPlease contact the owner ({app_info.owner.mention}) if this problem persists.', hidden=True)

    bot.run(bot.token)

if __name__ == "__main__":
    main()