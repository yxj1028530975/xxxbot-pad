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
                    # 直接使用 API 调用获取群成员信息
                    import aiohttp
                    import json

                    # 获取头像地址
                    avatar_url = ""

                    # 构造请求参数
                    json_param = {"QID": message["FromWxid"], "Wxid": bot.wxid}
                    # logger.info(f"发送请求参数: {json.dumps(json_param)}")

                    # 确定 API 基础路径
                    api_base = f"http://{bot.ip}:{bot.port}"

                    # 根据协议版本选择正确的 API 前缀
                    import tomllib
                    try:
                        with open("main_config.toml", "rb") as f:
                            config = tomllib.load(f)
                            protocol_version = config.get("Protocol", {}).get("version", "855")

                            # 根据协议版本选择前缀
                            if protocol_version == "849":
                                api_prefix = "/VXAPI"
                            else:  # 855 或 ipad
                                api_prefix = "/api"
                    except Exception as e:
                        logger.warning(f"读取协议版本失败，使用默认前缀: {e}")
                        # 默认使用 855 的前缀
                        api_prefix = "/api"

                    async with aiohttp.ClientSession() as session:
                        response = await session.post(
                            f"{api_base}{api_prefix}/Group/GetChatRoomMemberDetail",
                            json=json_param,
                            headers={"Content-Type": "application/json"}
                        )

                        # 检查响应状态
                        if response.status != 200:
                            logger.error(f"获取群成员列表失败: HTTP状态码 {response.status}")
                            raise Exception(f"HTTP状态码: {response.status}")

                        # 解析响应数据
                        json_resp = await response.json()
                        # logger.info(f"收到API响应: {json.dumps(json_resp)[:200]}...")

                        if json_resp.get("Success"):
                            # 获取群成员列表
                            group_data = json_resp.get("Data", {})
                            # logger.info(f"群数据结构: {json.dumps(list(group_data.keys()))}")

                            # 正确提取ChatRoomMember列表
                            if "NewChatroomData" in group_data and "ChatRoomMember" in group_data["NewChatroomData"]:
                                group_members = group_data["NewChatroomData"]["ChatRoomMember"]
                                # logger.info(f"获取到群成员列表，共{len(group_members) if isinstance(group_members, list) else 0}个成员")

                                if isinstance(group_members, list) and group_members:
                                    # 在群成员列表中查找指定成员
                                    for member_data in group_members:
                                        # 输出成员数据结构
                                        # logger.info(f"成员数据结构: {json.dumps(list(member_data.keys()))}")

                                        # 尝试多种可能的字段名
                                        member_wxid = member_data.get("UserName") or member_data.get("Wxid") or member_data.get("wxid") or ""
                                        # logger.info(f"比较成员ID: {member_wxid} vs {wxid}")

                                        if member_wxid == wxid:
                                            # 获取头像地址
                                            avatar_url = member_data.get("BigHeadImgUrl") or member_data.get("SmallHeadImgUrl") or ""
                                            # logger.info(f"成功获取到群成员 {nickname}({wxid}) 的头像地址: {avatar_url}")
                                            break
                        else:
                            error_msg = json_resp.get("Message") or json_resp.get("message") or "未知错误"
                            logger.warning(f"获取群 {message['FromWxid']} 成员列表失败: {error_msg}")

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