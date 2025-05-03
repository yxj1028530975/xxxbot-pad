# 高德地图 MCP 服务插件

这个插件为机器人提供了高德地图 MCP 服务的接入能力，可以实现天气查询、地点搜索、路径规划等功能。

## 功能介绍

该插件基于高德地图 MCP（Model Control Protocol）SSE 服务，提供以下功能：

1. 地理/逆地理编码：地址与经纬度转换
2. IP 定位：根据 IP 获取位置信息
3. 天气查询：获取城市天气信息
4. 路径规划：包含骑行、步行、驾车、公交等多种方式
5. 距离测量：计算两点之间的距离
6. 地点搜索：关键词搜索、周边搜索、详情查询

## 安装方法

1. 将插件目录放入`plugins`文件夹中
2. 安装依赖：`pip install -r plugins/AmapMCP/requirements.txt`
3. 在高德开放平台申请 API 密钥：[高德开放平台](https://lbs.amap.com/)
4. 在插件配置文件`config.toml`中填入申请的 API 密钥
5. 重启机器人

## 配置说明

修改`plugins/AmapMCP/config.toml`文件：

```toml
[basic]
# 是否启用插件
enable = true

[amap]
# 高德地图API密钥，需要在高德开放平台申请：https://lbs.amap.com/
api_key = "您的API密钥"

# MCP Server的SSE连接URL
sse_url = "https://mcp.amap.com/sse"

# 超时设置（秒）
timeout = 10

# 是否启用日志调试
debug = false
```

## 使用方法

以下是一些基本的使用指令：

1. 查询天气：`天气 城市名称`  
   例如：`天气 北京`

2. 搜索地点：`搜索 关键词 城市`  
   例如：`搜索 餐厅 上海`

## 开发文档

如需进一步开发和扩展此插件，请参考[高德 MCP Server 文档](https://lbs.amap.com/api/mcp-server/summary)

## 许可证

本插件遵循与主项目相同的许可证。
