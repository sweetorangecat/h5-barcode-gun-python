# H5扫码枪 - 安装使用指南

## 打包后的一键启动方案

### 方案1：智能启动（推荐）

打包后的exe运行时，会自动：

1. **检查证书** → 如果没有，自动生成
2. **检查端口** → 如果占用，提示用户
3. **启动HTTPS** → 使用生成的证书
4. **显示访问地址** → 清晰的提示信息

**使用方法：**

```bash
# 打包
cd D:\PythonWork\h5-barcode-gun-python
python package.py

# 运行（在dist目录）
dist\H5BarcodeGun.exe
```

### 方案2：批处理启动

如果不想打包成单个exe，可以使用批处理文件：

**start.bat:**
```bat
@echo off
echo 正在启动H5扫码枪服务...

# 生成证书（如果还没有）
python cert_utils.py --install

# 启动服务
python server_https.py

pause
```

### 方案3：手动步骤

1. **安装Python**
   - Python 3.8+
   - 添加到系统PATH

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **生成证书**
   ```bash
   python cert_utils.py --install
   ```

4. **启动服务**
   ```bash
   python server_https.py
   ```

## 打包配置说明

### 1. 打包命令

```bash
python package.py
```

### 2. 打包后文件结构

```
dist/
├── H5BarcodeGun.exe          # 主程序（包含服务器）
├── cert_utils.py             # 证书工具（可选）
├── generate_cert.py          # 证书生成（可选）
├── server_https.py           # HTTPS服务器（可选）
├── server_simple.py          # HTTP服务器（可选）
├── start.bat                 # 启动脚本（可选）
```

### 3. 运行方式

**方式A：直接运行exe**
```bash
H5BarcodeGun.exe
```
- 自动启动HTTPS服务器
- 自动创建证书（如果没有）

**方式B：使用启动脚本**
```bash
start.bat
```
- 先生成证书
- 再启动服务

**方式C：手动使用工具**
```bash
# 仅生成证书
cert_utils.exe --install

# 手动启动服务
server_https.exe
```

## 用户常见问题

### Q1: 手机访问时提示"不安全"？

**A:** 这是正常的，因为使用的是自签名证书。

**解决方案：**
1. 点击"高级"
2. 点击"继续访问"（或"前往[IP地址]"）
3. 允许摄像头权限

### Q2: 摄像头无法调用？

**可能原因1：** 没有使用HTTPS

**解决方案：**
- 确保使用 `https://` 而不是 `http://`
- 运行 `server_https.py` 而不是 `server.py`

**可能原因2：** 浏览器权限问题

**解决方案（iOS）：**
1. 设置 → Safari → 相机 → 允许
2. 设置 → Safari → 网站设置 → 相机 → 允许

**解决方案（Android）：**
1. 设置 → 应用 → Chrome → 权限 → 相机 → 允许

### Q3: 如何查找服务器IP？

**Windows：**
```bash
ipconfig
```
查找 "IPv4地址"（通常是 192.168.x.x）

**macOS/Linux：**
```bash
ifconfig
```
或
```bash
ip addr
```

### Q4: 端口被占用怎么办？

**错误提示：** "Address already in use"

**解决方案：**
1. 关闭占用端口的程序
2. 或修改服务器端口（在代码中修改）

### Q5: 打包后运行报错？

**常见错误：** "Module not found"

**解决方案：**
1. 确保所有依赖已安装
2. 使用 `--hidden-import` 添加缺失模块
3. 检查 `--add-data` 路径是否正确

## 完整打包示例

### 1. 安装打包工具
```bash
pip install pyinstaller
```

### 2. 配置打包脚本 `package.py`

已经创建好的配置：
- 单文件打包
- 包含静态文件
- 隐藏不必要的模块

### 3. 执行打包
```bash
python package.py
```

### 4. 分发文件
打包完成后，在 `dist/` 目录找到 `H5BarcodeGun.exe`

### 5. 使用
```bash
H5BarcodeGun.exe  # 一键启动
```

## 高级配置

### 修改默认端口

编辑 `core_server.py`：
```python
def __init__(self, host='0.0.0.0', port=8080):  # 修改5000为其他端口
```

### 修改证书有效期

编辑 `cert_utils.py`：
```python
cert.gmtime_adj_notAfter(10*365*24*60*60)  # 默认10年
```

### 自定义证书信息

编辑 `cert_utils.py`：
```python
cert.get_subject().CN = "your-domain.com"  # 修改域名
```

## 故障排查

### 1. 启动后立即退出

**检查：**
- Python版本是否 >= 3.8
- 依赖是否完整安装
- 端口是否被占用

**修复：**
```bash
# 查看详细错误
python server_https.py 2>&1 | tee error.log
```

### 2. 手机无法连接

**检查：**
- 手机和电脑是否在同一WiFi
- 防火墙是否允许5000端口
- IP地址是否正确

**修复：**
```bash
# Windows 防火墙
netsh advfirewall firewall add rule name="H5 Barcode Gun" dir=in action=allow protocol=TCP localport=5000
```

### 3. 扫码无反应

**检查：**
- 浏览器是否允许摄像头
- 是否使用HTTPS
- PC客户端是否连接

**修复：**
- 查看浏览器控制台（F12）
- 检查是否有错误信息
- 刷新页面重试

## 总结

### 最佳实践

1. **开发环境**：使用 `server_auto.py`
2. **生产环境**：使用打包后的 `H5BarcodeGun.exe`
3. **快速启动**：使用 `start.bat`
4. **故障排查**：使用 `cert_utils.py --info`

### 一键启动流程

```bash
# 1. 打包
python package.py

# 2. 复制到目标电脑
#    复制 dist\H5BarcodeGun.exe

# 3. 运行
H5BarcodeGun.exe

# 4. 访问
#    手机浏览器: https://<电脑IP>:5000
```

现在，用户只需要双击 `.exe` 文件或 `.bat` 脚本，即可自动完成所有配置并启动服务！
