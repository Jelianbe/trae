@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo NovelTTS 版本备份工具
echo ========================================
echo.

REM 获取当前日期
for /f "tokens=1-3 delims=/" %%a in ('date /t') do (
    set today=%%a-%%b-%%c
)

REM 设置备份目录
set BACKUP_DIR=%~dp0backups

REM 检查是否提供了版本描述
if "%1"=="" (
    set /p desc="请输入版本描述（如：分析功能修复）: "
) else (
    set desc=%*
)

REM 移除引号
set desc=%desc:"=%

REM 构建版本号
set VERSION=v1.0_%today%_%desc%
set BACKUP_PATH=%BACKUP_DIR%\%VERSION%

echo 备份版本: %VERSION%
echo 备份路径: %BACKUP_PATH%
echo.

REM 创建备份目录
if not exist "%BACKUP_PATH%" (
    mkdir "%BACKUP_PATH%"
    echo [OK] 创建备份目录
) else (
    echo [警告] 备份目录已存在，将覆盖
)

REM 备份核心目录
echo 开始备份...
xcopy /E /I /Q /Y "%~dp0backend" "%BACKUP_PATH%\backend\" >nul 2>&1
echo [OK] backend/
xcopy /E /I /Q /Y "%~dp0frontend" "%BACKUP_PATH%\frontend\" >nul 2>&1
echo [OK] frontend/
xcopy /E /I /Q /Y "%~dp0pipeline" "%BACKUP_PATH%\pipeline\" >nul 2>&1
echo [OK] pipeline/
xcopy /E /I /Q /Y "%~dp0utils" "%BACKUP_PATH%\utils\" >nul 2>&1
echo [OK] utils/
xcopy /E /I /Q /Y "%~dp0db" "%BACKUP_PATH%\db\" >nul 2>&1
echo [OK] db/

REM 备份配置文件
copy /Y "%~dp0pyproject.toml" "%BACKUP_PATH%\" >nul 2>&1
echo [OK] pyproject.toml
copy /Y "%~dp0requirements.txt" "%BACKUP_PATH%\" >nul 2>&1
echo [OK] requirements.txt

REM 生成变更日志
(
echo # 版本 %VERSION%
echo.
echo ## 备份日期
echo %today%
echo.
echo ## 版本说明
echo %desc%
echo.
echo ## 备份内容
echo - backend/
echo - frontend/
echo - pipeline/
echo - utils/
echo - db/
echo - 配置文件
) > "%BACKUP_PATH%\CHANGELOG.md"

echo [OK] CHANGELOG.md
echo.
echo ========================================
echo 备份完成！
echo 路径: %BACKUP_PATH%
echo ========================================
pause
