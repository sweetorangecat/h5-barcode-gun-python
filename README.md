# H5 扫码枪 - Python 版本 v2.0

本项目是一个完整的H5扫码枪系统，将手机变成扫码枪，通过局域网将扫码数据实时传输到PC并模拟键盘输入。

## 功能特点

- ✨ **H5扫码**：手机浏览器调用摄像头扫码，无需安装App
- 📡 **实时传输**：WebSocket实现毫秒级延迟传输
- ⌨️ **键盘模拟**：PC端自动模拟键盘输入扫码结果
- 📱 **跨平台支持**：支持Windows、macOS、Linux、iOS、Android
- ⚙️ **图形界面**：PC客户端集成服务器管理功能
- 🔒 **单实例运行**：只允许一个PC客户端运行
- 📷 **二维码生成**：自动生成手机访问二维码
- ⏱️ **扫码频率控制**：可调节扫码识别频率
- 🚫 **防重复扫描**：内置频率限制，防止重复输入
- 🚀 **一键启动**：点击即可启动所有服务

## 系统架构

```
┌─────────────────────────────────────────┐
│        PC客户端（Windows）              │
│  ┌─────────────┐    ┌─────────────┐  │
│  │  GUI界面    │◄──►│  服务器核心  │  │
│  │ (PyQt5)     │    │ (Flask+WS)  │  │
│  └─────────────┘    └──────┬──────┘  │
└─────────────────────────────┼──────────┘
                              │ WebSocket
                              ↓
                    ┌───────────────────┐
                    │  手机浏览器(H5)   │
                    │  (html5-qrcode)   │
                    └───────────────────┘
```

## 文件结构

```
h5-barcode-gun-python/
├── dual_server.py                     # 双端口服务器（集成Flask+WebSocket）
├── pc_client_windows.py               # Windows图形客户端（PyQt5）
├── cert_utils.py                      # SSL证书工具
├── keyboard_simulator.py              # 键盘模拟模块
├── test_keyboard_simulator.py         # 键盘模拟测试
├── check_ports.py                     # 端口检查工具
├── templates/
│   ├── scanner_new.html              # H5扫码页面（含频率控制）
│   └── admin.html                     # PC管理页面
├── static/
│   ├── html5-qrcode.min.js           # 扫码库
│   ├── socket.io.min.js              # SocketIO客户端
│   └── icon.ico                      # 应用图标
├── requirements.txt                   # Python依赖包
└── README.md                         # 项目文档
```

## 环境要求

- **Python版本**：3.8+
- **操作系统**：Windows 10/11（PC客户端）、macOS（服务器）、Linux（服务器）
- **网络**：手机和PC在同一WiFi网络
- **权限**：Windows需要管理员权限运行

## 快速开始

### 1. 安装依赖

```bash
cd D:\PythonWork\h5-barcode-gun-python
pip install -r requirements.txt
```

### 2. 启动PC客户端（推荐）

Windows用户直接运行图形客户端：

```bash
python pc_client_windows.py
```

界面功能：
- ⏯️ **启动/停止服务器** - 一键控制双端口服务器
- 📷 **二维码显示** - 自动生成手机访问二维码
- 📱 **状态监控** - 实时显示H5连接数
- 📋 **日志输出** - 查看系统运行日志
- 🔗 **系统托盘** - 支持后台运行

### 3. 手机端访问

1. **扫描二维码**
   - PC客户端启动后，左侧显示手机访问二维码
   - 使用手机扫码工具扫描二维码
   - 或直接访问显示的HTTP地址（如 https://192.168.1.100:5100）

2. **开始扫码**
   - 授权摄像头权限
   - 选择识别频率（高/中/低）
   - 对准条形码/二维码即可自动扫描

3. **数据接收**
   - 扫描结果实时发送到PC
   - PC自动模拟键盘输入并添加回车
   - 数据输入到当前光标位置

## 配置文件

### 修改端口

编辑 `dual_server.py`，修改环境变量或默认值：

```python
http_port = int(os.getenv('HTTP_PORT', '5100'))  # HTTP服务器端口
ws_port = int(os.getenv('WS_PORT', '9999'))      # WebSocket端口
```

### 配置识别频率

手机端H5页面提供4种识别频率：
- 高频率 (100ms) - 适合快速连续扫码
- 中频率 (500ms) - 默认，平衡速度和准确性
- 低频率 (1秒) - 减少重复扫描
- 较低频率 (2秒) - 适合扫码频率较低的场景

## PyInstaller打包

### Windows

```bash
# 安装PyInstaller
pip install pyinstaller==6.3.0

# 打包PC客户端
pyinstaller --clean --noconfirm --windowed --onefile \
  --icon=static/icon.ico \
  --add-data "templates;templates" \
  --add-data "static;static" \
  --name="H5BarcodeGun" \
  pc_client_windows.py

# 打包后的文件在 dist/H5BarcodeGun.exe
```

### 注意事项

1. **管理员权限**：PC客户端需要管理员权限才能模拟键盘输入
2. **单实例运行**：程序会自动检测是否已在运行，避免重复启动
3. **防火墙**：确保防火墙允许HTTP(5100)和WebSocket(9999)端口
4. **安全模式**：PyAutoGUI安全模式启用，鼠标移动到左上角会停止输入

##故障排除

### Q1: 手机无法访问服务器页面

**A1:**
- 检查手机和PC是否在同一WiFi网络
- 关闭防火墙或开放5100/9999端口
- 检查PC的IP地址是否正确

### Q2: 扫码后PC没有输入

**A2:**
- 确认PC客户端有管理员权限
- 检查当前窗口是否有输入焦点
- 确认安全模式未触发（鼠标不在左上角）

### Q3: 摄像头无法打开

**A3:**
- 检查浏览器摄像头权限
- iOS设备需使用HTTPS访问（使用PC客户端显示的HTTPS地址）

### Q4: 二维码无法显示

**A4:**
- 安装qrcode库：`pip install qrcode[pil]`
- 检查Pillow库版本：`pip install Pillow`

## 技术栈

- **后端**：Flask + Flask-SocketIO (Python 3.8+)
- **前端**：HTML5 + JavaScript + html5-qrcode
- **PC客户端**：PyQt5 (Windows)
- **键盘模拟**：PyAutoGUI + Win32 API
- **二维码**：qrcode + Pillow

## 许可证

MIT License

## 致谢

- [html5-qrcode](https://github.com/mebjas/html5-qrcode) - 浏览器端扫码库
- [Flask-SocketIO](https://flask-socketio.readthedocs.io/) - WebSocket通信
- [PyQt5](https://www.riverbankcomputing.com/software/pyqt/) - GUI框架
- [PyAutoGUI](https://pyautogui.readthedocs.io/) - 键盘模拟
