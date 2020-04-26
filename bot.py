import aiohttp
import discord
import re
import yaml
from discord.ext import commands

extensions = (
    'cogs.admin',
    'cogs.animu',
    'cogs.meta',
    'cogs.random',
    'cogs.weeb',
)

class Nano(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=None)

        try:
            with open('config.yml', 'r') as f:
                config = yaml.load(f, Loader=yaml.BaseLoader)
                self.token = config['token']
                self.command_suffix = config['suffix']
        except:
            print('Something went wrong. Do you have your bot `token` and `suffix` in a `config.yml` file?')

        for ext in extensions:
            self.load_extension(ext)

    async def on_ready(self):
        self.command_prefix = (f'<@!{self.user.id}> ', f'<@{self.user.id}> ')
        await self.change_presence(activity=discord.Game('type `help!`'))

        self.http_session = aiohttp.ClientSession()

        print('Nano is connected!')

    async def close(self):
        await super().close()
        await self.http_session.close()

    async def on_message(self, msg):
        if msg.author.bot:
            return
        
        ## check of there's a suffix, and if so, format the message to a prefix (its jank ik)
        if not msg.content.startswith(self.command_prefix):
            space_index = msg.content.find(' ')
            suffix_index = msg.content.find(self.command_suffix)

            if suffix_index != -1 and suffix_index != 0 and (space_index == -1 or suffix_index < space_index):
                msg.content = self.command_prefix[0] + msg.content[:suffix_index] + msg.content[suffix_index+len(self.command_suffix):]
            else:
                anime_match = re.search(r"\(\((.+)\)\)(?=(?:(?:\\.|[^`\\])*`(?:\\.|[^`\\])*`)*(?:\\.|[^`\\])*\Z)", msg.content)
                manga_match = re.search(r"<<(.+)>>(?=(?:(?:\\.|[^`\\])*`(?:\\.|[^`\\])*`)*(?:\\.|[^`\\])*\Z)", msg.content)

                if anime_match:
                    msg.content = f'{self.command_prefix[0]}quickanime {anime_match.groups()[0]}'
                elif manga_match:
                    msg.content = f'{self.command_prefix[0]}quickmanga {manga_match.groups()[0]}'

        await self.process_commands(msg)

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.BotMissingPermissions):
            await ctx.author.send(error)
        elif not isinstance(error, commands.CommandNotFound):
            await ctx.send(error)

    def run(self):
        if hasattr(self, 'token'):
            super().run(self.token)
        else:
            print('No token loaded. Exiting.')

bot = Nano()

bot.run()