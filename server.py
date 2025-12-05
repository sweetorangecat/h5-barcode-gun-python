#!/usr/bin/env python3
"""
H5 Barcode Gun - WebSocket服务器启动脚本
简化版，直接启动核心服务器模块
"""

import sys
import argparse
from core_server import BarcodeGunServer


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='H5扫码枪WebSocket服务器')
    parser.add_argument('--host', default='0.0.0.0', help='监听主机地址 (默认: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=5000, help='监听端口 (默认: 5000)')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')

    args = parser.parse_args()

    # 创建服务器实例
    server = BarcodeGunServer(host=args.host, port=args.port)

    try:
        # 获取服务器信息
        import eventlet
        eventlet.monkey_patch()

        info = server.get_server_info()
        local_ip = info['ip']

        print("\n" + "=" * 60)
        print("  H5 扫码枪 WebSocket 服务器")
        print("=" * 60)
        print(f"本机IP地址: {local_ip}")
        print(f"服务器端口: {args.port}")
        print(f"手机访问: http://{local_ip}:{args.port}")
        print(f"PC管理: http://{local_ip}:{args.port}/admin")
        print("\n使用说明:")
        print("1. 在需要接收扫码数据的电脑上运行PC客户端")
        print("2. 在手机浏览器访问上面的地址")
        print("3. 手机和PC客户端会自动连接到服务器")
        print("4. 手机扫码后数据会实时传输到PC")
        print("=" * 60 + "\n")

        # 启动服务器
        server.start()

    except KeyboardInterrupt:
        print("\n服务器已停止")
        sys.exit(0)
    except Exception as e:
        print(f"服务器运行出错: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
