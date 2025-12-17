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
from utils.keyboard_simulator import simulate_keyboard_input

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 禁用Flask的开发服务器警告
import warnings
warnings.filterwarnings('ignore', message='.*development server.*')
warnings.filterwarnings('ignore', message='.*production deployment.*')
import os
os.environ['FLASK_ENV'] = 'development'


class BarcodeGunServer:
    """HTTPS扫码枪服务器类（单端口）"""

    def __init__(self, host='0.0.0.0', port=5100, barcode_callback=None):
        self.host = host
        self.port = port
        self.barcode_callback = barcode_callback  # 用于通知PC客户端的回调函数

        # 创建Flask应用
        # 配置模板和静态文件路径，确保在打包后也能正确找到
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        template_folder = os.path.join(project_dir, 'templates')
        static_folder = os.path.join(project_dir, 'static')

        self.app = Flask(__name__,
                        template_folder=template_folder,
                        static_folder=static_folder)
        self.app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'h5-barcode-gun-secret')

        # 配置SocketIO - WebSocket通过HTTP端口升级，不需要独立端口
        # 注意：不使用eventlet，使用threading模式避免卡死
        self.socketio = SocketIO(
            self.app,
            cors_allowed_origins="*",
            logger=False,  # 关闭日志避免性能问题
            engineio_logger=False,
            async_mode='threading',  # 使用threading替代eventlet，更稳定
            ping_timeout=60,
            ping_interval=30,
            async_handlers=True  # 异步处理handler
        )

        # 存储连接的客户端
        self.mobile_clients = {}  # 手机端客户端
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
            return render_template('scanner.html')

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

                # 模拟键盘输入条码并添加回车符
                logger.info(f"正在模拟键盘输入条码: {barcode}")
                keyboard_success = simulate_keyboard_input(barcode)
                if keyboard_success:
                    logger.info("✓ 键盘模拟输入成功")
                else:
                    logger.error("✗ 键盘模拟输入失败")

                # 通过回调通知PC客户端（如果设置了回调）
                if self.barcode_callback:
                    try:
                        self.barcode_callback(barcode)
                    except Exception as e:
                        logger.error(f"调用条码回调失败: {e}")

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
            'host': self.host,
            'port': self.port,
            'ip': self.get_local_ip(),
            'mobile_clients': len(self.mobile_clients),
            'total_connections': len(self.mobile_clients),
            'scan_count': self.scan_count,
            'start_time': self.start_time.isoformat(),
            'uptime': str(datetime.now() - self.start_time)
        }

    def _signal_handler(self, signum, frame):
        """信号处理"""
        logger.info(f"接收到信号 {signum}，正在关闭服务器...")
        self.stop()

    def start(self):
        """启动HTTPS服务器（包含HTTP和WebSocket）"""
        if self.running:
            logger.warning("服务器已在运行")
            return

        self.running = True
        logger.info("正在启动HTTPS服务器...")

        try:
            # 加载SSL证书
            from utils.cert_utils import CertManager
            cert_manager = CertManager()

            if not cert_manager.check_and_create_cert():
                logger.error("SSL证书生成失败，无法启动HTTPS")
                return

            ssl_context = cert_manager.get_ssl_context()
            if not ssl_context:
                logger.error("无法创建SSL上下文")
                return

            logger.info(f"HTTPS/WSS服务器启动于 {self.host}:{self.port}")

            # 启动Flask + SocketIO服务器（WebSocket通过HTTP端口自动升级）
            # 注意：必须在主线程中运行，使用socketio.run()而不是app.run()
            self.socketio.run(
                self.app,
                host=self.host,
                port=self.port,
                debug=False,
                use_reloader=False,
                log_output=False,  # 关闭日志输出避免性能问题
                ssl_context=ssl_context,
                allow_unsafe_werkzeug=True  # 允许在threading模式下使用Werkzeug
            )

        except Exception as e:
            logger.error(f"服务器运行出错: {e}", exc_info=True)
            self.running = False

    def stop(self):
        """停止HTTPS服务器"""
        if not self.running:
            logger.warning("服务器未在运行")
            return

        logger.info("正在停止服务器...")
        self.running = False

        try:
            # 清空客户端列表
            logger.debug("清空客户端列表...")
            self.mobile_clients.clear()

            # 强制退出进程
            logger.info("服务器已停止（立即强制退出）")
            os._exit(0)
        except Exception as e:
            os._exit(0)

def main():
    """主函数"""
    # 使用环境变量或默认值
    port = int(os.getenv('PORT', '5100'))
    host = os.getenv('HOST', '0.0.0.0')

    server = BarcodeGunServer(host=host, port=port)

    # 启动服务器
    server.start()

    logger.info("=" * 60)
    logger.info("H5扫码枪 - HTTPS服务器已启动")
    logger.info("=" * 60)
    logger.info(f"服务器地址: https://{server.get_local_ip()}:{port}")
    logger.info("=" * 60)
    logger.info("手机访问HTTPS地址即可扫码")
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
