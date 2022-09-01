import disnake
from disnake.ext import commands
import json
from disnake import utils
from bot import Bot
from utils.embed import logEmbed
import requests


def chatbot(ctx):
    req = requests.get(
        f"https://api.popcat.xyz/chatbot?msg={ctx}&owner=𝙹𝚊𝚐𝚞𝚊𝚛000212&botname=Wizardi"
    )
    data = (json.loads(req.text))["response"]
    return data


async def configs(bot, id):
    config = {
        "_id": str(id),
        "censor": False,
        "nqn": False,
        "logchannel": "",
        "blacklist": [],
        "whitelist": [],
        "whitechannels": [],
    }
    await bot.database.Configs.insert_one(config)


class Message(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    async def getemote(self, arg):
        emoji = utils.get(self.bot.emojis, name=arg.strip(":"))

        if emoji is not None:
            if emoji.animated:
                add = "a"
            else:
                add = ""
            return f"<{add}:{emoji.name}:{emoji.id}>"
        else:
            return None

    async def getinstr(self, content):
        ret = []

        spc = content.split(" ")
        cnt = content.split(":")

        if len(cnt) > 1:
            for item in spc:
                if item.count(":") > 1:
                    wr = ""
                    if item.startswith("<") and item.endswith(">"):
                        ret.append(item)
                    else:
                        cnt = 0
                        for i in item:
                            if cnt == 2:
                                aaa = wr.replace(" ", "")
                                ret.append(aaa)
                                wr = ""
                                cnt = 0

                            if i != ":":
                                wr += i
                            else:
                                if wr == "" or cnt == 1:
                                    wr += " : "
                                    cnt += 1
                                else:
                                    aaa = wr.replace(" ", "")
                                    ret.append(aaa)
                                    wr = ":"
                                    cnt = 1

                        aaa = wr.replace(" ", "")
                        ret.append(aaa)
                else:
                    ret.append(item)
        else:
            return content

        return ret

    @commands.Cog.listener()
    async def on_message(self, ctx):
        if not ctx.author.bot:
            self.bot.process_commands
            mention = ctx.author.mention
            try:
                chatchannel = (
                    await self.bot.database.MiscConfigs.find_one({"_id": "1234"})
                )["chatbotchannels"]
                blacklist = await self.bot.censorBot.blacklist(ctx=ctx)
                whitelist = await self.bot.censorBot.whitelist(ctx=ctx)
                respond = await self.bot.censorBot.censor(ctx=ctx)
                white_channel = await self.bot.censorBot.whitechannel(ctx=ctx)
            except:
                await configs(self.bot, ctx.guild.id)
            finally:
                chatchannel = (
                    await self.bot.database.MiscConfigs.find_one({"_id": "1234"})
                )["chatbotchannels"]
                blacklist = await self.bot.censorBot.blacklist(ctx=ctx)
                whitelist = await self.bot.censorBot.whitelist(ctx=ctx)
                respond = await self.bot.censorBot.censor(ctx=ctx)
                white_channel = await self.bot.censorBot.whitechannel(ctx=ctx)

            if respond == True:
                if not any(
                    word in ctx.content.lower() for word in whitelist
                ) and not ctx.content.startswith("https://"):
                    if any(word in ctx.content.lower() for word in blacklist):
                        if (
                            ctx.channel.id not in map(int, white_channel)
                            and ctx.author.id != self.bot.user.id
                        ):
                            if not ctx.content.startswith(
                                tuple(await self.bot.get_prefix(ctx))
                            ):
                                embed_warn = disnake.Embed(
                                    title="Relax",
                                    description=mention
                                    + "Calm down man... I guess you went with the flow",
                                    color=16711680,
                                )
                                embed_warn.set_author(
                                    name="Moderators",
                                    icon_url="https://cdn.discordapp.com/emojis/946058860580446279.webp?size=96&quality=lossless",
                                )
                                embed_warn.set_footer(text="Mind the language buddy!")
                                await ctx.delete()
                                await ctx.channel.send(embed=embed_warn, delete_after=3)
                                warn = logEmbed(
                                    self.bot,
                                    ctx,
                                    "Censored Message",
                                    "Sucessfully censored the message",
                                    ctx.author,
                                    self.bot.user,
                                )
                                channel = self.bot.get_channel(
                                    int(await self.bot.config.logChannel(ctx=ctx))
                                )
                                await channel.send(embed=warn)

            if ":" in ctx.content:
                msg = await self.getinstr(ctx.content)
                ret = ""
                em = False
                smth = ctx.content.split(":")
                if len(smth) > 1:
                    for word in msg:
                        if (
                            word.startswith(":")
                            and word.endswith(":")
                            and len(word) > 1
                        ):
                            emoji = await self.getemote(word)
                            if emoji is not None:
                                em = True
                                ret += f" {emoji}"
                            else:
                                ret += f" {word}"
                        else:
                            ret += f" {word}"

                else:
                    ret += msg

                if em:
                    webhooks = await ctx.channel.webhooks()
                    webhook = utils.get(webhooks, name="Imposter NQN")
                    if webhook is None:
                        webhook = await ctx.channel.create_webhook(name="Imposter NQN")
                    await webhook.send(
                        ret,
                        username=ctx.author.name,
                        avatar_url=ctx.author.display_avatar.url,
                    )
                    await ctx.delete()

            if ctx.channel.id in chatchannel:
                try:
                    await ctx.channel.send(chatbot(ctx.content))
                except Exception as e:
                    await ctx.channel.send(disnake.Embed(description="`An unknown error occured and the same has been reported to the team.`"), delete_after=3)

    @commands.Cog.listener()
    async def on_message_edit(self, message_before, message_after):
        mention = message_before.author.mention
        blacklist = await self.bot.censorBot.blacklist(ctx=message_before)
        whitelist = await self.bot.censorBot.whitelist(ctx=message_before)
        respond = await self.bot.censorBot.censor(ctx=message_before)
        white_channel = await self.bot.censorBot.whitechannel(ctx=message_before)
        if respond == True:
            if not any(word in message_after.content.lower() for word in whitelist):
                if any(word in message_after.content.lower() for word in blacklist):
                    if message_before.channel.id not in map(int, white_channel):
                        embed_warn = disnake.Embed(
                            title="Relax",
                            description=mention
                            + "Calm down man... I guess you went with the flow",
                            color=16711680,
                        )
                        embed_warn.set_author(
                            name="Moderators",
                            icon_url="https://cdn.discordapp.com/emojis/946058860580446279.webp?size=96&quality=lossless",
                        )
                        embed_warn.set_footer(text="Mind the language buddy!")
                        await message_before.delete()
                        await message_before.channel.send(
                            embed=embed_warn, delete_after=3
                        )
                        channel = self.bot.get_channel(
                            await self.bot.config.logChannel(ctx=message_before)
                        )
                        await channel.send(
                            embed=logEmbed(
                                self,
                                message_before,
                                "Censored Message",
                                "Sucessfully censored the message",
                                message_before.author,
                                self.bot.user,
                            )
                        )


def setup(bot):
    bot.add_cog(Message(bot))
