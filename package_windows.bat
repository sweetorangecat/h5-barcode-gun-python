@echo off
chcp 65001 >nul
echo ========================================
echo H5 扫码枪 - Windows 打包脚本
echo ========================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: Python未安装或不在系统PATH中！
    echo 请安装Python 3.8+并添加到系统环境变量
    pause
    exit /b 1
)

echo ✅ Python环境检查通过
echo.

REM 检查PyInstaller是否安装
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo ℹ️  PyInstaller未安装，正在安装...
    pip install pyinstaller==6.3.0
    echo.
)

echo ✅ PyInstaller检查完成
echo.

REM 创建dist目录
if not exist dist mkdir dist

REM 打包Windows客户端
echo 📦 正在打包Windows客户端...
echo.

pyinstaller --version >nul 2>&1
if errorlevel 1 (
    echo ❌ PyInstaller未正确安装！
    pause
    exit /b 1
)

REM 使用PyInstaller打包pc_client_windows.py
echo 执行命令: pyinstaller --clean --noconfirm --windowed --onefile --icon=static/icon.ico --add-data "templates;templates" --add-data "static;static" --name="H5BarcodeGun" pc_client_windows.py

pyinstaller ^
    --clean ^
    --noconfirm ^
    --windowed ^
    --onefile ^
    --icon=static\icon.ico ^
    --add-data "templates;templates" ^
    --add-data "static;static" ^
    --name="H5BarcodeGun" ^
    pc_client_windows.py

if errorlevel 1 (
    echo ❌ 打包失败！
    echo 请检查错误信息并修复问题
    pause
    exit /b 1
)

echo.
echo ========================================
echo ✅ 打包完成！
echo ========================================
echo.
echo 可执行文件位置: dist\H5BarcodeGun.exe
echo.
echo 使用方法：
echo 1. 双击运行 H5BarcodeGun.exe
echo 2. 点击"启动服务器"按钮
echo 3. 在浏览器中打开管理界面
echo 4. 使用手机扫描二维码开始扫码
echo.
echo 提示：首次运行建议以管理员身份运行
echo ========================================
echo.

REM 询问是否打开dist目录
set /p open_dir=是否打开输出目录？(y/n):
if /i "%open_dir%"=="y" (
    start explorer dist
)

pause
