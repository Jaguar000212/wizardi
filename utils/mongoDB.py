from typing import Literal


class BotDB:
    def __init__(self, bot):
        self.bot = bot

    async def updateCensor(self, _id: str, response: bool = False):
        try:
            return (
                await self.bot.database.Configs.update_one(
                    {"_id": _id}, {"$set": {"censor": response}}
                )
            ).modified_count
        except Exception as e:
            print("Error", e)

    async def updateNSFW(self, _id: str, nsfw: bool = False):
        try:
            return (
                await self.bot.database.Configs.update_one(
                    {"_id": _id}, {"$set": {"nsfw": nsfw}}
                )
            ).modified_count
        except Exception as e:
            print("Error", e)

    async def updateNQN(self, _id: str, nqn: bool = False):
        try:
            return (
                await self.bot.database.Configs.update_one(
                    {"_id": _id}, {"$set": {"nqn": nqn}}
                )
            ).modified_count
        except Exception as e:
            print("Error", e)

    async def updateLogChannel(self, _id: str, channelID: str = None):
        try:
            return (
                await self.bot.database.Configs.update_one(
                    {"_id": _id}, {"$set": {"logchannel": channelID}}
                )
            ).modified_count
        except Exception as e:
            print("Error", e)

    async def updateBlackList(
        self, _id: str, word=None, function: Literal["append", "pop"] = "append"
    ):
        if function == "append":
            try:
                return (
                    await self.bot.database.Configs.update_one(
                        {"_id": _id}, {"$addToSet": {"blacklist": word}}
                    )
                ).modified_count
            except Exception as e:
                print("Error", e)
        if function == "pop":
            try:
                return (
                    await self.bot.database.Configs.update_one(
                        {"_id": _id}, {"$pull": {"blacklist": word}}
                    )
                ).modified_count
            except Exception as e:
                print("Error", e)

    async def updateWhiteList(
        self, _id: str, word=None, function: Literal["append", "pop"] = "append"
    ):
        if function == "append":
            try:
                return (
                    await self.bot.database.Configs.update_one(
                        {"_id": _id}, {"$addToSet": {"blacklist": word}}
                    )
                ).modified_count
            except Exception as e:
                print("Error", e)
        if function == "pop":
            try:
                return (
                    await self.bot.database.Configs.update_one(
                        {"_id": _id}, {"$pull": {"blacklist": word}}
                    )
                ).modified_count
            except Exception as e:
                print("Error", e)

    async def updateWhitechannelList(
        self, _id: str, channelID=None, function: Literal["append", "pop"] = "append"
    ):
        if function == "append":
            try:
                return (
                    await self.bot.database.Configs.update_one(
                        {"_id": _id}, {"$addToSet": {"whitechannels": channelID}}
                    )
                ).modified_count
            except Exception as e:
                print("Error", e)
        if function == "pop":
            try:
                return (
                    await self.bot.database.Configs.update_one(
                        {"_id": _id}, {"$pull": {"whitechannels": channelID}}
                    )
                ).modified_count
            except Exception as e:
                print("Error", e)

    async def updateChatbotChannel(
        self, channelID=None, function: Literal["append", "pop"] = "append"
    ):
        if function == "append":
            try:
                return (
                    await self.bot.database.ChatBotChannels.update_one(
                        {"_id": "1234"}, {"$addToSet": {"chatbotchannel": channelID}}
                    )
                ).modified_count
            except Exception as e:
                print("Error", e)
        if function == "pop":
            try:
                return (
                    await self.bot.database.ChatBotChannels.update_one(
                        {"_id": "1234"}, {"$pull": {"chatbotchannel": channelID}}
                    )
                ).modified_count
            except Exception as e:
                print("Error", e)
