import random
import sqlite3
import discord
import wavelink
from discord.ext import commands
from backend import log, embed_footer, embed_color, embed_url, get_user_playlists
from discord.commands import option


class Playlists(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.con = sqlite3.connect("./data/data.db")
        self.cur = self.con.cursor()

    playlists = discord.SlashCommandGroup("playlist", "Playlist commands")

    @playlists.command()
    @option("playlist",
            description="The playlist to play.",
            autocomplete=get_user_playlists
            )
    async def add(self, ctx, playlist):
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
            await ctx.respond("This song is already in the playlist.")
            return

        self.cur.execute("INSERT INTO playlists VALUES (?, ?, ?)", (ctx.author.id, playlist, vc.source.uri))
        self.con.commit()
        embed = discord.Embed(title="Playlist", description=f"Song added to `{playlist}`.",
                              url=embed_url, color=embed_color)
        embed.set_footer(text=embed_footer)
        await ctx.respond(embed=embed)

    @playlists.command()
    @option("playlist",
            description="The playlist to play.",
            autocomplete=get_user_playlists
            )
    async def delete(self, ctx, name):
        self.cur.execute("DELETE FROM playlists WHERE name = ? AND author = ?", (name, ctx.author.id))
        self.con.commit()

        embed = discord.Embed(title="Playlist", description=f"Playlist `{name}` deleted.",
                              url=embed_url, color=embed_color)
        embed.set_footer(text=embed_footer)
        await ctx.respond(embed=embed)

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
        if not ctx.voice_client:
            try:
                await ctx.author.voice.channel.connect(cls=wavelink.Player)
            except AttributeError:
                return await ctx.respond("You are not connected to a voice channel.")

        self.cur.execute("SELECT song FROM playlists WHERE name = ? AND author = ?", (playlist.strip(), ctx.author.id))
        songs = self.cur.fetchall()
        if shuffle:
            random.shuffle(songs)

        for song in songs:
            song = await wavelink.YouTubeTrack.search(song[0], return_first=True)
            if not ctx.voice_client.is_playing():
                await ctx.voice_client.play(song)
            else:
                ctx.voice_client.queue.put(song)
        await ctx.respond(f"Added {len(songs)} songs to the queue.")

    @playlists.command()
    async def remove(self, ctx, playlist):
        pass


def setup(client):
    client.add_cog(Playlists(client))
