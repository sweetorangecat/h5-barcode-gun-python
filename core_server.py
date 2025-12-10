#!/usr/bin/env python3
"""
H5 Barcode Gun - 核心服务器模块
独立的WebSocket服务器，与客户端分离
"""

import logging
from datetime import datetime
import os
import socket
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import signal
import sys
import qrcode
import base64
from io import BytesIO
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BarcodeGunServer:
    """扫码枪核心服务器类"""

    def __init__(self, host='0.0.0.0', port=5000):
        self.host = host
        self.port = port
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'h5-barcode-gun-secret')

        # 配置SocketIO
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

    def _register_routes(self):
        """注册Flask路由"""

        @self.app.route('/')
        def index():
            """手机端扫码页面"""
            return render_template('scanner.html')

        @self.app.route('/admin')
        def admin():
            """PC管理页面"""
            return render_template('admin.html')

        @self.app.route('/api/status')
        def get_status():
            """获取服务器状态"""
            return jsonify(self.get_server_info())

        # @self.app.route('/api/qrcode')
        # def get_qrcode():
        #     """生成手机端访问二维码"""
        #     local_ip = self.get_local_ip()
        #     mobile_url = f"http://{local_ip}:{self.port}"

            # 生成二维码
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(mobile_url)
            qr.make(fit=True)

            # 创建图像
            img = qr.make_image(fill_color="black", back_color="white")

            # 转换为base64
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()

            return jsonify({
                'qr_code': f"data:image/png;base64,{img_str}",
                'url': mobile_url
            })

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

            if client_type == 'pc_client':
                self.pc_clients[sid] = {
                    'platform': platform,
                    'connect_time': datetime.now(),
                    'ip': request.remote_addr
                }
                logger.info(f"PC客户端已注册: {sid} (平台: {platform})")

                # 通知PC客户端连接成功
                emit('pc_connected', {
                    'status': 'success',
                    'message': 'PC客户端已连接',
                    'connected_at': datetime.now().isoformat()
                })

            elif client_type == 'mobile':
                self.mobile_clients[sid] = {
                    'connect_time': datetime.now(),
                    'ip': request.remote_addr
                }
                logger.info(f"手机端已注册: {sid}")

                # 通知手机端连接成功
                emit('mobile_connected', {
                    'status': 'success',
                    'message': '手机端已连接',
                    'pc_connected': len(self.pc_clients) > 0
                })

                # 如果PC已连接,通知手机端
                if self.pc_clients:
                    emit('pc_status', {
                        'connected': True,
                        'count': len(self.pc_clients)
                    })
            else:
                logger.warning(f"未知的客户端类型: {client_type}")

        @self.socketio.on('barcode_scan')
        def handle_barcode_scan(data):
            """处理手机端扫描的条码"""
            barcode = data.get('barcode', '')
            barcode_type = data.get('type', 'unknown')
            timestamp = data.get('timestamp')

            if not barcode:
                logger.warning("接收到空的条码数据")
                emit('scan_error', {'message': '条码不能为空'})
                return

            logger.info(f"收到条码扫描: {barcode} (类型: {barcode_type})")

            # 转发给所有PC客户端
            if self.pc_clients:
                for pc_sid in self.pc_clients.keys():
                    emit('scan_result', {
                        'barcode': barcode,
                        'type': barcode_type,
                        'timestamp': timestamp or datetime.now().isoformat(),
                        'from_mobile': request.sid
                    }, room=pc_sid)

                logger.info(f"条码已转发给 {len(self.pc_clients)} 个PC客户端")
                self.scan_count += 1

                # 返回成功响应给手机端
                emit('scan_success', {
                    'barcode': barcode,
                    'sent_to_pc': len(self.pc_clients),
                    'timestamp': datetime.now().isoformat()
                })
            else:
                logger.warning("没有PC客户端连接,条码未发送")
                emit('scan_error', {
                    'message': '没有PC客户端连接',
                    'barcode': barcode
                })

        @self.socketio.on('ping')
        def handle_ping():
            """处理心跳检测"""
            emit('pong', {
                'timestamp': datetime.now().isoformat(),
                'server_time': datetime.now().timestamp()
            })

        @self.socketio.on('request_pc_status')
        def handle_pc_status_request():
            """处理PC客户端状态查询"""
            emit('pc_status', {
                'connected': len(self.pc_clients) > 0,
                'count': len(self.pc_clients),
                'clients': [
                    {
                        'platform': info['platform'],
                        'connect_time': info['connect_time'].isoformat()
                    }
                    for info in self.pc_clients.values()
                ]
            })

    def _signal_handler(self, signum, frame):
        """处理退出信号"""
        logger.info(f"接收到信号 {signum},正在关闭服务器...")
        self.stop()

    def get_local_ip(self):
        """获取本机局域网IP地址"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception as e:
            logger.error(f"获取IP地址失败: {e}")
            return '127.0.0.1'

    def get_server_info(self):
        """获取服务器信息"""
        return {
            'ip': self.get_local_ip(),
            'port': self.port,
            'mobile_clients': len(self.mobile_clients),
            'pc_clients': len(self.pc_clients),
            'scan_count': self.scan_count,
            'start_time': self.start_time.isoformat(),
            'running': self.running
        }

    def start(self):
        """启动服务器"""
        if self.running:
            logger.warning("服务器已经在运行")
            return False

        logger.info(f"正在启动服务器...")
        logger.info(f"监听地址: http://{self.host}:{self.port}")

        # 在后台线程中运行服务器
        self.running = True

        try:
            self.socketio.run(
                self.app,
                host=self.host,
                port=self.port,
                debug=False,
                log_output=False,
                use_reloader=False  # 禁用在生产环境中的自动重载
            )
        except KeyboardInterrupt:
            logger.info("服务器已停止")
            self.running = False
        except Exception as e:
            logger.error(f"服务器运行出错: {e}")
            self.running = False
            raise

        return True

    def stop(self):
        """停止服务器"""
        if not self.running:
            logger.warning("服务器未在运行")
            return False

        logger.info("正在停止服务器...")
        self.running = False

        # 关闭所有客户
        self.socketio.stop()

        return True

    print("恢复成功")
