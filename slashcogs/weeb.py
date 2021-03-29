import discord
from discord.ext import commands
from discord_slash import SlashContext
from discord_slash.utils.manage_commands import create_option
from enum import Enum
import asyncio
import html2text
import re
import math
import util

class Weeb(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _search(self, ctx, media_type, search, first):
        page = 1
        msg = None
        while True:
            async with self.bot.http_session.post(api_url, json={
                'query': queries[media_type+'_search'],
                'variables': {
                    'search': search,
                    'page': page,
                    'perPage': 1 if first else 5
                }
            }) as response: json = await response.json()

            page_json = json['data']['Page']

            if not page_json['media']:
                msg = await ctx.send(f'No {media_type} found.')
                return None, msg

            if page == 1 and len(page_json['media']) == 1:
                return page_json['media'][0]['siteUrl'], None

            embed = discord.Embed(
                title=f'Search results for: \'{search}\' ({page}/{page_json["pageInfo"]["lastPage"]})',
                description='\n'.join([f'{index+1}. [{status_symbols.get(anime["status"])} {anime["title"]["romaji"]} ({self._format_mediaformat(anime["format"])})]({anime["siteUrl"]})' for index, anime in enumerate(page_json['media'])]),
                color=anilist_colors[media_type],
            ).set_footer(text='AniList.co', icon_url=icon_url)

            if msg:
                await msg.edit(embed=embed)
            else:
                msg = await ctx.send(embed=embed)
                for emoji in search_reactions:
                    self.bot.loop.create_task(msg.add_reaction(emoji))

            def reaction_check(reaction, user):
                if user == ctx.author and reaction.message.id == msg.id and reaction.emoji in search_reactions:
                    index = search_reactions.index(reaction.emoji)
                    if index < 5: return index+1 <= len(page_json['media'])
                    elif reaction.emoji == '⬅️': return page > 1
                    elif reaction.emoji == '➡️': return page < page_json["pageInfo"]["lastPage"]
                    elif reaction.emoji == '❌': return True
                    
                return False

            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=60, check=reaction_check)
            except asyncio.TimeoutError:
                for emoji in search_reactions:
                    self.bot.loop.create_task(msg.remove_reaction(emoji, self.bot.user))

                await msg.edit(content='Search timed out', embed=None)

                return None, msg

            try:
                await msg.remove_reaction(reaction, user)
            except:
                pass

            index = search_reactions.index(reaction.emoji)
            if index < 5:
                for emoji in search_reactions:
                    self.bot.loop.create_task(msg.remove_reaction(emoji, self.bot.user))
                return page_json['media'][index]['siteUrl'], msg
            elif reaction.emoji == '⬅️':
                page -= 1
            elif reaction.emoji == '➡️':
                page += 1
            elif reaction.emoji == '❌':
                for emoji in search_reactions:
                    self.bot.loop.create_task(msg.remove_reaction(emoji, self.bot.user))

                await msg.edit(content='Search cancelled', embed=None)
                return None, msg
    
    def _format_mediaformat(self, fmt):
        """
        Converts the anilist media format (all caps with underscores), to a more human-friendly
        format. Can also be used for media and list statuses.
        """
        if fmt == 'TV_SHORT':
            return 'TV Short'
        elif fmt == 'TV' or fmt == 'OVA' or fmt == 'ONA':
            return fmt
        else:
            return ' '.join([word.capitalize() for word in fmt.split('_')])

    @util.command(
        name='anime',
        description='Search for an anime and display its info',
        options=[
            create_option(
                name='search',
                description='Anime to search for',
                option_type=3,
                required=True
            ),
            create_option(
                name='first',
                description='Display the first search result only',
                option_type=5,
                required=False
            )
        ])
    @util.cooldown(3, 10)
    async def anime(self, ctx, search, first=False):
        site_url, msg = await self._search(ctx, 'anime', search, first)
        if site_url:
            if msg:
                await msg.edit(content=site_url, embed=None)
            else:
                msg = await ctx.send(site_url)

            if animu := self.bot.get_cog('Aniμ'):
                await animu.play_from_anime(ctx, msg, json)

    @util.command(
        name='animelist',
        description='Get info about an AniList user\'s anime list',
        options=[
            create_option(
                name='username',
                description='The username on AniList',
                option_type=3,
                required=True
            )
        ])
    @util.cooldown(3, 10)
    async def animelist(self, ctx, username):
        async with self.bot.http_session.post(api_url, json={
            'query': queries['anime_list'],
            'variables': {
                'name': username
            }
        }) as response: json = await response.json()
            
        user = json['data']['User']

        if user:
            statuses = {}
            for anime_list in json['data']['MediaListCollection']['lists']:
                statuses[anime_list['name']] = len(anime_list['entries'])

            formatted_list = '```'
            for list_name in ('Watching', 'Completed', 'Paused', 'Dropped', 'Planning'):
                list_count = statuses[list_name] if list_name in statuses else 0
                formatted_list += f'{list_name}:{" "*(15-len(list_name)-len(str(list_count)))}{list_count}\n'
            formatted_list += '```'

            await ctx.send(embed=discord.Embed(
                    title=user['name'],
                    url=user['siteUrl'],
                    color=anilist_colors[user['options']['profileColor']]
                ).set_footer(
                    text='AniList.co', 
                    icon_url=icon_url
                ).set_thumbnail(
                    url=user['avatar']['large']
                ).add_field(
                    name='Total Anime', 
                    inline=True, 
                    value=user['statistics']['anime']['count'] if user['statistics']['anime']['count'] else 0
                ).add_field(
                    name='Days Watched',
                    inline=True,
                    value=(math.floor(user['statistics']['anime']['minutesWatched'] / (24*60) * 10) / 10) if user['statistics']['anime']['minutesWatched'] else 0
                ).add_field(
                    name='Mean Score',
                    inline=True,
                    value=f'{round(user["statistics"]["anime"]["meanScore"], 1)}%' if user['statistics']['anime']['meanScore'] else shrug
                ).add_field(
                    name='Anime List',
                    value=formatted_list
                )
            )
        else:
            await ctx.send('No AniList user found')

    @util.command(
        name='manga',
        description='Search for a manga and display its info',
        options=[
            create_option(
                name='search',
                description='Manga to search for',
                option_type=3,
                required=True
            ),
            create_option(
                name='first',
                description='Display the first search result only',
                option_type=5,
                required=False
            )
        ])
    @util.cooldown(3, 10)
    async def manga(self, ctx, search, first=False):
        site_url, msg = await self._search(ctx, 'manga', search, first)
        if site_url:
            if msg:
                await msg.edit(content=site_url, embed=None)
            else:
                await ctx.send(site_url)

    @util.command(
        name='mangalist',
        description='Get info about an AniList user\'s manga list',
        options=[
            create_option(
                name='username',
                description='The username on AniList',
                option_type=3,
                required=True
            )
        ])
    @util.cooldown(3, 10)
    async def mangalist(self, ctx, username):
        async with self.bot.http_session.post(api_url, json={
            'query': queries['manga_list'],
            'variables': {
                'name': username
            }
        }) as response: json = await response.json()
        
        user = json['data']['User']

        if user:
            statuses = {}
            for manga_list in json['data']['MediaListCollection']['lists']:
                statuses[manga_list['name']] = len(manga_list['entries'])

            formatted_list = '```'
            for list_name in ('Reading', 'Completed', 'Paused', 'Dropped', 'Planning'):
                list_count = statuses[list_name] if list_name in statuses else 0
                formatted_list += f'{list_name}:{" "*(15-len(list_name)-len(str(list_count)))}{list_count}\n'
            formatted_list += '```'

            await ctx.send(embed=discord.Embed(
                    title=user['name'],
                    url=user['siteUrl'],
                    color=anilist_colors[user['options']['profileColor']]
                ).set_footer(
                    text='AniList.co', 
                    icon_url=icon_url
                ).set_thumbnail(
                    url=user['avatar']['large']
                ).add_field(
                    name='Total Manga', 
                    inline=True, 
                    value=user['statistics']['manga']['count'] if user['statistics']['manga']['count'] else 0
                ).add_field(
                    name='Chapters Read',
                    inline=True,
                    value=user['statistics']['manga']['chaptersRead'] if user['statistics']['manga']['chaptersRead'] else 0
                ).add_field(
                    name='Mean Score',
                    inline=True,
                    value=f'{round(user["statistics"]["manga"]["meanScore"], 1)}%' if user['statistics']['manga']['meanScore'] else shrug
                ).add_field(
                    name='Manga List',
                    value=formatted_list
                )
            )
        else:
            await ctx.send('No AniList user found')

api_url = 'https://graphql.anilist.co'
icon_url = 'https://anilist.co/favicon.ico'

shrug = '¯\\_(ツ)_/¯'

status_symbols = {
    'FINISHED': '',
    'RELEASING': '🟢',
    'NOT_YET_RELEASED':  '🟠',
    'CANCELLED': ''
}

search_reactions = ('1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '⬅️', '➡️', '❌')

anilist_colors = {
    'blue': 0x3db4f2,
    'purple': 0xc063ff,
    'green': 0x4cca51,
    'orange': 0xef881a,
    'red': 0xe13333,
    'pink': 0xfc9dd6,
    'gray': 0x677b94,

    'anime': 0x3db4f2,
    'manga': 0xef881a,
}

queries = {
    'anime_search': 
'''
query AnimeSearch($search: String, $page: Int, $perPage: Int) {
  Page(page: $page, perPage: $perPage) {
    pageInfo {
      lastPage
      hasNextPage
    }
    media(search: $search, type: ANIME) {
      title {
        romaji
      }
      format
      status
      siteUrl
    }
  }
}
''',
    'anime_list':
'''
query AnimeList($name: String) {
  User(name: $name) {
    name
    avatar {
      large
    }
    options {
      profileColor
    }
    statistics {
      anime {
        count
        meanScore
        minutesWatched
      }
    }
    siteUrl
  }
  MediaListCollection(userName: $name, type: ANIME) {
    lists {
      name
      entries {
        id
      }
    }
  }
}
''',
    'manga_search':
'''
query MangaSearch($search: String, $page: Int, $perPage: Int) {
  Page(page: $page, perPage: $perPage) {
    pageInfo {
      lastPage
      hasNextPage
    }
    media(search: $search, type: MANGA) {
      title {
        romaji
      }
      format
      status
      siteUrl
    }
  }
}
''',
    'manga_list':
'''
query MangaList($name: String) {
  User(name: $name) {
    name
    avatar {
      large
    }
    options {
      profileColor
    }
    statistics {
      manga {
        count
        chaptersRead
        meanScore
      }
    }
    siteUrl
  }
  MediaListCollection(userName: $name, type: MANGA) {
    lists {
      name
      entries {
        id
      }
    }
  }
}
'''
}


def setup(bot):
    bot.add_cog(Weeb(bot))