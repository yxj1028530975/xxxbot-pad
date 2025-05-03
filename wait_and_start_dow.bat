@echo off
chcp 936
setlocal enabledelayedexpansion

echo ====================================
echo  等待原始框架登录并启动DOW框架
echo ====================================

set "WORKSPACE_DIR=%~dp0"
set "DOW_FRAMEWORK_PATH=%WORKSPACE_DIR%dow"
set MAX_WAIT_TIME=300
set WAIT_TIME=0
set "FORCE_DOW_BAT=%WORKSPACE_DIR%force_dow.bat"
set "ROBOT_STAT_FILE="

rem 检查可能的robot_stat.json文件位置
if exist "%WORKSPACE_DIR%resource\robot_stat.json" (
    set "ROBOT_STAT_FILE=%WORKSPACE_DIR%resource\robot_stat.json"
    echo 找到robot_stat.json文件: !ROBOT_STAT_FILE!
) else if exist "%WORKSPACE_DIR%resource\robot-stat.json" (
    set "ROBOT_STAT_FILE=%WORKSPACE_DIR%resource\robot-stat.json"
    echo 找到robot-stat.json文件: !ROBOT_STAT_FILE!
) else if exist "%WORKSPACE_DIR%robot_stat.json" (
    set "ROBOT_STAT_FILE=%WORKSPACE_DIR%robot_stat.json"
    echo 找到robot_stat.json文件(根目录): !ROBOT_STAT_FILE!
) else (
    set "ROBOT_STAT_FILE=%WORKSPACE_DIR%resource\robot_stat.json"
    echo 未找到robot_stat.json文件，使用默认路径: !ROBOT_STAT_FILE!
)

:wait_loop
if %WAIT_TIME% geq %MAX_WAIT_TIME% (
    echo 等待原始框架登录超时，DOW框架将不会启动
    goto :end
)

rem 检查是否存在强制启动信号
if exist "%FORCE_DOW_BAT%" (
    echo 检测到force_dow.bat文件，可以手动启动DOW框架
)

rem 检查robot_stat.json是否存在且包含wxid
if exist "!ROBOT_STAT_FILE!" (
    findstr /C:"wxid" "!ROBOT_STAT_FILE!" >nul
    if !ERRORLEVEL! equ 0 (
        echo 检测到原始框架已登录成功
        goto :start_dow
    ) else (
        echo robot_stat.json文件存在但未找到wxid
    )
) else (
    echo robot_stat.json文件不存在，继续等待...
)

rem 等待5秒后再次检查
timeout /t 5 /nobreak > nul
set /a WAIT_TIME+=5
echo 等待原始框架登录中... !WAIT_TIME!/!MAX_WAIT_TIME!秒
goto :wait_loop

:start_dow
echo 原始框架已登录成功，开始启动DOW框架...

rem 确保DOW框架配置正确
if exist "%DOW_FRAMEWORK_PATH%\config.json" (
    echo DOW框架配置文件已存在
)

rem 启动DOW框架
echo 启动DOW框架...
cd /d "%DOW_FRAMEWORK_PATH%"
start cmd /c "python app.py"
echo DOW框架已启动

:end
echo 守护进程完成 