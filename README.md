# 🤖 XXXBot 机器人项目 🤖

## 📝 项目概述

XXXBot 是一个基于微信的智能机器人系统，通过整合多种 API 和功能，提供了丰富的交互体验。本系统包含管理后台界面，支持插件扩展，具备联系人管理、文件管理、系统状态监控等功能，同时与人工智能服务集成，提供智能对话能力。系统支持多种微信接口，包括 PAD 协议和 WeChatAPI，可根据需要灵活切换。

## ✨ 主要特性

### 1. 💻 管理后台

- 📊 **控制面板**：系统概览、机器人状态监控
- 🔌 **插件管理**：安装、配置、启用/禁用各类功能插件
- 📁 **文件管理**：上传、查看和管理机器人使用的文件
- 📵 **联系人管理**：微信好友和群组联系人管理
- 📈 **系统状态**：查看系统资源占用和运行状态

### 2. 💬 聊天功能

- 📲 **私聊互动**：与单个用户的一对一对话
- 👥 **群聊响应**：在群组中通过@或特定命令触发
- 📞 **聊天室模式**：支持多人持续对话，带有用户状态管理
- 💰 **积分系统**：对话消耗积分，支持不同模型不同积分定价
- 📸 **朋友圈功能**：支持查看、点赞和评论朋友圈

### 3. 🤖 智能对话

- 🔍 **多模型支持**：可配置多种 AI 模型，支持通过关键词切换
- 📷 **图文结合**：支持图片理解和多媒体输出
- 🎤 **语音交互**：支持语音输入识别和语音回复
- 😍 **语音撒娇**：支持甜美语音撒娇功能

### 4. 🔗 插件系统

- 🔌 **插件管理**：支持加载、卸载和重载插件
- 🔧 **自定义插件**：可开发和加载自定义功能插件
- 🤖 **Dify 插件**：集成 Dify API，提供高级 AI 对话能力
- ⏰ **定时提醒**：支持设置定时提醒和日程管理
- 👋 **群欢迎**：自动欢迎新成员加入群聊
- 🌅 **早安问候**：每日早安问候功能

## 📍 安装指南

### 📦 系统要求

- 🐍 Python 3.11+
- 📱 微信客户端（支持 PAD 协议或 WeChatAPI）
- 🔋 Redis（用于数据缓存）
- 🎥 FFmpeg（用于语音处理）
- 🐳 Docker（可选，用于容器化部署）

### 📝 安装步骤

#### 🔹 方法一：直接安装

1. **克隆代码库**

   ```bash
   git clone https://github.com/NanSsye/XXXBot.git
   cd XXXBot
   ```

2. **安装依赖**

   ```bash
   pip install -r requirements.txt
   ```

3. **安装 Redis**

   - Windows: 下载 Redis for Windows
   - Linux: `sudo apt-get install redis-server`
   - macOS: `brew install redis`

4. **安装 FFmpeg**

   - Windows: 下载安装包并添加到系统 PATH
   - Linux: `sudo apt-get install ffmpeg`
   - macOS: `brew install ffmpeg`

5. **配置**

   - 复制`main_config.toml.example`为`main_config.toml`并填写配置
   - 设置管理员 ID 和其他基本参数

6. **启动必要的服务**

   **Windows 用户需要先启动 Redis 和 PAD 服务**（注意启动顺序！）：

   - ❗ **第一步**：启动 Redis 服务 🔋

     - 进入`849/redis`目录，双击`redis-server.exe`文件
     - 等待窗口显示 Redis 启动成功

   - ❗ **第二步**：启动 PAD 服务 📱

     - 进入`849/pad`目录，双击`linuxService.exe`文件
     - 等待窗口显示 PAD 服务启动成功

   - ⚠️ 请确保这两个服务窗口始终保持打开状态，不要关闭它们！

   **然后启动主服务**：

   ```bash
   python app.py
   ```

#### 🔺 方法二：Docker 安装 🐳

1. **克隆代码库**

   ```bash
   git clone https://github.com/NanSsye/XXXBot.git
   cd XXXBot
   ```

2. **构建 Docker 镜像**

   ```bash
   docker build -t xxxbot .
   ```

3. **启动容器**

   ```bash
   docker run -d -p 9090:9090 -v $(pwd)/data:/app/data -v $(pwd)/config:/app/config --name xxxbot xxxbot
   ```

### 🔍 访问后台

- 🌐 打开浏览器访问 `http://localhost:9090` 进入管理界面
- 👤 默认用户名：`admin`
- 🔑 默认密码：`admin123`

## ⚙️ 配置详解

### 📓 主配置文件

```toml
[XXXBot]
admins = ["admin_wxid"]  # 管理员微信ID列表
enable_plugin_market = true  # 是否启用插件市场

[Redis]
host = "localhost"
port = 6378
db = 0
password = ""

[PAD]
enable = true
api_url = "http://localhost:9011"
```

### 🤖 Dify 插件配置

```toml
[Dify]
enable = true
default-model = "model1"
command-tip = true
commands = ["ai", "机器人", "gpt"]
admin_ignore = true
whitelist_ignore = true
http-proxy = ""
voice_reply_all = false
robot-names = ["机器人", "小助手"]
remember_user_model = true
chatroom_enable = true

[Dify.models.model1]
api-key = "your_api_key"
base-url = "https://api.dify.ai/v1"
trigger-words = ["dify", "小d"]
price = 10
wakeup-words = ["你好小d", "嘿小d"]
```

## 📖 使用指南

### 👑 管理员命令

- 登录管理后台查看各项功能
- 通过微信直接向机器人发送命令管理

### 💬 用户交互

- 📲 **私聊模式**：直接向机器人发送消息
- 👥 **群聊模式**：
  - 👋 @机器人 + 问题
  - 💬 使用特定命令如 `ai 问题`
  - 🔔 使用唤醒词如 `你好小d 问题`

### 📞 聊天室功能

- 👋 **加入聊天**：@机器人或使用命令
- **查看状态**：发送"查看状态"
- **暂时离开**：发送"暂时离开"
- **回来**：发送"回来了"
- **退出聊天**：发送"退出聊天"
- **查看统计**：发送"我的统计"
- **聊天排行**：发送"聊天室排行"

### 图片和语音

- 发送图片和文字组合进行图像相关提问
- 发送语音自动识别并回复
- 语音回复可根据配置自动开启

## 插件开发

### 插件目录结构

```
plugins/
  ├── YourPlugin/
  │   ├── __init__.py
  │   ├── main.py
  │   ├── config.toml
  │   └── README.md
```

### 基本插件模板

```python
from utils.plugin_base import PluginBase
from WechatAPI import WechatAPIClient
from utils.decorators import *

class YourPlugin(PluginBase):
    description = "插件描述"
    author = "作者名称"
    version = "1.0.0"

    def __init__(self):
        super().__init__()
        # 初始化代码

    @on_text_message(priority=10)
    async def handle_text(self, bot: WechatAPIClient, message: dict):
        # 处理文本消息
        pass
```

## 常见问题

1. **安装依赖失败** 💻

   - 尝试使用 `pip install --upgrade pip` 更新 pip
   - 可能需要安装开发工具: `apt-get install python3-dev`

2. **语音识别失败** 🎤

   - 确认 FFmpeg 已正确安装并添加到 PATH
   - 检查 SpeechRecognition 依赖是否正确安装

3. **无法连接微信** 📱

   - 确认微信客户端和接口版本是否匹配
   - 检查网络连接和端口设置
   - 如果使用 PAD 协议，确认 PAD 服务是否正常运行
   - ⚠️ Windows 用户请确认是否按正确顺序启动服务：先启动 Redis，再启动 PAD

4. **Redis 连接错误** 🔋

   - 确认 Redis 服务器是否正常运行
   - 🔴 Windows 用户请确认是否已启动`849/redis`目录中的`redis-server.exe`
   - 检查 Redis 端口和访问权限设置
   - 确认配置文件中的 Redis 端口是否为 6378
   - 💡 提示：Redis 窗口应显示“已就绪接受指令”或类似信息

5. **Dify API 错误** 🤖

   - 验证 API 密钥是否正确
   - 确认 API URL 格式和访问权限

6. **Docker 部署问题** 🐳

   - 确认 Docker 容器是否正常运行：`docker ps`
   - 查看容器日志：`docker logs xxxbot`
   - 检查数据卷挂载是否正确
   - 💡 注意：Docker 容器内会自动启动 PAD 和 Redis 服务，无需手动启动
   - ⚠️ Windows 用户注意：Docker 容器使用的是 Linux 环境，不能直接使用 Windows 版的可执行文件

7. **无法访问管理后台** 🛑
   - 确认服务器正常运行在 9090 端口
   - 尝试使用默认账号密码: admin/admin123
   - 检查防火墙设置是否阻止了端口访问

## 技术架构

- **后端**：Python FastAPI
- **前端**：Bootstrap, Chart.js, AOS
- **数据库**：SQLite (aiosqlite)
- **缓存**：Redis
- **微信接口**：PAD 协议或 WeChatAPI
- **外部服务**：Dify API，Google Speech-to-Text
- **容器化**：Docker
- **Web 服务**：默认端口 9090，默认账号 admin/admin123

## 项目结构

```
XXXBot/
  ├── admin/                  # 管理后台
  │   ├── static/             # 静态资源
  │   ├── templates/          # HTML模板
  │   └── friend_circle_api.py # 朋友圈API
  ├── plugins/                # 插件目录
  │   ├── Dify/               # Dify插件
  │   ├── Menu/               # 菜单插件
  │   ├── SignIn/             # 签到插件
  │   └── YujieSajiao/        # 语音撒娇插件
  ├── database/               # 数据库相关
  ├── utils/                  # 工具函数
  ├── WechatAPI/              # 微信API接口
  ├── 849/                    # PAD协议相关
  │   ├── pad/               # PAD协议客户端
  │   └── redis/             # Redis服务
  ├── app.py                  # 主应用入口
  ├── main.py                 # 机器人主程序
  ├── entrypoint.sh           # Docker入口脚本
  ├── Dockerfile              # Docker构建文件
  ├── requirements.txt        # 依赖列表
  └── main_config.toml        # 主配置文件
```

## 协议和许可

本项目仅供学习和研究使用，使用前请确保符合微信和相关服务的使用条款。

## 鸣谢

特别感谢所有贡献者和使用的开源项目。

## 联系方式

GitHub: [https://github.com/NanSsye](https://github.com/NanSsye)
