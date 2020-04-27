import discord
from discord.ext import commands
from enum import Enum
import asyncio
import html2text
import re
import math

class Weeb(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _search(self, ctx, media_type, search):
        page = 1
        msg = None
        while True:
            async with self.bot.http_session.post(api_url, json={
                'query': queries[media_type+'_search'],
                'variables': {
                    'search': search,
                    'page': page,
                    'perPage': 5
                }
            }) as response: json = await response.json()

            page_json = json['data']['Page']

            if not page_json['media']:
                msg = await ctx.send(f'No {media_type} found.')
                return None, msg

            if page == 1 and len(page_json['media']) == 1:
                return page_json['media'][0]['id'], None

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
                return page_json['media'][index]['id'], msg
            elif reaction.emoji == '⬅️':
                page -= 1
            elif reaction.emoji == '➡️':
                page += 1
            elif reaction.emoji == '❌':
                for emoji in search_reactions:
                    self.bot.loop.create_task(msg.remove_reaction(emoji, self.bot.user))

                await msg.edit(content='Search cancelled', embed=None)
                return None, msg
                
    async def _anime_embed(self, json):
        anime = json['data']['Media']

        title = anime['title']['romaji']
        # cuz frickin kakushigoto decided they wanted to add a (TV) in their title already
        if not title.endswith(fmt := f'({self._format_mediaformat(anime["format"])})'): 
            title += ' ' + fmt

        embed = discord.Embed(
            title=title,
            description=self._format_description(anime['description']),
            url=anime['siteUrl'],
            color=anilist_colors['anime']
        ).set_footer(
            text='AniList.co', 
            icon_url=icon_url
        ).set_thumbnail(url=anime['coverImage']['extraLarge'])

        if anime['status'] == 'RELEASING':
            if anime['nextAiringEpisode']['episode'] == 1:
                embed.add_field(
                    name='Premieres', 
                    inline=True, 
                    value=self._format_time(anime['nextAiringEpisode']['timeUntilAiring']/60)
                )
            else:
                embed.add_field(
                    name='Next Episode', 
                    inline=True, 
                    value=f'Ep {anime["nextAiringEpisode"]["episode"]}: {self._format_time(anime["nextAiringEpisode"]["timeUntilAiring"]/60)}'
                )
        elif anime['season']:
            embed.add_field(
                name='Season', 
                inline=True, 
                value=f'{anime["season"].capitalize()} {anime["seasonYear"]}'
            )
        else:
            embed.add_field(
                name='Status', 
                inline=True, 
                value=self._format_mediaformat(anime['status'])
            )

        if anime['episodes'] or anime['duration']:
            if anime['episodes'] and anime['episodes'] > 1:
                embed.add_field(
                    name='Episodes', 
                    inline=True, 
                    value=anime['episodes']
                )
            elif anime['duration']:
                embed.add_field(
                    name='Duration', 
                    inline=True, 
                    value=self._format_time(anime['duration'])
                )
        
        embed.add_field(
            name='Mean Score', 
            inline=True, 
            value=f'{anime["meanScore"]}%' if anime['meanScore'] else shrug
        ).add_field(
            name='Genres', 
            inline=True, 
            value=', '.join(anime['genres']) if anime['genres'] else 'none'
        )

        return embed

    async def _manga_embed(self, json):
        manga = json['data']['Media']
        return discord.Embed(
            title=f'{manga["title"]["romaji"]} ({self._format_mediaformat(manga["format"])})',
            description=self._format_description(manga['description']),
            url=manga['siteUrl'],
            color=anilist_colors['manga']
        ).set_footer(
            text='AniList.co', 
            icon_url=icon_url
        ).set_thumbnail(
            url=manga['coverImage']['extraLarge']
        ).add_field(
            name='Status',
            inline=True,
            value=self._format_mediaformat(manga['status'])
        ).add_field(
            name='Chapters',
            inline=True,
            value=manga['chapters'] if manga['chapters'] else shrug
        ).add_field(
            name='Volumes',
            inline=True,
            value=manga['volumes'] if manga['volumes'] else shrug
        ).add_field(
            name='Mean Score', 
            inline=True, 
            value=f'{manga["meanScore"]}%' if manga['meanScore'] else shrug
        ).add_field(
            name='Genres', 
            inline=True, 
            value=', '.join(manga['genres']) if manga['genres'] else 'none'
        )
    
    def _format_time(self, time): 
        """
        Takes a time in minutes and converts it into the format '[days]d [hours]h [minutes]m', 
        excluding the days or hours if less than a day or hour respectively.
        """
        time= math.floor(time)
        formatted = ''
        
        day_minutes = 24*60
        hour_minutes = 60

        if time >= day_minutes:
            formatted += f'{math.floor(time / day_minutes)}d '
        
        if time >= hour_minutes:
            formatted += f'{math.floor((time % day_minutes) / hour_minutes)}h '

        formatted += f'{time % hour_minutes}m'

        return formatted

    def _format_description(self, description):
        if not description:
            return 'No description.'

        description = html2text.html2text(description).replace('\n', ' ').replace('  ', ' ')

        if len(description) < 256:
            return description
        else:
            return description[:256-3] + '...'

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

    @commands.command(aliases=['a'], help='Info about an anime')
    @commands.cooldown(3, 10, commands.BucketType.user)
    async def anime(self, ctx, *, search):
        anime_id, msg = await self._search(ctx, 'anime', search)
        if anime_id:
            async with self.bot.http_session.post(api_url, json={
                'query': queries['anime_info'],
                'variables': {
                    'id': anime_id
                }
            }) as response: json = await response.json()

            if msg:
                await msg.edit(embed=await self._anime_embed(json))
            else:
                msg = await ctx.send(embed=await self._anime_embed(json))

            if animu := self.bot.get_cog('Aniμ'):
                await animu.play_from_anime(ctx, msg, json)

    @commands.command(aliases=['qa'], help='Gets you the first anime result.\nYou can also do "((search))"')
    @commands.cooldown(3, 10, commands.BucketType.user)
    async def quickanime(self, ctx, *, search):
        async with self.bot.http_session.post(api_url, json={
            'query': queries['quick_anime'],
            'variables': {
                'search': search
            }
        }) as response: json = await response.json()

        if json['data']['Media']:
            msg = await ctx.send(embed=await self._anime_embed(json))
            if animu := self.bot.get_cog('Aniμ'):
                await animu.play_from_anime(ctx, msg, json)
        else:
            await ctx.send('No anime found.')

    @commands.command(aliases=['anilist', 'al'], help='Info about an AniList user\'s anime list')
    @commands.cooldown(3, 10, commands.BucketType.user)
    async def animelist(self, ctx, name):
        async with self.bot.http_session.post(api_url, json={
            'query': queries['anime_list'],
            'variables': {
                'name': name
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

    @commands.command(aliases=['m'], help='Info about a manga')
    @commands.cooldown(3, 10, commands.BucketType.user)
    async def manga(self, ctx, *, search):
        manga_id, msg = await self._search(ctx, 'manga', search)
        if manga_id:
            async with self.bot.http_session.post(api_url, json={
                'query': queries['manga_info'],
                'variables': {
                    'id': manga_id
                }
            }) as response: json = await response.json()

            if msg:
                await msg.edit(embed=await self._manga_embed(json))
            else:
                await ctx.send(embed=await self._manga_embed(json))

    @commands.command(aliases=['qm'], help='Gets you the first manga result.\nYou can also do "<<search>>"')
    async def quickmanga(self, ctx, *, search):
        async with self.bot.http_session.post(api_url, json={
            'query': queries['quick_manga'],
            'variables': {
                'search': search
            }
        }) as response: json = await response.json()

        if json['data']['Media']:
            await ctx.send(embed=await self._manga_embed(json))
        else:
            await ctx.send('No manga found.')

    @commands.command(aliases=['ml'], help='Info about an AniList user\'s manga list')
    @commands.cooldown(3, 10, commands.BucketType.user)
    async def mangalist(self, ctx, name):
        async with self.bot.http_session.post(api_url, json={
            'query': queries['manga_list'],
            'variables': {
                'name': name
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
      id
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

    'anime_info':
'''
query AnimeInfo($id: Int) {
  Media(id: $id) {
    title {
      romaji
    }
    format
    status
    description(asHtml: false)
    season
    seasonYear
    episodes
    duration
    coverImage {
      extraLarge
    }
    genres
    meanScore
    siteUrl
    nextAiringEpisode {
      timeUntilAiring
      episode
    }
  }
}
''',
    'quick_anime':
'''
query QuickAnime($search: String) {
  Media(search: $search, type: ANIME) {
    title {
      romaji
    }
    format
    status
    description(asHtml: false)
    season
    seasonYear
    episodes
    duration
    coverImage {
      extraLarge
    }
    genres
    meanScore
    siteUrl
    nextAiringEpisode {
      timeUntilAiring
      episode
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
      id
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
    'manga_info':
'''
query MangaInfo($id: Int) {
  Media(id: $id) {
    title {
      romaji
    }
    format
    status
    description(asHtml: false)
    chapters
    volumes
    coverImage {
      extraLarge
    }
    genres
    meanScore
    siteUrl
  }
}
''',
    'quick_manga':
'''
query QuickManga($search: String) {
  Media(search: $search, type: MANGA) {
    title {
      romaji
    }
    format
    status
    description(asHtml: false)
    chapters
    volumes
    coverImage {
      extraLarge
    }
    genres
    meanScore
    siteUrl
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