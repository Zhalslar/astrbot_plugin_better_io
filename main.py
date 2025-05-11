import random
import re
from astrbot.api.event import filter
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
        # 管理员列表
        self.admins_id: list = context.get_config().get("admins_id", [])
        # 管理群
        self.manage_group: str = config.get("manage_group", 0)
        # at概率
        self.at_prob: float = config.get("at_prob", 0.5)
        # Reply概率
        self.reply_prob: float = config.get("reply_prob", 0.5)
        # 保留的标点符号
        self.additional_chars: str = config.get("additional_chars", "")
        # 唤醒增强的正则表达式
        self.waking_regex: list[str] = config.get("waking_regex", "")
        # 正则表达式列表
        self.REGEX_RULES = [
            r'[@#￥%（）\$\^\&\*\{\}$$`~！!\?:";<>+=\-—／《》]',  # 第一条：去除指定的特殊符号
            r"print$'$'$",  # 第二条：去除类似 print('') 的结构
            r"^阿苗：",  # 第三条：去除开头的“阿苗：”
        ]

    @filter.on_decorating_result()
    async def on_message(self, event: AstrMessageEvent):
        """监听消息"""

        if event.get_platform_name() != "aiocqhttp":
            return

        sender_id = event.get_sender_id()
        message_id = event.message_obj.message_id
        chain = event.get_result().chain
        # 当消息段中只含有纯文本、图片、表情时才进行回复
        if all(isinstance(comp, (Plain, Image, Face)) for comp in chain):
            # 按概率@发送者
            if random.random() < self.at_prob and At(qq=sender_id) not in chain:
                chain.insert(0, At(qq=sender_id))

            # 按概率引用回复
            elif random.random() < self.reply_prob:
                chain.insert(0, Reply(id=message_id))

            # 清理特殊符号
            end_seg = chain[-1]
            if isinstance(end_seg, Plain):
                end_seg.text = self.clean_text(end_seg.text)


    def clean_text(self, text):
        """使用预定义的正则规则清洗文本"""
        for pattern in self.REGEX_RULES:
            text = re.sub(pattern, "", text)
        return text.strip()


    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def on_waking(self, event: AstrMessageEvent):
        """持续唤醒监听器"""
        for regex in self.waking_regex:
            if re.match(regex, event.message_str):
                event.is_at_or_wake_command = True
