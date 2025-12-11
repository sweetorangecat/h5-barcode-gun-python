#!/usr/bin/env python3
"""
H5 Barcode Gun - 双端口服务器（修复版）
HTTP服务器(5100) + WebSocket服务器(9999) - 只使用一个Flask应用
"""

import logging
from datetime import datetime
import os
import socket
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import signal
import sys
import threading
import time
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DualBarcodeGunServer:
    """扫码枪双端口服务器类"""

    def __init__(self, http_host='0.0.0.0', http_port=5100, ws_port=9999, barcode_callback=None):
        self.http_host = http_host
        self.http_port = http_port
        self.ws_port = ws_port
        self.barcode_callback = barcode_callback  # 用于通知PC客户端的回调函数

        # 创建Flask应用
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'h5-barcode-gun-secret')

        # 配置SocketIO绑定到ws_port
        self.socketio = SocketIO(
            self.app,
            cors_allowed_origins="*",
            logger=True,
            engineio_logger=True,
            async_mode='eventlet',
            ping_timeout=60,
            ping_interval=30
        )

        # 存储连接的客户端
        self.mobile_clients = {}  # 手机端客户端
        self.pc_clients = {}      # PC客户端
        self.scan_count = 0       # 扫码次数统计
        self.start_time = datetime.now()  # 服务器启动时间

        # 注册路由和SocketIO事件
        self._register_routes()
        self._register_socketio_events()

        # 注册信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        self.running = False
        self.http_thread = None
        self.ws_thread = None

    def _register_routes(self):
        """注册Flask路由"""

        @self.app.route('/')
        def index():
            """手机端扫码页面"""
            return render_template('scanner_new.html', ws_port=self.ws_port)

        @self.app.route('/admin')
        def admin():
            """PC管理页面"""
            return render_template('admin.html', ws_port=self.ws_port)

        @self.app.route('/api/status')
        def get_status():
            """获取服务器状态"""
            return jsonify(self.get_server_info())

    def _register_socketio_events(self):
        """注册SocketIO事件处理"""

        @self.socketio.on('connect')
        def handle_connect():
            """处理客户端连接"""
            logger.info(f"客户端连接: {request.sid} (IP: {request.remote_addr})")

            emit('server_response', {
                'status': 'connected',
                'message': '已连接到服务器',
                'timestamp': datetime.now().isoformat()
            })

        @self.socketio.on('disconnect')
        def handle_disconnect():
            """处理客户端断开连接"""
            sid = request.sid

            # 从客户端列表中移除
            if sid in self.mobile_clients:
                del self.mobile_clients[sid]
                logger.info(f"手机端断开连接: {sid}")
            elif sid in self.pc_clients:
                del self.pc_clients[sid]
                logger.info(f"PC客户端断开连接: {sid}")
            else:
                logger.info(f"未知客户端断开连接: {sid}")

        @self.socketio.on('client_info')
        def handle_client_info(data):
            """处理客户端信息"""
            sid = request.sid
            client_type = data.get('type', 'unknown')
            platform = data.get('platform', 'unknown')

            client_info = {
                'sid': sid,
                'type': client_type,
                'platform': platform,
                'ip': request.remote_addr,
                'connect_time': datetime.now().isoformat(),
                'version': data.get('version', 'unknown')
            }

            if client_type == 'mobile_client':
                self.mobile_clients[sid] = client_info
                logger.info(f"手机端连接: {sid} (平台: {platform})")
                emit('server_response', {
                    'status': 'registered',
                    'message': '手机端已注册',
                    'client_type': 'mobile'
                })

            elif client_type == 'pc_client':
                self.pc_clients[sid] = client_info
                logger.info(f"PC客户端连接: {sid} (平台: {platform})")
                emit('server_response', {
                    'status': 'registered',
                    'message': 'PC客户端已注册',
                    'client_type': 'pc'
                })
            else:
                logger.warning(f"未知客户端类型: {client_type}")

        @self.socketio.on('scan_result')
        def handle_scan_result(data):
            """处理扫码结果"""
            barcode = data.get('barcode', '')
            client_info = self.mobile_clients.get(request.sid, {})

            if barcode:
                self.scan_count += 1
                # 打印H5页面上报的条码
                logger.info(f"=*==*==*==*==*==*==*==*==*==*==*==*==*==*==*==*==*==*==*==*=")
                logger.info(f"H5页面扫码上报: {barcode}")
                logger.info(f"手机平台: {client_info.get('platform', 'unknown')}, 连接ID: {request.sid}")
                logger.info(f"=*==*==*==*==*==*==*==*==*==*==*==*==*==*==*==*==*==*==*==*=")

                # 通过回调通知PC客户端（如果设置了回调）
                if self.barcode_callback:
                    try:
                        self.barcode_callback(barcode)
                    except Exception as e:
                        logger.error(f"调用条码回调失败: {e}")

                # 广播给所有PC客户端
                for pc_sid in self.pc_clients.keys():
                    emit('scan_result', {
                        'barcode': barcode,
                        'timestamp': datetime.now().isoformat(),
                        'from_mobile': client_info.get('platform', 'unknown')
                    }, room=pc_sid)

                # 确认收到并打印确认消息
                emit('scan_confirm', {
                    'status': 'success',
                    'barcode': barcode
                })
                logger.info(f"已确认收到条码: {barcode}")
            else:
                logger.warning(f"收到空条码 (来自: {request.sid})")
                emit('scan_confirm', {
                    'status': 'error',
                    'message': '条码不能为空'
                })

    def get_local_ip(self):
        """获取本机IP地址"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return '127.0.0.1'

    def get_server_info(self):
        """获取服务器信息"""
        return {
            'running': self.running,
            'host': self.http_host,
            'http_port': self.http_port,
            'ws_port': self.ws_port,
            'ip': self.get_local_ip(),
            'mobile_clients': len(self.mobile_clients),
            'pc_clients': len(self.pc_clients),
            'total_connections': len(self.mobile_clients) + len(self.pc_clients),
            'scan_count': self.scan_count,
            'start_time': self.start_time.isoformat(),
            'uptime': str(datetime.now() - self.start_time)
        }

    def _signal_handler(self, signum, frame):
        """信号处理"""
        logger.info(f"接收到信号 {signum}，正在关闭服务器...")
        self.stop()

    def start_http_server(self):
        """在后台线程运行HTTP服务器"""
        try:
            logger.info(f"HTTPS服务器启动于 {self.http_host}:{self.http_port}")

            # 加载SSL证书
            from cert_utils import CertManager
            cert_manager = CertManager()

            if not cert_manager.check_and_create_cert():
                logger.error("SSL证书生成失败，无法启动HTTPS")
                return

            ssl_context = cert_manager.get_ssl_context()
            if not ssl_context:
                logger.error("无法创建SSL上下文")
                return

            self.app.run(
                host=self.http_host,
                port=self.http_port,
                debug=False,
                use_reloader=False,
                threaded=True,
                ssl_context=ssl_context
            )
        except Exception as e:
            logger.error(f"HTTP服务器运行出错: {e}", exc_info=True)

    def start_ws_server(self):
        """在后台线程运行WebSocket服务器"""
        try:
            logger.info(f"WebSocket服务器启动于 {self.http_host}:{self.ws_port}")

            # 加载SSL证书用于WebSocket服务器（支持HTTPS/WSS）
            from cert_utils import CertManager
            cert_manager = CertManager()

            if not cert_manager.check_and_create_cert():
                logger.error("SSL证书生成失败，无法启动WSS")
                return

            ssl_context = cert_manager.get_ssl_context()
            if not ssl_context:
                logger.error("无法创建SSL上下文")
                return

            # 使用证书文件路径而不是ssl_context对象
            cert_file = cert_manager.cert_file
            key_file = cert_manager.key_file

            self.socketio.run(
                self.app,
                host=self.http_host,
                port=self.ws_port,
                debug=False,
                use_reloader=False,
                log_output=True,
                certfile=cert_file,  # 使用certfile参数
                keyfile=key_file     # 使用keyfile参数
            )
        except Exception as e:
            logger.error(f"WebSocket服务器运行出错: {e}", exc_info=True)

    def start(self):
        """启动服务器"""
        if self.running:
            logger.warning("服务器已在运行")
            return

        self.running = True
        logger.info("正在启动双端口服务器...")

        # 启动HTTP服务器线程（非守护线程）
        self.http_thread = threading.Thread(target=self.start_http_server, daemon=False)
        self.http_thread.start()

        # 等待一下确保HTTP服务器启动
        time.sleep(0.5)

        # 启动WebSocket服务器线程（非守护线程）
        self.ws_thread = threading.Thread(target=self.start_ws_server, daemon=False)
        self.ws_thread.start()

        logger.info("双端口服务器启动完成")

    def stop(self):
        """停止服务器"""
        if not self.running:
            logger.warning("服务器未在运行")
            return

        logger.info("正在停止服务器...")
        self.running = False

        # 停止SocketIO服务器（会同时停止WebSocket）
        self.socketio.stop()

        logger.info("服务器已停止")


def main():
    """主函数"""
    # 使用环境变量或默认值
    http_port = int(os.getenv('HTTP_PORT', '5100'))
    ws_port = int(os.getenv('WS_PORT', '9999'))
    host = os.getenv('HOST', '0.0.0.0')

    server = DualBarcodeGunServer(http_host=host, http_port=http_port, ws_port=ws_port)

    # 启动服务器
    server.start()

    logger.info("=" * 60)
    logger.info("H5扫码枪 - 双端口服务器已启动")
    logger.info("=" * 60)
    logger.info(f"HTTP服务器: http://{server.get_local_ip()}:{http_port}")
    logger.info(f"WebSocket服务器: ws://{server.get_local_ip()}:{ws_port}")
    logger.info("=" * 60)
    logger.info("手机访问HTTP地址即可扫码")
    logger.info("=" * 60)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("\n正在关闭服务器...")
        server.stop()
        sys.exit(0)


if __name__ == '__main__':
    main()
