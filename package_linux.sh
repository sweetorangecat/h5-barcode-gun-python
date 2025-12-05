#!/bin/bash

# H5 扫码枪 - Linux 打包脚本
# 注意：Linux下推荐使用原生Python环境运行

set -e

echo "========================================"
echo "H5 扫码枪 - Linux 打包脚本"
echo "========================================"
echo ""
echo "⚠️  注意：Linux平台建议使用源码运行"
echo "    打包后的可执行文件可能存在兼容性问题"
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

# 推荐方案：生成可执行脚本
echo "📋 生成Linux启动脚本..."
echo ""

# 创建启动脚本
cat > H5BarcodeGun << 'EOF'
#!/bin/bash

# H5 扫码枪 - Linux启动脚本

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# 检查Python3
if ! command -v python3 &> /dev/null; then
    echo "错误: Python3未安装！"
    exit 1
fi

# 检查依赖
python3 -c "import flask, flask_socketio, qrcode" &> /dev/null
if [ $? -ne 0 ]; then
    echo "正在安装依赖..."
    pip3 install -r requirements.txt
fi

# 启动对应的客户端（根据系统类型选择）
system_type=$(uname -s)
if [ "$system_type" = "Darwin" ]; then
    echo "检测到macOS系统"
    python3 pc_client_macos.py
else
    echo "检测到Linux系统"
    echo "注意：Linux平台没有原生图形客户端，请使用："
    echo "1. python3 server.py    # 启动服务器"
    echo "2. 在其他设备访问 http://<服务器IP>:5000"
    echo ""
    read -p "是否继续启动服务器？(y/n) " choice
    if [ "$choice" = "y" ] || [ "$choice" = "Y" ]; then
        python3 server.py
    fi
fi
EOF

chmod +x H5BarcodeGun
echo "✅ 启动脚本已生成: H5BarcodeGun"
echo ""

# 创建requirements.txt（如果不存在）
if [ ! -f requirements.txt ]; then
    cat > requirements.txt << 'EOF'
Flask==2.3.3
Flask-SocketIO==5.3.5
python-socketio[client]==5.9.0
eventlet==0.40.4
PyAutoGUI==0.9.54
python-dotenv==1.0.0
qrcode==7.4.2
EOF
    echo "✅ requirements.txt 已生成"
fi

# 询问是否使用PyInstaller打包
echo ""
read -p "是否使用PyInstaller打包？(y/n): " use_pyinstaller

if [ "$use_pyinstaller" = "y" ] || [ "$use_pyinstaller" = "Y" ]; then
    echo ""
    echo "📦 正在检查PyInstaller..."

    if ! python3 -c "import PyInstaller" &> /dev/null; then
        echo "ℹ️  PyInstaller未安装，正在安装..."
        pip3 install pyinstaller==6.3.0
    fi

    echo ""
    echo "📦 打包Linux版本..."
    echo "⚠️  注意：Linux打包可能存在兼容性问题"
    echo "    建议在目标系统上直接运行源码"

    pyinstaller \
        --clean \
        --noconfirm \
        --onefile \
        --console \
        --name="H5BarcodeGun_Server" \
        --add-data "templates:templates" \
        --add-data "static:static" \
        server.py

    if [ $? -eq 0 ]; then
        echo "✅ 服务器打包完成"
        echo "位置: dist/H5BarcodeGun_Server"
    else
        echo "❌ 打包失败，建议使用源码运行"
    fi
fi

echo ""
echo "========================================"
echo "✅ Linux部署文件生成完成！"
echo "========================================"
echo ""
echo "推荐使用方式："
echo "1. 安装Python3和pip"
echo "2. 安装依赖: pip3 install -r requirements.txt"
echo "3. 运行服务器: python3 server.py"
echo "4. 在手机浏览器访问显示的IP地址"
echo ""
echo "或使用启动脚本:"
echo "  ./H5BarcodeGun"
echo ""
echo "位置:"
echo "  H5BarcodeGun          - 启动脚本"
echo "  dist/H5BarcodeGun_Server - 可执行文件（如果打包成功）"
echo "  requirements.txt      - 依赖列表"
echo ""
echo "注意："
echo "- Linux没有原生图形客户端"
echo "- 建议在终端运行服务器，使用Web界面管理"
echo "- 需要安装依赖库"
echo "========================================"
echo ""

# 创建运行说明
cat > README_LINUX.md << 'EOF'
# Linux运行说明

## 快速启动

1. 安装Python3和pip
   ```bash
   sudo apt-get update
   sudo apt-get install python3 python3-pip  # Ubuntu/Debian
   # 或
   sudo yum install python3 python3-pip      # CentOS/RHEL
   ```

2. 安装依赖
   ```bash
   pip3 install -r requirements.txt
   ```

3. 启动服务器
   ```bash
   python3 server.py
   ```

4. 在手机浏览器访问显示的地址

## 使用说明

Linux平台没有原生图形客户端，但可以通过以下方式使用：

1. **Web管理界面**
   - 访问 http://localhost:5000/admin
   - 查看服务器状态、二维码等信息

2. **手机扫码**
   - 访问 http://<服务器IP>:5000
   - 授权摄像头并开始扫码

3. **接收数据**
   - 扫码数据会自动输入到PC光标位置
   - 需要在运行服务器的电脑上接收数据

## 高级用法

如果想要在Linux上接收扫码数据：

```bash
# 安装PyAutoGUI（需要X11环境）
pip3 install PyAutoGUI

# 修改server.py，添加PC客户端功能
```

## 常见问题

### Q: 无法安装PyAutoGUI
A: 需要安装X11开发库
```bash
sudo apt-get install scrot python3-tk python3-dev
```

### Q: 无法模拟键盘输入
A: Linux需要图形界面环境，确保在X11会话中运行

### Q: 服务器启动失败
A: 检查端口5000是否被占用
```bash
lsof -i :5000
```
EOF

echo "📋 已生成 Linux专用说明文档: README_LINUX.md"
echo ""

# 询问是否打开目录
read -p "是否打开当前目录？(y/n): " open_dir
if [ "$open_dir" = "y" ] || [ "$open_dir" = "Y" ]; then
    xdg-open . 2>/dev/null || open . 2>/dev/null || nautilus . 2>/dev/null &
fi

echo ""
echo "🎉 完成！"
