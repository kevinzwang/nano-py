import discord
from discord.ext import commands, tasks
import aiohttp
import asyncio

class Berkeley(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.catalog = {}
        self._get_catalog_loop.start()

    async def _get_catalog(self):
        async with self.bot.http_session.get('https://www.berkeleytime.com/api/catalog/catalog_json/') as response:
            json = await response.json()

        new_catalog = {}
        for course in json['courses']:
            if course['abbreviation'] not in new_catalog:
                new_catalog[course['abbreviation']] = {}

            new_catalog[course['abbreviation']][course['course_number']] = course['id']

        if not self.catalog:
            print('Course catalog initialized!')

        self.catalog = new_catalog

    @tasks.loop(hours=24)
    async def _get_catalog_loop(self):
        await self._get_catalog()

    @_get_catalog_loop.before_loop
    async def _before_get_catalog_loop(self):
        await self.bot.wait_until_ready()
        while not hasattr(self.bot, 'http_session'):
            await asyncio.sleep(1)

    def _format_description(self, description):
        if not description:
            return 'No description.'

        description = html2text.html2text(description).replace('\n', ' ').replace('  ', ' ')

        if len(description) < 256:
            return description
        else:
            return description[:256-3] + '...'

    @commands.command(name='course', aliases=['class', 'c'], help='Info about a Berkeley class')
    @commands.cooldown(3, 10, commands.BucketType.user)
    async def course(self, ctx, *, search):
        search_upper = search.strip().upper()
        layman = False
        longest_abbrev = ''
        for abbrev in self.catalog:
            if search_upper.startswith(abbrev) and len(abbrev) > len(longest_abbrev):
                longest_abbrev = abbrev

        for abbrev in layman_to_abbreviation:
            if search_upper.startswith(abbrev) and len(abbrev) > len(longest_abbrev):
                longest_abbrev = abbrev
                layman = True

        if not longest_abbrev:
            return await ctx.send(f'Course `{search}` not found.')

        course_num = search_upper[len(longest_abbrev):].strip()
        longest_abbrev = layman_to_abbreviation[longest_abbrev] if layman else longest_abbrev

        if course_id := self.catalog[longest_abbrev].get(course_num):
            async with self.bot.http_session.get(
                'https://www.berkeleytime.com/api/catalog/catalog_json/course_box/', 
                params={'course_id': course_id}
            ) as response:
                json = await response.json()

            description = 'No description.'
            if json['course']['description']:
                description = json['course']['description']
                if len(description) > 256:
                    description = description[:256-3] + '...'

            abbrev = json['course']['abbreviation']
            number = json['course']['course_number']

            return await ctx.send(embed=discord.Embed(
                title=f'{abbrev} {number}',
                description=description,
                url=f'https://www.berkeleytime.com/catalog/{abbrev}/{number}/',
                color=0x003262,
            ).set_footer(
                text='BerkeleyTime.com', 
                icon_url='https://www.berkeleytime.com/favicon.png'
            ).set_thumbnail(
                url='https://brand.berkeley.edu/wp-content/uploads/2016/10/ucbseal_139_540.png'
            ).add_field(
                name='Title',
                inline=False,
                value=json['course']['title']
            ).add_field(
                name='Units',
                inline=True,
                value=json['course']['units']
            ).add_field(
                name='Average Grade',
                inline=True,
                value=json['course']['letter_average']
            ).add_field(
                name='Enrolled',
                inline=True,
                value=f'{round(json["course"]["enrolled_percentage"] * 100)}%'
            ))
        else:
            return await ctx.send(f'Course `{search}` not found.')

    @commands.command(help='Refreshes the course catalog.')
    @commands.is_owner()
    async def refresh_catalog(self, ctx):
        await self._get_catalog()
        await ctx.send('Catalog successfully updated. Go bears!')


layman_to_abbreviation = {
  "ASTRO": "ASTRON",
  "CS": "COMPSCI",
  "MCB": "MCELLBI",
  "NUTRISCI": "NUSCTX",
  "BIOE": "BIO ENG",
  "BIO E": "BIO ENG",
  "BIO P": "BIO PHY",
  "BIOENG": "BIO ENG",
  "BIO": "BIOLOGY",
  "CIVE": "CIV ENG",
  "CIV E": "CIV ENG",
  "CHEME": "CHM ENG",
  "CIVENG": "CIV ENG",
  "CLASSICS": "CLASSIC",
  "COGSCI": "COG SCI",
  "COLLEGE WRITING": "COLWRIT",
  "COMPLIT": "COM LIT",
  "COMLIT": "COM LIT",
  "CYPLAN": "CY PLAN",
  "CP" : "CY PLAN",
  "DESINV": "DES INV",
  "DESIGN" : "DES INV",
  "DEVENG": "DEV ENG",
  "DEVSTD": "DEV STD",
  "DS" : "DATASCI",
  "EALANG": "EA LANG",
  "ED": "ENV DES",
  "EE": "EL ENG",
  "ERG": "ENE,RES",
  "ER": "ENE,RES",
  "ENERES": "ENE,RES",
  "E": "ENGIN",
  "ENGINEERING": "ENGIN",
  "ENVSCI": "ENV SCI",
  "ETHSTD": "ETH STD",
  "EURAST": "EURA ST",
  "GEOLOGY": "GEOG",
  "HINURD": "HIN-URD",
  "HUMBIO": "HUM BIO",
  "IB": "INTEGBI",
  "IE": "IND ENG",
  "IEOR": "IND ENG",
  "LING": "LINGUIS",
  "L&S": "L & S",
  "LS": "L & S",
  "MALAYI": "MALAY/I",
  "MATSCI": "MAT SCI",
  "MS": "MAT SCI",
  "MSE": "MAT SCI",
  "MECENG": "MEC ENG",
  "MECHE": "MEC ENG",
  "MECH E": "MEC ENG",
  "ME": "MEC ENG",
  "MEDST": "MED ST",
  "MESTU": "M E STU",
  "MIDDLE EASTERN STUDIES": "M E STU",
  "MILAFF": "MIL AFF",
  "MILSCI": "MIL SCI",
  "NEUROSCI": "NEUROSC",
  "NE": "NUC ENG",
  "NESTUD": "NE STUD",
  "MEDIA": "MEDIAST",
  "PE": "PHYS ED",
  "PHYSED": "PHYS ED",
  "PHILO": "PHILOS",
  "PHIL": "PHILOS",
  "POLI ECON" : "POLECON",
  "POLIECON" : "POLECON",
  "PHILOSOPHY": "PHILO",
  "PMB": "PLANTBI",
  "POLI": "POL SCI",
  "POLSCI": "POL SCI",
  "POLISCI": "POL SCI",
  "POLI SCI": "POL SCI",
  "PS" : "POL SCI",
  "PUBPOL": "PUB POL",
  "PP": "PUB POL",
  "PUBLIC POLICY": "PUB POL",
  "PUBAFF": "PUB AFF",
  "PSYCHOLOGY": "PSYCH",
  "SASIAN": "S ASIAN",
  "SSEASN": "S,SEASN",
  "STATS": "STAT",
  "TDPS": "THEATER",
  "HAAS": "UGBA",
  "VIETNAMESE": "VIETNMS",
  "VISSCI": "VIS SCI",
  "VISSTD": "VIS STD",
}

def setup(bot):
    bot.add_cog(Berkeley(bot))