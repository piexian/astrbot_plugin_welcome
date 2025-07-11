from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig
import astrbot.api.message_components as Comp
from astrbot.core.star import StarTools
import os

@register(
    "welcome","piexian","新成员入群时艾特他并自动发送欢迎消息（支持文本、图片）","1.0"," "
)
class WelcomePlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.welcome_image_path = self._get_image_path()
        self.welcome_text = self.config.get("welcome_text", "")
        logger.info("入群欢迎插件初始化完成")

    def _get_image_path(self) -> str:
        if self.config.get("image_path") and os.path.exists(self.config["image_path"]):
            return self.config["image_path"]
        plugin_data_dir = StarTools.get_data_dir() / "welcome"
        plugin_data_dir.mkdir(parents=True, exist_ok=True)
        return str(plugin_data_dir / "welcome.jpg")

    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def on_group_join(self, event: AstrMessageEvent):
        platform = event.get_platform_name()
        if platform != "aiocqhttp" or event.get_sender_id() != "system":
            return
        if "加入本群" in event.message_str:
            new_member_id = self._extract_new_member_id(event.message_obj.raw_message)
            if not new_member_id:
                logger.warning("未识别到新成员ID")
                return
            message_chain = self._build_message_chain(new_member_id)
            yield event.chain_result(message_chain)
            logger.info(f"已发送欢迎消息给 {new_member_id}")

    def _extract_new_member_id(self, raw_msg: dict) -> str:
        return str(raw_msg.get("user_id", "")) if isinstance(raw_msg, dict) else ""

    def _build_message_chain(self, new_member_id: str) -> list:
        welcome_text = self.welcome_text.replace("{at}", f"[CQ:at,qq={new_member_id}]")
        message_chain = [Comp.Plain(text=welcome_text)]
        if os.path.exists(self.welcome_image_path):
            try:
                message_chain.append(Comp.Image.fromFileSystem(path=self.welcome_image_path))
            except Exception as e:
                logger.error(f"加载图片失败：{e}")
        else:
            logger.warning(f"图片不存在：{self.welcome_image_path}")
        return message_chain

    async def terminate(self):
        logger.info("入群欢迎插件已卸载")
