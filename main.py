from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig
import astrbot.api.message_components as Comp
from astrbot.core.star import StarTools
import os

@register("welcome", "piexian", "新成员入群时艾特他并自动发送欢迎消息（支持文本、图片）", "1.1.2", "https://github.com/piexian/astrbot_plugin_welcome")
class WelcomePlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.welcome_image_path = self._get_image_path()
        self.welcome_text = self.config.get("welcome_text", "欢迎{at}加入本群！快来和大家打个招呼吧～")
        logger.info("入群欢迎插件初始化完成")

    def _get_image_path(self) -> str:
        if self.config.get("image_path") and os.path.exists(self.config["image_path"]):
            return self.config["image_path"]
        plugin_data_dir = StarTools.get_data_dir() / "welcome"
        plugin_data_dir.mkdir(parents=True, exist_ok=True)
        return str(plugin_data_dir / "welcome.jpg")

    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def on_group_join(self, event: AstrMessageEvent):
        if event.get_sender_id() != "system":
            return
        if "加入本群" in event.message_str or "加入群聊" in event.message_str:
            new_member_id = self._extract_new_member_id(event)
            if not new_member_id:
                logger.warning("未识别到新成员ID")
                return           
            result = self._build_message_result(event, new_member_id)
            yield result
            logger.info(f"已发送欢迎消息给新成员：{new_member_id}")

    def _extract_new_member_id(self, event: AstrMessageEvent) -> str:
        raw_event = event.platform_meta.raw_event or {}
        if isinstance(raw_event, dict):
            return str(raw_event.get("user_id") or raw_event.get("operator_id", ""))
        for comp in event.get_messages():
            if isinstance(comp, At):
                return comp.target
        return ""

    def _build_message_result(self, event: AstrMessageEvent, new_member_id: str):
        """使用 MessageEventResult 构建消息（替代 MessageChain）"""
        # 创建空的消息结果
        result = event.make_result()
        
        # 处理欢迎文本中的 {at} 占位符
        welcome_text = self.welcome_text
        if "{at}" in welcome_text:
            parts = welcome_text.split("{at}")
            for i, part in enumerate(parts):
                if part:
                    result.add(Plain(text=part))
                if i < len(parts) - 1:
                    result.add(At(target=new_member_id))
        else:
            result.add(Plain(text=welcome_text))
        
        # 添加欢迎图片
        if self.welcome_image_path:
            try:
                if os.path.exists(self.welcome_image_path):
                    result.add(Image(path=self.welcome_image_path))
                elif self.welcome_image_path.startswith(("http://", "https://")):
                    result.add(Image(url=self.welcome_image_path))
            except Exception as e:
                logger.error(f"加载欢迎图片失败：{e}")
        
        return result

    async def terminate(self):
        logger.info("入群欢迎插件已卸载")