import datetime
import math
import re
import typing

import disnake
import humanize
from disnake.ext import commands
from disnake.ext.commands.params import Param

import wavelink
from bot import Bot
from utils.exceptions import NoChannelProvided
from utils.helpers import LyricsPaginator
from utils.MusicPlayerInteraction import Player, QueuePages, Track
from utils.views import FilterView, SongSelectionView
from wavelink.errors import FilterInvalidArgument, NoPermissions
from lyricsgenius import Genius
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

import humanize
from utils.checks import voter

url_regex = re.compile(r"https?://(?:www\.)?.+")

youtube_url_regex = re.compile(
    r"https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)(?P<id>[\w-]{11})(?:&.+)?$"
)

SOUNDCLOUD_URL_REGEX = re.compile(
    r"^(https?:\/\/)?(www.)?(m\.)?soundcloud\.com\/[\w\-\.]+(\/)+[\w\-\.]+/?$"
)

SPOTIFY_URL_REGEX = re.compile(
    r"https?://open.spotify.com/(?P<type>album|playlist|track)/(?P<id>[a-zA-Z0-9]+)"
)

APPLEMUSIC_URL_REGEX = re.compile(
    r"https?://(?:www\.)?music\.apple\.com/[a-zA-Z0-9]+(/[a-zA-Z0-9]+)?$"
)


async def searchSpotifyPlaylist(self, player, interaction, query):
    playlist_link = query
    playlist_URI = playlist_link.split("/")[-1].split("?")[0]
    if ((self.spotify.playlist(playlist_URI))["description"]).startswith("<a"):
        desc = ""
    else:
        desc = f"`Description` - {(self.spotify.playlist(playlist_URI))['description']}"
    embed = disnake.Embed(
        title="Spotify Playlist",
        description="Adding your playlist to the queue!\n\n"
        + f"`Title` - {(self.spotify.playlist(playlist_URI))['name']}"
        + "\n"
        + f"{desc}"
        + "\n"
        + f"`Followers` - {(self.spotify.playlist(playlist_URI))['followers']['total']}",
        colour=53759,
    )
    embed.set_thumbnail(url=(self.spotify.playlist(playlist_URI))["images"][0]["url"])
    embed.set_author(
        name=self.bot.user.display_name, icon_url=f"{self.bot.user.avatar.url}"
    )
    embed.set_footer(
        text=f"Requested by {interaction.author.display_name}",
        icon_url=interaction.author.avatar.url,
    )
    await interaction.followup.send(embed=embed)
    for track in self.spotify.playlist_tracks(playlist_URI)["items"]:
        title = track["track"]["name"]
        artist = track["track"]["artists"][0]["name"]
        tracks = await self.bot.wavelink.get_tracks(f"ytsearch:{title} {artist}")
        if not track is None:
            track = Track(tracks[0].id, tracks[0].info, requester=interaction.author)
            await interaction.edit_original_message(
                content=f"\n{self.bot.icons['headphones']} Enqueued `{track.title}` to the Queue\n"
            )
            await player.queue.put(track)
        if not player.is_playing:
            await player.play_next_song()
            continue


class Music(commands.Cog, wavelink.WavelinkMixin):
    """
    Your friendly music bot
    """

    def __init__(self, bot: Bot):
        self.bot = bot
        client_credentials_manager = SpotifyClientCredentials(
            client_id=self.bot.config.spotify["clientID"],
            client_secret=self.bot.config.spotify["clientSecret"],
        )
        self.spotify = spotipy.Spotify(
            client_credentials_manager=client_credentials_manager
        )
        self.LyricsGenius = Genius(self.bot.config.lyricGenius)

    async def cog_load(self) -> None:
        if not hasattr(self.bot, "wavelink"):
            self.bot.wavelink = wavelink.Client(bot=self.bot)

        self.bot.loop.create_task(self.start_nodes())

    async def start_nodes(self) -> None:
        await self.bot.wait_until_ready()

        if self.bot.wavelink.nodes:
            previous = self.bot.wavelink.nodes.copy()

            for node in previous.values():
                await node.destroy()

        nodes = {
            "node1": {
                "host": "lavalink.jaguar000212.repl.co",
                "port": 443,
                "rest_uri": "https://lavalink.jaguar000212.repl.co:443",
                "password": "wizardi's",
                "identifier": "Wizardi's",
                "region": "automatic",
                "secure": True,
            }
        }

        for n in nodes.values():
            await self.bot.wavelink.initiate_node(**n)

    @wavelink.WavelinkMixin.listener()
    async def on_node_ready(self, node: wavelink.Node) -> None:
        self.bot.logger.info(f"Node {node.identifier} is running!", __name="Music Bot")

    @wavelink.WavelinkMixin.listener("on_track_stuck")
    @wavelink.WavelinkMixin.listener("on_track_end")
    @wavelink.WavelinkMixin.listener("on_track_exception")
    async def on_player_stop(self, node: wavelink.Node, payload) -> None:
        await payload.player.play_next_song()

    @commands.Cog.listener("on_voice_state_update")
    async def DJ_assign(
        self,
        member: disnake.Member,
        before: disnake.VoiceState,
        after: disnake.VoiceState,
    ):
        if member.bot:
            return

        player: Player = self.bot.wavelink.get_player(member.guild.id, cls=Player)

        if not player.channel_id or not player.context:
            player.node.players.pop(member.guild.id)
            return

        channel: disnake.VoiceChannel = await self.bot.fetch_channel(player.channel_id)

        if member == player.dj and after.channel is None:
            for m in channel.members:
                if m.bot:
                    continue
                else:
                    player.dj = m
                    return

        elif after.channel == channel and player.dj not in channel.members:
            player.dj = member

    async def cog_before_slash_command_invoke(
        self, interaction: disnake.ApplicationCommandInteraction
    ) -> None:

        music_player: Player = self.bot.wavelink.get_player(
            interaction.guild.id, cls=Player, context=interaction
        )
        channel = 0
        try:
            channel = self.bot.get_channel(int(music_player.channel_id))
        except:
            pass
        if not channel:
            return

    def vote_check(self, interaction: disnake.ApplicationCommandInteraction):

        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )
        channel = self.bot.get_channel(int(player.channel_id))
        required = math.ceil((len(channel.members) - 1) / 2.5)

        if interaction.application_command.name == "stop":
            if len(channel.members) == 3:
                required = 2

        return required

    def is_author(self, interaction: disnake.ApplicationCommandInteraction):

        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        return (
            player.dj == interaction.author
            or interaction.author.guild_permissions.manage_guild
            or interaction.author.guild_permissions.moderate_members
        )

    async def connect(
        self,
        interaction: disnake.ApplicationCommandInteraction,
        channel: typing.Union[disnake.VoiceChannel, disnake.StageChannel] = None,
    ) -> None:

        music_player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        channel = getattr(interaction.author.voice, "channel", channel)
        if channel is None:
            raise NoChannelProvided

        await music_player.connect(channel.id)
        if not music_player.is_connected:
            raise NoPermissions(
                f"`No permissions to connect/speak in` {channel.mention}."
            )

        embed = disnake.Embed(
            description=f"Joined {channel.mention}", color=disnake.Colour.green()
        )
        await interaction.channel.send(embed=embed)

    # @voter()


    @commands.guild_only()
    @commands.slash_command(
        name="player-play", description="Play or queue a song with the given query."
    )
    async def play(
        self,
        interaction: disnake.ApplicationCommandInteraction,
        name: str = Param(description="Search your song...."),
    ):
        await interaction.response.defer()
        query = name
        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        if not player.is_connected:
            await self.connect(interaction)

        if url_regex.match(query):
            query = query.strip("<>")

            if SPOTIFY_URL_REGEX.match(query):
                await searchSpotifyPlaylist(self, player, interaction, query)

            elif youtube_url_regex.match(query):
                tracks = await self.bot.wavelink.get_tracks(query)
                if not tracks:
                    return await interaction.edit_original_message(
                        embed=disnake.Embed(
                            description=f"{self.bot.icons['redtick']} No songs were found with that query. "
                            f"Please try again.",
                        )
                    )

                if isinstance(tracks, wavelink.TrackPlaylist):
                    for track in tracks.tracks:
                        track = Track(
                            track.id, track.info, requester=interaction.author
                        )
                        await player.queue.put(track)

                    return await interaction.edit_original_message(
                        embed=disnake.Embed(
                            description=f'```ini\nAdded the playlist {tracks.data["playlistInfo"]["name"]}'
                            f" with {len(tracks.tracks)} songs to the queue.\n```",
                        ).set_footer(
                            text=f"Requested by {interaction.author.name}",
                            icon_url=interaction.author.display_avatar.url,
                        )
                    )

                else:
                    track = Track(
                        tracks[0].id, tracks[0].info, requester=interaction.author
                    )
                    await interaction.edit_original_message(
                        embed=disnake.Embed(
                            f"\n{self.bot.icons['headphones']} Enqueued `{track.title}` to the Queue\n"
                        )
                    )
                    await player.queue.put(track)

                if not player.is_playing:
                    await player.play_next_song()
                    return
            else:
                return await interaction.edit_original_message(
                    embed=disnake.Embed(
                        description=f"{self.bot.icons['redtick']} This source is not supported yet"
                    )
                )

        else:
            query = f"ytsearch:{query}"
            tracks = await self.bot.wavelink.get_tracks(query)
            if not tracks:
                return await interaction.edit_original_message(
                    embed=disnake.Embed(
                        description=f"{self.bot.icons['redtick']} No songs were found with that query. "
                        f"Please try again.",
                    )
                )
            else:
                await interaction.edit_original_message(
                    embed=disnake.Embed(
                        description=f"\n{self.bot.icons['headphones']} Please select a song to play.\n"
                    ),
                    view=SongSelectionView(
                        tracks=tracks[:10],
                        player=player,
                        bot=self.bot,
                        interaction=interaction,
                    ),
                )
                return

    @commands.guild_only()
    @commands.slash_command(
        name="player-pause", description="Pause the current playing song."
    )
    async def pause(self, interaction: disnake.ApplicationCommandInteraction):
        await interaction.response.defer()

        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        if not player.is_connected:
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `Bot is not connected.`",
                ),
                delete_after=5,
            )

        if not player.is_playing:
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `There is no track playing right now.`",
                ),
                delete_after=5,
            )

        if player.is_paused:
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `The player is already paused.`",
                ),
                delete_after=5,
            )

        if self.is_author(interaction):
            await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} `{player.dj}` has paused the player.",
                ),
                delete_after=5,
            )
            player.pause_votes.clear()

            return await player.set_pause(True)

        required = self.vote_check(interaction)
        player.pause_votes.add(interaction.author)

        if len(player.pause_votes) >= required:
            await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['check']} `Vote to pause passed. Pausing player.`",
                ),
                delete_after=5,
            )
            player.pause_votes.clear()
            await player.set_pause(True)
        else:
            await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} `{interaction.author} has voted to pause the player.`",
                ),
            )

    @commands.guild_only()
    @commands.slash_command(
        name="player-resume", description="Resumes a currently paused song."
    )
    async def resume(self, interaction: disnake.ApplicationCommandInteraction):
        await interaction.response.defer()
        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        if not player.is_connected:
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `Bot is not connected.`",
                ),
                delete_after=5,
            )

        if not player.is_playing:
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `There is no track playing right now.`",
                )
            )

        if not player.is_paused:
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `The player is not paused.`",
                ),
                delete_after=5,
            )

        if self.is_author(interaction):
            await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} `{player.dj}` has resumed the player.",
                ),
                delete_after=5,
            )
            player.resume_votes.clear()

            return await player.set_pause(False)

        required = self.vote_check(interaction)
        player.resume_votes.add(interaction.author)

        if len(player.resume_votes) >= required:
            await interaction.send(
                embed=disnake.Embed(
                    description="Vote to resume passed. Resuming player.",
                    delete_after=5,
                )
            )
            player.resume_votes.clear()
            await player.set_pause(False)
        else:
            await interaction.send(
                embed=disnake.Embed(
                    description=f"{interaction.author} has voted to resume the song.",
                )
            )

    @commands.guild_only()
    @commands.slash_command(
        name="player-skip", description="Skip the currently playing song."
    )
    async def skip(self, interaction: disnake.ApplicationCommandInteraction):
        await interaction.response.defer()
        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        if not player.is_connected:
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `Bot is not connected.`",
                ),
                delete_after=5,
            )

        if self.is_author(interaction):
            await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} `{player.dj}` has skipped the song."
                ),
                delete_after=5,
            )
            player.skip_votes.clear()

            return await player.stop()

        required = self.vote_check(interaction)
        player.skip_votes.add(interaction.author)

        if len(player.skip_votes) >= required:
            await interaction.send(
                embed=disnake.Embed(description="Vote to skip passed. Skipping song."),
                delete_after=5,
            )
            player.skip_votes.clear()
            await player.stop()
        else:
            await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} `{interaction.author}` has voted to skip the song.",
                ),
            )

    @commands.guild_only()
    @commands.slash_command(
        name="player-stop",
        description="Stop the currently playing song and the music player.",
    )
    async def stop(self, interaction: disnake.ApplicationCommandInteraction):
        await interaction.response.defer()
        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        if not player.is_connected:
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `Bot is not connected.`",
                ),
                delete_after=5,
            )

        if not player.is_playing:
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `There is no track playing right now.`",
                )
            )

        if self.is_author(interaction):
            await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} `{player.dj}` has stopped the player.",
                ),
                delete_after=5,
            )

        required = self.vote_check(interaction)
        player.stop_votes.add(interaction.author)

        if len(player.stop_votes) >= required:
            await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} Vote passed, stopping the player.",
                )
            )
            await player.teardown()
        else:
            await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} `{interaction.author}` has voted to stop the song.",
                )
            )

    @commands.guild_only()
    @commands.slash_command(
        name="player-disconnect",
        description="Disconnect the bot and stop the music player.",
    )
    async def disconnect(self, interaction: disnake.ApplicationCommandInteraction):
        await interaction.response.defer()
        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        if not player.is_connected:
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `Bot is not connected.`",
                ),
                delete_after=5,
            )

        if not self.is_author(interaction):
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} Only `{player.dj}` can disconnect the player.",
                ),
                delete_after=5,
            )
        await interaction.send(
            embed=disnake.Embed(
                description=f"{self.bot.icons['info']} `{player.dj}` has disconnected the player.",
            )
        )
        await player.teardown()

    @commands.guild_only()
    @commands.slash_command(
        name="player-volume",
        description="Change the players volume, between 1 and 100.",
    )
    async def volume(
        self,
        interaction: disnake.ApplicationCommandInteraction,
        vol: int = commands.Range[1, 100],
    ):
        await interaction.response.defer()
        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        if not player.is_connected:
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `Bot is not connected.`",
                )
            )

        if not player.is_playing:
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `There is no track playing right now.`",
                )
            )

        if not self.is_author(interaction):
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} Only the `{player.dj}` can change the volume of this song.",
                )
            )

        if not 0 < vol < 101:
            return await interaction.response.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} Please enter a value between 1 and 100."
                )
            )

        await player.set_volume(vol)
        await interaction.send(
            embed=disnake.Embed(
                description=f"{self.bot.icons['check']} Set the volume "
                f"to **{vol}%**",
            )
        )

    @commands.guild_only()
    @commands.slash_command(name="player-loop", description="Loop setting")
    async def loop(self, interaction: disnake.ApplicationCommandInteraction):
        await interaction.response.defer()
        pass

    @loop.sub_command(description="Loops the current playing track.")
    async def on(self, interaction: disnake.ApplicationCommandInteraction):

        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        if not player.is_connected:
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `Bot is not connected.`",
                ),
                delete_after=5,
            )

        if not player.is_playing:
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `There is no track playing right now.`",
                )
            )

        if not self.is_author(interaction):
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} Only the `{player.dj}` can loop this song.",
                )
            )

        if player.loop is False:
            await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['check']} Looped the current track.",
                )
            )
            player.loop = True
            return
        if player.loop is True:
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['check']} This track is on loop already.",
                )
            )

    @loop.sub_command(description="Stops looping the current playing track.")
    async def off(self, interaction: disnake.ApplicationCommandInteraction):
        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        if not player.is_connected:
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `Bot is not connected.`",
                ),
                delete_after=5,
            )

        if not player.is_playing:
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `There is no track playing right now.`",
                )
            )

        if not self.is_author(interaction):
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} Only the `{player.dj}` can loop this song.",
                )
            )

        if player.loop is False:
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['check']} The track is not on loop.",
                )
            )
        if player.loop is True:
            await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['check']} Un-looped the current track.",
                )
            )
            player.loop = False
            return

    @commands.guild_only()
    @commands.slash_command(
        name="player-lyrics", description="Show lyrics of the current playing song."
    )
    async def lyrics(self, interaction: disnake.ApplicationCommandInteraction, *, name):
        await interaction.response.defer()

        lyrics_query = self.LyricsGenius.search_song(name)
        if not lyrics_query is None:
            lyrics = lyrics_query.lyrics
            thmb = lyrics_query.song_art_image_thumbnail_url
            pag = LyricsPaginator(lyrics=lyrics, ctx=interaction, thumbnail=thmb)
            await pag.start()
        else:
            return await interaction.edit_original_message(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `Lyrics for this song is not found.`",
                ),
            )

    @commands.guild_only()
    @commands.slash_command(
        name="player-filter", description="Add a Filter to the player."
    )
    async def filter(self, interaction: disnake.ApplicationCommandInteraction):
        await interaction.response.defer()

        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        if not player.is_connected:
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `Bot is not connected.`",
                )
            )

        if not self.is_author(interaction):
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} Only the `{player.dj}` can add filters to the player.",
                )
            )

        if not player.is_playing:
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `There is no track playing right now.`",
                )
            )

        await interaction.send(
            content="Select a Filter:",
            view=FilterView(interaction=interaction, player=player),
        )

    @commands.guild_only()
    @commands.slash_command(
        name="player-create_filter", description="Create and set a custom filter."
    )
    async def create_filter(self, interaction: disnake.ApplicationCommandInteraction):
        await interaction.response.defer()
        pass

    @create_filter.sub_command(
        description="Add a custom filter, built from channel_mix."
    )
    async def channel_mix(
        self,
        interaction: disnake.ApplicationCommandInteraction,
        left_to_right: float = Param(
            description="Left to Right", default=0.5, ge=0.0, le=10.0
        ),
        right_to_left: float = Param(
            description="Right to Left", default=0.5, ge=0.0, le=10.0
        ),
        right_to_right: float = Param(
            description="Right to Right", default=0.5, ge=0.0, le=10.0
        ),
        left_to_left: float = Param(
            description="Left to Left", default=0.5, ge=0.0, le=10.0
        ),
    ):

        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        if not player.is_connected:
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `Bot is not connected.`",
                ),
                delete_after=5,
            )

        if not player.is_playing:
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `There is no track playing right now.`",
                )
            )

        if not self.is_author(interaction):
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} Only the `{player.dj}` can set the filter to the player.",
                )
            )
        try:
            filter_ = wavelink.BaseFilter.build_from_channel_mix(
                left_to_left=left_to_left,
                left_to_right=left_to_right,
                right_to_left=right_to_left,
                right_to_right=right_to_right,
            )
        except ValueError as e:
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `{e}`",
                )
            )

        await player.set_filter(filter_)
        await interaction.send(
            embed=disnake.Embed(
                description=f"{self.bot.icons['check']} `Filter set to:` {filter_.name}",
            )
        )

    @create_filter.sub_command(
        description="Build a custom Filter from base TimeScale Filter."
    )
    async def time_scale(
        self,
        interaction: disnake.ApplicationCommandInteraction,
        speed: float = Param(description="Speed", default=1.0, ge=0.0),
        pitch: float = Param(description="Pitch", default=1.0, ge=0.0),
        rate: float = Param(description="Rate", default=1.0, ge=0.0),
    ):

        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        if not player.is_connected:
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `Bot is not connected.`",
                ),
                delete_after=5,
            )

        if not player.is_playing:
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `There is no track playing right now.`",
                )
            )

        if not self.is_author(interaction):
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} Only the `{player.dj}` can set the filter to the player.",
                )
            )
        try:
            filter_ = wavelink.BaseFilter.build_from_timescale(
                speed=speed, pitch=pitch, rate=rate
            )
        except FilterInvalidArgument as e:
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `{e}`",
                )
            )

        await player.set_filter(filter_)
        await interaction.send(
            embed=disnake.Embed(
                description=f"{self.bot.icons['check']} `Filter set to:` {filter_.name}",
            )
        )

    @create_filter.sub_command(
        description="Build a custom Filter from base Distortion Filter."
    )
    async def distortion(
        self,
        interaction: disnake.ApplicationCommandInteraction,
        sin_offset: float = Param(description="Sin Offset", default=0.0),
        cos_offset: float = Param(description="Cos Offset", default=0.0),
        sin_scale: float = Param(description="Sin Scale", default=1.0),
        cos_scale: float = Param(description="Cos Scale", default=1.0),
        tan_offset: float = Param(description="Tan Offset", default=0.0),
        tan_scale: float = Param(description="Tan Scale", default=1.0),
        offset: float = Param(description="Offset", default=0.0),
        scale: float = Param(description="Scale", default=1.0),
    ):

        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        if not player.is_connected:
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `Bot is not connected.`",
                ),
                delete_after=5,
            )

        if not player.is_playing:
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `There is no track playing right now.`",
                )
            )

        if not self.is_author(interaction):
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} Only the `{player.dj}` can set the filter to the player.",
                )
            )

        filter_ = wavelink.BaseFilter.build_from_distortion(
            sin_offset=sin_offset,
            cos_offset=cos_offset,
            sin_scale=sin_scale,
            cos_scale=cos_scale,
            tan_offset=tan_offset,
            tan_scale=tan_scale,
            offset=offset,
            scale=scale,
        )

        await player.set_filter(filter_)
        await interaction.send(
            embed=disnake.Embed(
                description=f"{self.bot.icons['check']} `Filter set to:` {filter_.name}",
            )
        )

    @commands.guild_only()
    @commands.slash_command(
        name="player-queue", description="Display the player's queued songs."
    )
    async def queue(self, interaction: disnake.ApplicationCommandInteraction):
        await interaction.response.defer()
        pass

    @queue.sub_command(description="Display the player's queued songs.")
    async def show(self, interaction: disnake.ApplicationCommandInteraction):
        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        if not player.is_connected:
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `Bot is not connected.`",
                ),
                delete_after=5,
            )

        if player.queue.qsize() == 0:
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} There are no more songs "
                    f"in the queue.",
                ),
            )

        entries = []
        n = 0
        for track in player.queue._queue:
            n += 1
            entries.append(
                f"**{n}** `{track.title}` - `{track.author}` - {humanize.precisedelta(datetime.timedelta(milliseconds=track.length))}"
            )

        await interaction.send("Loading...")

        paginator = QueuePages(entries=entries, ctx=interaction)

        await paginator.start()

    @queue.sub_command(description="Clear the player's queued songs.")
    async def clear(self, interaction: disnake.ApplicationCommandInteraction):
        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        if not player.is_connected:
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `Bot is not connected.`",
                ),
                delete_after=5,
            )

        if player.queue.qsize() == 0:
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} Queue is empty.",
                )
            )

        if self.is_author(interaction):
            await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} `{player.dj}` has cleared the queue.",
                )
            )

            player.clear_votes.clear()
            player.queue.clear()
            return

        required = self.vote_check(interaction)
        player.clear_votes.add(interaction.author)

        if len(player.shuffle_votes) >= required:
            await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} Vote passed, clearing the queue.",
                )
            )

            player.clear_votes.clear()
            player.queue.clear()
        else:
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} `{interaction.author}` has voted to clear the queue.",
                )
            )

    @queue.sub_command(description="Remove a song from the queue by its index.")
    async def remove(
        self,
        interaction: disnake.ApplicationCommandInteraction,
        index: int = Param(description="The index of the song to remove."),
    ):

        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        if not player.is_connected:
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `Bot is not connected.`",
                )
            )

        if not player.is_playing:
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `There is no song playing right now.`",
                )
            )
        if player.queue.qsize() == 0:
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} There are no more songs "
                    f"in the queue.",
                ),
            )
        if not self.is_author(interaction):
            return await interaction.channel.send(
                embed=disnake.Embed(
                    description=f"Only {player.dj} can use this command.",
                )
            )
        if index > player.queue.qsize():
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `That is not a valid index.`",
                )
            )
        song_to_remove = index - 1
        player.queue.remove(song_to_remove)
        await interaction.send(
            embed=disnake.Embed(
                description=f"{self.bot.icons['check']} `Removed song from queue.`",
            )
        )

    @queue.sub_command(description="Shuffle the queue.")
    async def shuffle(self, interaction: disnake.ApplicationCommandInteraction):
        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        if not player.is_connected:
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `Bot is not connected.`",
                ),
                delete_after=5,
            )

        if player.queue.qsize() < 3:
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} Add more songs before shuffling.",
                )
            )

        if self.is_author(interaction):
            await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} `{player.dj}` has shuffled the queue.",
                )
            )

            player.shuffle_votes.clear()
            return player.queue.shuffle()

        required = self.vote_check(interaction)
        player.shuffle_votes.add(interaction.author)

        if len(player.shuffle_votes) >= required:
            await interaction.channel.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} Vote passed, shuffling songs.",
                )
            )

            player.shuffle_votes.clear()
            player.queue.shuffle()
        else:
            return await interaction.channel.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} `{interaction.author}` has voted to shuffle the queue.",
                )
            )

    @commands.guild_only()
    @commands.slash_command(
        name="player-nowplaying", description="Show the current playing song"
    )
    async def nowplaying(self, interaction: disnake.ApplicationCommandInteraction):
        await interaction.response.defer()
        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        if not player.is_connected:
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `Bot is not connected.`",
                )
            )

        if not player.is_playing:
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `There is no song playing right now.`",
                )
            )

        embed = await player.make_song_embed()  # shows the song embed.
        await interaction.send(embed=embed, ephemeral=True)

    @commands.guild_only()
    @commands.slash_command(
        name="player-save", description="Save the current playing song in your dms."
    )
    async def save(self, interaction: disnake.ApplicationCommandInteraction):
        await interaction.response.defer()
        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        if not player.is_connected:
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `Bot is not connected.`",
                )
            )

        if not player.is_playing:
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `There is no song playing right now.`",
                )
            )

        embed = await player.make_song_embed()
        await interaction.send(
            embed=disnake.Embed(description="I have dm'ed you!"),
            ephemeral=True,
        )
        try:
            await interaction.author.send(embed=embed)
        except disnake.Forbidden:
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `I don't have permission to send messages in your dms.`",
                ),
                ephemeral=True,
            )

    @commands.guild_only()
    @commands.slash_command(
        name="player-seek", description="Seek to a specific time in the song."
    )
    async def seek(
        self,
        interaction: disnake.ApplicationCommandInteraction,
        position: str = Param(
            description="The time position to seek to. For eg: /seek 3:56"
        ),
    ):
        await interaction.response.defer()

        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        if not player.is_connected:
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `Bot is not connected.`",
                )
            )

        if not player.is_playing:
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `There is no song playing right now.`",
                )
            )
        if player.is_paused:
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `There player is paused right now, resume it in order to `seek`.",
                )
            )

        if not self.is_author(interaction):
            return await interaction.channel.send(
                embed=disnake.Embed(
                    description=f"Only {player.dj} can use this command.",
                )
            )
        pos = position.split(":")
        if len(pos) > 1:
            secs = (int(pos[0]) * 60) + int(pos[1])
        else:
            secs = (int(pos[0]) * 60)

        await player.seek(secs * 1000)
        await interaction.send(
            embed=disnake.Embed(
                description=f"{self.bot.icons['check']} Successfully seeked to {secs} seconds.",
            )
        )

    @commands.guild_only()
    @commands.slash_command(
        name="player-swapdj",
        description="Swap the current DJ to another member in the voice channel.",
    )
    async def swap_dj(
        self,
        interaction: disnake.ApplicationCommandInteraction,
        member: disnake.Member = Param(description="The member to switvj to"),
    ):
        await interaction.response.defer()
        player: Player = self.bot.wavelink.get_player(
            guild_id=interaction.guild.id, cls=Player, context=interaction
        )

        if not player.is_connected:
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `Bot is not connected.`",
                )
            )

        if not self.is_author(interaction):
            return await interaction.channel.send(
                embed=disnake.Embed(
                    description=f"Only {player.dj} can use this command.",
                )
            )

        members = self.bot.get_channel(int(player.channel_id)).members

        if member and member not in members:
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} `{member}` is not currently in voice, "
                    f"so they cannot be a DJ."
                ),
            )

        if member and member == player.dj:
            return await interaction.send(
                embed=disnake.Embed(
                    description="Cannot swap DJ to the current DJ... :)",
                )
            )

        if len(members) <= 2:
            return await interaction.channel.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} `{member}` No more members to swap to."
                ),
                color=disnake.Colour.red(),
            )

        if member:
            player.dj = member
            return await interaction.send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['info']} `{member}` is now a DJ."
                ),
            )

        for m in members:
            if m == player.dj or m.bot:
                continue
            else:
                player.dj = m
                return await interaction.send(
                    embed=disnake.Embed(
                        description=f"{self.bot.icons['info']} `{member}` is now a DJ.",
                    )
                )


def setup(bot):
    bot.add_cog(Music(bot))
