from loguru import logger
import tomllib
import os
import io
import re
import json
import random
import aiohttp
import asyncio
import time
import hashlib
from PIL import Image

from WechatAPI import WechatAPIClient
from utils.decorators import *
from utils.plugin_base import PluginBase
from meme_generator import get_meme


class MemeGen(PluginBase):
    """表情包生成器插件 - 基于微信群聊中的用户头像生成各种有趣的表情包"""
    description = "表情包生成器插件"
    author = "阿孟"
    version = "1.0.0"

    def __init__(self):
        super().__init__()

        # 获取配置文件路径
        config_path = os.path.join(os.path.dirname(__file__), "config.toml")

        try:
            with open(config_path, "rb") as f:
                config = tomllib.load(f)

            # 读取基本配置
            basic_config = config.get("basic", {})
            self.enable = basic_config.get("enable", True)

            # 读取缓存配置
            cache_config = config.get("cache", {})
            self.real_avatar_ttl = cache_config.get("real_avatar_ttl", 86400)  # 默认24小时
            self.default_avatar_ttl = cache_config.get("default_avatar_ttl", 43200)  # 默认12小时
            self.cleanup_interval = cache_config.get("cleanup_interval", 24)  # 默认24小时
            self.cleanup_threshold = cache_config.get("cleanup_threshold", 3)  # 默认3次
            self.cleanup_expire_days = cache_config.get("cleanup_expire_days", 7)  # 默认7天

            # 读取管理员配置
            admin_config = config.get("admin", {})
            self.local_admin_users = admin_config.get("admin_users", [])

            # 读取命令配置
            commands_config = config.get("commands", {})
            self.list_commands = commands_config.get("list_commands", ["表情列表"])

        except Exception as e:
            logger.error(f"加载MemeGen配置文件失败: {str(e)}")
            self.enable = False
            self.real_avatar_ttl = 86400
            self.default_avatar_ttl = 43200
            self.cleanup_interval = 24
            self.cleanup_threshold = 3
            self.cleanup_expire_days = 7
            self.local_admin_users = []
            self.list_commands = ["表情列表"]
            return

        # 创建临时文件夹
        self.temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp")
        os.makedirs(self.temp_dir, exist_ok=True)

        # 创建头像缓存目录
        self.avatar_dir = os.path.join(self.temp_dir, "avatars")
        os.makedirs(self.avatar_dir, exist_ok=True)

        # 加载表情配置
        self.meme_cache = {}  # 用于缓存meme生成器
        try:
            self.load_emoji_config()
        except Exception as e:
            logger.error(f"加载表情配置失败: {str(e)}")
            self.enable = False

    def load_emoji_config(self):
        """加载表情配置文件"""
        emoji_path = os.path.join(os.path.dirname(__file__), "emoji.json")
        if not os.path.exists(emoji_path):
            logger.error(f"表情配置文件不存在: {emoji_path}")
            raise FileNotFoundError(f"表情配置文件不存在: {emoji_path}")

        with open(emoji_path, "r", encoding="utf-8") as f:
            emoji_config = json.load(f)

        # 单人表情
        self.single_emojis = emoji_config.get("one_PicEwo", {})
        # 双人表情
        self.two_person_emojis = emoji_config.get("two_PicEwo", {})

        # 创建禁用表情追踪
        self.disabled_emojis = {}  # 格式: {group_id: set(disabled_meme_types)}
        self.globally_disabled_emojis = set()  # 全局禁用的表情类型

        logger.info(f"成功加载表情配置，单人表情: {len(self.single_emojis)}，双人表情: {len(self.two_person_emojis)}")

    @on_text_message()
    async def handle_text(self, bot: WechatAPIClient, message: dict):
        """处理文本消息"""
        if not self.enable:
            logger.info("MemeGen插件已禁用，忽略消息")
            return

        content = message.get("Content", "").strip()
        from_wxid = message.get("FromWxid", "")
        is_group = message.get("IsGroup", False)
        actual_user_id = message.get("ActualUserWxid", "")

        logger.info(f"MemeGen收到消息: {content}, 来自: {from_wxid}, 实际发送者: {actual_user_id}")

        # 检查是否请求表情列表
        if content in self.list_commands:
            await self.send_emoji_list(bot, from_wxid)
            return

        # 处理清理头像缓存命令
        if content.startswith("清理表情缓存") or content.startswith("清除表情缓存"):
            # 检查权限
            admin_users = self.get_admin_users()
            if actual_user_id not in admin_users:
                await bot.send_text_message(from_wxid, "只有管理员才能执行此操作！")
                return

            try:
                # 提取目标wxid，如果没有则清除所有
                parts = content.split(maxsplit=1)
                target_wxid = parts[1].strip() if len(parts) > 1 else None

                if target_wxid:
                    # 清除特定用户的头像缓存
                    files_removed = await self.clear_avatar_cache(target_wxid)
                    await bot.send_text_message(from_wxid, f"已清除用户 {target_wxid} 的头像缓存，移除了 {files_removed} 个文件")
                else:
                    # 清除所有低使用率的缓存
                    avatars_cleaned = await self.clear_all_avatar_cache()
                    await bot.send_text_message(from_wxid, f"已清除头像缓存，共移除了 {avatars_cleaned} 个文件")

                return
            except Exception as e:
                logger.error(f"清理缓存出错: {str(e)}")
                await bot.send_text_message(from_wxid, f"清理缓存失败: {str(e)}")
                return

        # 检查是否是表情启用/禁用命令
        if re.match(r'^(全局)?(禁用|启用)表情\s+.+$', content):
            await self.handle_enable_disable_commands(bot, message)
            return

        # 提取@用户
        at_users = self.extract_at_users(content, message)

        # 输出at_users调试信息
        logger.info(f"提取到的@用户列表: {at_users}")

        # 如果没有@用户，则不处理（只处理@用户的情况）
        if not at_users:
            logger.info("未提取到@用户，不处理表情生成")
            return

        # 清理后的内容（移除@用户部分）
        clean_content = self.clean_at_text(content)
        logger.info(f"清理@后的内容: {clean_content}")

        # 检查表情是否被禁用
        group_id = from_wxid if is_group else None

        # 如果清理后的内容为空，尝试从原始内容中提取触发词
        if not clean_content:
            # 尝试提取常见的触发词
            for trigger_word in self.single_emojis.keys():
                if trigger_word in content:
                    clean_content = trigger_word
                    logger.info(f"从原始内容中提取到触发词: {clean_content}")
                    break

        if (clean_content in self.globally_disabled_emojis or
            (group_id in self.disabled_emojis and clean_content in self.disabled_emojis[group_id])):
            logger.info(f"表情 {clean_content} 已被禁用，不处理")
            return

        # 处理双人表情：格式为 "@用户A 触发词 @用户B"
        if len(at_users) >= 2:
            logger.info("检测到至少两个@用户，尝试生成双人表情")
            # 尝试查找双人表情触发词
            for trigger_word, emoji_type in self.two_person_emojis.items():
                if trigger_word in content:
                    logger.info(f"找到双人表情触发词: {trigger_word}, 类型: {emoji_type}")
                    # 获取第一个被@用户的头像
                    first_avatar = await self.download_avatar(bot, at_users[0], from_wxid if is_group else None)
                    if not first_avatar:
                        await bot.send_text_message(from_wxid, f"无法获取用户 {at_users[0]} 的头像")
                        return

                    # 获取第二个被@用户的头像
                    second_avatar = await self.download_avatar(bot, at_users[1], from_wxid if is_group else None)
                    if not second_avatar:
                        await bot.send_text_message(from_wxid, f"无法获取用户 {at_users[1]} 的头像")
                        return

                    # 生成并发送双人表情
                    await self.generate_and_send_meme(bot, from_wxid, emoji_type, [first_avatar, second_avatar], two_person=True)
                    logger.info(f"生成双人表情：{trigger_word}，使用用户 {at_users[0]} 和 {at_users[1]} 的头像")
                    return

            logger.info("未找到匹配的双人表情触发词")

        # 处理单人表情：格式为 "@用户 触发词"
        if len(at_users) == 1:
            logger.info("检测到一个@用户，尝试生成单人表情")
            # 检查消息中的所有单人表情触发词
            for trigger_word, emoji_type in self.single_emojis.items():
                if trigger_word in content:
                    logger.info(f"找到单人表情触发词: {trigger_word}, 类型: {emoji_type}")
                    # 获取被@用户的头像
                    avatar_path = await self.download_avatar(bot, at_users[0], from_wxid if is_group else None)
                    if avatar_path:
                        await self.generate_and_send_meme(bot, from_wxid, emoji_type, [avatar_path])
                        logger.info(f"生成单人表情：{trigger_word}，使用用户 {at_users[0]} 的头像")
                    else:
                        await bot.send_text_message(from_wxid, f"无法获取用户 {at_users[0]} 的头像")
                    return

            logger.info("未找到匹配的单人表情触发词")

        logger.info("消息处理完毕，没有找到匹配的表情生成条件")

    async def generate_and_send_meme(self, bot, to_wxid, emoji_type, avatars, two_person=False):
        """生成并发送表情包"""
        try:
            # 获取或创建meme生成器
            if emoji_type not in self.meme_cache:
                self.meme_cache[emoji_type] = get_meme(emoji_type)

            meme_gen = self.meme_cache[emoji_type]

            # 生成表情 - 使用更适合微信的GIF参数
            result = meme_gen(images=avatars, texts=[], args={
                "circle": True,
                "gif": True,
                "gif_fps": 8,  # 降低帧率
                "image_size": (235, 196),  # 使用与微信表情相同的尺寸
                "optimize": True,  # 优化GIF
                "quality": 75,  # 降低质量以减小文件大小
                "duration": 120  # 控制每帧的持续时间（毫秒）
            })

            # 处理协程结果
            if asyncio.iscoroutine(result):
                buf_gif = await result
            else:
                buf_gif = result

            # 保存为临时GIF文件
            temp_gif_path = os.path.join(self.temp_dir, f"temp_meme_{int(time.time())}.gif")
            with open(temp_gif_path, "wb") as f:
                f.write(buf_gif.getvalue())

            logger.info(f"生成的GIF表情已保存到: {temp_gif_path}")

            # 确保文件已写入并关闭
            logger.info(f"已生成GIF文件: {temp_gif_path}")

            # 尝试使用文件上传API上传文件，然后使用表情API发送
            try:
                # 上传文件到服务器
                try:
                    # 使用新的upload_file方法上传GIF文件
                    upload_result = await bot.upload_file(temp_gif_path)
                    logger.info(f"文件上传成功: {upload_result}")

                    # 从上传结果中获取mediaId和总长度
                    media_id = upload_result.get("mediaId")
                    total_length = upload_result.get("totalLen")

                    # 计算文件的真实MD5值
                    with open(temp_gif_path, "rb") as f:
                        file_data = f.read()
                        real_md5 = hashlib.md5(file_data).hexdigest()
                        file_size = len(file_data)

                    # 尝试从 mediaId 中提取信息
                    cdn_info = {}
                    if media_id and media_id.startswith("@cdn_"):
                        # 尝试提取最后一个下划线前的部分
                        parts = media_id.split("_")
                        if len(parts) >= 2:
                            # 最后一个下划线前的部分可能包含文件信息
                            cdn_info["filekey"] = parts[-2]
                            # 尝试提取storeid
                            match = re.search(r'storeid=([^&]+)', media_id)
                            if match:
                                cdn_info["storeid"] = match.group(1)

                        logger.info(f"从 mediaId 提取的CDN信息: {cdn_info}")

                    logger.info(f"文件的真实MD5值: {real_md5}, 大小: {file_size} 字节")

                    # 只发送静态图片
                    logger.info(f"发送静态图片: {emoji_type}")
                    # 直接使用图片API发送静态图片
                    image_data = buf_gif.getvalue()
                    static_result = await bot.send_image_message(to_wxid, image_data)
                    logger.info(f"成功发送静态图片: {emoji_type}, 返回结果: {static_result}")



                    # 等待一秒
                    await asyncio.sleep(1)

                    # 尝试使用真实MD5值发送表情
                    try:
                        logger.info(f"尝试使用真实MD5发送表情: {emoji_type}, MD5: {real_md5}")

                        # 使用简化的XML结构，使用机器人自己的wxid作为fromusername
                        # 生成一个随机的 aeskey
                        aeskey = "".join([format(random.randint(0, 255), "02x") for _ in range(16)])

                        # 构建简化的表情XML
                        emoji_xml = f"""<msg>
                        <emoji
                        fromusername = \"{bot.wxid}\"
                        tousername = \"{to_wxid}\"
                        type=\"2\"
                        idbuffer=\"media:0_0\"
                        md5=\"{real_md5}\"
                        len = \"{file_size}\"
                        androidmd5=\"{real_md5}\"
                        androidlen=\"{file_size}\"
                        cdnurl = \"http://wxapp.tc.qq.com/262/20304/stodownload?m={real_md5}\"
                        aeskey= \"{aeskey}\"
                        width= \"235\"
                        height= \"196\"
                        ></emoji>
                        </msg>"""

                        logger.info(f"尝试使用更完整的XML发送表情")

                        # 优化的表情发送流程: 先发送，再下载，再发送

                        # 步骤1: 先尝试发送表情（即使不成功）
                        # 这一步可能会在服务器上注册表情
                        try:
                            logger.info(f"第1步: 先尝试发送表情 {emoji_type}, MD5: {real_md5}, 大小: {file_size}字节")
                            emoji_result = await bot.send_emoji_message(to_wxid, real_md5, file_size)
                            logger.info(f"第1步成功: 表情发送返回结果: {emoji_result}")

                            # 尝试将返回结果发送到文件助手以便于分析
                            try:
                                await bot.send_text_message("filehelper", f"第1步表情发送返回结果: {emoji_result}")
                            except Exception as fh_err:
                                logger.warning(f"发送表情返回结果到文件助手失败: {str(fh_err)}")
                        except Exception as emoji_err:
                            logger.warning(f"第1步失败: 发送表情失败: {str(emoji_err)}")

                        # 等待一秒，给服务器时间处理
                        await asyncio.sleep(1)

                        # 步骤2: 下载表情
                        # 这一步可能会触发服务器生成必要的链接
                        try:
                            logger.info(f"第2步: 尝试下载表情 {emoji_type}, MD5: {real_md5}")
                            download_result = await bot.download_emoji(real_md5)
                            logger.info(f"第2步成功: 表情下载结果: {download_result}")

                            # 尝试将下载结果发送到文件助手以便于分析
                            try:
                                await bot.send_text_message("filehelper", f"第2步表情下载结果: {download_result}")
                            except Exception as fh_err:
                                logger.warning(f"发送表情下载结果到文件助手失败: {str(fh_err)}")
                        except Exception as download_err:
                            logger.warning(f"第2步失败: 下载表情失败: {str(download_err)}")

                        # 等待一秒，给服务器时间处理
                        await asyncio.sleep(1)

                        # 步骤3: 再次发送表情
                        # 这一步可能会成功，因为服务器已经有了这个表情的记录
                        try:
                            # 尝试发送给自己
                            self_wxid = bot.wxid  # 机器人自己的wxid
                            logger.info(f"第3步: 再次尝试发送表情 {emoji_type}, MD5: {real_md5}, 大小: {file_size}字节, 发送给自己: {self_wxid}")
                            emoji_result2 = await bot.send_emoji_message(self_wxid, real_md5, file_size)
                            logger.info(f"第3步成功: 第二次表情发送返回结果: {emoji_result2}")

                            # 尝试将返回结果发送到文件助手以便于分析
                            try:
                                await bot.send_text_message("filehelper", f"第3步表情发送返回结果: {emoji_result2}")
                            except Exception as fh_err:
                                logger.warning(f"发送第二次表情返回结果到文件助手失败: {str(fh_err)}")

                            # 尝试将表情发送到文件助手
                            try:
                                logger.info(f"尝试将表情发送到文件助手: {emoji_type}, MD5: {real_md5}")
                                filehelper_result = await bot.send_emoji_message("filehelper", real_md5, file_size)
                                logger.info(f"文件助手表情发送结果: {filehelper_result}")
                            except Exception as fh_err:
                                logger.warning(f"发送表情到文件助手失败: {str(fh_err)}")

                            # 也发送到原始目标（群聊）
                            try:
                                logger.info(f"也尝试发送到原始目标: {to_wxid}")
                                group_result = await bot.send_emoji_message(to_wxid, real_md5, file_size)
                                logger.info(f"原始目标发送结果: {group_result}")
                            except Exception as group_err:
                                logger.warning(f"发送到原始目标失败: {str(group_err)}")

                            return
                        except Exception as emoji_err2:
                            logger.warning(f"第3步失败: 第二次发送表情失败: {str(emoji_err2)}")

                        # 如果所有方法都失败，尝试使用CDN文件发送方式

                        # 方法3: 尝试使用CDN文件发送方式
                        try:
                            cdn_result = await bot.send_cdn_file_msg(to_wxid, emoji_xml)
                            logger.info(f"成功发送动态表情(使用CDN文件API): {emoji_type}, MD5: {real_md5}")
                            logger.info(f"CDN文件发送返回结果: {cdn_result}")

                            # 尝试将返回结果发送到文件助手以便于分析
                            try:
                                await bot.send_text_message("filehelper", f"CDN文件发送返回结果: {cdn_result}")
                            except Exception as fh_err:
                                logger.warning(f"发送CDN返回结果到文件助手失败: {str(fh_err)}")
                            return
                        except Exception as cdn_err:
                            logger.warning(f"使用CDN文件API发送表情失败: {str(cdn_err)}")

                        # 所有方法都失败，返回错误
                        logger.error(f"所有发送表情的方法都失败了")
                        return
                    except Exception as md5_err:
                        logger.warning(f"使用真实MD5发送表情失败: {str(md5_err)}")

                        # 如果使用真实MD5失败，尝试使用mediaId
                        if media_id and total_length:
                            try:
                                # 尝试使用mediaId作为MD5发送
                                logger.info(f"尝试使用mediaId发送表情: {emoji_type}, mediaId: {media_id}")
                                await bot.send_emoji_message(to_wxid, media_id, total_length)
                                logger.info(f"成功发送动态表情(通过文件上传): {emoji_type}, mediaId: {media_id}, 大小: {total_length}字节")
                                return
                            except Exception as media_err:
                                logger.warning(f"使用mediaId发送表情失败: {str(media_err)}")
                    if not media_id or not total_length:
                        logger.warning(f"上传文件成功但未返回mediaId或总长度: {upload_result}")
                except Exception as upload_err:
                    logger.warning(f"文件上传失败，尝试直接使用表情API: {str(upload_err)}")

                    # 如果文件上传失败，尝试直接使用表情API
                    # 从文件计算MD5和总长度
                    with open(temp_gif_path, "rb") as f:
                        file_data = f.read()
                        md5_hash = hashlib.md5(file_data).hexdigest()
                        total_length = len(file_data)

                    try:
                        await bot.send_emoji_message(to_wxid, md5_hash, total_length)
                        logger.info(f"成功发送动态表情(直接使用Emoji API): {emoji_type}, MD5: {md5_hash}, 大小: {total_length}字节")
                        return
                    except Exception as emoji_err:
                        logger.warning(f"使用Emoji API发送失败，尝试使用图片API: {str(emoji_err)}")

                # 如果表情API失败，回退到图片API
                await bot.send_image_message(to_wxid, temp_gif_path)
                logger.info(f"成功发送表情(图片API): {emoji_type}")
            except Exception as img_err:
                logger.error(f"发送表情图片失败: {str(img_err)}")
                # 尝试再次发送
                try:
                    await bot.send_image_message(to_wxid, temp_gif_path)
                    logger.info(f"成功发送表情(再次尝试): {emoji_type}")
                except Exception as retry_err:
                    logger.error(f"再次发送表情失败: {str(retry_err)}")
                    await bot.send_text_message(to_wxid, f"发送表情失败，请稍后再试")

        except Exception as e:
            logger.error(f"生成表情失败: {str(e)}")
            await bot.send_text_message(to_wxid, f"生成表情失败: {str(e)}")

    async def download_avatar(self, bot, wxid, from_wxid=None, force_update=False):
        """下载用户头像并保存到临时目录"""
        try:
            # 定义头像文件路径
            avatar_path = os.path.join(self.avatar_dir, f"{wxid}.jpg")

            # 创建缓存目录
            os.makedirs(self.avatar_dir, exist_ok=True)

            avatar_url = None
            avatar_source = "未知"

            # 1. 优先使用get_contact方法获取头像
            try:
                # 直接使用API获取联系人信息
                async with aiohttp.ClientSession() as session:
                    json_param = {"Wxid": bot.wxid, "Towxids": wxid}
                    response = await session.post(f'http://{bot.ip}:{bot.port}/VXAPI/Friend/GetContractDetail', json=json_param)
                    json_resp = await response.json()

                    if json_resp.get("Success") and json_resp.get("Data") and json_resp.get("Data").get("ContactList"):
                        profile = json_resp.get("Data").get("ContactList")[0]
                        logger.info(f"获取到用户资料: {profile}")
                        if "BigHeadImgUrl" in profile and profile["BigHeadImgUrl"]:
                            avatar_url = profile["BigHeadImgUrl"]
                            avatar_source = "联系人信息"
                        elif "SmallHeadImgUrl" in profile and profile["SmallHeadImgUrl"]:
                            avatar_url = profile["SmallHeadImgUrl"]
                            avatar_source = "联系人信息"
            except Exception as e:
                logger.warning(f"通过GetContact API获取头像失败: {str(e)}")

            # 2. 如果是群聊消息，尝试从群获取用户头像
            if not avatar_url and from_wxid and "@chatroom" in from_wxid:
                try:
                    # 使用新的API获取群成员信息
                    async with aiohttp.ClientSession() as session:
                        json_param = {"Wxid": bot.wxid, "QID": from_wxid, "ToWxid": wxid}
                        response = await session.post(f'http://{bot.ip}:{bot.port}/VXAPI/Group/GetSomeMemberInfo', json=json_param)
                        json_resp = await response.json()

                        if json_resp.get("Success") and json_resp.get("Data"):
                            member_info = json_resp.get("Data")
                            logger.info(f"获取到群成员信息: {member_info}")

                            # 提取头像URL
                            if "BigHeadImgUrl" in member_info and member_info["BigHeadImgUrl"]:
                                avatar_url = member_info["BigHeadImgUrl"]
                                avatar_source = "群成员信息"
                            elif "SmallHeadImgUrl" in member_info and member_info["SmallHeadImgUrl"]:
                                avatar_url = member_info["SmallHeadImgUrl"]
                                avatar_source = "群成员信息"
                            elif "HeadImgUrl" in member_info and member_info["HeadImgUrl"]:
                                avatar_url = member_info["HeadImgUrl"]
                                avatar_source = "群成员信息"

                except Exception as e:
                    logger.warning(f"从群成员列表获取头像失败: {str(e)}")

            # 3. 如果前两种方式都失败，尝试通过个人资料API获取
            if not avatar_url:
                try:
                    # 使用User/GetContractProfile API获取用户资料
                    async with aiohttp.ClientSession() as session:
                        json_param = {"wxid": wxid}
                        response = await session.post(f'http://{bot.ip}:{bot.port}/VXAPI/User/GetContractProfile', json=json_param)
                        json_resp = await response.json()

                        if json_resp.get("Success") and json_resp.get("Data"):
                            user_info = json_resp.get("Data")
                            logger.info(f"获取到用户资料(GetContractProfile): {user_info}")
                            # 尝试各种可能的头像字段名
                            for field in ["smallHeadImgUrl", "avatar", "avatarUrl", "headImgUrl", "BigHeadImgUrl", "SmallHeadImgUrl"]:
                                if field in user_info and user_info[field]:
                                    avatar_url = user_info[field]
                                    avatar_source = "个人资料"
                                    break

                except Exception as e:
                    logger.warning(f"通过个人资料API获取头像失败: {str(e)}")

            # 如果获取不到头像URL，返回None
            if not avatar_url:
                logger.error(f"无法获取用户 {wxid} 的头像")
                return None

            # 下载头像
            logger.info(f"下载头像: {avatar_url} (来源: {avatar_source})")
            try:
                async with aiohttp.ClientSession() as session:
                    # 添加超时设置
                    timeout = aiohttp.ClientTimeout(total=10)
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                    }

                    async with session.get(avatar_url, headers=headers, timeout=timeout) as resp:
                        if resp.status == 200:
                            # 直接保存到头像文件
                            with open(avatar_path, "wb") as f:
                                avatar_data = await resp.read()
                                f.write(avatar_data)

                            # 检查下载的文件是否有效
                            if os.path.exists(avatar_path) and os.path.getsize(avatar_path) > 100:
                                logger.info(f"头像下载成功: {avatar_path}")
                                return avatar_path
                            else:
                                logger.error(f"下载的头像文件无效")
                                return None
                        else:
                            logger.error(f"下载头像失败，状态码: {resp.status}")
                            return None
            except Exception as e:
                logger.error(f"下载头像异常: {str(e)}")
                return None

        except Exception as e:
            logger.error(f"获取头像过程中发生错误: {str(e)}")
            return None

    async def send_emoji_list(self, bot, to_wxid):
        """发送表情列表"""
        single_emoji_list = list(self.single_emojis.keys())
        two_person_emoji_list = list(self.two_person_emojis.keys())

        response = "【单人表情】"
        response += "、".join(single_emoji_list) if single_emoji_list else "没有单人表情触发词"

        response += "\n\n【双人表情】"
        response += "、".join(two_person_emoji_list) if two_person_emoji_list else "没有双人表情触发词"

        await bot.send_text_message(to_wxid, response)

    async def handle_enable_disable_commands(self, bot, message):
        """处理表情的启用/禁用命令"""
        content = message.get("Content", "").strip()
        from_wxid = message.get("FromWxid", "")
        is_group = message.get("IsGroup", False)
        actual_user_id = message.get("ActualUserWxid", "")

        # 检查权限
        admin_users = self.get_admin_users()
        if actual_user_id not in admin_users:
            await bot.send_text_message(from_wxid, "只有管理员才有权执行此操作！")
            return

        # 解析命令
        match = re.match(r'^(全局)?(禁用|启用)表情\s+(.+)$', content)
        if not match:
            return

        is_global, action, emoji_name = match.groups()

        # 检查表情是否存在
        emoji_type = self.single_emojis.get(emoji_name)
        if not emoji_type and emoji_name not in self.two_person_emojis:
            await bot.send_text_message(from_wxid, "未找到指定的表情！")
            return

        group_id = from_wxid if is_group else None

        if is_global:  # 全局控制
            if action == "禁用":
                self.globally_disabled_emojis.add(emoji_name)
                await bot.send_text_message(from_wxid, f"已全局禁用表情：{emoji_name}")
            else:  # 启用
                self.globally_disabled_emojis.discard(emoji_name)
                await bot.send_text_message(from_wxid, f"已全局启用表情：{emoji_name}")
        else:  # 群组控制
            if group_id:
                if action == "禁用":
                    if group_id not in self.disabled_emojis:
                        self.disabled_emojis[group_id] = set()
                    self.disabled_emojis[group_id].add(emoji_name)
                    await bot.send_text_message(from_wxid, f"已在当前群禁用表情：{emoji_name}")
                else:  # 启用
                    if group_id in self.disabled_emojis:
                        self.disabled_emojis[group_id].discard(emoji_name)
                        await bot.send_text_message(from_wxid, f"已在当前群启用表情：{emoji_name}")
            else:
                await bot.send_text_message(from_wxid, "该命令只能在群聊中使用")

    def extract_at_users(self, content, message):
        """从消息内容中提取被@的用户wxid"""
        at_users = []

        # 输出原始消息内容中的AtUserList字段
        logger.info(f"原始消息AtUserList: {message.get('AtUserList', 'None')}, Ats: {message.get('Ats', 'None')}")

        # 从消息对象中提取被@用户
        if "AtUserList" in message and isinstance(message["AtUserList"], list):
            at_users = message["AtUserList"]
            logger.info(f"从AtUserList获取到的@用户: {at_users}")
        elif "Ats" in message and isinstance(message["Ats"], list):
            at_users = message["Ats"]
            logger.info(f"从Ats获取到的@用户: {at_users}")

        # 如果从消息中提取不到@用户，尝试从MsgSource中提取
        if not at_users and "MsgSource" in message:
            try:
                msg_source = message["MsgSource"]
                # 尝试提取atuserlist
                match = re.search(r'<atuserlist><![CDATA\[(.+?)\]\]></atuserlist>', msg_source)
                if match:
                    user_list = match.group(1)
                    # 去除开头的逗号
                    if user_list.startswith(','):
                        user_list = user_list[1:]
                    at_users = user_list.split(',')
                    logger.info(f"从MsgSource提取到的@用户: {at_users}")
            except Exception as e:
                logger.error(f"从MsgSource提取@用户失败: {str(e)}")

        # 检查at_users是否为空
        if not at_users:
            logger.warning("未能从消息中提取到@用户")

        return at_users

    def clean_at_text(self, content):
        """移除所有@部分并返回清理后的字符串"""
        # 修改正则表达式，避免过度清理
        clean_content = re.sub(r'@[\u4e00-\u9fa5a-zA-Z0-9_\^\-~\*]+(?:\s*[\u4e00-\u9fa5a-zA-Z0-9_\^\-~\*]+)*\s*', '', content)
        result = clean_content.strip()
        logger.debug(f"原内容: '{content}', 清理后: '{result}'")

        # 如果清理后的内容为空，则直接返回原始内容中的非@部分
        if not result and content:
            # 尝试提取非@部分，如“拍”、“打”等触发词
            words = content.split()
            for word in words:
                if not word.startswith('@'):
                    return word

        return result

    def get_admin_users(self):
        """获取管理员用户列表"""
        try:
            # 首先尝试从全局配置文件获取管理员列表
            global_admins = []
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)

                    # 尝试获取管理员列表
                    if "admin_users" in config:
                        global_admins.extend(config["admin_users"])
                    if "admins" in config:
                        global_admins.extend(config["admins"])
                except Exception as e:
                    logger.warning(f"读取全局管理员配置失败: {str(e)}")

            # 合并全局管理员和本地管理员
            all_admins = set(global_admins + self.local_admin_users)
            return list(all_admins)
        except Exception as e:
            logger.error(f"获取管理员列表失败: {str(e)}")
            # 发生错误时返回本地管理员列表作为后备
            return self.local_admin_users

    async def async_init(self):
        """异步初始化函数"""
        pass

    @schedule('interval', hours=24)
    async def cleanup_avatar_cache(self, bot: WechatAPIClient):
        """定期清理头像缓存"""
        if not self.enable:
            return

        logger.info("开始清理头像缓存...")
        try:
            current_time = time.time()
            avatars_cleaned = 0
            total_files = 0

            # 获取所有缓存文件
            for filename in os.listdir(self.avatar_dir):
                total_files += 1
                filepath = os.path.join(self.avatar_dir, filename)

                # 跳过目录
                if os.path.isdir(filepath):
                    continue

                # 检查是否是头像文件
                if filename.endswith('.jpg'):
                    wxid = filename[:-4]  # 移除.jpg后缀

                    # 检查使用计数和最后更新时间
                    use_count_file = os.path.join(self.avatar_dir, f"{wxid}.count")
                    last_update_file = os.path.join(self.avatar_dir, f"{wxid}.update")

                    should_remove = False

                    # 如果存在使用计数文件，检查使用次数
                    if os.path.exists(use_count_file):
                        try:
                            with open(use_count_file, 'r') as f:
                                count = int(f.read().strip())

                            # 如果使用次数少于配置的阈值，并且超过配置的天数未更新，删除文件
                            if count < self.cleanup_threshold and os.path.exists(last_update_file):
                                try:
                                    with open(last_update_file, 'r') as f:
                                        last_update = float(f.read().strip())

                                    if current_time - last_update > self.cleanup_expire_days * 86400:
                                        should_remove = True
                                except:
                                    pass
                        except:
                            pass

                    # 执行清理
                    if should_remove:
                        try:
                            # 删除所有相关文件
                            for ext in ['.jpg', '.mark', '.update', '.count', '.tmp']:
                                ext_file = os.path.join(self.avatar_dir, f"{wxid}{ext}")
                                if os.path.exists(ext_file):
                                    os.remove(ext_file)
                                    avatars_cleaned += 1
                        except Exception as e:
                            logger.error(f"清理头像文件失败: {str(e)}")

            logger.info(f"头像缓存清理完成。共清理 {avatars_cleaned} 个文件，剩余 {total_files - avatars_cleaned} 个文件。")

        except Exception as e:
            logger.error(f"清理头像缓存过程中发生错误: {str(e)}")

    async def clear_avatar_cache(self, wxid):
        """清理特定用户的头像缓存"""
        files_removed = 0
        for ext in ['.jpg', '.mark', '.update', '.count', '.tmp']:
            ext_file = os.path.join(self.avatar_dir, f"{wxid}{ext}")
            if os.path.exists(ext_file):
                os.remove(ext_file)
                files_removed += 1
        return files_removed

    async def clear_all_avatar_cache(self):
        """清理所有头像缓存"""
        current_time = time.time()
        avatars_cleaned = 0

        # 获取所有缓存文件
        for filename in os.listdir(self.avatar_dir):
            filepath = os.path.join(self.avatar_dir, filename)

            # 跳过目录
            if os.path.isdir(filepath):
                continue

            # 清理所有临时文件
            if filename.endswith('.tmp'):
                os.remove(filepath)
                avatars_cleaned += 1
                continue

            # 检查是否是头像文件
            if filename.endswith('.jpg'):
                wxid = filename[:-4]  # 移除.jpg后缀

                # 检查是否超过3天未使用
                last_update_file = os.path.join(self.avatar_dir, f"{wxid}.update")
                if os.path.exists(last_update_file):
                    try:
                        with open(last_update_file, 'r') as f:
                            last_update = float(f.read().strip())

                        # 如果超过3天未使用，删除文件
                        if current_time - last_update > 3 * 86400:  # 3天
                            for ext in ['.jpg', '.mark', '.update', '.count']:
                                ext_file = os.path.join(self.avatar_dir, f"{wxid}{ext}")
                                if os.path.exists(ext_file):
                                    os.remove(ext_file)
                                    avatars_cleaned += 1
                    except:
                        pass

        return avatars_cleaned