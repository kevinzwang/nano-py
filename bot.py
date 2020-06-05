import aiohttp
import discord
import re
import yaml
from discord.ext import commands
from discord.ext.commands.view import StringView

extensions = (
    'cogs.admin',
    'cogs.animu',
    'cogs.meta',
    'cogs.random',
    'cogs.weeb',
    'cogs.berkeley',
)


class SuffixContext(commands.Context):
    def __init__(self, **attrs):
        super().__init__(**attrs)
        self.suffix = attrs.pop('suffix')

    @property
    def valid(self):
        return (self.suffix is not None or self.prefix is not None) and self.command is not None

    async def reinvoke(self, *, call_hooks=False, restart=True):
        if self.suffix is not None:
            # since the command was invoked with a suffix,
            # we need to make sure the view doesn't try to skip a nonexistent prefix
            original_prefix = self.prefix
            self.prefix = ''

        await super().reinvoke(call_hooks=call_hooks, restart=restart)

        try:
            self.prefix = original_prefix
        except NameError:
            pass


class Nano(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=None, case_insensitive=True)

        try:
            with open('config.yml', 'r') as f:
                config = yaml.load(f, Loader=yaml.BaseLoader)
                self.token = config['token']
                self.command_suffix = config['suffix']
                self.client_id = config['client_id']
        except:
            print('Something went wrong. Do you have your bot `token`, `suffix`, and `client_id` in a `config.yml` file?')

        for ext in extensions:
            self.load_extension(ext)

    async def on_ready(self):
        self.command_prefix = (f'<@!{self.user.id}> ', f'<@{self.user.id}> ')
        await self.change_presence(activity=discord.Game('type "help!"'))

        self.http_session = aiohttp.ClientSession()

        print(f'{self.user} is connected!')

    async def close(self):
        await super().close()
        await self.http_session.close()

    async def on_message(self, msg):
        if msg.author.bot:
            return
        
        if not msg.content.startswith(self.command_prefix):
            anime_match = re.search(r"\(\((.+)\)\)(?=(?:(?:\\.|[^`\\])*`(?:\\.|[^`\\])*`)*(?:\\.|[^`\\])*\Z)", msg.content)
            manga_match = re.search(r"<<(.+)>>(?=(?:(?:\\.|[^`\\])*`(?:\\.|[^`\\])*`)*(?:\\.|[^`\\])*\Z)", msg.content)

            if anime_match:
                msg.content = f'{self.command_prefix[0]}quickanime {anime_match.groups()[0]}'
            elif manga_match:
                msg.content = f'{self.command_prefix[0]}quickmanga {manga_match.groups()[0]}'

        await self.process_commands(msg)

    def _parse_suffix(self, message):
        """Returns the command suffix used in a message, if any"""
        space_index = message.content.find(' ')
        suffix_index = message.content.find(self.command_suffix)
        if suffix_index > 0 and (space_index == -1 or suffix_index < space_index):
            return self.command_suffix

    async def get_context(self, message, *, cls=SuffixContext):
        view = StringView(message.content)
        ctx = cls(prefix=None, suffix=None, view=view, bot=self, message=message)

        if self._skip_check(message.author.id, self.user.id):
            return ctx

        prefix = await self.get_prefix(message)
        invoked_prefix = prefix

        if isinstance(prefix, str):
            if not view.skip_string(prefix):
                invoked_suffix = self._parse_suffix(message)
        else:
            try:
                if message.content.startswith(tuple(prefix)):
                    invoked_prefix = discord.utils.find(view.skip_string, prefix)
                else:
                    if (invoked_suffix := self._parse_suffix(message)) is None:
                        return ctx

            except TypeError:
                if not isinstance(prefix, list):
                    raise TypeError("get_prefix must return either a string or a list of string, "
                                    "not {}".format(prefix.__class__.__name__))

                for value in prefix:
                    if not isinstance(value, str):
                        raise TypeError("Iterable command_prefix or list returned from get_prefix must "
                                        "contain only strings, not {}".format(value.__class__.__name__))

                raise

        invoker = view.get_word()

        try:
            ctx.suffix = invoked_suffix
        except NameError:
            ctx.prefix = invoked_prefix
        else:
            invoker = invoker[:-len(invoked_suffix)]
            # I would have liked to only assign context.prefix if a prefix was actually used,
            # but the default help command uses context.prefix for some reason
            # so we are going to always assign context.prefix in order to preserve the default help command
            ctx.prefix = invoked_prefix if isinstance(invoked_prefix, str) else self.user.mention + ' '

        ctx.invoked_with = invoker
        ctx.command = self.all_commands.get(invoker)
        return ctx

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