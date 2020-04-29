import asyncio
import discord
import html2text
import math
import random
import re
import wavelink
import yaml
from bs4 import BeautifulSoup
from discord.ext import commands
from typing import Set, Dict

class GameSettings:
    def __init__(self):
        self.anime_lists: Set[str] = {'top200'}
        self.past_queue = asyncio.Queue()
        self.past_set: Set[str] = set()
        self.repeat_limit = 100

class GameState:
    def __init__(self, channel: discord.VoiceChannel, loop: asyncio.Task):
        self.channel = channel
        self.loop = loop

class AniMu(commands.Cog, name='AniMu (Anime Music)'):
    def __init__(self, bot):
        self.bot = bot
        self.settings: Dict[int, GameSettings] = {} # key is guild id
        self.games: Dict[int, GameState] = {} # key is guild id

        try:
            with open('application.yml', 'r') as f:
                self.config = yaml.load(f, Loader=yaml.BaseLoader)
                self.wavelink = wavelink.Client(self.bot)

                self.bot.loop.create_task(self.start_nodes())
        except OSError:
            print('Failed to load application.yml. Music commands are disabled.')
        except yaml.YAMLError:
            print('There\'s something wrong with your application.yml file. Music commands are disabled')

    async def start_nodes(self):
        """Starts the connection to the Lavalink server"""
        await self.bot.wait_until_ready()

        await self.wavelink.initiate_node(
            host=self.config['server']['address'],
            port=self.config['server']['port'],
            rest_uri=f'http://{self.config["server"]["address"]}:{self.config["server"]["port"]}',
            password=self.config['lavalink']['server']['password'],
            identifier=f'{self.bot.user.name}#{self.bot.user.discriminator}',
            region='us_central'
        )

    def cog_unload(self):
        """Disconnects all the music on unload"""
        if hasattr(self, 'wavelink'):
            self.bot.loop.create_task(self.wavelink.session.close())

    def cog_check(self, ctx):
        """Makes sure that the Lavalink connection is established for running music commands"""
        return hasattr(self, 'wavelink')

    async def _game_loop(self, voice_channel: discord.VoiceChannel, text_channel: discord.TextChannel, settings: GameSettings):
        """The main game loop, runs a game."""
        next_up = self.bot.loop.create_task(self._get_next_up(settings))
        round_number = 1
        scores: Dict[discord.Member, int] = {}

        player = self.wavelink.get_player(text_channel.guild.id)
        await player.connect(voice_channel.id)

        await text_channel.send(embed=rules)
        await text_channel.send(embed=discord.Embed(
            title='AniMu',
            description=f'Game starting in 5 seconds...',
            color=colors['info']
        ))
        
        on_message = None

        format_scores = lambda: '\n'.join([f'{player.mention}: {score}' for player, score in sorted(scores.items(), key=lambda item: item[1], reverse=True)]) if scores else 'None'

        try:
            while True:
                await asyncio.sleep(5)
                
                anime, theme, track = await next_up

                future = self.bot.loop.create_future()
                async def on_message(msg):
                    if msg.channel == text_channel and msg.content.endswith('??') and msg.author.voice and msg.author.voice.channel.id == voice_channel.id:
                        if msg.author not in scores:
                                scores[msg.author] = 0

                        if await self._find_anime(msg.content[:-2], anime['idMal']):
                            await msg.add_reaction('✅')
                            scores[msg.author] += 10
                            future.set_result(msg.author)
                        else:
                            scores[msg.author] -= 5
                            await msg.add_reaction('❌')
                self.bot.add_listener(on_message)

                await player.play(track)
                
                next_up = self.bot.loop.create_task(self._get_next_up(settings))

                embed = discord.Embed(
                    title=f'AniMu - Round {round_number} results',
                    description=f'The song was [**{theme["name"]}**]({track.uri}) from __{anime["title"]["romaji"]}__',
                ).set_thumbnail(
                    url=anime['coverImage']['extraLarge']
                )

                try:
                    winner = await asyncio.wait_for(future, timeout=45)
                    embed.color = colors['success']
                    embed.set_author(
                        name=(winner.nick if winner.nick else winner.name) + ' got the right answer!', 
                        icon_url=winner.avatar_url
                    )
                except asyncio.TimeoutError:
                    embed.color = colors['failure']
                    embed.set_author(
                        name='Nobody got this round :(', 
                    )
                
                self.bot.remove_listener(on_message)

                embed.add_field(
                    name='Scores',
                    value=format_scores()
                )
                await text_channel.send(embed=embed)

                round_number += 1

        except asyncio.CancelledError:
            await text_channel.send(
                embed=discord.Embed(
                    title=f'AniMu - Ending game',
                    color=colors['info']
                ).add_field(
                    name='Final Scores',
                    value=format_scores()
                )
            )
        except Exception as e:
            await text_channel.send(e)
            await text_channel.send('```{' + ', '.join(anime['title']['romaji'], anime['idMal'], theme['name'], theme['url']) + '}```')
        finally:
            await player.disconnect()
            if on_message:
                self.bot.remove_listener(on_message)

    async def _get_next_up(self, settings: GameSettings):
        """Returns data for an anime, a theme, and a wavelink track"""
        try:
            chosen_list = random.sample(settings.anime_lists, 1)[0]
            if chosen_list == 'top200':
                async with self.bot.http_session.post(api_url, json={
                    'query': queries['from_top'],
                    'variables': {
                        'page': random.randint(1, 200)
                    }
                }) as response:
                    json = await response.json()
                
                chosen_anime = json['data']['Page']['media'][0]
            else:
                async with self.bot.http_session.post(api_url, json={
                    'query': queries['from_list'],
                    'variables': {
                        'name': chosen_list
                    }
                }) as response:
                    json = await response.json()
                
                all_anime = [a['media'] for l in json['data']['MediaListCollection']['lists'] for a in l['entries']]
                chosen_anime = random.choice(all_anime)

            if chosen_anime['seasonYear'] < 2000:
                year = f'{str(chosen_anime["seasonYear"])[2]}0s'
            else:
                year = chosen_anime['seasonYear']

            async with self.bot.http_session.get(f'https://www.reddit.com/r/AnimeThemes/wiki/{year}.json') as response:
                json = await response.json()
            
            # this is where we do our html parsing of r/AnimeThemes wiki
            soup = BeautifulSoup(html2text.html2text(json['data']['content_html']), features='html.parser')
            anime_link = soup.find(href=f'https://myanimelist.net/anime/{chosen_anime["idMal"]}/')
            if anime_link:
                rows = anime_link.parent.find_next_sibling('table').find('tbody').find_all('tr')
                themes = []
                for r in rows:
                    children = r.find_all('td')
                    name = children[0].string
                    link = children[1].find('a', href=True)

                    if name and link:
                        themes.append({'name': name.strip().replace('\n', ' '), 'url': "".join(link['href'].split())})
                    elif name:
                        themes.append({'name': name.strip().replace('\n', ' ')})

                if themes:
                    chosen_theme = random.choice(themes)
                    
                    ## now it's time to get the wavelink track
                    search = chosen_anime['title']['romaji']
                    short_name = re.search('"([^"]*)"',chosen_theme['name'])
                    if short_name:
                        if chosen_theme['name'].startswith('OP'):
                            search += ' OP'
                        elif chosen_theme['name'].startswith('ED'):
                            search += ' ED'

                        search += ' ' + short_name.groups()[0]
                    else:
                        search += ' ' + chosen_theme['name']

                    # avoid excessive duplication
                    if not search in settings.past_set:
                        tracks = None
                        # try youtube
                        attempts = 1
                        while not tracks and attempts <= 3:
                            tracks = await self.wavelink.get_tracks('ytsearch:' + search)
                            attempts += 1
                                
                        # try the given url as backup
                        if not tracks and chosen_theme['url']:
                            attempts = 1
                            while not tracks and attempts <= 3:
                                tracks = await self.wavelink.get_tracks(chosen_theme['url'])
                                attempts += 1

                        if tracks:
                            # add the theme to our cache
                            settings.past_set.add(search)
                            await settings.past_queue.put(search)

                            # rotate out the older ones
                            while settings.past_queue.qsize() > settings.repeat_limit:
                                oldest = await settings.past_queue.get()
                                settings.past_set.remove(oldest)

                            return chosen_anime, chosen_theme, tracks[0]
            
            return await self._get_next_up(settings) # in case there's no theme found for this 
        except Exception as e:
            print(type(e))
            return await self._get_next_up(settings) # something done fucked up but it ain't my fault so i'm trying again

    async def _find_anime(self, search, id_mal):
        async with self.bot.http_session.post(api_url, json={
            'query': queries['find_anime'],
            'variables': {
                'search': search
            }
        }) as response:
            json = await response.json()
        
        media = json['data']['Page']['media']
        if not media:
            return False

        for m in media:
            if m['idMal'] == id_mal:
                return True

        return False
    
    def _get_and_add_settings(self, guild_id):
        if guild_id not in self.settings:
            self.settings[guild_id] = GameSettings()

        return self.settings[guild_id]

    async def _get_list_repeat_limit(self, name):
        """Gets the repeat limit for a setting if given list was the largest list. Half the size of completed and current lists"""
        async with self.bot.http_session.post(api_url, json={
            'query': queries['from_list'],
            'variables': {
                'name': name
            }
        }) as response:
            json = await response.json()

        return sum([len(l['entries']) for l in json['data']['MediaListCollection']['lists']])

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Exit game when there are no members left in the voice channel"""
        if before.channel and (game := self.games.get(before.channel.guild.id)) and \
            game.channel == before.channel and len(game.channel.members) == 1 and \
            self.bot.user in game.channel.members:
            
            game.loop.cancel()            

    @commands.group(
        aliases=['am'],
        invoke_without_command=True,
        help='The anime music guesser game!'
    )
    @commands.guild_only()
    async def animu(self, ctx):
        await ctx.send(embed=rules)

    @animu.command(aliases=['new'], help='Starts an AniMu game')
    async def start(self, ctx):
        if (game := self.games.get(ctx.guild.id)) and not game.loop.done():
            return await ctx.send('There is already a game running on this server!')
        
        if not ctx.author.voice:
            return await ctx.send('Please join a voice channel first before starting the game.')

        settings = self._get_and_add_settings(ctx.guild.id)
        if not settings.anime_lists:
            return await ctx.send('No anime lists! Please add some anime lists with `am! addlist` first before starting the game.')

        self.games[ctx.guild.id] = GameState(ctx.author.voice.channel, self.bot.loop.create_task(self._game_loop(ctx.author.voice.channel, ctx.channel, settings = self._get_and_add_settings(ctx.guild.id))))

    @animu.command(aliases=['exit', 'quit', 'end'], help='Stops the current AniMu game.\nThis command will automatically be called when there are no more players in the voice channel.')
    async def stop(self, ctx):
        game = self.games.get(ctx.guild.id)
        if not game or game.loop.done():
            return await ctx.send('No game currently running!')
        
        if not ctx.author.voice or game.channel != ctx.author.voice.channel:
            return await ctx.send('You must be in the game channel to stop the game!')

        game.loop.cancel()

    @animu.command(aliases=['add', 'al'], help='Adds one or more AniList user\'s anime list to the game.')
    async def addlist(self, ctx, *names):
        settings = self._get_and_add_settings(ctx.guild.id)

        unknown_list = False
        for n in names:
            if n == 'top200':
                settings.anime_lists.add(n)
                settings.repeat_limit = 100
            else:
                async with self.bot.http_session.post(api_url, json={
                    'query': queries['check_user'],
                    'variables': {
                        'name': n
                    }
                }) as response:
                    if response.status == 200:
                        settings.anime_lists.add(n)

                        if settings.repeat_limit != 100 and (limit := await self._get_list_repeat_limit(n)) > settings.repeat_limit:
                                settings.repeat_limit = limit if limit < 100 else 100
                    else:
                        unknown_list = True

        return await ctx.send(
            embed=discord.Embed(
                title='AniMu - Add Anime Lists',
                description='One or more of the requested users could not be found.' if unknown_list else 'Lists successfully added!',
                color=colors['failure'] if unknown_list else colors['info'],
            ).add_field(
                name='Anime Lists',
                value='\n'.join(settings.anime_lists) if settings.anime_lists else 'No anime lists! Add some!',
                inline=False
            ).add_field(
                name='Min rounds btw repeats',
                value=settings.repeat_limit,
                inline=False
            )
        )

    @animu.command(aliases=['remove', 'rm', 'rl'], help='Remove one or more AniList user\'s anime list from the game.')
    async def removelist(self, ctx, *names):
        settings = self._get_and_add_settings(ctx.guild.id)
        
        update_limit = False
        for n in names:
            if n in settings.anime_lists:
                settings.anime_lists.remove(n)
                
                if n == 'top200' or (limit := await self._get_list_repeat_limit(n)) >= settings.repeat_limit:
                    update_limit = True

        if update_limit and 'top200' not in settings.anime_lists:
            settings.repeat_limit = 0
            for l in settings.anime_lists:
                limit = await self._get_list_repeat_limit(l)
                if limit >= 100:
                    settings.repeat_limit = 100
                    break
                elif limit > settings.repeat_limit:
                    settings.repeat_limit = limit

        return await ctx.send(
            embed=discord.Embed(
                title='AniMu - Remove Anime Lists',
                description='Lists successfully removed!',
                color=colors['info'],
            ).add_field(
                name='Anime Lists',
                value='\n'.join(settings.anime_lists) if settings.anime_lists else 'No anime lists! Add some!',
                inline=False,
            ).add_field(
                name='Min rounds btw repeats',
                value=settings.repeat_limit,
                inline=False
            )
        )

    @animu.command(aliases=['list', 'l'], help='Shows what anime lists are in the game set')
    async def lists(self, ctx):
        settings = self._get_and_add_settings(ctx.guild.id)
        return await ctx.send(
            embed=discord.Embed(
                title='AniMu - Anime Lists',
                description='\n'.join(settings.anime_lists),
                color=colors['info']
            ).add_field(
                name='Min rounds btw repeats',
                value=settings.repeat_limit,
                inline=False
            )
        )

    @commands.command(hidden=True)
    @commands.guild_only()
    @commands.is_owner()
    async def play(self, ctx, *, url):
        if not ctx.author.voice:
            return await ctx.send('Join a voice channel first!')


        player = self.wavelink.get_player(ctx.guild.id)
        await player.connect(ctx.author.voice.channel.id)
        track = await self.wavelink.get_tracks(url)
        await player.play(track[0])


def setup(bot):
    bot.add_cog(AniMu(bot))

colors = {
    'info': 0xcc4dff,
    'success': 0x4cca51,
    'failure': 0xfc2626
}
icon_url = 'https://www.reddit.com/favicon.ico'
api_url = 'https://graphql.anilist.co'

rules = discord.Embed(
    title='AniMu (Anime Music Guessing Game)',
    color=colors['info'],
    description=
'''
The game is simple: the bot plays a random anime theme, and players have 45 seconds to guess what it is. To guess, put two question marks at the end of your message, ex: `sao??`.

You get 10 points for a correct guess and lose 5 points for an incorrect guess. You can guess as many times as you want, but keep an eye on those points!

Additionally, you can add and remove users (from AniList) to pull anime from in the game with the `am! addlist` and `am! removelist` commands. The bot will get music from anime in the watching and completed lists of those users. There is also the special `top200` "user" which will get music from the top 200 most popular anime.

To start a game, type `am! start` while in a voice channel. You can end the game with `am! stop`. Have fun!
'''
).set_footer(text='Thank you Anilist and r/AnimeThemes for the data.')

queries = {
    'check_user':
'''
query CheckUser($name: String) {
  User(name: $name) {
    id
  }
}
''',
    'find_anime':
'''
query FindAnime($search: String) {
  Page(page: 1, perPage: 10) {
    media(search: $search) {
      idMal
    }
  }
}
''',
    'from_list':
'''
query RandomAnimeFromList($name: String) {
  MediaListCollection(userName: $name, type: ANIME, status_in: [CURRENT, COMPLETED]) {
    lists {
      entries {
        media {
          idMal
          seasonYear
          title {
            romaji
          }
          coverImage {
            extraLarge
          }
        }
      }
    }
  }
}
''',
    'from_top':
'''
query RandomAnimeFromTop($page: Int) {
  Page(page: $page, perPage: 1) {
    media(type: ANIME, sort: [POPULARITY_DESC]) {
      idMal
      seasonYear
      title {
        romaji
      }
      coverImage {
        extraLarge
      }
    }
  }
}
'''
}
