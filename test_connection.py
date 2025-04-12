import requests
import aiohttp
import asyncio
import httpx

# 测试URL
url = "http://xianan.xin:1562/api/plugins"

print(f"测试连接到: {url}")

# 使用requests库测试
try:
    print("\n=== 使用requests库测试 ===")
    response = requests.get(url, timeout=10)
    print(f"状态码: {response.status_code}")
    print(f"响应内容: {response.text[:100]}...")
except Exception as e:
    print(f"requests测试失败: {e}")

# 使用httpx库测试
try:
    print("\n=== 使用httpx库测试 ===")
    response = httpx.get(url, timeout=10)
    print(f"状态码: {response.status_code}")
    print(f"响应内容: {response.text[:100]}...")
except Exception as e:
    print(f"httpx测试失败: {e}")

# 使用aiohttp库测试
async def test_aiohttp():
    try:
        print("\n=== 使用aiohttp库测试 ===")
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10, ssl=False) as response:
                print(f"状态码: {response.status}")
                text = await response.text()
                print(f"响应内容: {text[:100]}...")
    except Exception as e:
        print(f"aiohttp测试失败: {e}")

# 运行异步测试
asyncio.run(test_aiohttp())

# 测试不同的端口
alternative_ports = [1561, 1563, 8080, 80]
print("\n=== 测试其他可能的端口 ===")
for port in alternative_ports:
    alt_url = f"http://xianan.xin:{port}/api/plugins"
    try:
        response = requests.get(alt_url, timeout=5)
        print(f"端口 {port} 可访问! 状态码: {response.status_code}")
    except Exception as e:
        print(f"端口 {port} 测试失败: {type(e).__name__}")
