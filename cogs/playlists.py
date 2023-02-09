import random
import sqlite3
import string
import discord
import wavelink
from discord.ext import commands
from backend import log, embed_footer, embed_color, embed_url, get_user_playlists, vc_exists, embed_template, \
    error_template, increment_listens
from discord.commands import option

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

"""


class Playlists(commands.Cog):
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

    playlists = discord.SlashCommandGroup("playlist", "Playlist commands")

    @commands.Cog.listener()
    async def on_ready(self):
        log.info("Cog: Playlists.py loaded.")

    @playlists.command()
    async def create(self, ctx, name: str,
                     playlist_visibility: discord.Option(choices=[
                         discord.OptionChoice(name="Private", value="0"),
                         discord.OptionChoice(name="Public", value="1")
                     ])
                     ):
        # remove unicode characters and allow only a-z, A-Z, 0-9, and _ in playlist names
        if not name.isalnum() and not name.replace("-", "").replace("_", "").isalnum():

            # noinspection PyCompatibility
            if (better_name := ''.join(e for e in name if e.isalnum() or e == '_')) == "":
                await ctx.respond(embed=error_template("Playlist names can only contain letters, numbers, and underscores."))
            else:
                await ctx.respond(embed=error_template("Invalid playlist name. Only a-z, 0-9, `-`, `_` are allowed.\n"
                                  f"Use `{better_name}` instead?"))

            return

        # Check if the name is too small or too big
        if 3 > len(name) > 32:
            await ctx.respond(embed=error_template("Playlist names must be from 3 to 32 characters long."))
            return

        # Check if the user already has a playlist with that name
        if name in await get_user_playlists(ctx):
            await ctx.respond(embed=error_template("You already have a playlist with that name."))
            return

        if name[0].isdigit():
            await ctx.respond(embed=error_template("Playlist names cannot start with a number."))
            return

        # Create a Unique ID for the playlist, and add it to the database which starts with a number
        id_ = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(8))

        # make sure it starts with a number # TODO: make this better
        while not id_[0].isdigit():
            id_ = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(8))

        try:
            self.cur.execute("INSERT INTO playlists VALUES (?, ?, ?, ?, ?)",
                             (id_, ctx.author.id, name.lower().strip(), int(playlist_visibility), 0))

        # If the ID already exists (The chance of this happening is 1 in 36^8!)
        except sqlite3.IntegrityError:

            while True:
                id_ = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(8))

                try:
                    self.cur.execute("INSERT INTO playlists VALUES (?, ?, ?, ?)",
                                     (id_, ctx.author.id, name.lower().strip(), int(playlist_visibility)))
                    break

                # If the ID already exists AGAIN (The chance of this happening is 1 in 36^16!)
                except sqlite3.IntegrityError:
                    continue

        self.con.commit()
        await ctx.respond(f"Created playlist `{name.lower().strip()}`.")
    @option("playlist",
            description="The playlist to play.",
            autocomplete=get_user_playlists
            )
    async def add(self, ctx, playlist):
        await ctx.defer()
        vc = ctx.voice_client

        if not vc:
            try:
                vc = await ctx.author.voice.channel.connect(cls=wavelink.Player)
            except AttributeError:
                return await ctx.respond("You are not connected to a voice channel.")

        if ctx.author.voice.channel.id != vc.channel.id:
            return await ctx.respond("You are not in the same voice channel as me.")

        self.cur.execute("SELECT * FROM playlists WHERE name = ? AND song = ?",
                         (playlist, ctx.voice_client.source.uri))
        if self.cur.fetchone():
            await ctx.followup.send("This song is already in the playlist.")
            return

        self.cur.execute("INSERT INTO playlists VALUES (?, ?, ?)", (ctx.author.id, playlist, vc.source.uri))
        self.con.commit()
        embed = discord.Embed(title="Playlist", description=f"Song added to `{playlist}`.",
                              url=embed_url, color=embed_color)
        embed.set_footer(text=embed_footer)
        await ctx.followup.send(embed=embed)

    @playlists.command()
    @option("playlist",
            description="The playlist to play.",
            autocomplete=get_user_playlists
            )
    async def delete(self, ctx, name):
        await ctx.defer()
        self.cur.execute("DELETE FROM playlists WHERE name = ? AND author = ?", (name, ctx.author.id))
        self.con.commit()

        embed = discord.Embed(title="Playlist", description=f"Playlist `{name}` deleted.",
                              url=embed_url, color=embed_color)
        embed.set_footer(text=embed_footer)
        await ctx.followup.send(embed=embed)

    @playlists.command()
    @option("playlist",
            description="The playlist to play.",
            autocomplete=get_user_playlists
            )
    async def list_(self, ctx, playlist):
        await ctx.defer()
        self.cur.execute("SELECT song FROM playlists WHERE name = ? AND author = ?", (playlist.strip(), ctx.author.id))
        songs = self.cur.fetchall()
        embed = discord.Embed(title="Playlist", description=f"Playlist `{playlist}` has {len(songs)} songs.",
                              url=embed_url, color=embed_color)
        for song in songs:
            song = await wavelink.YouTubeTrack.search(song[0], return_first=True)
            embed.add_field(name=f"`{song.title}`", value=song.uri, inline=False)
        embed.set_footer(text=embed_footer)
        await ctx.followup.send(embed=embed)

    @playlists.command()
    @option("playlist",
            description="The playlist to play.",
            autocomplete=get_user_playlists
            )
    async def play(self, ctx, playlist: str, shuffle: bool = False):
        await ctx.defer()
        if not ctx.voice_client:
            try:
                await ctx.author.voice.channel.connect(cls=wavelink.Player)
            except AttributeError:
                return await ctx.followup.send("You are not connected to a voice channel.")

        self.cur.execute("SELECT song FROM playlists WHERE name = ? AND author = ?", (playlist.strip(), ctx.author.id))
        songs = self.cur.fetchall()
        if shuffle:
            random.shuffle(songs)

        for song in songs:
            song = await wavelink.YouTubeTrack.search(song[0], return_first=True)    # TODO: Implement use of partial-track object from wavelink
            if not ctx.voice_client.is_playing():
                await ctx.voice_client.play(song)
            else:
                ctx.voice_client.queue.put(song)
        await ctx.followup.send(f"Added {len(songs)} songs to the queue.")

    @playlists.command()
    async def remove(self, ctx, playlist):
        pass


def setup(client):
    client.add_cog(Playlists(client))
