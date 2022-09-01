from disnake.ext.commands import CommandError


class NoChannelProvided(CommandError):
    pass


class NSFWChannel(CommandError):
    pass


class NoVote(CommandError):
    pass


class NoNeko(CommandError):
    pass
