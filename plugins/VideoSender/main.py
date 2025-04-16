import asyncio
import tomllib
from typing import Optional
import time

import aiohttp
from loguru import logger
import random
import binascii

from WechatAPI import WechatAPIClient
from utils.decorators import *
from utils.plugin_base import PluginBase
import os
import base64
import shutil
import subprocess  # 导入 subprocess 模块


class VideoSender(PluginBase):
    """
    一个点击链接获取视频并发送给用户的插件，支持多个视频源。
    """

    description = "点击链接获取视频并发送给用户的插件，支持多个视频源"
    author = "老夏的金库"
    version = "1.1.0"

    def __init__(self):
        super().__init__()
        # 确保 self.ffmpeg_path 始终有值
        self.ffmpeg_path = "/usr/bin/ffmpeg"  # 设置默认值

        # 添加一个默认的静态缩略图，Base64编码的小图片
        # 这是一个1x1像素的透明PNG图片的Base64编码
        self.default_thumbnail = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

        # 缩略图分块上传设置
        self.thumbnail_chunk_size = 40000  # 每块最大大小，小于50KB
        self.last_successful_thumbnail = None  # 保存最后一次成功的缩略图
        self.upload_delay = 1  # 上传间隔（秒）
        try:
            with open("plugins/VideoSender/config.toml", "rb") as f:
                plugin_config = tomllib.load(f)
            config = plugin_config["VideoSender"]
            self.enable = config["enable"]
            self.commands = config["commands"]
            self.ffmpeg_path = config.get("ffmpeg_path", "/usr/bin/ffmpeg")  # ffmpeg 路径
            self.video_sources = config.get("video_sources", [])  # 视频源列表

            logger.info("VideoSender 插件配置加载成功")
        except FileNotFoundError:
            logger.error("VideoSender 插件配置文件未找到，插件已禁用。")
            self.enable = False
            self.commands = ["发送视频", "来个视频"]
            self.video_sources = []
        except Exception as e:
            logger.exception(f"VideoSender 插件初始化失败: {e}")
            self.enable = False
            self.commands = ["发送视频", "来个视频"]
            self.video_sources = []

        self.ffmpeg_available = self._check_ffmpeg()  # 在配置加载完成后检查 ffmpeg

    def _check_ffmpeg(self) -> bool:
        """检查 ffmpeg 是否可用"""
        try:
            process = subprocess.run([self.ffmpeg_path, "-version"], check=False, capture_output=True)
            if process.returncode == 0:
                logger.info(f"ffmpeg 可用，版本信息：{process.stdout.decode()}")
                return True
            else:
                logger.warning(f"ffmpeg 执行失败，返回码: {process.returncode}，错误信息: {process.stderr.decode()}")
                return False
        except FileNotFoundError:
            logger.warning(f"ffmpeg 未找到，路径: {self.ffmpeg_path}")
            return False
        except Exception as e:
            logger.exception(f"检查 ffmpeg 失败: {e}")
            return False

    async def _get_video_url(self, source_name: str = "") -> str:
        """
        根据视频源名称获取视频URL。

        Args:
            source_name (str, optional): 视频源名称. Defaults to "".

        Returns:
            str: 视频URL.
        """
        if not self.video_sources:
            logger.error("没有配置视频源")
            return ""

        if source_name:
            for source in self.video_sources:
                if source["name"] == source_name:
                    url = f"{source['url']}?type=json"  # 确保请求类型为 JSON
                    logger.debug(f"使用视频源: {source['name']}")
                    break
            else:
                logger.warning(f"未找到名为 {source_name} 的视频源，随机选择一个视频源")
                url = f"{random.choice(self.video_sources)['url']}?type=json"
                logger.debug(f"随机使用视频源: {url}")
        else:
            source = random.choice(self.video_sources)
            url = f"{source['url']}?type=json"
            logger.debug(f"随机使用视频源: {source['name']}")

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
                }
                async with session.get(url, headers=headers) as response:
                    logger.debug(f"尝试获取视频源: {url}")
                    if response.status == 200:
                        json_response = await response.json()  # 解析 JSON 响应
                        video_url = json_response.get("data")  # 提取视频 URL
                        logger.info(f"获取到视频链接: {video_url}")
                        return video_url
                    else:
                        logger.error(f"获取视频失败，状态码: {response.status}")
                        return ""
        except Exception as e:
            logger.exception(f"获取视频过程中发生异常: {e}")
            return ""

    async def _download_video(self, video_url: str) -> bytes:
        """下载视频文件"""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                async with session.get(video_url) as response:
                    if response.status == 200:
                        video_data = await response.read()
                        logger.debug(f"下载的视频数据大小: {len(video_data)} bytes")
                        return video_data
                    else:
                        logger.error(f"下载视频失败，状态码: {response.status}")
                        return b""  # 返回空字节
        except Exception as e:
            logger.exception(f"下载视频过程中发生异常: {e}")
            return b""  # 返回空字节

    async def _extract_thumbnail_from_video(self, video_data: bytes) -> Optional[str]:
        """从视频数据中提取缩略图，并确保大小小于50KB"""
        temp_dir = "temp_videos"  # 创建临时文件夹
        os.makedirs(temp_dir, exist_ok=True)
        video_path = os.path.join(temp_dir, f"temp_video_{int(time.time())}.mp4")
        thumbnail_path = os.path.join(temp_dir, f"temp_thumbnail_{int(time.time())}.jpg")

        try:
            with open(video_path, "wb") as f:
                f.write(video_data)

            # 先尝试生成小尺寸的缩略图，控制在50KB以下
            process = await asyncio.create_subprocess_exec(
                self.ffmpeg_path,
                "-i", video_path,
                "-ss", "00:00:01",  # 从视频的第 1 秒开始提取
                "-vframes", "1",
                "-vf", "scale=160:120",  # 调整尺寸为很小的尺寸
                "-q:v", "15",  # 设置较低的质量（1-31，值越大质量越低）
                thumbnail_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            _, stderr = await process.communicate()

            if process.returncode != 0:
                logger.error(f"ffmpeg 执行失败: {stderr.decode()}")
                return None

            # 检查缩略图大小
            if not os.path.exists(thumbnail_path):
                logger.error("缩略图文件未生成")
                return None

            file_size = os.path.getsize(thumbnail_path)
            logger.info(f"生成的缩略图大小: {file_size} 字节")

            # 如果缩略图还是太大，尝试更极端的压缩
            if file_size > 30000:  # 如果超过30KB，再次压缩
                logger.warning(f"缩略图还是太大 ({file_size} 字节)，尝试更极端的压缩")
                compressed_path = os.path.join(temp_dir, f"compressed_{int(time.time())}.jpg")

                # 再次使用 ffmpeg 压缩图片，使用更小的尺寸和更高的压缩率
                compress_process = await asyncio.create_subprocess_exec(
                    self.ffmpeg_path,
                    "-i", thumbnail_path,
                    "-q:v", "25",  # 非常高的压缩率
                    "-vf", "scale=80:60",  # 非常小的尺寸
                    compressed_path,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )

                await compress_process.communicate()

                if os.path.exists(compressed_path):
                    thumbnail_path = compressed_path
                    file_size = os.path.getsize(thumbnail_path)
                    logger.info(f"压缩后的缩略图大小: {file_size} 字节")

                    # 如果还是太大，尝试最后的办法
                    if file_size > 30000:
                        logger.warning(f"缩略图仍然太大 ({file_size} 字节)，尝试最后的办法")
                        final_path = os.path.join(temp_dir, f"final_{int(time.time())}.jpg")

                        # 使用最小的尺寸和最高的压缩率
                        final_process = await asyncio.create_subprocess_exec(
                            self.ffmpeg_path,
                            "-i", thumbnail_path,
                            "-q:v", "31",  # 最高压缩率
                            "-vf", "scale=40:30",  # 极小尺寸
                            final_path,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE
                        )

                        await final_process.communicate()

                        if os.path.exists(final_path):
                            thumbnail_path = final_path
                            file_size = os.path.getsize(thumbnail_path)
                            logger.info(f"最终压缩后的缩略图大小: {file_size} 字节")

            # 确保缩略图小于50KB
            if os.path.getsize(thumbnail_path) > 49000:  # 留一点余量
                logger.warning("无法将缩略图压缩到足够小，使用默认缩略图")
                # 使用一个已知大小的小图片
                return "iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAAOxAAADsQBlSsOGwAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAADMSURBVDiN7ZOxCsIwFEXPi4Pg5uTgJl0c/QDpJLg5+HEtTvULOnTwE5wKDg5uLhVcGhciCFIXhw5NStM0FQQPBELeu+feJCEB/hQBZJL2kqKkpqTYOTdJvZNVgCvQAQxQB3rABahVAQZADIyAJbB2zq2AJbAARkAMDMsaZjlLgA3QBCbOuW1qwTm3BSZAyzmXlgLdQxE/ZYsH4HlgAZgDR+BeNMwA28DYe78Kw7Drve8CK2BbBfgIw3Dqvd8YY+bGmHkQBDNgU9pQ0he9AZgIHGo4/UjpAAAAAElFTkSuQmCC"

            with open(thumbnail_path, "rb") as image_file:
                image_data = image_file.read()
                image_base64 = base64.b64encode(image_data).decode("utf-8")
                # 保存成功的缩略图以便重用
                self.last_successful_thumbnail = image_base64
                return image_base64

        except FileNotFoundError:
            logger.error("ffmpeg 未找到，无法提取缩略图")
            return None
        except Exception as e:
            logger.exception(f"提取缩略图失败: {e}")
            return None
        finally:
            # 清理临时文件
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)  # 递归删除临时文件夹
            except Exception as e:
                logger.warning(f"清理临时文件失败: {e}")



    @on_text_message
    async def handle_text_message(self, bot: WechatAPIClient, message: dict):
        """处理文本消息，判断是否需要触发发送视频。"""
        if not self.enable:
            return True  # 插件未启用，继续执行后续处理

        content = message["Content"].strip()
        chat_id = message["FromWxid"]

        for command in self.commands:
            if content == command:
                if command == "随机视频":
                    source_name = ""  # 随机选择
                elif command == "视频目录":
                    source_list = "\n".join([source["name"] for source in self.video_sources])
                    await bot.send_text_message(chat_id, f"可用的视频系列：\n{source_list}")
                    return False  # 返回 False，阻止后续执行
                else:
                    source_name = command  # 命令就是视频源名称

                try:
                    video_url = await self._get_video_url(source_name)

                    if video_url:
                        logger.info(f"获取到视频链接: {video_url}")
                        video_data = await self._download_video(video_url)

                        if video_data:
                            image_base64 = None
                            if self.ffmpeg_available:
                                # 获取缩略图
                                image_base64 = await self._extract_thumbnail_from_video(video_data)

                                if image_base64:
                                    logger.info("成功提取缩略图")
                                else:
                                    logger.warning("未能成功提取缩略图")
                            else:
                                await bot.send_text_message(chat_id, "由于 ffmpeg 未安装，无法提取缩略图。")

                            try:
                                video_base64 = base64.b64encode(video_data).decode("utf-8")
                                logger.debug(f"视频 Base64 长度: {len(video_base64) if video_base64 else '无效'}")
                                logger.debug(f"图片 Base64 长度: {len(image_base64) if image_base64 else '无效'}")

                                # 确保缩略图大小小于50KB
                                if image_base64 and len(base64.b64decode(image_base64)) > 49000:
                                    logger.warning(f"缩略图大小超过49KB，使用默认缩略图")
                                    image_base64 = self.default_thumbnail

                                # 如果没有缩略图，尝试使用上次成功的缩略图
                                if not image_base64 and self.last_successful_thumbnail:
                                    logger.info("使用上次成功的缩略图")
                                    image_base64 = self.last_successful_thumbnail

                                # 如果还是没有缩略图，使用默认缩略图
                                if not image_base64:
                                    logger.info("使用默认缩略图")
                                    image_base64 = self.default_thumbnail

                                # 添加延迟，避免请求过快
                                await asyncio.sleep(1)

                                # 尝试先使用 upload_file 上传缩略图
                                try:
                                    logger.info("尝试使用 upload_file 上传缩略图")
                                    # 如果是字符串，需要解码为字节
                                    if isinstance(image_base64, str):
                                        thumbnail_data = base64.b64decode(image_base64)
                                    else:
                                        thumbnail_data = image_base64

                                    # 使用 upload_file 上传缩略图
                                    upload_result = await bot.upload_file(thumbnail_data)
                                    logger.info(f"缩略图上传成功: {upload_result}")

                                    # 从上传结果中获取 mediaId
                                    media_id = upload_result.get('mediaId')

                                    if media_id:
                                        logger.info(f"获取到媒体ID: {media_id}")
                                        # 直接使用媒体ID作为缩略图发送视频
                                        try:
                                            # 尝试使用媒体ID发送视频
                                            await bot.send_video_message(chat_id, video=video_base64, image=media_id)
                                            logger.info(f"成功使用媒体ID发送视频到 {chat_id}")
                                        except Exception as e:
                                            logger.exception(f"使用媒体ID发送视频失败: {e}")
                                            # 如果失败，尝试使用Base64发送视频
                                            await bot.send_video_message(chat_id, video=video_base64, image=image_base64)
                                            logger.info(f"成功发送视频到 {chat_id}")
                                    else:
                                        # 如果没有获取到 mediaId，直接发送视频
                                        logger.warning("未获取到媒体ID，尝试直接发送视频")
                                        await bot.send_video_message(chat_id, video=video_base64, image=image_base64)
                                        logger.info(f"成功发送视频到 {chat_id}")

                                    # 保存成功的缩略图
                                    self.last_successful_thumbnail = image_base64

                                except Exception as e:
                                    logger.exception(f"使用 upload_file 上传缩略图失败: {e}")

                                    # 如果上传失败，尝试直接发送
                                    logger.info("尝试直接发送视频")

                                    # 发送视频消息
                                    for attempt in range(3):  # 最多重试3次
                                        try:
                                            # 尝试发送视频
                                            await bot.send_video_message(chat_id, video=video_base64, image=image_base64)
                                            logger.info(f"成功发送视频到 {chat_id}")

                                            # 保存成功的缩略图
                                            self.last_successful_thumbnail = image_base64
                                            break
                                        except Exception as e:
                                            if "缩略图上传失败" in str(e) and attempt < 2:
                                                # 如果是缩略图问题，尝试使用默认缩略图
                                                logger.warning(f"缩略图上传失败，尝试使用默认缩略图，尝试次数: {attempt+1}")
                                                image_base64 = self.default_thumbnail
                                                await asyncio.sleep(2)  # 等待一段时间再重试
                                            else:
                                                # 其他错误或最后一次尝试，抛出异常
                                                raise

                            except binascii.Error as e:
                                logger.error(f"Base64 编码失败： {e}")
                                await bot.send_text_message(chat_id, "视频编码失败，请稍后重试。")

                            except Exception as e:
                                logger.exception(f"发送视频过程中发生异常: {e}")
                                # 如果发送视频失败，尝试发送链接
                                try:
                                    await bot.send_text_message(chat_id, f"发送视频失败，请点击链接直接观看: {video_url}")
                                    logger.info(f"成功发送视频链接到 {chat_id}")
                                except Exception as e2:
                                    logger.exception(f"发送视频链接文本也失败: {e2}")
                                    await bot.send_text_message(chat_id, "发送视频失败，请稍后重试。")

                        else:
                            logger.warning(f"未能下载到有效的视频数据")
                            await bot.send_text_message(chat_id, "未能下载到有效的视频，请稍后重试。")

                    else:
                        logger.warning(f"未能获取到有效的视频链接")
                        await bot.send_text_message(chat_id, "未能获取到有效的视频，请稍后重试。")

                except Exception as e:
                    logger.exception(f"处理视频过程中发生异常: {e}")
                    await bot.send_text_message(chat_id, f"处理视频过程中发生异常，请稍后重试: {e}")
                return False  # 找到匹配的命令后，结束循环并阻止后续执行

        return True  # 如果没有匹配的命令，继续执行后续处理

    async def close(self):
        """插件关闭时执行的操作。"""
        logger.info("VideoSender 插件已关闭")