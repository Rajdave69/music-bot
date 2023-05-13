import asyncio
import os
import random
import sqlite3
import string
import zipfile
import aiosqlite
import discord
import wavelink
import yt_dlp
from discord.ext import commands
from backend import log, embed_footer, embed_color, embed_url, get_user_playlists, vc_exists, embed_template, \
    error_template, increment_listens
from discord import app_commands

"""
Cog Playlists:
    This cog is responsible for handling all playlist related commands.
    
    Commands:
        playlist create <name> <visibility> - Creates a new playlist
        playlist delete <name> - Deletes a playlist
        playlist add <name> - Adds a song to a playlist (currently, the current playing song)
        playlist remove <name> - Removes a song from a playlist
        playlist play <name/id> - Plays a playlist
        playlist list <name/id> - Lists all songs in a playlist
        playlist playlists - Lists all playlists
        playlist info <name> - Shows info about a playlist
        playlist export <type> <name/id> - Exports a playlist to another format

"""


class Playlists(commands.GroupCog, name="playlist"):
    def __init__(self, client):
        self.client = client
        self.con = sqlite3.connect("./data/data.db")
        self.cur = self.con.cursor()

        """
        DB Structure:

        Table: playlists
         │
         ├─► id, TEXT, NOT NULL, UNIQUE
         │─► author, INTEGER, NOT NULL
         │─► name, INTEGER, NOT NULL
         │─► visibility, INTEGER, NOT NULL, DEFAULT=0
         └─► listens, INTEGER, NOT NULL, DEFAULT=0

        Table: playlist_data
         │
         ├─► id, TEXT, NOT NULL
         └─► song, TEXT, NOT NULL
        
        """

    @commands.Cog.listener()
    async def on_ready(self):
        log.info("Cog: Playlists.py loaded.")
        await self.client.tree.sync()

    @app_commands.command()
    @app_commands.describe(playlist_visibility="The visibility of the playlist. Can be either `public` or `private`.")
    @app_commands.choices(playlist_visibility=[
        discord.app_commands.Choice(name="public", value="1"),
        discord.app_commands.Choice(name="private", value="0")
    ])
    async def create(self, interaction, name: str,
                     playlist_visibility: str):  # todo test
        # remove unicode characters and allow only a-z, A-Z, 0-9, and _ in playlist names
        if not name.isalnum() and not name.replace("-", "").replace("_", "").isalnum():

            # noinspection PyCompatibility
            if (better_name := ''.join(e for e in name if e.isalnum() or e == '_')) == "":
                await interaction.followup.send(
                    embed=error_template("Playlist names can only contain letters, numbers, and underscores."))
            else:
                await interaction.followup.send(
                    embed=error_template("Invalid playlist name. Only a-z, 0-9, `-`, `_` are allowed.\n"
                                         f"Use `{better_name}` instead?"))

            return

        # Check if the name is too small or too big
        if 3 > len(name) > 32:
            await interaction.followup.send(
                embed=error_template("Playlist names must be from 3 to 32 characters long."))
            return

        # Check if the user already has a playlist with that name
        async with aiosqlite.connect('data/data.db') as db:
            async with db.execute("SELECT name FROM playlists WHERE author = ?", (interaction.user.id,)) as cursor:
                playlists = await cursor.fetchall()
                if name.strip().lower() in [i for i in playlists]:
                    await interaction.followup.send(embed=error_template("You already have a playlist with that name."))
                    return

        if name[0].isdigit():
            await interaction.followup.send(embed=error_template("Playlist names cannot start with a number."))
            return

        # Create a unique id with the first character being a number
        id_ = str(random.randint(0, 9))
        id_ += ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(7))

        try:
            self.cur.execute("INSERT INTO playlists VALUES (?, ?, ?, ?, ?)",
                             (id_, interaction.user.id, name.lower().strip(), int(playlist_visibility), 0))

        # If the ID already exists (The chance of this happening is 1 in 36^8!)
        except sqlite3.IntegrityError:

            while True:
                id_ = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(8))

                try:
                    self.cur.execute("INSERT INTO playlists VALUES (?, ?, ?, ?, ?)",
                                     (id_, interaction.user.id, name.lower().strip(), int(playlist_visibility), 0))
                    break

                # If the ID already exists AGAIN (The chance of this happening is 1 in 36^16!)
                except sqlite3.IntegrityError:
                    continue

        self.con.commit()
        embed = embed_template()
        embed.title = "Playlist"
        embed.description = f"Your playlist `{name}` has been created with the ID `{id_}`.\n" \
                            f"Use `/playlist add` to add songs to your playlist."  # TODO: add a command link

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="add", description="Add a song to a playlist.")
    @app_commands.autocomplete(playlist=get_user_playlists)
    async def add(self, interaction, playlist: str):
        await interaction.response.defer()
        log.debug(playlist)
        vc = interaction.guild.voice_client

        if not await vc_exists(interaction):
            return

        if interaction.user.voice.channel.id != vc.channel.id:
            return await interaction.followup.send(
                embed=error_template("You are not in the same voice channel as me."), ephemeral=True)

        self.cur.execute("SELECT id FROM playlists WHERE author = ? AND name = ?", (interaction.user.id, playlist))

        if (res := self.cur.fetchone()) is None:
            return await interaction.followup.send(
                embed=error_template("You don't have a playlist with that name."), ephemeral=True)

        id_ = res[0]

        self.cur.execute("SELECT * FROM playlist_data WHERE id = ? AND song = ?",
                         (id_, interaction.guild.voice_client.current.encoded))
        if self.cur.fetchone():
            await interaction.followup.send(embed=error_template("This song is already in the playlist."),
                                            ephemeral=True)
            return

        self.cur.execute("INSERT INTO playlist_data VALUES (?, ?)",
                         (id_, interaction.guild.voice_client.current.encoded))
        self.con.commit()

        embed = embed_template()
        embed.title = "Playlist"
        embed.description = f"Successfully added the song to your playlist."
        embed.add_field(name="Playlist", value=f"`{playlist}`", inline=False)
        embed.add_field(name="Song",
                        value=f"[{interaction.guild.voice_client.current.title}]({interaction.guild.voice_client.current.uri})",
                        inline=False)

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="delete", description="Delete a playlist.")
    @app_commands.autocomplete(playlist=get_user_playlists)
    async def delete(self, interaction, playlist: str):
        await interaction.response.defer()

        self.cur.execute("SELECT id FROM playlists WHERE author = ? AND name = ?",
                         (interaction.user.id, playlist))

        if not (res := self.cur.fetchone()):
            return await interaction.followup.send(embed=error_template("You don't have a playlist with that name."),
                                                   ephemeral=True)

        id_ = res[0]

        self.cur.execute("DELETE FROM playlist_data WHERE id = ?", (id_,))
        self.cur.execute("DELETE FROM playlists WHERE id = ?", (id_,))
        self.con.commit()

        embed = discord.Embed(title="Playlist", description=f"Playlist `{playlist}` deleted.",
                              url=embed_url, color=embed_color)
        embed.set_footer(text=embed_footer)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="list", description="List the songs in a playlist.")
    @app_commands.autocomplete(playlist=get_user_playlists)
    async def list_(self, interaction, playlist: str):
        await interaction.response.defer()

        self.cur.execute("SELECT id FROM playlists WHERE author = ? AND name = ?", (interaction.user.id, playlist))
        if not (res := self.cur.fetchone()):
            return await interaction.followup.send(
                embed=error_template("You don't have a playlist with that name."), ephemeral=True)

        id_ = res[0]

        self.cur.execute("SELECT song FROM playlist_data WHERE id = ?",
                         (id_,))
        song_ids = self.cur.fetchall()

        embed = discord.Embed(title="Playlist", description=f"Playlist `{playlist}` has {len(song_ids)} songs.",
                              url=embed_url, color=embed_color)
        embed.set_footer(text=embed_footer)

        counter = 1
        embed_list = []

        for song_id in song_ids:
            song = await wavelink.NodePool.get_node().build_track(cls=wavelink.YouTubeTrack, encoded=song_id[0])
            embed.add_field(name=f"`{song.title}`", value=song.uri, inline=False)

            counter += 1

            if counter == 10:   # TODO fix this
                counter = 1
                embed_list.append(embed.copy())
                embed.clear_fields()

        if len(embed_list) == 0:
            await interaction.followup.send(embed=error_template("This playlist is empty."), ephemeral=True)

        import paginator
        await paginator.Simple(timeout=60).start(interaction, embed_list)

    @app_commands.command(name="play", description="Play a playlist.")
    @app_commands.autocomplete(playlist=get_user_playlists)
    async def play(self, interaction, playlist: str, shuffle: bool = False):
        await interaction.response.defer()

        # Try to look for the playlist in the author's playlists
        self.cur.execute("SELECT id FROM playlists WHERE author = ? AND name = ?", (interaction.user.id, playlist))
        if not (res := self.cur.fetchone()):

            # If the playlist is not in the author's playlists, try to look for it in the global playlists
            self.cur.execute("SELECT id FROM playlists WHERE id = ? AND visibility = '1'", (playlist,))
            if not (res := self.cur.fetchone()):
                # If the playlist is not in the global playlists, return
                await interaction.followup.send(
                    embed=error_template("There is no playlist with that name or ID. Is it public?"), ephemeral=True)
                return

        id_ = res[0]
        await increment_listens(id_)

        if not interaction.guild.voice_client:
            try:
                await interaction.user.voice.channel.connect(cls=wavelink.Player)
                await interaction.guild.voice_client.set_volume(50)
            except AttributeError:
                return await interaction.followup.send("You are not connected to a voice channel.")

        self.cur.execute("SELECT song FROM playlist_data WHERE id = ?",
                         (id_,))
        song_ids = self.cur.fetchall()

        if shuffle:
            random.shuffle(song_ids)

        song_list = []

        for song_id in song_ids:
            song = await interaction.guild.voice_client.current_node.build_track(
                cls=wavelink.YouTubeTrack,
                encoded=song_id[0]
            )

            if not interaction.guild.voice_client.is_playing():
                await interaction.guild.voice_client.play(song)
            else:
                song_list.append(song)

        if song_list:
            interaction.guild.voice_client.queue.extend(song_list, atomic=False)

        embed = embed_template()
        embed.title = "Playlist"
        embed.description = f"Successfully added the playlist to the queue."
        embed.add_field(name="Playlist", value=f"`{playlist}`", inline=True)
        embed.add_field(name="Songs", value=f"`{len(song_ids)}`", inline=True)
        embed.add_field(name="Shuffle", value=f"`{shuffle}`", inline=True)

        await interaction.followup.send(embed=embed)

    @app_commands.command()
    @app_commands.autocomplete(playlist=get_user_playlists)
    async def remove(self, interaction, playlist: str):
        await interaction.response.defer()

        # check if playlist exists
        self.cur.execute("SELECT id FROM playlists WHERE author = ? AND name = ?", (interaction.user.id, playlist))
        if not (res := self.cur.fetchone()):
            return await interaction.followup.send(
                embed=error_template("You don't have a playlist with that name."), ephemeral=True)

        id_ = res[0]
        print(res)

        # check if the bot is playing anything
        if interaction.guild.voice_client:
            if interaction.guild.voice_client.is_playing():
                # check if the song is in the playlist
                self.cur.execute("SELECT * FROM playlist_data WHERE id = ? AND song = ?",
                                 (id_, interaction.guild.voice_client.current.encoded))
                if self.cur.fetchone():
                    # remove the song from the playlist
                    self.cur.execute("DELETE FROM playlist_data WHERE id = ? AND song = ?",
                                     (id_, interaction.guild.voice_client.current.encoded))
                    self.con.commit()

                    embed = embed_template()
                    embed.title = "Playlist"
                    embed.description = f"Removed the current song from the playlist."
                    embed.add_field(name="Playlist", value=f"`{playlist}`", inline=True)
                    embed.add_field(name="Song",
                                    value=f"[{interaction.guild.voice_client.current.title}]({interaction.guild.voice_client.current.uri})",
                                    inline=False)

                    await interaction.followup.send(embed=embed)

                else:
                    embed = error_template("The song that's currently playing is not already in the playl ist.")
                    embed.add_field(name="Playlist", value=f"`{playlist}`", inline=True)
                    embed.add_field(name="Song",
                                    value=f"[{interaction.guild.voice_client.current.title}]({interaction.guild.voice_client.current.uri})",
                                    inline=False)
                    await interaction.followup.send(embed=embed, ephemeral=True)

        else:  # TODO fix this
            self.cur.execute("SELECT song FROM playlist_data WHERE id = ?", (id_,))
            if not (songs := self.cur.fetchall()):
                return await interaction.followup.send(embed=error_template("The playlist is empty."), ephemeral=True)
            songs = [song[0] for song in songs]

            # create a context menu to select songs to remove
            option_list = []

            print(songs)
            for song in songs:
                # build song with wavelink
                node = wavelink.NodePool.get_node()
                song_obj = await node.build_track(cls=wavelink.YouTubeTrack, encoded=song)

                option_list.append(discord.SelectOption(
                    label=song_obj.title[:97] + "..." if len(str(song_obj.title)) > 100 else song_obj.title,
                    value=str(songs.index(song_obj.encoded)),
                    description=song_obj.author[:97] + "..." if len(str(song_obj.author)) > 100 else song_obj.author,
                ))

            select = discord.ui.Select(  # TODO playlist remove context menu
                placeholder="Select songs to remove.",
                options=option_list,
                min_values=1,
                max_values=len(option_list)
            )

            embed = embed_template()
            embed.title = "Playlist"
            embed.description = "Select the songs to remove from the playlist."
            embed.add_field(name="Playlist", value=f"`{playlist}`", inline=True)

            await interaction.followup.send(
                embed=embed,
                components=[select]
            )

            try:
                interaction = await self.client.wait_for("select_option", check=lambda i: i.user == interaction.user,
                                                         timeout=60)
            except asyncio.TimeoutError:
                return await interaction.followup.edit("Timed out.")

            # remove songs from playlist
            for option in interaction.values:
                self.cur.execute("DELETE FROM playlist_data WHERE id = ? AND song = ?", (id_, option))
                self.con.commit()

    @app_commands.command(name="info")
    @app_commands.autocomplete(playlist=get_user_playlists)
    async def info_(self, interaction, playlist: str):
        await interaction.response.defer()

        # Try to look for the playlist in the author's playlists
        self.cur.execute("SELECT id FROM playlists WHERE author = ? AND name = ?", (interaction.user.id, playlist))
        if not (res := self.cur.fetchone()):

            # If the playlist is not in the author's playlists, try to look for it in the global playlists
            self.cur.execute("SELECT id FROM playlists WHERE name = ? AND visibility = '1'", (playlist,))
            if not (res := self.cur.fetchone()):
                # If the playlist is not in the global playlists, return
                await interaction.followup.send("There is no playlist with that name or ID. Is it public?")
                return

        id_ = res[0]

        self.cur.execute("SELECT * FROM playlists WHERE id = ?",
                         (id_,))
        details = self.cur.fetchall()[0]
        self.cur.execute("SELECT song FROM playlist_data WHERE id = ?",
                         (id_,))
        song_ids = [song[0] for song in self.cur.fetchall()]
        log.debug(song_ids)
        log.debug(details)

        embed = embed_template()
        embed.title = "Playlist"
        embed.description = f"Details about the playlist."
        embed.add_field(name="Name", value=f"`{details[2]}`", inline=True)
        embed.add_field(name="Author", value=f"`{details[1]}`", inline=True)
        embed.add_field(name="ID", value=f"`{id_}`", inline=True)
        embed.add_field(name="Songs", value=f"`{len(song_ids)}`", inline=True)
        embed.add_field(name="Visibility", value=f"{'Public' if details[3] == 1 else 'Private'}", inline=True)
        embed.add_field(name="Listens", value=f"{details[4]}", inline=True)

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="playlists")
    async def playlists_(self, interaction, only_public: bool = False):
        # get all playlists of this user
        await interaction.response.defer()

        async with aiosqlite.connect("data/data.db") as con:
            if only_public:
                async with con.execute("SELECT id, author, visibility FROM playlists WHERE author = ? AND visibility "
                                       "= ?", (interaction.user.id, True)) as cur:
                    playlists = await cur.fetchall()
            else:
                async with con.execute("SELECT id, author, visibility FROM playlists WHERE author = ?",
                                       (interaction.user.id,)) as cur:
                    playlists = await cur.fetchall()

        embed = embed_template()
        embed.title = "Playlists"
        embed.description = f"You have {len(playlists)} {'public' if only_public else ''} playlists."

        # Create a field for each playlist
        for playlist in playlists:
            embed.add_field(
                name=f"`{playlist[0]}`",
                value=f"ID: `{playlist[1]}`\n"
                # Show visibility as "Public" or "Private", only if only_public is False
                      f"{'Visibility': `{'Private' if playlist[2] == 0 else 'Public'}` if not only_public else ''}",
                inline=False)

        await interaction.followup.send(embed=embed)

    @app_commands.command()
    @app_commands.autocomplete(playlist=get_user_playlists)
    async def visibility(self, interaction, playlist: str, visibility: bool):
        await interaction.response.defer()

        # check if playlist exists
        self.cur.execute("SELECT id FROM playlists WHERE author = ? AND name = ?", (interaction.user.id, playlist))
        if not (res := self.cur.fetchone()):
            return await interaction.followup.send(
                embed=error_template("You don't have a playlist with that name."), ephemeral=True
            )

        id_ = res[0]

        self.cur.execute("UPDATE playlists SET visibility = ? WHERE id = ?", (visibility, id_))
        self.con.commit()

        embed = embed_template()
        embed.title = "Playlist"
        embed.description = f"Successfully changed the visibility of the playlist."
        embed.add_field(name="Playlist", value=f"`{playlist}`", inline=True)
        embed.add_field(name="Visibility", value=f"`{visibility}`", inline=True)

        await interaction.followup.send(embed=embed)

    @app_commands.command()
    @app_commands.autocomplete(playlist=get_user_playlists)
    @app_commands.choices(export_format=[
            app_commands.Choice(name="MP3 - 192", value="mp3_192"),
            app_commands.Choice(name="MP3 - 320", value="mp3_320"),
    ])
    async def export(self, interaction, playlist: str, export_format: app_commands.Choice[str]):
        await interaction.response.defer()

        # check if playlist exists
        if playlist[0].isdigit():
            self.cur.execute("SELECT id FROM playlists WHERE id = ? AND visibility = '1'", (playlist,))
        else:
            self.cur.execute("SELECT id FROM playlists WHERE author = ? AND name = ?",
                             (interaction.user.id, playlist))

        if not (res := self.cur.fetchone()):
            return await interaction.followup.send(
                embed=error_template(
                    "You don't have a playlist with that name, or a playlist with that ID doesn't exist."
                ),
                ephemeral=True
            )

        id_ = res[0]

        self.cur.execute("SELECT song FROM playlist_data WHERE id = ?", (id_,))
        song_ids = [song[0] for song in self.cur.fetchall()]

        match export_format.value.split("_")[0]:
            case "mp3":
                # build the song objects
                songs = []
                for song_id in song_ids:
                    song = await wavelink.NodePool.get_node().build_track(cls=wavelink.YouTubeTrack, encoded=song_id)
                    songs.append(song.uri)
                    print(song.uri)

                # download the songs with the song metadata
                yt_options = {
                    "format": "bestaudio/best",
                    "outtmpl": "%(title)s.%(ext)s",
                    "noplaylist": True,
                    "postprocessors": [{
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "320" if export_format == "mp3_320" else "192",
                    }],
                    # make it quiet
                    "quiet": True,
                }

                import threading

                def download_song(song_uri):
                    with yt_dlp.YoutubeDL(yt_options) as ydl:
                        ydl.extract_info(song_uri, download=True)

                threads = []

                for song in songs:
                    thread = threading.Thread(target=download_song, args=(song,))
                    thread.start()
                    threads.append(thread)

                for thread in threads:
                    thread.join()

                for file in os.listdir():
                    if file.endswith(".mp3"):
                        await interaction.channel.send(file=discord.File(file))

                await interaction.followup.send(
                    embed=embed_template(
                        title="Export",
                        description="Successfully exported the playlist."
                    )
                )





async def setup(client):
    await client.add_cog(Playlists(client))
