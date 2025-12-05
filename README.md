# H5 扫码枪 - Python 版本

使用 Python 实现的 H5 扫码枪项目,将手机变成扫码枪,通过局域网将扫码数据发送到电脑。

[TOC]

## 功能特点

- ✨ 手机调用摄像头扫码
- 📡 局域网实时传输
- ⌨️ 自动模拟键盘输入
- 🖥️ 支持 Windows 和 macOS
- 📱 支持 iOS 和 Android
- 🔄 WebSocket 实时通信
- 📊 图形化PC客户端界面
- ⚙️ 集成服务器管理功能
- 📱 手机访问二维码生成
- ⏯️ 一键启动/停止服务器
- 🔗 自动化工作流程

## 系统架构

```
┌─────────────────────────────────────────┐
│        PC客户端 (集成服务器)             │
│  ┌─────────────┐    ┌─────────────┐  │
│  │             │    │             │  │
│  │  GUI界面    │◄──►│  服务器核心  │  │
│  │             │    │             │  │
│  └─────────────┘    └──────┬──────┘  │
└─────────────────────────────┼──────────┘
                              │ WebSocket
                              ↓
                    ┌───────────────────┐
                    │  手机浏览器       │
                    │  (扫码端)         │
                    └───────────────────┘
```

## 文件结构

```
h5-barcode-gun-python/
├── core_server.py            # 核心服务器模块（独立）
├── server.py                 # 服务器启动脚本（独立模式）
├── pc_client_windows.py      # Windows图形客户端
├── pc_client_macos.py        # macOS菜单栏客户端
├── templates/
│   ├── scanner.html          # 手机扫码页面
│   └── admin.html            # Web管理控制台
├── static/
│   ├── scanner.js            # 扫码逻辑
│   └── icon.ico             # Windows图标（可选）
├── requirements.txt          # Python依赖
└── README.md                # 本文档
```

## 环境要求

- Python 3.8+
- 手机和电脑在同一WiFi网络下
- Windows 10/11 或 macOS 10.15+

## 快速开始

### 1. 安装依赖

```bash
cd D:\PythonWork\h5-barcode-gun-python
pip install -r requirements.txt
```

### 2. 使用Web管理控制台(推荐)

```bash
# Windows
double-click start_web_admin.bat  或
python server.py

# Linux/macOS
./start_web_admin.sh  或
python server.py
```

启动后浏览器会自动打开控制台: `http://localhost:5000/admin`

控制台功能:
- 📊 实时查看服务器状态
- 📱 查看手机访问二维码
- 📋 一键复制访问地址
- 🔗 快捷启动PC客户端
- 📝 查看实时日志

### 3. 启动服务器

```bash
# Windows
start_server.bat

# Linux/macOS (如果服务器部署在这些系统上)
./start_server.sh
```

服务器启动后会显示IP地址,例如:
```
服务器已启动!
本机IP: 192.168.1.100
端口: 5000
手机访问: http://192.168.1.100:5000
```

### 4. 启动PC客户端

在需要接收扫码数据的电脑上运行:

```bash
python pc_client.py
```

PC客户端会:
- 自动连接到服务器
- 在系统托盘中运行(Windows)
- 后台运行(macOS)
- 实时接收扫码数据并模拟键盘输入

### 5. 手机端扫码

1. **使用二维码扫描**
   - 在Web控制台查看二维码
   - 或访问 `http://localhost:5000/admin` 查看二维码
   - 用手机扫描二维码

2. **手动访问**
   - 打开手机浏览器
   - 访问 `http://{服务器IP}:5000`

3. **开始扫码**
   - 授权摄像头权限
   - 对准条形码或二维码
   - 扫描结果会自动发送到PC并输入到当前光标位置


## 配置说明

### 修改服务器地址

编辑 `pc_client.py`,修改 `SERVER_URL`:

```python
# 服务器配置(修改为实际的服务器IP)
SERVER_URL = "http://192.168.1.100:5000"
```

### 修改服务器端口

编辑 `server.py`,修改 `PORT`:

```python
PORT = 5000  # 修改为其他端口
```

### 一键启动脚本配置

#### start_server.bat / start_server.sh
基本的服务器启动脚本，运行后显示服务器IP和二维码链接

#### start_web_admin.bat / start_web_admin.sh
启动服务器并自动打开Web管理控制台

**配置浏览器路径(Windows)**:
编辑 `start_web_admin.bat`，修改chrome.exe路径：

```batch
@echo off
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" http://localhost:5000/admin
python server.py
```

如果没有Chrome，可以修改为其他浏览器：
```batch
:: Firefox
start "" firefox http://localhost:5000/admin

:: Edge
start "" microsoft-edge:http://localhost:5000/admin

:: 系统默认浏览器
start http://localhost:5000/admin
```

**配置浏览器路径(macOS)**:
编辑 `start_web_admin.sh`：

```bash
open -a "Google Chrome" http://localhost:5000/admin
python3 server.py
```

## PyInstaller 打包

### Windows

```bash
pyinstaller pc_client.spec
```

生成的可执行文件在 `dist/pc_client.exe`

### macOS

```bash
pyinstaller pc_client_mac.spec
```

生成的可执行文件在 `dist/pc_client.app`

## 打包说明

### Windows 打包

使用提供的打包脚本将PC客户端打包成独立可执行文件：

```bash
# 方式一：使用打包脚本（推荐）
double-click package_windows.bat

# 方式二：手动打包
pyinstaller --clean --noconfirm --windowed --onefile --icon=static\icon.ico --add-data "templates;templates" --add-data "static;static" --name="H5BarcodeGun" pc_client_windows.py
```

打包后的文件在 `dist\H5BarcodeGun.exe`，可以在没有Python环境的电脑上直接运行。

### macOS 打包

```bash
# 方式一：使用打包脚本（推荐）
./package_macos.sh

# 方式二：手动打包
pyinstaller --clean --noconfirm --windowed --onefile --name="H5BarcodeGun" --add-data "templates:templates" --add-data "static:static" pc_client_macos.py
```

打包后的文件在 `dist/H5BarcodeGun.app`，可以直接安装到应用程序文件夹。

### Linux 打包

Linux平台推荐使用源码运行，但也提供了打包脚本：

```bash
# 使用打包脚本
./package_linux.sh

# 该脚本会：
# 1. 生成可执行启动脚本 H5BarcodeGun
# 2. 生成依赖列表 requirements.txt
# 3. 生成 Linux使用说明 README_LINUX.md
# 4. 可选：使用PyInstaller打包服务器
```

**注意**：Linux下没有原生图形客户端，建议直接使用 `python3 server.py` 启动服务器。

### 打包要求

在打包前请确保：

1. **安装所有依赖**
   ```bash
   pip install -r requirements.txt
   ```

2. **安装PyInstaller**
   ```bash
   pip install pyinstaller==6.3.0
   ```

3. **准备图标文件**（可选）
   - Windows: `static/icon.ico` (256x256)
   - macOS: 创建 `static/icon.icns`

4. **测试运行**
   打包前确保程序可以正常运行：
   ```bash
   python pc_client_windows.py  # Windows
   python3 pc_client_macos.py    # macOS
   ```

### 打包优化建议

#### Windows优化
- 使用UPX压缩减小文件体积
- 添加版本信息
- 代码签名（避免安全警告）

#### macOS优化
- 创建DMG安装包
- 代码签名（避免Gatekeeper阻止）
- 添加到登录启动项

#### 跨平台PyInstaller配置

创建 `package.spec` 文件进行高级配置：

```python
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['pc_client_windows.py'],
    pathex=[],
    binaries=[],
    datas=[('templates', 'templates'), ('static', 'static')],
    hiddenimports=[
        'core_server',
        'flask',
        'flask_socketio',
        'eventlet',
        'socketio',
        'pyautogui',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='H5BarcodeGun',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    icon=['static/icon.ico'],
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
```

## 使用方法

### 方式一：使用PC客户端（推荐）

PC客户端集成了服务器管理功能，无需手动启动服务器。

#### Windows 用户

```bash
python pc_client_windows.py
```

或直接双击 `pc_client_windows.py`

界面功能：
- ⏯️ **启动/停止服务器** - 一键控制WebSocket服务器
- 🔗 **连接客户端** - 自动连接到本地服务器
- 📊 **状态显示** - 实时显示服务器状态和扫码数据
- 📋 **日志输出** - 查看系统运行日志
- 🖥️ **系统托盘** - 支持后台运行

#### macOS 用户

```bash
python pc_client_macos.py
```

或直接双击 `pc_client_macos.app`

菜单功能：
- 📱 **状态图标** - 菜单栏显示连接状态
- ⚙️ **服务器管理** - 启动/停止服务器
- 🔗 **客户端控制** - 连接/断开PC客户端
- 📱 **快捷访问** - 打开管理界面、复制访问地址
- 📊 **状态信息** - 查看服务器运行状态

### 方式二：独立模式

如需单独运行服务器（适合服务器与客户端分离的场景）：

```bash
# 启动服务器
python server.py

# 在其他电脑上运行PC客户端（需要配置服务器IP）
python pc_client_windows.py
```

**注意**：此模式下需要在PC客户端代码中手动配置服务器IP地址。

### 扫码流程

1. **启动客户端**
   - 运行对应平台的PC客户端
   - 点击"启动服务器"按钮
   - 浏览器自动打开管理界面（Windows）

2. **手机访问**
   - 在Web管理界面查看二维码
   - 手机扫描二维码访问H5页面
   - 或手动输入显示的IP地址

3. **开始扫码**
   - 手机端授权摄像头权限
   - 点击"开始扫描"按钮
   - 对准条形码/二维码

4. **数据接收**
   - 扫码数据自动传输到PC
   - PC客户端接收并模拟键盘输入
   - 数据输入到当前光标位置


## 注意事项

### 1. **网络要求**
- 所有设备必须在同一WiFi网络
- 关闭防火墙或开放5000端口
- 确保路由器AP隔离功能已关闭

### 2. **PC客户端**
- **管理员权限**: Windows需要以管理员身份运行（右键-以管理员身份运行）
- **后台运行**: 关闭窗口后程序仍在系统托盘运行
  - Windows: 右键托盘图标退出
  - macOS: 选择"退出"菜单
- **安全模式**: 鼠标移动到左上角可停止输入（PyAutoGUI安全模式）

### 3. **手机端**
- **浏览器要求**: iOS Safari / Android Chrome
- **HTTPS限制**: iOS 13+ 需要使用HTTPS才能访问摄像头
  - 解决方案：使用IP地址访问（如 http://192.168.x.x:5000）
  - 或使用localhost访问（手机和PC在同一设备上）
- **摄像头权限**: 首次使用需要允许摄像头访问
- **网络切换**: 手机WiFi切换后需要重新访问页面

### 4. **多客户端场景**
- 支持多个手机同时连接
- 支持多个PC客户端同时连接
- 扫码数据会广播到所有已连接的PC客户端

## 故障排除

### Q1: 手机无法访问服务器页面
**A1:**
- 检查手机和PC是否连接同一WiFi网络
- 检查防火墙设置，允许5000端口通过
- 尝试使用`http://localhost:5000`测试
- 检查PC的IP地址是否变更

### Q2: PC客户端无法连接服务器
**A2:**
- 确认服务器已启动（状态显示"运行中"）
- 检查服务器IP地址配置
- 重启PC客户端
- 检查网络连通性（ping 服务器IP）

### Q3: 扫码后PC没有输入
**A3:**
- 确认PC客户端已连接（状态显示"已连接"）
- 检查当前窗口是否有输入焦点
- 确认PyAutoGUI安全模式未触发（鼠标不在左上角）
- 尝试重启PC客户端

### Q4: 摄像头无法打开（黑屏）
**A4:**
- 检查浏览器摄像头权限设置
- iOS设备：设置-浏览器-相机权限
- Android设备：应用权限管理
- 确保未使用HTTPS访问（iOS限制）

### Q5: 二维码显示异常
**A5:**
- 刷新管理界面页面
- 检查服务器是否正常运行
- 检查浏览器控制台是否有错误

### Q6: Windows客户端闪退
**A6:**
- 检查是否已安装PyQt5: `pip install PyQt5`
- 以管理员身份运行
- 检查日志文件`client.log`
- 尝试从命令行运行查看错误信息

### Q7: macOS客户端无法启动
**A7:**
- 安装rumps: `pip install rumps`
- 检查Python版本: `python3 --version`
- 尝试从终端运行: `python3 pc_client_macos.py`
- 检查系统偏好设置-安全性与隐私

### Q8: 扫码数据乱码
**A8:**
- 检查条码编码格式
- 确认输入法和键盘布局
- 尝试修改PyAutoGUI配置

### Q9: 连接不稳定，频繁断开
**A9:**
- 检查网络信号强度
- 关闭省电模式（手机）
- 减少网络负载（关闭下载等）
- 增加心跳检测间隔（高级配置）

## 高级配置

### 修改服务器端口

编辑 `core_server.py` 中的端口配置：

```python
def __init__(self, host='0.0.0.0', port=5000):  # 修改5000为其他端口
    self.host = host
    self.port = port
```

### 自定义按键

编辑 `pc_client_*.py` 中的输入配置：

```python
# 修改按键间隔
pyautogui.PAUSE = 0.1  # 增加间隔时间（秒）

# 修改按键动作
pyautogui.typewrite(barcode)  # 输入条码
pyautogui.press('tab')         # 改为按Tab键
# pyautogui.press('enter')     # 注释掉回车键
```

### 添加扫码音效

在 `pc_client_macos.py` 中添加通知：

```python
rumps.notification(
    title="扫码成功",
    subtitle=barcode,
    message=f"已接收扫码数据",
    sound=True  # 启用声音
)
```

## 开发说明

### 技术架构

- **核心服务器** (`core_server.py`)
  - Flask + Flask-SocketIO 提供WebSocket服务
  - 独立模块，可被任何客户端调用
  - 支持手机和PC客户端连接管理

- **Windows客户端** (`pc_client_windows.py`)
  - PyQt5 图形界面框架
  - 多线程架构（服务器在后台线程运行）
  - 信号槽机制实现异步通信

- **macOS客户端** (`pc_client_macos.py`)
  - rumps 菜单栏应用框架
  - 异步SocketIO客户端
  - 与macOS系统集成

- **手机端**
  - HTML5 + JavaScript
  - html5-qrcode 库处理扫码
  - SocketIO客户端实时通信

### 核心模块说明

**ServerManager** - 服务器管理器
```python
manager = ServerManager()
success, message = manager.start()  # 启动服务器
info = manager.get_status()         # 获取状态
manager.stop()                      # 停止服务器
```

**PCClient** - PC客户端
```python
client = PCClient()
client.connect(server_url)          # 连接到服务器
client.disconnect()                 # 断开连接
```

### 扩展建议

1. **添加扫码历史记录**
   - 在core_server.py中添加数据库
   - 保存扫码时间、内容、设备信息

2. **支持批量扫码模式**
   - 添加队列管理
   - 实现批量导入导出功能

3. **添加用户认证**
   - Flask-Login集成
   - Token认证机制

4. **支持多个PC客户端**
   - 实现客户端分组管理
   - 选择性发送扫码数据

5. **添加Web API**
   - RESTful API接口
   - 支持第三方集成

6. **移动端App**
   - 封装为Hybrid App
   - 发布到应用商店

## 许可证

MIT License

## 鸣谢

- 原Java项目: https://gitee.com/zkool/h5-barcode-gun
- html5-qrcode: https://github.com/mebjas/html5-qrcode
- Flask-SocketIO: https://flask-socketio.readthedocs.io/
- PyQt5: https://www.riverbankcomputing.com/software/pyqt/
- rumps: https://github.com/jaredks/rumps
