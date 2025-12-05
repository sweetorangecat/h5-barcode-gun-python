#!/bin/bash

# H5 扫码枪 - macOS 打包脚本

set -e

echo "========================================"
echo "H5 扫码枪 - macOS 打包脚本"
echo "========================================"
echo ""

# 检查Python3是否安装
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: Python3未安装！"
    echo "请安装Python 3.8+"
    exit 1
fi

python3_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✅ Python3版本: $python3_version"
echo ""

# 检查PyInstaller是否安装
if ! python3 -c "import PyInstaller" &> /dev/null; then
    echo "ℹ️  PyInstaller未安装，正在安装..."
    pip3 install pyinstaller==6.3.0
    echo ""
fi

echo "✅ PyInstaller检查完成"
echo ""

# 创建dist目录
mkdir -p dist

# 打包macOS客户端
echo "📦 正在打包macOS客户端..."
echo ""

# 检查rumps是否安装
if ! python3 -c "import rumps" &> /dev/null; then
    echo "ℹ️  rumps未安装，正在安装..."
    pip3 install rumps
fi

# 使用PyInstaller打包pc_client_macos.py
echo "执行命令: pyinstaller --clean --noconfirm --windowed --onefile --name="H5BarcodeGun" --add-data "templates:templates" --add-data "static:static" pc_client_macos.py"

pyinstaller \
    --clean \
    --noconfirm \
    --windowed \
    --onefile \
    --name="H5BarcodeGun" \
    --add-data "templates:templates" \
    --add-data "static:static" \
    pc_client_macos.py

if [ $? -ne 0 ]; then
    echo "❌ 打包失败！"
    echo "请检查错误信息并修复问题"
    exit 1
fi

echo ""
echo "========================================"
echo "✅ 打包完成！"
echo "========================================"
echo ""
echo "可执行文件位置:"
echo "  dist/H5BarcodeGun (命令行版本)"
echo "  dist/H5BarcodeGun.app (macOS App包)"
echo ""
echo "使用方法："
echo "1. 双击运行 H5BarcodeGun.app"
echo "2. 在菜单栏点击📱图标"
echo "3. 选择"启动服务器"菜单项"
echo "4. 选择"打开管理界面"或扫描二维码"
echo "5. 使用手机开始扫码"
echo ""
echo "注意："
echo "- 首次运行可能需要在"系统偏好设置-安全性与隐私"中允许"
echo "- 建议添加到"登录项"实现开机自启"
echo "========================================"
echo ""

# 询问是否打开dist目录
read -p "是否打开输出目录？(y/n): " open_dir
if [ "$open_dir" = "y" ] || [ "$open_dir" = "Y" ]; then
    open dist
fi

echo ""
echo "🎉 打包完成！"
