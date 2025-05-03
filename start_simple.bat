@echo off
chcp 936
setlocal enabledelayedexpansion

echo ====================================
echo       XXXBot Windows 启动脚本
echo ====================================
echo 启动中...请稍等...

rem 设置工作目录
set "WORKSPACE_DIR=%~dp0"
set "LOGS_DIR=%WORKSPACE_DIR%logs"
set FRAMEWORK_TYPE=default
set PROTOCOL_VERSION=849

echo [%date% %time%] 启动脚本开始执行 > "%WORKSPACE_DIR%startup_log.txt"

rem 创建日志目录
if not exist "%LOGS_DIR%" (
    echo 创建日志目录: %LOGS_DIR%
    mkdir "%LOGS_DIR%"
    echo [%date% %time%] 创建日志目录: %LOGS_DIR% >> "%WORKSPACE_DIR%startup_log.txt"
)

rem 检查Python是否可用
echo 检查Python是否安装...
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo 错误: 未找到Python! 请确保Python已安装并添加到PATH环境变量
    echo [%date% %time%] 错误: 未找到Python >> "%WORKSPACE_DIR%startup_log.txt"
    pause
    exit /b 1
)

rem 检查main_config.toml配置文件
echo 读取配置文件...
if exist "%WORKSPACE_DIR%main_config.toml" (
    echo 配置文件存在，尝试获取配置...
    
    rem 提取协议版本和框架类型（简单提取方法）
    for /f "tokens=2 delims==" %%a in ('findstr /c:"version =" "%WORKSPACE_DIR%main_config.toml"') do (
        set PROTOCOL_VERSION=%%a
        set PROTOCOL_VERSION=!PROTOCOL_VERSION:"=!
        set PROTOCOL_VERSION=!PROTOCOL_VERSION: =!
        echo 协议版本: !PROTOCOL_VERSION!
    )
    
    for /f "tokens=2 delims==" %%a in ('findstr /c:"type =" "%WORKSPACE_DIR%main_config.toml"') do (
        set FRAMEWORK_TYPE=%%a
        set FRAMEWORK_TYPE=!FRAMEWORK_TYPE:"=!
        set FRAMEWORK_TYPE=!FRAMEWORK_TYPE: =!
        echo 框架类型: !FRAMEWORK_TYPE!
    )
) else (
    echo 配置文件不存在，使用默认设置
    echo 默认协议版本: %PROTOCOL_VERSION%
    echo 默认框架类型: %FRAMEWORK_TYPE%
)

rem 检查Redis服务
echo 检查Redis服务...
tasklist /fi "imagename eq redis-server.exe" 2>nul | find /i "redis-server.exe" >nul
if %ERRORLEVEL% neq 0 (
    echo Redis服务未运行，尝试启动...
    if exist "%WORKSPACE_DIR%849\redis\redis-server.exe" (
        echo 启动Redis服务...
        start /b "" "%WORKSPACE_DIR%849\redis\redis-server.exe"
        timeout /t 2 /nobreak > nul
        echo Redis服务已启动
    ) else (
        echo 警告: Redis服务可执行文件不存在: %WORKSPACE_DIR%849\redis\redis-server.exe
    )
) else (
    echo Redis服务已在运行
)

rem 选择协议服务路径
echo 使用协议版本: %PROTOCOL_VERSION%
if "%PROTOCOL_VERSION%"=="855" (
    set "PAD_SERVICE_PATH=%WORKSPACE_DIR%849\pad2\main.exe"
    echo 使用855协议服务路径: !PAD_SERVICE_PATH!
) else if "%PROTOCOL_VERSION%"=="ipad" (
    set "PAD_SERVICE_PATH=%WORKSPACE_DIR%849\pad3\main.exe" 
    echo 使用iPad协议服务路径: !PAD_SERVICE_PATH!
) else (
    set "PAD_SERVICE_PATH=%WORKSPACE_DIR%849\pad\main.exe"
    echo 使用849协议服务路径: !PAD_SERVICE_PATH!
)

rem 启动PAD服务
echo 启动PAD服务...
if exist "!PAD_SERVICE_PATH!" (
    start /b "" "!PAD_SERVICE_PATH!" > "%LOGS_DIR%\pad_service.log" 2>&1
    echo PAD服务已启动
    timeout /t 2 /nobreak > nul
) else (
    echo 警告: PAD服务文件不存在: !PAD_SERVICE_PATH!
)

rem 根据框架类型选择启动方式
echo 根据配置选择框架类型: %FRAMEWORK_TYPE%

if "%FRAMEWORK_TYPE%"=="dow" (
    rem 使用DOW框架
    set "DOW_FRAMEWORK_PATH=%WORKSPACE_DIR%dow"
    echo 选择使用DOW框架: !DOW_FRAMEWORK_PATH!
    
    if exist "!DOW_FRAMEWORK_PATH!" (
        echo 直接启动DOW框架...
        if exist "!DOW_FRAMEWORK_PATH!\app.py" (
            rem 启动admin后台
            echo 启动admin后台...
            start /b cmd /c "cd /d "%WORKSPACE_DIR%" && python admin\run_server.py"
            
            rem 启动DOW主程序
            echo 启动DOW主程序...
            cd /d "!DOW_FRAMEWORK_PATH!"
            start cmd /c "python app.py"
        ) else (
            echo 警告: 未找到DOW框架的app.py
            echo 启动默认框架...
            cd /d "%WORKSPACE_DIR%"
            start cmd /c "python main.py"
        )
    ) else (
        echo 警告: DOW框架目录不存在: !DOW_FRAMEWORK_PATH!
        echo 启动默认框架...
        cd /d "%WORKSPACE_DIR%"
        start cmd /c "python main.py"
    )
) else if "%FRAMEWORK_TYPE%"=="dual" (
    rem 双框架模式
    echo 选择使用双框架模式: 先启动原始框架，登录成功后再启动DOW框架
    
    set "DOW_FRAMEWORK_PATH=%WORKSPACE_DIR%dow"
    set "ORIGINAL_FRAMEWORK_PATH=%WORKSPACE_DIR%"
    
    if not exist "!DOW_FRAMEWORK_PATH!" (
        echo 警告: DOW框架目录不存在: !DOW_FRAMEWORK_PATH!，将只启动原始框架
        cd /d "%WORKSPACE_DIR%"
        start cmd /c "python main.py"
        goto :eof
    )
    
    rem 启动原始框架
    echo 启动原始框架...
    cd /d "%WORKSPACE_DIR%"
    start /b cmd /c "python main.py"
    
    rem 启动消息回调守护进程
    echo 等待3秒后启动消息回调守护进程...
    timeout /t 3 /nobreak > nul
    
    cd /d "%WORKSPACE_DIR%"
    if exist "%WORKSPACE_DIR%wx849_callback_daemon.py" (
        echo 启动消息回调守护进程...
        start /b cmd /c "python wx849_callback_daemon.py"
    ) else (
        echo 警告: 消息回调守护进程脚本不存在
    )
    
    rem 等待原始框架登录成功
    echo 等待原始框架登录成功...
    
    rem 创建启动DOW的辅助批处理文件
    echo @echo off > "%WORKSPACE_DIR%force_dow.bat"
    echo cd /d "%DOW_FRAMEWORK_PATH%" >> "%WORKSPACE_DIR%force_dow.bat"
    echo start cmd /c "python app.py" >> "%WORKSPACE_DIR%force_dow.bat"
    echo echo DOW框架已手动启动 >> "%WORKSPACE_DIR%force_dow.bat"
    
    echo 您可以运行force_dow.bat手动启动DOW框架
    
    rem 启动DOW守护进程脚本
    echo 启动等待脚本...
    cd /d "%WORKSPACE_DIR%"
    start cmd /c "%WORKSPACE_DIR%wait_and_start_dow.bat"
) else (
    rem 使用默认框架
    echo 使用默认框架...
    
    rem 启动主应用
    echo 启动XXXBot主应用...
    cd /d "%WORKSPACE_DIR%"
    start cmd /c "python main.py"
)

echo 启动脚本执行完毕！
echo [%date% %time%] 启动脚本执行完毕 >> "%WORKSPACE_DIR%startup_log.txt"
echo 如果遇到问题，请检查startup_log.txt日志文件
echo.
pause 