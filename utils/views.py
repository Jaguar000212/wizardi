import datetime
from typing import List

import disnake
import humanize
from disnake import MessageInteraction

import wavelink
from bot import Bot
from utils.MusicPlayerInteraction import Player, Track


class Filter(disnake.ui.Select["FilterView"]):
    def __init__(self, player: Player):
        self.player = player
        options = [
            disnake.SelectOption(
                label="Tremolo", description="Tremolo Filter.", emoji="🟫"
            ),
            disnake.SelectOption(
                label="Karaoke", description="Karaoke Filter.", emoji="🟥"
            ),
            disnake.SelectOption(label="8D", description="8D Audio Filter.", emoji="🟪"),
            disnake.SelectOption(
                label="Vibrato", description="Vibrato Filter.", emoji="🟨"
            ),
            disnake.SelectOption(
                label="ExtremeBass", description="ExtremeBass Filter.", emoji="🟩"
            ),
            disnake.SelectOption(
                label="Default", description="Default Filter.", emoji="🟦"
            ),
        ]

        super().__init__(
            placeholder="Choose your Filter...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(
        self, interaction: disnake.ApplicationCommandInteraction
    ) -> None:

        await interaction.response.send_message(f"Filter set to {self.values[0]}.")
        extreme_bass = wavelink.BaseFilter.build_from_channel_mix(
            left_to_right=1.0, right_to_left=3.0, right_to_right=8.8, left_to_left=9.0
        )
        eqs = {
            "Tremolo": wavelink.BaseFilter.tremolo(),
            "Karaoke": wavelink.BaseFilter.karaoke(),
            "8D": wavelink.BaseFilter.Eight_D_Audio(),
            "Vibrato": wavelink.BaseFilter.vibrato(),
            "ExtremeBass": extreme_bass,
            # "Default": ""
        }  # you can make your own custom Filters and pass it here.
        await self.player.set_filter(eqs[self.values[0]])


class FilterView(disnake.ui.View):
    def __init__(
        self, interaction: disnake.ApplicationCommandInteraction, player: Player
    ):
        super().__init__(timeout=60)
        self.interaction = interaction
        self.add_item(Filter(player=player))

    async def interaction_check(
        self, interaction: disnake.ApplicationCommandInteraction
    ) -> bool:

        if interaction.author.id != self.interaction.author.id:
            return await interaction.response.send_message(
                "This is not your menu!", ephemeral=True
            )
        return True

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        await self.interaction.edit_original_message(view=self)


class SongSelection(disnake.ui.Select["SongSelectionView"]):
    def __init__(self, tracks: List[Track], bot: Bot, player: Player):

        self.bot = bot
        self.player = player
        self.tracks = tracks

        options = []
        for index, track in enumerate(self.tracks):
            option = disnake.SelectOption(
                label=f"{index + 1}. {track.title}",
                description=f"{track.author} - {humanize.precisedelta(datetime.timedelta(milliseconds=track.duration))}",
                value=str(index),
            )
            options.append(option)
            for track in options:
                if len(track.label) > 100:
                    track.label = track.label[:100]

        super().__init__(
            placeholder="Select a song",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: MessageInteraction) -> None:

        track = Track(
            self.tracks[int(self.values[0])].id,
            self.tracks[int(self.values[0])].info,
            requester=interaction.author,
        )
        #  Creating a Track object from the selected track.
        await interaction.response.send_message(
            embed=disnake.Embed(
                description=f"\n{self.bot.icons['headphones']} Enqueued `{track.title}` to the Queue\n"
            )
        )
        await self.player.queue.put(track)

        if not self.player.is_playing:
            await self.player.play_next_song()


class SongSelectionView(disnake.ui.View):
    def __init__(
        self,
        tracks: List[Track],
        interaction: disnake.ApplicationCommandInteraction,
        player: Player,
        bot: Bot,
    ):
        super().__init__(timeout=60)
        self.tracks = tracks
        self.bot = bot
        self.interaction = interaction
        self.player = player
        self.add_item(SongSelection(tracks=tracks, bot=self.bot, player=self.player))

    async def interaction_check(
        self, interaction: disnake.ApplicationCommandInteraction
    ) -> bool:

        if interaction.author.id != self.player.dj.id:
            return await interaction.response.send_message(
                "This is not your menu!", ephemeral=True
            )
        return True

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        await self.interaction.edit_original_message(view=self)
