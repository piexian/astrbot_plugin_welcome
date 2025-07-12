from astrbot.api.event import filter, AstrEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig
import astrbot.api.message_components as Comp
from astrbot.core.star import StarTools
import os


@register(
    "welcome", "piexian", 
    "新成员入群时艾特他并自动发送欢迎消息（支持文本、图片）", 
    "1.1", "https://github.com/piexian/astrbot_plugin_welcome"
)
class WelcomePlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.welcome_image_path = self._get_image_path()
        self.welcome_text = self.config.get("welcome_text", "欢迎加入本群！")
        logger.info("入群欢迎插件初始化完成")

    def _get_image_path(self) -> str:
        """获取欢迎图片路径，优先使用配置路径，否则使用默认路径"""
        if self.config.get("image_path") and os.path.exists(self.config["image_path"]):
            return self.config["image_path"]
        
        plugin_data_dir = StarTools.get_data_dir() / "welcome"
        plugin_data_dir.mkdir(parents=True, exist_ok=True)
        return str(plugin_data_dir / "welcome.jpg")

    @filter.event_type(filter.EventType.GROUP_MEMBER_INCREASE)
    async def on_group_join(self, event: AstrEvent):
        """监听群成员增加事件，触发欢迎流程"""
        # 从事件中获取新成员ID（框架统一属性，跨平台兼容）
        new_member_id = event.user_id  # 框架抽象属性，无需依赖具体平台实现
        
        if not new_member_id:
            logger.warning("无法获取新成员ID")
            return
        
        message_chain = self._build_message_chain(new_member_id)
        yield event.chain_result(message_chain)
        logger.info(f"已发送欢迎消息给新成员：{new_member_id}")

    def _build_message_chain(self, new_member_id: str) -> list:
        """构建跨平台的消息链，包含艾特组件和文本"""
        message_chain = []
        welcome_text = self.welcome_text
        
        # 处理艾特占位符，拆分文本并插入艾特组件
        if "{at}" in welcome_text:
            parts = welcome_text.split("{at}")
            for i, part in enumerate(parts):
                if part:
                    message_chain.append(Comp.Plain(text=part))
                # 除最后一个分片外，在分片后添加艾特组件
                if i < len(parts) - 1:
                    message_chain.append(Comp.At(target=new_member_id))
        else:
            # 若无艾特占位符，直接添加文本
            message_chain.append(Comp.Plain(text=welcome_text))
        
        # 添加欢迎图片（处理具体异常）
        if os.path.exists(self.welcome_image_path):
            try:
                image_comp = Comp.Image.fromFileSystem(path=self.welcome_image_path)
                message_chain.append(image_comp)
            except (IOError, FileNotFoundError, OSError) as e:
                logger.error(f"图片加载失败：{e}")
            except Exception as e:
                # 保留特定未知异常的捕获，但明确日志
                logger.error(f"加载图片时发生意外错误：{e}")
        else:
            logger.warning(f"欢迎图片不存在（路径：{self.welcome_image_path}）")
        
        return message_chain

    async def terminate(self):
        logger.info("入群欢迎插件已卸载")
