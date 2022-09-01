class CensorBot:
    def __init__(self, bot):
        self.bot = bot

    async def censor(self, ctx):
        censor = await self.bot.database.Configs.find_one({"_id": str(ctx.guild.id)})
        if not censor is None:
            return censor["censor"]
        else:
            return False

    async def whitelist(self, ctx):
        whitelist = await self.bot.database.Configs.find_one({"_id": str(ctx.guild.id)})
        if not whitelist is None:
            return whitelist["whitelist"]
        else:
            return []

    async def blacklist(self, ctx):
        blacklist = await self.bot.database.Configs.find_one({"_id": str(ctx.guild.id)})
        if not blacklist is None:
            return blacklist["blacklist"]
        else:
            return []

    async def whitechannel(self, ctx):
        whitechannel = await self.bot.database.Configs.find_one({"_id": str(ctx.guild.id)})
        if not whitechannel is None:
            return whitechannel["whitechannels"]
        else:
            return []
