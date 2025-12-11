#!/usr/bin/env python3
"""
测试扫码流程
验证H5页面的扫码结果能通过WebSocket上报给服务端并打印
"""

import time
from dual_server import DualBarcodeGunServer

print("=" * 60)
print("测试扫码流程")
print("=" * 60)
print("1. 启动双端口服务器")
print("2. 等待H5页面连接并扫码")
print("3. 验证服务端是否能打印扫描的条码")
print("=" * 60)

# 启动双端口服务器
server = DualBarcodeGunServer(http_host='0.0.0.0', http_port=5100, ws_port=9999)
server.start()

print("\n服务器已启动")
print("请在浏览器中打开: https://localhost:5100")
print("然后使用H5页面扫描条码")
print("\n服务器日志将显示扫描的条码内容")
print("=" * 60)

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\n\n停止服务器...")
    server.stop()
