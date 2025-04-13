# 硅基流动 API 兼容插件 🚀

## 简介

硅基流动 API 兼容插件为 XYBot 提供了标准的硅基流动 API 接口，使您可以将机器人与任何支持硅基流动 API 的应用程序集成。这个插件创建了一个本地 API 服务器，它可以将请求转发到硅基流动的 API 服务。

## 特性

- **标准硅基流动 API 兼容性**：完全兼容硅基流动 API 的请求和响应格式 ✅
- **丰富的模型支持**：支持硅基流动平台上的各种模型，包括通义千问、GLM等 🤖
- **安全访问控制**：可以设置 API 密钥验证 🔐
- **积分系统集成**：支持使用 XYBot 的积分系统控制 API 使用 💰
- **代理支持**：支持配置 HTTP 代理，解决网络访问问题 🌐

## 安装

1. 将插件文件夹复制到 `plugins` 目录
2. 编辑 `config.toml` 配置文件，设置您的硅基流动 API 密钥
3. 重启 XYBot 或使用管理命令加载插件

## 配置说明

```toml
[SiliconFlowAPI]
enable = true                           # 是否启用此功能
api-key = ""                            # 硅基流动API密钥，必填
base-url = "https://api.siliconflow.cn/v1"  # 硅基流动API地址

# 模型配置
default-model = "Qwen/QwQ-32B"          # 默认使用的模型
available-models = [                    # 可用模型列表
    "Qwen/QwQ-32B",
    "Qwen/Qwen2.5-72B-Instruct",
    "Qwen/Qwen2.5-32B-Instruct",
    "Qwen/Qwen2.5-14B-Instruct",
    "Qwen/Qwen2.5-7B-Instruct",
    "THUDM/glm-4-9b-chat",
    "deepseek-ai/DeepSeek-R1"
]

# 插件配置
port = 8200                             # API服务端口
host = "0.0.0.0"                        # API服务主机

# 积分系统
price = 0                               # 每次使用扣除的积分，0表示不扣除
admin_ignore = true                     # 管理员是否忽略积分扣除
whitelist_ignore = true                 # 白名单用户是否忽略积分扣除

# Http代理设置
http-proxy = ""                         # HTTP代理设置

# 高级设置
max_tokens = 4096                       # 最大token数
temperature = 0.7                       # 温度参数
top_p = 0.7                             # Top-p采样
top_k = 50                              # Top-k采样
frequency_penalty = 0.5                 # 频率惩罚
```

## 使用方法

1. 启用插件后，API 服务器将在配置的端口上启动
2. 使用标准的硅基流动 API 客户端连接到 `http://你的IP:配置的端口`
3. 在请求中使用您的硅基流动 API 密钥

### 示例（Python）

```python
import requests
import json

# 设置API基础URL为你的机器人地址
api_base = "http://你的IP:8200/v1"
# 使用你的硅基流动API密钥
api_key = "你的API密钥"

# 发送聊天请求
response = requests.post(
    f"{api_base}/chat/completions",
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    },
    json={
        "model": "Qwen/QwQ-32B",
        "messages": [
            {"role": "user", "content": "你好，请介绍一下自己。"}
        ],
        "temperature": 0.7,
        "max_tokens": 1024
    }
)

print(json.dumps(response.json(), ensure_ascii=False, indent=2))
```

## 支持的API端点

- `/v1/chat/completions` - 聊天完成API
- `/v1/models` - 模型列表API

## 注意事项

- 此插件需要安装额外的依赖：`fastapi` 和 `uvicorn`
- 确保配置的端口未被其他应用占用
- 如果使用代理，确保代理服务器正常工作
- 需要有效的硅基流动 API 密钥

## 故障排除

- 如果API服务无法启动，检查端口是否被占用
- 如果请求失败，检查硅基流动 API 密钥是否正确
- 如果响应速度慢，考虑使用代理

## 开发者信息

- 作者：XYBot团队
- 版本：1.0.0
- 许可证：MIT
