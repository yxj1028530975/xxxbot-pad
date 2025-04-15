#!/bin/bash
set -e

# 启动系统Redis服务
echo "启动系统Redis服务..."
redis-server /etc/redis/redis.conf --daemonize yes

# 等待系统Redis服务启动
echo "等待系统Redis服务可用..."
sleep 2

# 确保849/redis目录存在
if [ -d "/app/849/redis" ]; then
    # 启动849目录中的Redis服务（端口6378）
    echo "启动849目录中的Redis服务（端口6378）..."
    cd /app/849/redis
    redis-server /app/849/redis/redis.linux.conf --daemonize yes --port 6378

    # 等待849 Redis服务启动
    echo "等待849 Redis服务可用..."
    sleep 2

    # 检查Redis服务是否正常启动（使用redis-cli替代nc命令）
    if redis-cli -p 6378 ping > /dev/null 2>&1; then
        echo "849 Redis服务（端口6378）已成功启动"
    else
        echo "警告：849 Redis服务（端口6378）可能未正常启动"
    fi

    # 返回应用根目录
    cd /app
else
    echo "警告：849/redis目录不存在，跳过启动849 Redis服务"
fi

# 检查并确保3000端口可用
echo "检查终端服务端口..."
# 使用lsof检查端口是否被占用
if lsof -i:3000 > /dev/null 2>&1; then
    echo "警告：端口3000已被占用，尝试终止占用进程..."
    kill -9 $(lsof -t -i:3000) 2>/dev/null || true
    sleep 1
fi

# 启动WeTTy终端服务 - 使用/wetty作为基础路径
echo "启动WeTTy终端服务..."
# 使用完整路径或者尝试多种可能的路径
if command -v wetty &> /dev/null; then
    wetty --port 3000 --host 0.0.0.0 --allow-iframe --base /wetty --command /bin/bash &
elif [ -f "/usr/local/bin/wetty" ]; then
    /usr/local/bin/wetty --port 3000 --host 0.0.0.0 --allow-iframe --base /wetty --command /bin/bash &
elif [ -f "/usr/bin/wetty" ]; then
    /usr/bin/wetty --port 3000 --host 0.0.0.0 --allow-iframe --base /wetty --command /bin/bash &
else
    echo "警告：wetty命令未找到，跳过启动WeTTy终端服务"
fi

# 等待WeTTy服务启动
echo "等待WeTTy服务可用..."
sleep 3

# 注释: 不再单独启动管理后台服务器，由main.py统一管理
# 管理后台将由main.py自动启动，使用main_config.toml中配置的端口

# 读取协议版本配置
echo "读取协议版本配置..."
PROTOCOL_VERSION="849"  # 默认使用849协议

# 检查配置文件是否存在
if [ -f "/app/main_config.toml" ]; then
    # 直接使用awk提取Protocol部分中的version值
    # 这种方法更可靠，可以准确地提取配置值
    EXTRACTED_VERSION=$(awk '/\[Protocol\]/{flag=1; next} /\[/{flag=0} flag && /version *=/{gsub(/[^0-9]/, "", $3); print $3}' /app/main_config.toml)

    if [ ! -z "$EXTRACTED_VERSION" ]; then
        PROTOCOL_VERSION="$EXTRACTED_VERSION"
        echo "从配置文件中提取到协议版本: $PROTOCOL_VERSION"
    else
        echo "未从配置文件中提取到协议版本，使用默认值: $PROTOCOL_VERSION"
    fi
fi

# 打印协议版本信息，包括字符长度和十六进制表示
echo "使用协议版本: '$PROTOCOL_VERSION'"
echo "协议版本字符长度: ${#PROTOCOL_VERSION}"
echo "协议版本十六进制表示: $(echo -n "$PROTOCOL_VERSION" | hexdump -C)"

# 清理可能的空格和不可见字符
CLEAN_VERSION=$(echo "$PROTOCOL_VERSION" | tr -d '[:space:]')
echo "清理后的协议版本: '$CLEAN_VERSION'"

# 启动pad服务
echo "启动pad服务..."

# 根据协议版本选择不同的服务路径
# 使用更严格的比较方式
if [[ "$CLEAN_VERSION" == "855" ]]; then
    # 855版本使用pad2目录
    PAD_SERVICE_PATH="/app/849/pad2/linuxService"
    echo "使用855协议服务路径: $PAD_SERVICE_PATH"
else
    # 849版本使用pad目录
    PAD_SERVICE_PATH="/app/849/pad/linuxService"
    echo "使用849协议服务路径: $PAD_SERVICE_PATH"
fi

if [ -f "$PAD_SERVICE_PATH" ]; then
    # 在Linux系统上确保文件有执行权限
    chmod +x "$PAD_SERVICE_PATH"

    # 使用nohup在后台启动linuxService
    nohup "$PAD_SERVICE_PATH" > /app/logs/pad_service.log 2>&1 &

    # 记录进程号
    PAD_PID=$!
    echo "pad服务已启动，进程ID: $PAD_PID"

    # 等待pad服务启动
    echo "等待pad服务启动..."
    # 等待短暂停，给pad服务一些初始化时间
    sleep 2

    # 尝试最多5次，每次间隔短一些
    for i in {1..5}; do
        if curl -s http://127.0.0.1:9011 > /dev/null 2>&1 || curl -s http://127.0.0.1:9011/VXAPI/Login/GetQR > /dev/null 2>&1; then
            echo "pad服务已启动并可用"
            break
        else
            if [ $i -lt 5 ]; then
                echo "等待pad服务启动，尝试 $i/5..."
                sleep 1
            else
                echo "警告：pad服务可能未完全启动，继续启动主应用..."
            fi
        fi
    done
else
    echo "警告：pad服务文件不存在: $PAD_SERVICE_PATH"
fi

# 启动主应用
echo "启动XXXBot主应用..."
exec python main.py

# 保持容器运行
wait