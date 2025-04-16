import tomllib
import xml.etree.ElementTree as ET
from datetime import datetime

from loguru import logger

from WechatAPI import WechatAPIClient
from utils.decorators import on_system_message
from utils.plugin_base import PluginBase


class GroupWelcome(PluginBase):
    description = "进群欢迎"
    author = "HenryXiaoYang"
    version = "1.0.0"

    def __init__(self):
        super().__init__()

        with open("plugins/GroupWelcome/config.toml", "rb") as f:
            plugin_config = tomllib.load(f)

        config = plugin_config["GroupWelcome"]

        self.enable = config["enable"]
        self.welcome_message = config["welcome-message"]
        self.url = config["url"]

    @on_system_message
    async def group_welcome(self, bot: WechatAPIClient, message: dict):
        if not self.enable:
            return

        if not message["IsGroup"]:
            return

        xml_content = str(message["Content"]).strip().replace("\n", "").replace("\t", "")
        root = ET.fromstring(xml_content)

        if root.tag != "sysmsg":
            return

        # 检查是否是进群消息
        if root.attrib.get("type") == "sysmsgtemplate":
            sys_msg_template = root.find("sysmsgtemplate")
            if sys_msg_template is None:
                return

            template = sys_msg_template.find("content_template")
            if template is None:
                return

            template_type = template.attrib.get("type")
            if template_type not in ["tmpl_type_profile", "tmpl_type_profilewithrevoke"]:
                return

            template_text = template.find("template").text

            if '"$names$"加入了群聊' in template_text:  # 直接加入群聊
                new_members = self._parse_member_info(root, "names")
            elif '"$username$"邀请"$names$"加入了群聊' in template_text:  # 通过邀请加入群聊
                new_members = self._parse_member_info(root, "names")
            elif '你邀请"$names$"加入了群聊' in template_text:  # 自己邀请成员加入群聊
                new_members = self._parse_member_info(root, "names")
            elif '"$adder$"通过扫描"$from$"分享的二维码加入群聊' in template_text:  # 通过二维码加入群聊
                new_members = self._parse_member_info(root, "adder")
            elif '"$adder$"通过"$from$"的邀请二维码加入群聊' in template_text:
                new_members = self._parse_member_info(root, "adder")
            else:
                logger.warning(f"未知的入群方式: {template_text}")
                return

            if not new_members:
                return

            for member in new_members:
                wxid = member["wxid"]
                nickname = member["nickname"]

                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                try:
                    # 使用新添加的方法获取群成员信息
                    member_info = await bot.get_some_member_info(message["FromWxid"], wxid)
                    
                    # 获取头像地址
                    avatar_url = ""
                    if member_info and isinstance(member_info, dict):
                        avatar_url = member_info.get("HeadImgUrl", "")
                    
                    # 发送欢迎消息
                    await bot.send_link_message(message["FromWxid"],
                                            title=f"👏欢迎 {nickname} 加入群聊！🎉",
                                            description=f"⌚时间：{now}\n{self.welcome_message}",
                                            url=self.url,
                                            thumb_url=avatar_url
                                            )
                except Exception as e:
                    logger.error(f"获取群成员信息失败: {e}")
                    # 如果获取失败，使用默认头像发送欢迎消息
                    await bot.send_link_message(message["FromWxid"],
                                            title=f"👏欢迎 {nickname} 加入群聊！🎉",
                                            description=f"⌚时间：{now}\n{self.welcome_message}",
                                            url=self.url,
                                            thumb_url=""
                                            )

    @staticmethod
    def _parse_member_info(root: ET.Element, link_name: str = "names") -> list[dict]:
        """解析新成员信息"""
        new_members = []
        try:
            # 查找指定链接中的成员列表
            names_link = root.find(f".//link[@name='{link_name}']")
            if names_link is None:
                return new_members

            memberlist = names_link.find("memberlist")

            if memberlist is None:
                return new_members

            for member in memberlist.findall("member"):
                username = member.find("username").text
                nickname = member.find("nickname").text
                new_members.append({
                    "wxid": username,
                    "nickname": nickname
                })

        except Exception as e:
            logger.warning(f"解析新成员信息失败: {e}")

        return new_members