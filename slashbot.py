from discord.ext import commands
from discord_slash import SlashCommand
import yaml
import aiohttp

extensions = (
    # 'slashcogs.animu',
    'slashcogs.meta',
    'slashcogs.random',
    'slashcogs.weeb',
    'slashcogs.berkeley',
)

def main():
    bot = commands.Bot(command_prefix=None)
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

    @bot.event
    async def on_ready():
        bot.command_prefix = (f'<@!{bot.user.id}> ', f'<@{bot.user.id}> ')
        bot.http_session = aiohttp.ClientSession()
        print(f'{bot.user} is connected!')

    @bot.event
    async def close():
        await bot.http_session.close()

    bot.run(bot.token)

if __name__ == "__main__":
    main()