#!/usr/bin/env python3
"""
H5 Barcode Gun - macOS PC客户端
集成服务器管理功能，使用rumps创建菜单栏应用
"""

import sys
import asyncio
import socketio
import pyautogui
import logging
from datetime import datetime
import platform
from pathlib import Path
import subprocess
import webbrowser
import requests
import socket

project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from core_server import BarcodeGunServer
from threading import Thread
import time

# 检查macOS平台
if platform.system() != 'Darwin':
    print("错误：此客户端仅支持macOS平台")
    sys.exit(1)

import rumps

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('client.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class ServerManager:
    """服务器管理器"""

    def __init__(self):
        self.server = None
        self.running = False

    def start(self):
        """启动服务器"""
        if self.running:
            return False, "服务器已在运行"

        try:
            self.server = BarcodeGunServer()
            self.running = True

            # 在后台线程启动服务器
            self.thread = Thread(target=self._run_server, daemon=True)
            self.thread.start()

            # 等待服务器启动
            time.sleep(2)
            if self.running:
                info = self.server.get_server_info()
                return True, f"服务器启动成功 - http://{info['ip']}:{info['port']}"
            else:
                return False, "服务器启动失败"

        except Exception as e:
            logger.error(f"启动服务器失败: {e}")
            return False, f"启动失败: {e}"

    def _run_server(self):
        """在后台运行服务器"""
        try:
            self.server.start()
        except Exception as e:
            logger.error(f"服务器运行出错: {e}")
            self.running = False

    def stop(self):
        """停止服务器"""
        if not self.running:
            return False, "服务器未在运行"

        try:
            self.running = False
            if self.server:
                self.server.stop()
            return True, "服务器已停止"
        except Exception as e:
            logger.error(f"停止服务器失败: {e}")
            return False, f"停止失败: {e}"

    def get_status(self):
        """获取服务器状态"""
        if not self.running or not self.server:
            return {
                'running': False,
                'ip': '未知',
                'port': 5000,
                'mobile_clients': 0,
                'pc_clients': 0,
                'scan_count': 0
            }
        return self.server.get_server_info()

    def is_running(self):
        """检查服务器是否在运行"""
        return self.running


class PCClient:
    """PC客户端类"""

    def __init__(self):
        self.sio = None
        self.is_connected = False

        # PyAutoGUI配置
        pyautogui.PAUSE = 0
        pyautogui.FAILSAFE = True

    def connect(self, server_url):
        """连接到服务器"""
        if self.is_connected:
            return False, "已经连接"

        try:
            self.sio = socketio.Client(
                reconnection=True,
                reconnection_attempts=5,
                reconnection_delay=1
            )

            # 注册事件
            self.sio.on('connect', self.on_connect)
            self.sio.on('disconnect', self.on_disconnect)
            self.sio.on('scan_result', self.on_scan_result)
            self.sio.on('pong', self.on_pong)

            self.server_url = server_url

            # 异步连接
            asyncio.create_task(self._connect())

            return True, "正在连接..."

        except Exception as e:
            logger.error(f"连接服务器失败: {e}")
            return False, f"连接失败: {e}"

    async def _connect(self):
        """异步连接"""
        try:
            await self.sio.connect(self.server_url)
        except Exception as e:
            logger.error(f"连接失败: {e}")

    def on_connect(self):
        """连接成功"""
        logger.info("PC客户端已连接到服务器")
        self.is_connected = True

        # 发送客户端信息
        self.sio.emit('client_info', {
            'type': 'pc_client',
            'platform': 'macOS',
            'version': '2.0.0'
        })

    def on_disconnect(self):
        """断开连接"""
        logger.warning("与服务器断开连接")
        self.is_connected = False

    async def on_scan_result(self, data):
        """接收扫码结果"""
        barcode = data.get('barcode', '')
        if not barcode:
            logger.warning("接收到空的条码数据")
            return

        logger.info(f"收到条码: {barcode}")

        try:
            # 模拟键盘输入
            pyautogui.typewrite(barcode)
            pyautogui.press('enter')

            logger.info(f"条码已输入: {barcode}")

        except Exception as e:
            logger.error(f"模拟键盘输入失败: {e}")

    def on_pong(self, data):
        """心跳响应"""
        logger.debug("收到心跳响应")

    def disconnect(self):
        """断开连接"""
        if self.sio:
            asyncio.create_task(self.sio.disconnect())
            self.is_connected = False

    def is_connected(self):
        """检查是否已连接"""
        return self.is_connected


class BarcodeGunApp(rumps.App):
    """macOS菜单栏应用主类"""

    def __init__(self):
        super(BarcodeGunApp, self).__init__(
            name="H5 扫码枪",
            title="📱",
            quit_button=None  # 自定义退出按钮
        )

        # 初始化组件
        self.server_manager = ServerManager()
        self.pc_client = PCClient()

        # 状态
        self.server_running = False
        self.client_connected = False
        self.last_barcode = ""
        self.scan_count = 0

        # 构建菜单
        self.build_menu()

        # 定期更新状态
        self.update_timer = rumps.Timer(self.update_status, 5)  # 每5秒更新一次
        self.update_timer.start()

    def build_menu(self):
        """构建菜单"""
        self.menu = [
            rumps.MenuItem("服务器", callback=None, key=''),
            None,
            rumps.MenuItem("启动服务器", callback=self.start_server),
            rumps.MenuItem("停止服务器", callback=self.stop_server, enabled=False),
            None,
            rumps.MenuItem("客户端", callback=None, key=''),
            None,
            rumps.MenuItem("连接客户端", callback=self.connect_client),
            rumps.MenuItem("断开客户端", callback=self.disconnect_client, enabled=False),
            None,
            rumps.MenuItem("📱 打开管理界面", callback=self.open_admin),
            rumps.MenuItem("📱 在浏览器打开", callback=self.open_mobile),
            rumps.MenuItem("📋 复制访问地址", callback=self.copy_address),
            None,
            rumps.MenuItem("📊 状态信息", callback=self.show_status),
            None,
            rumps.MenuItem("关于", callback=self.show_about),
            None,
            rumps.MenuItem("退出", callback=self.quit)
        ]

    def start_server(self, sender):
        """启动服务器"""
        success, message = self.server_manager.start()

        if success:
            self.server_running = True
            sender.set_callback(None)  # 禁用启动按钮
            self.menu[2].set_callback(None)  # 启动服务器
            self.menu[3].set_callback(self.stop_server)  # 启用停止按钮
            self.menu[3].title = "停止服务器"

            # 自动连接客户端
            info = self.server_manager.get_status()
            server_url = f"http://localhost:{info['port']}"
            self.connect_client(None, server_url)

            rumps.notification(
                title="服务器已启动",
                subtitle="",
                message=message,
                sound=False
            )
        else:
            rumps.alert(title="启动失败", message=message)

    def stop_server(self, sender):
        """停止服务器"""
        # 先断开客户端
        if self.client_connected:
            self.disconnect_client(self.menu[8])

        success, message = self.server_manager.stop()

        if success:
            self.server_running = False
            sender.set_callback(None)  # 禁用停止按钮
            self.menu[2].set_callback(self.start_server)  # 启用启动按钮
            self.menu[2].title = "启动服务器"
            self.menu[3].set_callback(None)  # 停止服务器

            rumps.notification(
                title="服务器已停止",
                subtitle="",
                message=message,
                sound=False
            )
        else:
            rumps.alert(title="停止失败", message=message)

    def connect_client(self, sender, server_url=None):
        """连接PC客户端"""
        if not server_url:
            if not self.server_running:
                rumps.alert("请先启动服务器")
                return

            info = self.server_manager.get_status()
            server_url = f"http://localhost:{info['port']}"

        success, message = self.pc_client.connect(server_url)

        if success:
            self.client_connected = True

            if sender:
                sender.set_callback(None)  # 禁用连接按钮
                self.menu[8].title = "连接中..."

            self.menu[8].set_callback(None)  # 连接客户端
            self.menu[9].set_callback(self.disconnect_client)  # 启用断开按钮
            self.menu[9].title = "断开客户端"

            # 使用rumps定时器检查连接状态
            if not hasattr(self, 'connection_check_timer'):
                self.connection_check_timer = rumps.Timer(
                    lambda t: self.check_connection(),
                    1
                )
            self.connection_check_timer.start()

            if not "正在连接" in message:
                rumps.notification(
                    title="PC客户端已连接",
                    subtitle="",
                    message=message,
                    sound=False
                )

    def check_connection(self):
        """检查连接状态"""
        if self.pc_client.is_connected:
            self.menu[8].title = "已连接"
            self.menu[8].set_callback(None)
            self.connection_check_timer.stop()
        elif not self.pc_client.sio:
            self.menu[8].title = "连接客户端"
            self.menu[8].set_callback(self.connect_client)
            self.connection_check_timer.stop()

    def disconnect_client(self, sender):
        """断开客户端连接"""
        self.pc_client.disconnect()
        self.client_connected = False

        sender.set_callback(None)  # 禁用断开按钮
        self.menu[8].set_callback(self.connect_client)  # 启用连接按钮
        self.menu[8].title = "连接客户端"
        self.menu[9].set_callback(None)  # 断开客户端

        rumps.notification(
            title="PC客户端已断开",
            subtitle="",
            message="客户端与服务器断开连接",
            sound=False
        )

    def open_admin(self, sender):
        """在浏览器打开管理界面"""
        if self.server_running:
            info = self.server_manager.get_status()
            admin_url = f"http://localhost:{info['port']}/admin"
            webbrowser.open(admin_url)
        else:
            rumps.alert("请先启动服务器")

    def open_mobile(self, sender):
        """在浏览器打开手机端页面"""
        if self.server_running:
            info = self.server_manager.get_status()
            mobile_url = f"http://{info['ip']}:{info['port']}"
            webbrowser.open(mobile_url)
        else:
            rumps.alert("请先启动服务器")

    def copy_address(self, sender):
        """复制访问地址"""
        if self.server_running:
            info = self.server_manager.get_status()
            mobile_url = f"http://{info['ip']}:{info['port']}"

            try:
                process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
                process.communicate(mobile_url.encode('utf-8'))
                rumps.notification(
                    title="已复制",
                    subtitle="",
                    message="访问地址已复制到剪贴板",
                    sound=False
                )
            except Exception as e:
                logger.error(f"复制失败: {e}")
                rumps.alert("复制失败，请手动复制")
        else:
            rumps.alert("请先启动服务器")

    def show_status(self, sender):
        """显示状态信息"""
        if self.server_running:
            info = self.server_manager.get_status()
            message = f"""
服务器状态: {'运行中' if info['running'] else '已停止'}
服务器地址: http://{info['ip']}:{info['port']}
手机端连接: {info['mobile_clients']} 台
PC客户端连接: {info['pc_clients']} 台
总扫码次数: {info['scan_count']} 次
运行时间: {self.get_uptime()}

最近扫码: {self.last_barcode if self.last_barcode else '无'}
"""
            rumps.alert(title="系统状态", message=message)
        else:
            rumps.alert("服务器未运行")

    def get_uptime(self):
        """获取运行时间"""
        if not self.server_running or not self.server_manager.server:
            return "0分钟"

        start_time = self.server_manager.server.start_time
        uptime = datetime.now() - start_time
        minutes = uptime.total_seconds() // 60
        hours = minutes // 60
        days = hours // 24

        if days > 0:
            return f"{int(days)}天 {int(hours % 24)}小时"
        elif hours > 0:
            return f"{int(hours)}小时 {int(minutes % 60)}分"
        else:
            return f"{int(minutes)}分钟"

    def show_about(self, sender):
        """显示关于信息"""
        rumps.alert(
            title="关于 H5 扫码枪",
            message="版本: 2.0.0\n开发: H5 Barcode Gun\n描述: 将手机变成扫码枪\n支持: WebSocket实时传输"
        )

    def update_status(self, timer):
        """定时更新状态"""
        if self.server_running and self.server_manager.server:
            info = self.server_manager.get_status()
            self.scan_count = info['scan_count']

            # 更新状态图标
            if self.client_connected:
                self.title = "✅"
            elif self.server_running:
                self.title = "🟢"
            else:
                self.title = "📱"

    def quit(self, sender):
        """退出应用"""
        # 断开客户端
        if self.client_connected:
            self.pc_client.disconnect()

        # 停止服务器
        if self.server_running:
            self.server_manager.stop()

        rumps.quit_application()

    def on_scan_result(self, data):
        """处理扫码结果"""
        barcode = data.get('barcode', '')
        if barcode:
            self.last_barcode = barcode
            self.scan_count += 1

            # 显示通知
            rumps.notification(
                title="扫码成功",
                subtitle=barcode,
                message=f"已发送到 {data.get('sent_to_pc', 0)} 台PC",
                sound=False
            )


def main():
    """主函数"""
    app = BarcodeGunApp()
    app.run()


if __name__ == '__main__':
    main()
