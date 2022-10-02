import json
from discord.utils import get
from discord.ext import commands
from discord import SlashCommandGroup
import discord, os, sqlite3, random, yt_dlp, re, time
from youtube_search import YoutubeSearch
from backend import embed_icon, embed_color, embed_footer, embed_header, embed_url, client, music_channel  # , music_vc
from backend import log, input_sanitizer
from discord.ext import tasks

class Queue:
    def __init__(self):
        self.song_list = {}
        self.current_song = None  # [id, title,  loop]
        self.shuffle = False

    def get_next_song(self, guild_id: int, override=False) -> list | None:

        if not (self.current_song is None) and self.current_song[2] and not override:
            return self.current_song

        if self.shuffle and len(self.song_list[str(guild_id)]):
            self.current_song = random.choice(self.song_list)
            return self.current_song

        elif len(self.song_list[str(guild_id)]):
            self.current_song = self.song_list[str(guild_id)].pop()
            return self.current_song
        else:
            return None

    def add_song(self, song_id, title, guild_id):
        if self.song_list.get(str(guild_id)) is None:
            self.song_list[str(guild_id)] = []
        self.song_list[str(guild_id)].insert(0, [song_id, title, False])

    # def loop_song(self):
    #     log.debug(self.current_song)
    #     self.current_song = [self.current_song[0], self.current_song[1], not self.current_song[2]]

    def skip_song(self, guild_id):
        return self.get_next_song(override=True, guild_id=guild_id)



q = Queue()

class ReplayButton(discord.ui.View):
    def __init__(self, video_url, video_title):
        super().__init__(timeout=None)
        self.url = video_url
        self.title = video_title

    # async def on_timeout(self):
    #     for child in self.children:
    #         child.disabled = True
    #     await self.message.edit(view=self)

    @discord.ui.button(label="Replay", style=discord.ButtonStyle.gray, custom_id="replay")
    async def button_callback(self, button, interaction):  # Don't remove the unused variable
        await interaction.response.send_message("Added song to queue.", ephemeral=True)
        # get song id from url
        video_id = re.search(r"v=(.*)", self.url).group(1)
        q.add_song(video_id, self.title, interaction.guild.id)

        # await self.client.cogs.get('Music').player(self.ctx, self.url)


class DedicatedButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.queues = q

    # == Row 1 ==
    @discord.ui.button(emoji="<:music_loop:1003968639189397574>", style=discord.ButtonStyle.green, custom_id="music_loop", row=1)
    async def loop_button(self, button, interaction):
        # loop button
        await interaction.response.send_message("Loop toggled", ephemeral=True)
        # if self.voice.is_playing():
        #     q.loop_song() TODO: the loop stuff

    @discord.ui.button(emoji="<:music_pause:1003968631731925082>", style=discord.ButtonStyle.blurple, custom_id="music_playpause", row=1)
    async def play_pause_button(self, button, interaction):
        # play pause button
        voice = get(client.voice_clients, guild=client.get_guild(interaction.guild.id))
        if voice.is_playing():
            voice.pause()
            await interaction.response.send_message("Paused the current song.", ephemeral=True)
        else:
            voice.resume()
            await interaction.response.send_message("Resumed the current song.", ephemeral=True)

    @discord.ui.button(emoji="<:music_skip:1003968637054484610>", style=discord.ButtonStyle.green, custom_id="music_skip", row=1)
    async def skip_button(self, button, interaction):
        # skip button
        voice = get(client.voice_clients, guild=client.get_guild(interaction.guild.id))
        await interaction.response.send_message("Skip button pressed", ephemeral=True)
        if voice.is_playing():
            voice.stop()
            await interaction.response.send_message("Skipped the current song.", ephemeral=True)


    @discord.ui.button(emoji="<:music_stop:1003968634311426091>", style=discord.ButtonStyle.red, custom_id="music_stop", row=1)
    async def stop_button(self, button, interaction):
        # stop button
        voice = get(client.voice_clients, guild=client.get_guild(interaction.guild.id))
        if voice.is_playing():
            voice.stop()
            voice.channel.disconnect()
        await interaction.response.send_message("Stopped the music", ephemeral=True)


    # == Row 2 ==
    @discord.ui.button(emoji="<:music_vol_down:1003968641064255521>", style=discord.ButtonStyle.green, custom_id="music_vol_down", row=2)
    async def vol_down_button(self, button, interaction):
        voice = get(client.voice_clients, guild=client.get_guild(interaction.guild.id))
        voice.source.volume *= 0.9
        if voice.source.volume < 0.1:
            voice.source.volume = 0.01
        await interaction.response.send_message(f"Volume is now {voice.source.volume * 100}%", ephemeral=True)


    @discord.ui.button(emoji="<:shuffle:1004287992984240148>", style=discord.ButtonStyle.blurple, custom_id="music_shuffle", row=2)
    async def shuffle_button(self, button, interaction):
        await interaction.response.send_message("Shuffle button pressed", ephemeral=True)
        self.queues.shuffle = True


    @discord.ui.button(emoji="<:music_vol_up:1003968645820596287>", style=discord.ButtonStyle.green, custom_id="music_vol_up", row=2)
    async def vol_up_button(self, button, interaction):
        voice = get(client.voice_clients, guild=client.get_guild(interaction.guild.id))
        voice.source.volume *= 1.1
        if voice.source.volume > 1:
            voice.source.volume = 1
        await interaction.response.send_message(f"Volume is now {voice.source.volume * 100}%", ephemeral=True)


    @discord.ui.button(emoji="<:music_heart:1003968643656319047>", style=discord.ButtonStyle.red, custom_id="music_heart", row=2)
    async def heart_button(self, button, interaction):
        db = sqlite3.connect("./data/music.db")
        c = db.cursor()
        c.execute(f"CREATE TABLE IF NOT EXISTS playlists_{interaction.user.id} (playlist TEXT, song_id TEXT, titles TEXT)")
        db.commit()
        # get user that clicked button

        if not self.queues.current_song[0]:
            await interaction.response.send_message("No song is currently playing")
            return

        c.execute(f'SELECT song_id FROM playlists_{interaction.user.id} WHERE song_id="{self.queues.current_song[0]}" AND playlist="main"')
        res = c.fetchone()
        if res is not None:
            await interaction.response.send_message("The song already exists in the `main` playlist!")
            return

        c.execute(f'INSERT INTO playlists_{interaction.user.id} (playlist, song_id, titles) values("main", "{self.queues.current_song[0]}", "{self.queues.current_song[1][0]}")')
        db.commit()

        p_embed = discord.Embed(title="Music | Playlist", color=embed_color, url=embed_url, description=f"Adding to the playlist was successful!")
        p_embed.add_field(name="Song", value=f"`{self.queues.current_song[1][0]}`", inline=False)
        p_embed.add_field(name="Playlist", value=f"`main`", inline=False)
        p_embed.set_footer(text=embed_footer)
        p_embed.set_author(name=embed_header, icon_url=embed_icon)
        await interaction.response.send_message(embed=p_embed, ephemeral=True)








class Music(commands.Cog):
    music = SlashCommandGroup("music", "Music related commands")
    playlist = music.create_subgroup("playlist", "Commands which interact with your playlists")

    def __init__(self, client):
        self.client = client

        self.db = sqlite3.connect('./data/music.db')
        self.c = self.db.cursor()

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
        self.queues = q
        self.volume = 0.5

    @commands.Cog.listener()
    async def on_ready(self):
        log.info("Cog : Music.py Loaded")
        # client.add_view(ReplayButton)
        client.add_view(DedicatedButtons())


    @commands.Cog.listener()
    async def on_message(self, ctx):
        if ctx.channel.id != music_channel: return
        if ctx.author.id == self.client.user.id:
            await ctx.delete()
            return

        content = ctx.content
        await ctx.delete()

        if not re.search(r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|.+\?v=)?([^&=%\n]*)',content):
            results = YoutubeSearch(content, max_results=1).to_dict()
            log.debug(results[0]['id'])
            content = f"https://www.youtube.com/watch?v={results[0]['id']}"
            log.debug(content)

        # key | title | song_id | duration
        res = await self.player(ctx, content)

        if res == "length_too_long":
            return
        log.debug(res)







    def next_song(self, voice) -> None:
        song = self.queues.get_next_song(guild_id=voice.guild.id)
        if song: voice.play(discord.FFmpegPCMAudio(f'./data/songs/{song[0]}.mp3'), after=lambda x: self.next_song(voice))



    async def player(self, ctx, song_url):
        vc = get(ctx.guild.voice_channels, name="Music")
        voice = get(self.client.voice_clients, guild=ctx.guild)
        log.debug(str(voice))

        if voice is None:
            await vc.connect()
            voice = get(self.client.voice_clients, guild=ctx.guild)

        else:
            if not voice.is_connected():
                await vc.connect()

        self.c.execute('SELECT * FROM songs_cache')
        songs = self.c.fetchall()

        # get video id
        with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
            try:
                vid_info = ydl.extract_info(song_url, download=False)
                song_id = vid_info['id']
                video_duration = vid_info['duration']
                video_title = vid_info['title'].replace('"', '')
                video_banner = vid_info['thumbnail']

            except Exception as e:
                log.error(e)
                return "vid_not_found"
            if video_duration > 599:
                return "length_too_long"

        if song_id not in [s[0] for s in songs]:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                ydl.extract_info(song_url, download=True)

            for file in os.listdir('./'):
                if file.endswith('.mp3'):
                    try:
                        os.rename(file, f'./data/songs/{song_id}.mp3')
                    except FileExistsError:
                        log.warning(f"File {song_id} already exists in ./data/songs/")

            self.c.execute(f'INSERT INTO songs_cache values("{song_id}","{video_title}")')
            self.db.commit()

        if not video_title:
            for s in songs:
                if s[0] == song_id:
                    log.debug("s1", s[1])
                    video_title = s[1]
        log.debug(video_title)

        if voice:
            r_dict = {
                "status": "",
                "video_title": video_title,
                "song_id": song_id,
                "video_duration": video_duration,
                "video_banner": video_banner
            }
            if not voice.is_playing():
                self.queues.add_song(song_id, video_title, guild_id=voice.guild.id)
                self.next_song(voice)
                voice.source = discord.PCMVolumeTransformer(voice.source, volume=self.volume)
                r_dict["status"] = "now_playing"
                return r_dict
            else:
                self.queues.add_song(song_id, video_title, guild_id=voice.guild.id)
                r_dict["status"] = "added_to_queue"
                return r_dict

    """
    @tasks.loop(seconds=15)
    async def save_queue(self):
        log.debug("Saving queue")
        with open('./data/queue.json', 'w') as f:
            json.dump(self.queues, f, indent=4)

    @tasks.loop(seconds=15)
    async def get_queue(self):
        log.debug("Getting queue")
        with open('./data/queue.json', 'r') as f:
            self.queues = json.load(f)
        
        self.queuelist = self.queues.get_queue(guild_id=voice.guild.id)

    @save_queue.before_loop
    async def before_save_queue(self):
        await self.client.wait_until_ready()
    """



    @music.command(name="setup", description="Setup the music channel")
    async def m_setup(self, ctx):
        m_embed = discord.Embed(title="Music",
                                description="Paste a **YouTube URL** or **Song Name** into this Channel.",
                                color=embed_color, url=embed_url)
        m_embed.set_image(url="https://media.discordapp.net/attachments/988082459658813490/1004316068476624977/music_banner.jpg")
        m_embed.set_footer(text=embed_footer)
        m_embed.set_author(name=embed_header, icon_url=embed_icon)
        await ctx.send(embed=m_embed)



    @music.command()
    async def play(self, ctx, song: str):
        await ctx.defer()
        song = await input_sanitizer(song)
        log.debug(song)
        start_time = time.time()

        m_embed = discord.Embed(title="Music", color=embed_color, url=embed_url)
        m_embed.set_footer(text=embed_footer)
        m_embed.set_author(name=embed_header, icon_url=embed_icon)

        # check valid YouTube url with regex
        if not re.search(r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|.+\?v=)?([^&=%\n]*)',song):
            results = YoutubeSearch(song, max_results=1).to_dict()
            if not results:
                m_embed.add_field(name="Error", value="No results found!", inline=False)
                await ctx.followup.send(embed=m_embed)
                return
            song = f"https://www.youtube.com/watch?v={results[0]['id']}"
            log.debug(song)

        # key | title | song_id | duration
        res = await self.player(ctx, song)

        if res == "length_too_long":
            m_embed.add_field(name="Error", value="Song is too long!", inline=False)
            await ctx.followup.send(embed=m_embed)
            return

        video_duration = str(round(int((res["video_duration"]))/60, 2)).replace(".", ":")

        log.debug(f"Took {round(time.time() - start_time, 2)} seconds to fetch and play song")
        log.debug(res)

        m_embed.set_image(url=res["video_banner"])
        if res["status"] == "now_playing":
            m_embed.add_field(name="Now Playing", value=f"{res['video_title']}")

        elif res["status"] == "added_to_queue":
            m_embed.add_field(name="Song added to queue!", value=f"*{res['video_title']}*", inline=False)
            
        m_embed.add_field(name="Duration", value=f"{video_duration}")
        await ctx.followup.send(embed=m_embed, view=ReplayButton(song, res['video_title']))

    @music.command()
    async def volume(self, ctx, volume: int):

        voice = get(self.client.voice_clients, guild=ctx.guild)
        if (not voice) or (not voice.is_playing()):
            await ctx.respond("I'm not playing anything right now!")
            return

        if 0 > volume > 100:
            await ctx.respond('Please provide volume as a number between 1 and 100.')
            return
        voice.source.volume = volume / 100
        self.volume = volume / 100
        await ctx.respond(f"Volume set to {volume}%")



    @music.command()
    async def loop(self, ctx):
        # self.queues.loop_song() TODO: loop again
        song = self.queues.current_song[1][0].replace("[", "").replace("'", "").replace("]", "")
        await ctx.respond(f'{song} will be looped!')



    @music.command()
    async def unloop(self, ctx):

        # self.queues.loop_song(ctx.guild.id) TODO: loop again
        song = self.queues.current_song[1].replace("[", "").replace("'", "").replace("]", "")
        await ctx.respond(f'{song} will no longer be looped!')



    @music.command(name="leave", description="Leave the voice channel")
    async def leave(self, ctx):
        voice = get(self.client.voice_clients, guild=ctx.guild)

        if voice.is_connected():
            await voice.disconnect()
        else:
            await ctx.respond("I am not connected to a voice channel")



    @music.command(name="pause", description="Pause the music")
    async def pause(self, ctx):
        voice = get(self.client.voice_clients, guild=ctx.guild)

        if voice.is_playing():
            voice.pause()
            await ctx.respond("Paused!", ephemeral=True)
        else:
            await ctx.respond("Currently no music is playing!", ephemeral=True)



    @music.command(name="resume", description="Resume the music")
    async def resume(self, ctx):
        voice = get(self.client.voice_clients, guild=ctx.guild)

        if voice.is_paused():
            voice.resume()
            await ctx.respond("Resumed!", ephemeral=True)
        else:
            await ctx.respond("The music is not paused!", ephemeral=True)



    @music.command(name="stop", description="Stops the music and clears the queue")
    async def stop(self, ctx):
        voice = get(self.client.voice_clients, guild=ctx.guild)
        if voice.is_playing():
            voice.stop()
            await ctx.respond("Stopped!", ephemeral=True)



    @music.command(name="queue", description="Shows the current queue")
    async def queuelist(self, ctx):

        m_embed = discord.Embed(title="Music", color=embed_color, url=embed_url)
        m_embed.set_footer(text=embed_footer)
        m_embed.set_author(name=embed_header, icon_url=embed_icon)

        if not self.queues.song_list:
            m_embed.add_field(name="Queue", value="No songs in queue", inline=False)
            await ctx.respond(embed=m_embed)
            return

        queue_list = [f"{self.queues.song_list[str(ctx.guild.id)][i][1]}" for i in range(len(self.queues.song_list[str(ctx.guild.id)]))][::-1]
        queue_list = "\n".join([f"{i + 1}. {queue_list[i]}".replace("[", "").replace("]", "").replace("'", "") for i in range(len(queue_list))])

        if queue_list:
            m_embed.add_field(name="Queue", value=queue_list, inline=False)
        else:
            m_embed.add_field(name="Queue", value="No songs in queue", inline=False)
        await ctx.respond(embed=m_embed)



    @music.command(name="skip", description="Skips the current song")
    async def skip(self, ctx):

        voice = get(self.client.voice_clients, guild=ctx.guild)

        if voice.is_playing():
            voice.stop()
            song = self.queues.skip_song(guild_id=ctx.guild.id)
            if song: voice.play(discord.FFmpegPCMAudio(f'./data/songs/{song[0]}.mp3'),
                                after=lambda x: self.next_song(voice))
            await ctx.respond("Skipped current song!")
        else:
            await ctx.respond("No music is playing")




    #
    #   === Playlist Commands ===
    #

    @playlist.command()
    async def add(self, ctx, playlist_name: str):
        playlist_name = await input_sanitizer(playlist_name)
        self.c.execute(f"CREATE TABLE IF NOT EXISTS playlists_{ctx.author.id} (playlist TEXT, song_id TEXT, titles TEXT)")
        self.db.commit()

        if not self.queues.current_song[0]:
            await ctx.respond("No song is currently playing")
            return

        playlist_name = playlist_name.replace(";", "").replace('"', '').replace("'", "").replace("`", "")

        self.c.execute(f'SELECT song_id FROM playlists_{ctx.author.id} WHERE song_id="{self.queues.current_song[0]}" AND playlist="{playlist_name}"')
        res = self.c.fetchone()
        if res is not None:
            log.debug(res)
            await ctx.respond("Already added!")
            return

        self.c.execute(f'INSERT INTO playlists_{ctx.author.id} (playlist, song_id, titles) values("{playlist_name}", "{self.queues.current_song[0]}", "{self.queues.current_song[1][0]}")')
        self.db.commit()

        p_embed = discord.Embed(title="Music | Playlist", color=embed_color, url=embed_url, description=f"Adding to the playlist was successful!")
        p_embed.add_field(name="Song", value=f"`{self.queues.current_song[1]}`", inline=False)
        p_embed.add_field(name="Playlist", value=f"`{playlist_name}`", inline=False)
        p_embed.set_footer(text=embed_footer)
        p_embed.set_author(name=embed_header, icon_url=embed_icon)
        await ctx.respond(embed=p_embed)


    @playlist.command(name="play")
    async def play_playlist(self, ctx, playlist_name: str):
        playlist_name = await input_sanitizer(playlist_name)
        self.c.execute(f"SELECT song_id, titles FROM playlists_{ctx.author.id} WHERE playlist='{playlist_name}'")
        songs = self.c.fetchall()

        if not songs:
            await ctx.respond(f"No songs in your `{playlist_name}` playlist! Try again.")
            return

        # voice = get(self.client.voice_clients, guild=ctx.guild)
        for song in songs:
            self.queues.add_song(song[0], song[1], ctx.guild.id)
            log.debug(self.queuelist)
        # self.next_song(voice)
        p_embed = discord.Embed(title="Music | Playlist", color=embed_color, url=embed_url,
                                description=f"Successfully added all songs from the playlist to the queue!")
        p_embed.add_field(name="Playlist", value=f"`{playlist_name}`", inline=False)
        p_embed.add_field(name="Number of Songs", value=f"`{len(songs)}`", inline=False)
        p_embed.set_footer(text=embed_footer)
        p_embed.set_author(name=embed_header, icon_url=embed_icon)
        await ctx.respond(embed=p_embed)


    @playlist.command(name="listsongs", description="Lists all the songs in a playlist")
    async def playlist_list(self, ctx, playlist_name: str):
        playlist_name = await input_sanitizer(playlist_name)
        self.c.execute(f"SELECT song_id, titles FROM playlists_{ctx.author.id} WHERE playlist='{playlist_name}'")
        songs = self.c.fetchall()

        if not songs:
            await ctx.respond("No songs in your songs playlist! Try again.")
            return


        song_list = [f"{i+1}. {song[1]}" for i, song in enumerate(songs)]
        song_list = "\n".join(song_list)

        m_embed = discord.Embed(title="Music | Playlist", color=embed_color, url=embed_url)
        m_embed.set_footer(text=embed_footer)
        m_embed.set_author(name=embed_header, icon_url=embed_icon)
        m_embed.add_field(name="Songs", value=song_list, inline=False)
        await ctx.respond(embed=m_embed)


    @playlist.command(name="list", description="Lists all your playlists")
    async def show_playlists(self, ctx):
        self.c.execute(f"SELECT playlist FROM playlists_{ctx.author.id}")
        playlists = self.c.fetchall()
        # remove duplicates
        playlists = list(set(playlists))

        if not playlists:
            await ctx.respond("No playlists found!")
            return
        m_embed = discord.Embed(title="Music | Playlist", color=embed_color, url=embed_url)
        m_embed.set_footer(text=embed_footer)
        m_embed.set_author(name=embed_header, icon_url=embed_icon)
        m_embed.add_field(name="Playlists", value="\n".join([f"`{playlist[0]}`" for playlist in playlists]), inline=False)
        await ctx.respond(embed=m_embed)



    @playlist.command(name="remove", description="Remove a song from a playlist")
    async def removesong(self, ctx, playlist_name: str):
        playlist_name = await input_sanitizer(playlist_name)
        self.c.execute(f'DELETE FROM playlists_{ctx.author.id} WHERE song_id="{self.queues.current_song[0]}" AND playlist="{playlist_name}"')
        self.db.commit()

        p_embed = discord.Embed(title="Music | Playlist", color=embed_color, url=embed_url, description=f"Deleting the song from the playlist was successful!")
        p_embed.add_field(name="Song", value=f"{self.queues.current_song[1]}", inline=False)
        p_embed.add_field(name="Playlist", value=f"`{playlist_name}`", inline=False)
        p_embed.set_footer(text=embed_footer)
        p_embed.set_author(name=embed_header, icon_url=embed_icon)
        await ctx.respond(embed=p_embed)


    @playlist.command(name="rename", description="Rename a playlist")
    async def rename_playlist(self, ctx, old_name: str, new_name: str):
        old_name = await input_sanitizer(old_name)
        new_name = await input_sanitizer(new_name)
        self.c.execute(f'UPDATE playlists_{ctx.author.id} SET playlist="{new_name}" WHERE playlist="{old_name}"')
        self.db.commit()

        p_embed = discord.Embed(title="Music | Playlist", color=embed_color, url=embed_url, description=f"Renaming the playlist was successful!")
        p_embed.add_field(name="Playlist", value=f"`{new_name}`", inline=False)
        p_embed.set_footer(text=embed_footer)
        p_embed.set_author(name=embed_header, icon_url=embed_icon)
        await ctx.respond(embed=p_embed)


    @playlist.command(name="delete", description="Delete a playlist")
    async def deleteall(self, ctx, playlist_name: str):
        playlist_name = await input_sanitizer(playlist_name)
        self.c.execute(f"SELECT titles FROM playlists_{ctx.author.id} WHERE playlist='{playlist_name}'")
        songs = len(self.c.fetchall())

        if songs == 0:
            await ctx.respond("There are no songs in this playlist or it doesn't exist!")
            return

        class Confirm(discord.ui.View): # Confirm Button Class
            def __init__(self):
                super().__init__()
                self.value = None
                self.author = ctx.author

            @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
            async def confirm_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
                if not interaction.user.id == self.author.id:
                    return await interaction.response.send_message("This button is not for you", ephemeral=True)
                self.value = True
                for child in self.children: # Disable all buttons
                    child.disabled = True
                await interaction.response.edit_message(view=self)
                self.stop()

            @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey)
            async def cancel_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
                if not interaction.user.id == self.author.id:
                    return await interaction.response.send_message("This button is not for you", ephemeral=True)
                self.value = False
                for child in self.children:
                    child.disabled = True
                await interaction.response.edit_message(view=self)
                self.stop()

        _view = Confirm()
        msg = await ctx.respond(f"You have {songs} in the {playlist_name} playlist! Are you sure you want to delete all songs from this playlist?", view=_view)

        await _view.wait()
        if _view.value is None:  # timeout
            await ctx.respond("Cancelled. Didn't respond in time", ephemeral=True)
            return
        if not _view.value:    # cancel
            await ctx.respond("Cancelled.", ephemeral=True)
            return

        self.c.execute(f'DELETE FROM playlists_{ctx.author.id} WHERE playlist="{playlist_name}"')
        self.db.commit()

        await msg.edit_original_message(f"The `{playlist_name}` was successfully deleted!")
        p_embed = discord.Embed(title="Music | Playlist", color=embed_color, url=embed_url, description=f"Deleting the playlist was successful!")
        p_embed.add_field(name="Playlist", value=f"`{playlist_name}`", inline=False)
        p_embed.add_field(name="Number of Songs", value=f"`{songs}`", inline=False)
        p_embed.set_footer(text=embed_footer)
        p_embed.set_author(name=embed_header, icon_url=embed_icon)
        await ctx.respond(embed=p_embed)




def setup(client):
    client.add_cog(Music(client))