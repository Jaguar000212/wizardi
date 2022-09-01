from disnake.ext import commands
import requests
from utils.exceptions import NoVote
from utils.helpers import Config
from wavelink.errors import NoPermissions


def voter():
    async def check(ctx):
        header = {"authorization": Config().topgg}
        check = requests.get(
            f"https://top.gg/api/bots/884117357327429704/check?userId={ctx.author.id}",
            headers=header,
        )
        check = check.json()
        if not check["voted"]:
            raise NoVote("No Vote")
        return check["voted"]

    return commands.check(check)
