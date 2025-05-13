import random
import re
from astrbot.api.event import filter
from astrbot import logger
from astrbot.api.star import Context, Star, register
from astrbot.core import AstrBotConfig
from astrbot.core.platform.astr_message_event import AstrMessageEvent
from astrbot.core.message.components import (
    At,
    Face,
    Image,
    Plain,
    Reply,
)


@register(
    "astrbot_plugin_better_io",
    "Zhalslar",
    "对输入输出的消息进行各种预处理，从而获得更好的体验",
    "1.0.0",
    "https://github.com/Zhalslar/astrbot_plugin_better_io",
)
class BetterIOPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config

        # at概率
        self.at_prob: float = config.get("at_prob", 0.5)
        # Reply概率
        self.reply_prob: float = config.get("reply_prob", 0.5)

        # 唤醒增强的正则表达式
        self.waking_regex: list[str] = config.get("waking_regex", "")

        # 多少个字符以下时执行文本清理
        self.clean_text_length: int = config.get("clean_text_length", 150)

        # 需要清理的特殊符号
        self.clean_punctuation: str = config.get("clean_punctuation", "")

        # 需要去除的指定开头字符
        self.remove_lead: list[str] = config.get("remove_lead", [])

        # 错误关键字
        self.error_keywords = config.get("error_keywords", ["请求失败"])

        # 黑名单用户ID列表
        self.user_blacklist: list[str] = config.get("user_blacklist", [])

    @filter.on_decorating_result()
    async def on_message(self, event: AstrMessageEvent):
        """发送消息前的预处理"""
        # 拦截错误信息(根据关键词拦截)
        result = event.get_result()
        if not result:
            return
        message_str = (
            result.get_plain_text() if hasattr(result, "get_plain_text") else ""
        )
        matched_keyword = next(
            (keyword for keyword in self.error_keywords if keyword in message_str), None
        )
        if matched_keyword:
            try:
                event.set_result(event.plain_result(""))
                logger.info("已将回复内容替换为空消息")
            except AttributeError:
                event.stop_event()
                logger.info("不支持 set_result，尝试使用 stop_event 阻止消息发送")
            return

        # 过滤不支持的消息类型
        chain = event.get_result().chain
        if not chain:
            return
        if not all(isinstance(comp, (Plain, Image, Face)) for comp in chain):
            return

        # 清洗文本消息
        end_seg = chain[-1]
        if isinstance(end_seg, Plain) and len(end_seg.text) < self.clean_text_length:
            # 清洗标点符号
            if self.clean_punctuation:
                end_seg.text = re.sub(self.clean_punctuation, "", end_seg.text)
            # 去除指定开头字符
            if self.remove_lead:
                for remove_lead in self.remove_lead:
                    if end_seg.text.startswith(remove_lead):
                        end_seg.text = end_seg.text[len(remove_lead) :]

        # 随机附加At,引用回复
        if event.get_platform_name() == "aiocqhttp":
            sender_id = event.get_sender_id()
            message_id = event.message_obj.message_id
            if not message_id:
                return
            # 按概率@发送者
            if random.random() < self.at_prob and At(qq=sender_id) not in chain:
                chain.insert(0, At(qq=sender_id))
            # 按概率引用回复
            elif (
                random.random() < self.reply_prob
                and isinstance(end_seg, Plain)
                and end_seg.text.strip()
            ):
                chain.insert(0, Reply(id=message_id))

    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def on_waking(self, event: AstrMessageEvent):
        """收到消息后的预处理"""
        # 屏蔽黑名单用户
        if event.get_sender_id() == event.get_self_id():
            return
        if event.get_sender_id() in self.user_blacklist:
            event.stop_event()

        # 唤醒增强
        for regex in self.waking_regex:
            if re.match(regex, event.message_str):
                event.is_at_or_wake_command = True
