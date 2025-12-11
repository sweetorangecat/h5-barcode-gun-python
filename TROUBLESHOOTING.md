# H5扫码枪 - 问题排查指南

## 问题1: "[WinError 10048] 端口被占用"

### 症状
```
OSError: [WinError 10048] 通常每个套接字地址(协议/网络地址/端口)只允许使用一次。
```

### 原因
端口5000已被其他程序占用

### 解决方案

#### 方案A：查找并终止占用进程（推荐）

**Windows:**
```cmd
# 查找占用端口5000的进程
netstat -ano | findstr :5000

# 查看进程名称
tasklist /FI "PID eq <进程号>"

# 终止进程
taskkill /PID <进程号> /F
```

**macOS/Linux:**
```bash
# 查找占用端口5000的进程
lsof -i :5000

# 终止进程
kill -9 <进程号>
```

#### 方案B：修改服务器端口

编辑 `core_server.py`：
```python
def __init__(self, host='0.0.0.0', port=5100):  # 改为5100或其他端口
```

#### 方案C：自动端口切换

查看 `server_auto.py` 已经实现了自动检测可用端口

## 问题2: "code 400, message Bad request version"

### 症状
```
code 400, message Bad request version ('\\x00*')
```

### 原因
浏览器尝试使用**HTTPS**协议访问**HTTP**服务器

### 解决方案

#### 方案A：使用正确的协议访问

**重要：** 查看服务器启动时的日志，确定服务器使用的协议

如果是HTTP服务器：
```
访问: http://localhost:5000
```

如果是HTTPS服务器：
```
访问: https://localhost:5000
```

#### 方案B：清除浏览器缓存

浏览器可能缓存了HTTPS重定向，需要清除：
1. 按 `Ctrl + Shift + Delete` (Windows) / `Cmd + Shift + Delete` (macOS)
2. 选择"缓存"和"Cookie"
3. 清除数据
4. 重新访问

#### 方案C：使用隐身模式

打开浏览器隐身/无痕模式访问，避免缓存影响

#### 方案D：检查服务器配置

查看服务器启动日志：
```
# HTTP服务器
[INFO] - 监听地址: http://0.0.0.0:5000

# HTTPS服务器
[INFO] - 监听地址: https://0.0.0.0:5000
[INFO] - SSL证书: D:\\...\\server.crt
```

确保使用与服务器匹配的协议访问

## 问题3: 摄像头无法调用

### 症状
- 浏览器没有弹出摄像头权限请求
- 提示"无法访问摄像头"

### 原因
1. 必须使用HTTPS协议
2. 浏览器安全限制

### 解决方案

#### 方案A：使用HTTPS服务器（推荐）

```bash
# 1. 生成证书（如果还没有）
pip install pyOpenSSL
python generate_cert.py

# 2. 启动HTTPS服务器
python server_https.py
```

然后访问 `https://<服务器IP>:5000`

#### 方案B：使用localhost（仅限本机测试）

http://localhost:5000 可以在某些浏览器上调用摄像头

#### 方案C：配置浏览器权限

**iOS Safari:**
1. 设置 → Safari → 相机 → 允许
2. 设置 → Safari → 网站设置 → 相机 → 允许

**Android Chrome:**
1. 设置 → 应用 → Chrome → 权限 → 相机 → 允许

## 问题4: 连接超时或断开

### 症状
- 手机显示"未连接到服务器"
- 连接后很快断开

### 原因
1. 手机和服务器不在同一网络
2. 防火墙阻止连接
3. Socket.IO版本不匹配

### 解决方案

#### 方案A：检查网络连接

确保手机和服务器电脑在同一WiFi网络

#### 方案B：检查防火墙

**Windows:**
```cmd
# 开放端口5000
netsh advfirewall firewall add rule name="H5 Barcode Gun" dir=in action=allow protocol=TCP localport=5000
```

#### 方案C：检查IP地址

查看服务器实际IP：
```bash
# Windows
ipconfig

# macOS/Linux
ifconfig
```

使用手机访问显示的IP地址

## 问题5: 扫码结果无法发送到PC

### 症状
- 手机扫码成功
- PC客户端没有反应

### 原因
1. PC客户端未连接到服务器
2. 网络问题
3. 权限问题

### 解决方案

#### 方案A：检查PC客户端连接

查看 `pc_client_windows.py` 界面：
- 是否显示"已连接到服务器"
- 如果没有，检查IP和端口是否正确

#### 方案B：查看服务器日志

服务器应该显示：
```
PC客户端已连接 (1台)
```

#### 方案C：检查安全软件

某些杀毒软件可能阻止WebSocket连接

## 快速诊断清单

运行前检查：
- [ ] 端口5000没有被占用
- [ ] Python版本 >= 3.8
- [ ] eventlet 已安装
- [ ] 手机和电脑在同一网络

运行时检查：
- [ ] 服务器启动无错误
- [ ] 使用正确的协议访问（HTTP/HTTPS）
- [ ] 浏览器允许摄像头权限
- [ ] PC客户端已连接

访问时检查：
- [ ] 使用服务器IP，不是localhost（手机访问）
- [ ] HTTPS协议时，点击"高级"→"继续访问"
- [ ] 清除浏览器缓存或使用隐身模式

## 调试方法

### 启用详细日志

修改 `core_server.py`：
```python
logging.basicConfig(
    level=logging.DEBUG,  # 改为DEBUG级别
    format='%(asctime)s - %(levelname)s - %(message)s'
)
```

### 查看浏览器控制台

1. 按F12打开开发者工具
2. 切换到"Console"选项卡
3. 查看错误信息

### 使用curl测试

```bash
# 测试服务器连接
curl http://localhost:5000/api/status
```

## 总结

1. **端口被占用** → 终止进程或修改端口
2. **Bad request version** → 使用正确的HTTP/HTTPS协议
3. **摄像头无法调用** → 使用HTTPS或localhost
4. **连接超时** → 检查网络和防火墙
5. **无法发送到PC** → 检查PC客户端连接

按照以上步骤排查，大部分问题都可以解决。
