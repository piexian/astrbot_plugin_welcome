from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig
from astrbot.api.event import MessageChain
import astrbot.api.message_components as Comp
from astrbot.core.star import StarTools
import os

@register(
    "welcome", "piexian", 
    "新成员入群时艾特他并自动发送欢迎消息（支持文本、图片）", 
    "1.1.1", "https://github.com/piexian/astrbot_plugin_welcome"
)
class WelcomePlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.welcome_image_path = self._get_image_path()
        self.welcome_text = self.config.get("welcome_text", "欢迎{at}加入本群！快来和大家打个招呼吧～")  # 默认欢迎语
        logger.info("入群欢迎插件初始化完成")

    def _get_image_path(self) -> str:
        if self.config.get("image_path") and os.path.exists(self.config["image_path"]):
            return self.config["image_path"]
        plugin_data_dir = StarTools.get_data_dir() / "welcome"
        plugin_data_dir.mkdir(parents=True, exist_ok=True)
        return str(plugin_data_dir / "welcome.jpg")

    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def on_group_join(self, event: AstrMessageEvent):
        # 仅处理系统发送的入群通知
        if event.get_sender_id() != "system":
            return
        # 识别入群消息关键词（兼容多平台）
        if "加入本群" in event.message_str or "加入群聊" in event.message_str:
            new_member_id = self._extract_new_member_id(event)
            if not new_member_id:
                logger.warning("未识别到新成员ID")
                return
            # 构建并发送欢迎消息
            message_chain = self._build_message_chain(new_member_id)
            yield event.chain_result(message_chain)
            logger.info(f"已发送欢迎消息给新成员：{new_member_id}")

    def _extract_new_member_id(self, event: AstrMessageEvent) -> str:
        """从事件中提取新成员ID（兼容多平台事件结构）"""
        # 尝试从事件原始数据中提取
        raw_data = event.get_raw_data() or {}
        if isinstance(raw_data, dict):
            # 适配常见平台的user_id字段
            return str(raw_data.get("user_id") or raw_data.get("operator_id", ""))
        # 尝试从消息链中提取@对象（部分平台入群消息会@新成员）
        for comp in event.get_message_chain():
            if isinstance(comp, Comp.At):
                return comp.target
        return ""

    def _build_message_chain(self, new_member_id: str) -> MessageChain:
        """使用MessageChain构建富媒体消息（符合框架规范）"""
        chain = MessageChain()
        welcome_text = self.welcome_text

        # 处理{at}占位符，插入艾特组件（支持占位符在任意位置）
        if "{at}" in welcome_text:
            parts = welcome_text.split("{at}")
            for i, part in enumerate(parts):
                if part:  # 添加文本片段
                    chain.append(Comp.Plain(text=part))
                # 除最后一个片段外，插入艾特组件
                if i < len(parts) - 1:
                    chain.append(Comp.At(target=new_member_id))
        else:
            # 无占位符时直接添加文本
            chain.append(Comp.Plain(text=welcome_text))

        # 添加欢迎图片（支持本地文件和URL，优先本地）
        if os.path.exists(self.welcome_image_path):
            try:
                # 从本地文件加载图片
                chain.append(Comp.Image.fromFileSystem(self.welcome_image_path))
            except Exception as e:
                logger.error(f"本地图片加载失败：{e}")
        elif self.welcome_image_path.startswith(("http://", "https://")):
            try:
                # 从URL加载图片（如果配置的是URL）
                chain.append(Comp.Image.fromURL(self.welcome_image_path))
            except Exception as e:
                logger.error(f"URL图片加载失败：{e}")
        else:
            logger.warning(f"欢迎图片不存在（路径/URL：{self.welcome_image_path}）")

        return chain

    async def terminate(self):
        logger.info("入群欢迎插件已卸载")
