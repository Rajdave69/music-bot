import re
import discord
import yt_dlp
from discord.ext import commands
from youtube_search import YoutubeSearch
from backend import log, embed_url, embed_footer, embed_header, embed_color, embed_icon


class Other(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.ydl_opts = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        }

    @commands.Cog.listener()
    async def on_ready(self):
        log.info("Cogs : Misc.py Loaded")

    @commands.slash_command(name="search", description="Searches for a song on YouTube.")
    async def search(self, ctx, query):
        await ctx.defer()

        embed = discord.Embed(title=f"YouTube Search", url=embed_url,
                              description=f"Here are your search results. Requested by {ctx.author.mention}",
                              color=embed_color)
        embed.set_author(name=embed_header, icon_url=embed_icon)

        # If it not a URL, search for it
        if not re.search(
                r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|.+\?v=)?([^&=%\n]*)',
                query):
            results = YoutubeSearch(query, max_results=1).to_dict()
            content = f"https://www.youtube.com/watch?v={results[0]['id']}"

            log.debug(results[0])
            log.debug(content)

            title = results[0]['title']
            # change mm:ss duration to seconds
            duration = results[0]['duration']
            duration = duration.split(":")
            duration = int(duration[0]) * 60 + int(duration[1])
            duration = f"{str(duration // 60)}:{str(duration % 60).zfill(2)}"

            views = re.sub(r'\D', '', results[0]['views'])  # Remove all non-digits from views
            channel = results[0]['channel']
            url = content
            thumbnail = results[0]['thumbnails'][0]

        else:  # If it is a Valid YT URL

            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                try:
                    vid_info = ydl.extract_info(query, download=False)

                    title = vid_info['title']
                    duration = vid_info['duration']

                    views = vid_info['view_count']
                    channel = vid_info['uploader']
                    url = vid_info['webpage_url']
                    thumbnail = vid_info['thumbnail']

                except Exception as e:
                    log.error(e)
                    return "vid_not_found"

        # add commas to views
        views = "{:,}".format(int(views))

        embed.add_field(name="Title", value=f"`{title}`", inline=False)
        embed.add_field(name="Duration", value=f"`{str(duration).replace('.', ':')}`", inline=False)
        embed.add_field(name="Views", value=f"`{views}`", inline=False)
        embed.add_field(name="Channel", value=f"`{channel}`", inline=False)
        embed.add_field(name="Link", value=f"{url}", inline=False)
        embed.set_image(url=thumbnail)
        embed.set_footer(text=embed_footer)
        await ctx.followup.send(embed=embed)


def setup(client):
    client.add_cog(Other(client))
