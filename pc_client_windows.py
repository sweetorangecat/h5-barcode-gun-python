#!/usr/bin/env python3
"""
H5 Barcode Gun - Windows PC客户端
图形界面版本，Start/Stop管理服务器
"""

import sys
import os
import asyncio
import socketio
import pyautogui
import logging
from datetime import datetime
from pathlib import Path

# 检查Windows平台
if sys.platform != 'win32':
    print("错误：此客户端仅支持Windows平台")
    sys.exit(1)

# 导入PyQt5
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QMessageBox, QGroupBox,
    QStatusBar, QSystemTrayIcon, QMenu, QAction, QSplitter, QStyle
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, pyqtSlot
from PyQt5.QtGui import QIcon, QPixmap, QImage, QTextCursor

# 将项目目录加入Python路径
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from core_server import BarcodeGunServer
from threading import Thread
import requests
import socket

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


class ServerThread(QObject):
    """服务器线程，管理服务器生命周期"""

    # 定义信号
    server_started = pyqtSignal(str, int)
    server_stopped = pyqtSignal()
    status_update = pyqtSignal(dict)
    log_message = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self.server = None
        self.running = False
        self.thread = None

    @pyqtSlot()
    def start_server(self, host='0.0.0.0', port=5000):
        """启动服务器"""
        if self.running:
            self.log_message.emit("服务器已在运行", "warning")
            return

        try:
            self.log_message.emit("正在启动服务器...", "info")
            self.server = BarcodeGunServer(host=host, port=port)
            self.running = True

            # 启动定时器更新状态
            self.timer = QTimer()
            self.timer.timeout.connect(self.update_status)
            self.timer.start(2000)  # 每2秒更新一次

            # 在后台线程运行服务器
            self.thread = Thread(target=self._run_server, daemon=True)
            self.thread.start()

            # 触发信号
            self.server_started.emit(host, port)
            self.log_message.emit("服务器启动成功", "success")

        except Exception as e:
            logger.error(f"启动服务器失败: {e}")
            self.log_message.emit(f"启动服务器失败: {e}", "error")
            self.running = False

    def _run_server(self):
        """在后台线程运行服务器"""
        try:
            self.server.start()
        except Exception as e:
            logger.error(f"服务器运行出错: {e}")

    @pyqtSlot()
    def stop_server(self):
        """停止服务器"""
        if not self.running:
            self.log_message.emit("服务器未在运行", "warning")
            return

        try:
            self.log_message.emit("正在停止服务器...", "info")
            self.running = False

            if hasattr(self, 'timer'):
                self.timer.stop()

            if self.server:
                self.server.stop()

            self.server_stopped.emit()
            self.log_message.emit("服务器已停止", "success")

        except Exception as e:
            logger.error(f"停止服务器失败: {e}")

    @pyqtSlot()
    def update_status(self):
        """更新服务器状态"""
        if not self.server or not self.running:
            return

        try:
            info = self.server.get_server_info()
            self.status_update.emit(info)
        except Exception as e:
            logger.debug(f"更新状态失败: {e}")


class PCClientWorker(QObject):
    """PC客户端Worker，负责接收扫码数据"""

    qr_detected = pyqtSignal(str)
    connection_changed = pyqtSignal(bool)
    log_message = pyqtSignal(str, str)

    def __init__(self, server_ip='localhost', port=7788):
        super().__init__()
        self.server_ip = server_ip
        self.port = port
        self.is_connected = False

        # SocketIO客户端
        self.sio = None

        # PyAutoGUI配置
        pyautogui.PAUSE = 0
        pyautogui.FAILSAFE = True

    @pyqtSlot()
    def connect(self):
        """连接到服务器"""
        try:
            self.server_url = f"http://{self.server_ip}:{self.port}"
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

            self.log_message.emit(f"正在连接服务器: {self.server_url}", "info")
            self.sio.connect(self.server_url)

        except Exception as e:
            logger.error(f"连接服务器失败: {e}")
            self.log_message.emit(f"连接服务器失败: {e}", "error")

    def on_connect(self):
        """连接成功"""
        logger.info("PC客户端已连接到服务器")
        self.is_connected = True
        self.connection_changed.emit(True)

        # 发送客户端信息
        self.sio.emit('client_info', {
            'type': 'pc_client',
            'platform': 'Windows',
            'version': '2.0.0'
        })

        self.log_message.emit("PC客户端已连接", "success")

    def on_disconnect(self):
        """断开连接"""
        logger.warning("与服务器断开连接")
        self.is_connected = False
        self.connection_changed.emit(False)
        self.log_message.emit("与服务器断开连接", "warning")

    def on_scan_result(self, data):
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

            self.qr_detected.emit(barcode)
            self.log_message.emit(f"已输入条码: {barcode}", "success")

        except Exception as e:
            logger.error(f"模拟键盘输入失败: {e}")
            self.log_message.emit(f"输入失败: {e}", "error")

    def on_pong(self, data):
        """心跳响应"""
        logger.debug("收到心跳响应")

    @pyqtSlot()
    def disconnect(self):
        """断开连接"""
        if self.sio:
            self.sio.disconnect()


class PCClientWindow(QMainWindow):
    """主窗口类"""

    def __init__(self):
        super().__init__()

        self.setWindowTitle("H5 扫码枪 - Windows 客户端 v2.0")
        self.setMinimumSize(900, 700)

        # 创建主Widget
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)

        # 创建布局
        self.main_layout = QHBoxLayout(self.main_widget)

        # 初始化组件
        self.init_ui()
        self.init_server_thread()
        self.init_client_worker()
        self.init_tray_icon()
        self.barcode = None

        # 初始化状态
        self.server_running = False
        self.client_connected = False

        self.show()
        self.log("H5 扫码枪客户端已启动", "info")
        self.log("请点击\"启动服务器\"按钮开始\n", "info")

    def init_ui(self):
        """初始化UI"""

        # 左侧：控制面板
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # 服务器控制区域
        server_group = QGroupBox("服务器控制")
        server_layout = QVBoxLayout()

        # 启动/停止服务器按钮
        self.btn_start_server = QPushButton("▶ 启动服务器")
        self.btn_start_server.clicked.connect(self.on_start_server_clicked)

        self.btn_stop_server = QPushButton("⏹ 停止服务器")
        self.btn_stop_server.clicked.connect(self.on_stop_server_clicked)
        self.btn_stop_server.setEnabled(False)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.btn_start_server)
        button_layout.addWidget(self.btn_stop_server)
        server_layout.addLayout(button_layout)

        # 服务器状态
        self.lbl_server_status = QLabel("服务器状态: 未启动")
        self.lbl_server_status.setStyleSheet("font-weight: bold; color: #666;")
        server_layout.addWidget(self.lbl_server_status)

        # 服务器地址显示
        self.lbl_server_url = QLabel("服务器地址: -")
        server_layout.addWidget(self.lbl_server_url)

        server_group.setLayout(server_layout)
        left_layout.addWidget(server_group)

        # PC客户端控制区域
        client_group = QGroupBox("PC 客户端")
        client_layout = QVBoxLayout()

        # 连接/断开按钮
        self.btn_connect = QPushButton("🔗 连接服务器")
        self.btn_connect.clicked.connect(self.on_connect_clicked)

        self.btn_disconnect = QPushButton("⏏ 断开连接")
        self.btn_disconnect.clicked.connect(self.on_disconnect_clicked)
        self.btn_disconnect.setEnabled(False)

        client_button_layout = QHBoxLayout()
        client_button_layout.addWidget(self.btn_connect)
        client_button_layout.addWidget(self.btn_disconnect)
        client_layout.addLayout(client_button_layout)

        # 客户端状态
        self.lbl_client_status = QLabel("客户端状态: 未连接")
        self.lbl_client_status.setStyleSheet("font-weight: bold; color: #666;")
        client_layout.addWidget(self.lbl_client_status)

        client_group.setLayout(client_layout)
        left_layout.addWidget(client_group)

        # 最近扫码显示
        scan_group = QGroupBox("最近扫码")
        scan_layout = QVBoxLayout()

        self.lbl_last_barcode = QLabel("等待扫描...")
        self.lbl_last_barcode.setStyleSheet(
            "font-family: 'Courier New'; font-size: 14px; padding: 10px;"
            "background: #f0f0f0; border: 1px solid #ccc; border-radius: 5px;"
        )
        self.lbl_last_barcode.setWordWrap(True)
        scan_layout.addWidget(self.lbl_last_barcode)

        scan_group.setLayout(scan_layout)
        left_layout.addWidget(scan_group)

        # 添加拉伸区域
        left_layout.addStretch()

        # 右侧：日志面板
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        log_group = QGroupBox("系统日志")
        log_layout = QVBoxLayout()

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        # self.log_text.setMaximumBlockCount(1000)  # 注释掉以兼容旧版本
        log_layout.addWidget(self.log_text)

        log_group.setLayout(log_layout)
        right_layout.addWidget(log_group)

        # 添加状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")

        # 将面板添加到主布局
        self.main_layout.addWidget(left_panel, 1)
        self.main_layout.addWidget(right_panel, 1)

    def init_server_thread(self):
        """初始化服务器线程"""
        self.server_thread = ServerThread()

        # 连接信号
        self.server_thread.server_started.connect(self.on_server_started)
        self.server_thread.server_stopped.connect(self.on_server_stopped)
        self.server_thread.status_update.connect(self.on_status_update)
        self.server_thread.log_message.connect(self.log)

    def init_client_worker(self):
        """初始化客户端"""
        self.client_worker = PCClientWorker()

        # 连接信号
        self.client_worker.connection_changed.connect(self.on_client_connection_changed)
        self.client_worker.qr_detected.connect(self.on_qr_detected)
        self.client_worker.log_message.connect(self.log)

    def init_tray_icon(self):
        """初始化系统托盘图标"""
        self.tray_icon = QSystemTrayIcon(self)

        # 创建托盘菜单
        tray_menu = QMenu()

        # 创建菜单动作
        self.show_action = QAction("显示(&S)", self)
        self.show_action.triggered.connect(self.show_normal)

        self.hide_action = QAction("隐藏(&H)", self)
        self.hide_action.triggered.connect(self.hide)

        self.start_server_action = QAction("启动服务器", self)
        self.start_server_action.triggered.connect(self.on_start_server_clicked)

        self.stop_server_action = QAction("停止服务器", self)
        self.stop_server_action.triggered.connect(self.on_stop_server_clicked)

        self.connect_client_action = QAction("连接客户端", self)
        self.connect_client_action.triggered.connect(self.on_connect_clicked)

        self.disconnect_client_action = QAction("断开客户端", self)
        self.disconnect_client_action.triggered.connect(self.on_disconnect_clicked)

        self.quit_action = QAction("退出(&Q)", self)
        self.quit_action.triggered.connect(QApplication.quit)

        # 添加到菜单
        tray_menu.addAction(self.show_action)
        tray_menu.addAction(self.hide_action)
        tray_menu.addSeparator()
        tray_menu.addAction(self.start_server_action)
        tray_menu.addAction(self.stop_server_action)
        tray_menu.addSeparator()
        tray_menu.addAction(self.connect_client_action)
        tray_menu.addAction(self.disconnect_client_action)
        tray_menu.addSeparator()
        tray_menu.addAction(self.quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        self.tray_icon.setToolTip("H5 扫码枪")
        self.tray_icon.show()

        # 点击托盘图标显示窗口
        self.tray_icon.activated.connect(self.on_tray_icon_activated)

    def log(self, message, level='info'):
        """添加日志"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        level_colors = {
            'info': '#000000',
            'warning': '#FF9800',
            'error': '#F44336',
            'success': '#4CAF50'
        }

        color = level_colors.get(level, '#000000')
        self.log_text.append(
            f"<span style='color: {color}; font-weight: bold;'>[{timestamp}]</span> "
            f"<span style='color: {color};'>{message}</span>"
        )

        # 自动滚动到底部
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.log_text.setTextCursor(cursor)

    def on_start_server_clicked(self):
        """点击启动服务器按钮"""
        self.btn_start_server.setEnabled(False)
        self.btn_stop_server.setEnabled(True)
        self.start_server_action.setEnabled(False)
        self.stop_server_action.setEnabled(True)

        # 启动服务器
        self.server_thread.start_server(port=5000)

    def on_stop_server_clicked(self):
        """点击停止服务器按钮"""
        self.server_thread.stop_server()

    @pyqtSlot(str, int)
    def on_server_started(self, host, port):
        """服务器已启动"""
        self.server_running = True
        self.lbl_server_status.setText("服务器状态: <span style='color: green;'>运行中</span>")
        self.lbl_server_url.setText(f"服务器地址: http://localhost:{port}")
        self.status_bar.showMessage("服务器运行中")
        self.log(f"服务器启动成功 - 地址: http://localhost:{port}", 'success')

        # 自动连接客户端
        self.client_worker.server_ip = 'localhost'
        self.client_worker.port = port
        self.on_connect_clicked()

    @pyqtSlot()
    def on_server_stopped(self):
        """服务器已停止"""
        self.server_running = False
        self.btn_start_server.setEnabled(True)
        self.btn_stop_server.setEnabled(False)
        self.start_server_action.setEnabled(True)
        self.stop_server_action.setEnabled(False)
        self.lbl_server_status.setText("服务器状态: <span style='color: red;'>已停止</span>")
        self.lbl_server_url.setText("服务器地址: -")
        self.status_bar.showMessage("服务器已停止")
        self.log("服务器已停止", 'warning')

        # 断开客户端连接
        self.on_disconnect_clicked()

    @pyqtSlot(dict)
    def on_status_update(self, info):
        """接收状态更新"""
        if info.get('running'):
            local_ip = info.get('ip', 'localhost')
            self.lbl_server_url.setText(f"服务器地址: http://{local_ip}:{info['port']}")

    def on_connect_clicked(self):
        """连接客户端"""
        if not self.server_running:
            self.log("请先启动服务器", 'warning')
            return

        self.btn_connect.setEnabled(False)
        self.btn_disconnect.setEnabled(True)
        self.connect_client_action.setEnabled(False)
        self.disconnect_client_action.setEnabled(True)

        # 连接客户端
        self.client_worker.connect()

    def on_disconnect_clicked(self):
        """断开客户端连接"""
        self.btn_connect.setEnabled(True)
        self.btn_disconnect.setEnabled(False)
        self.connect_client_action.setEnabled(True)
        self.disconnect_client_action.setEnabled(False)

        self.client_worker.disconnect()
        self.on_client_connection_changed(False)

    @pyqtSlot(bool)
    def on_client_connection_changed(self, connected):
        """客户端连接状态改变"""
        self.client_connected = connected

        if connected:
            self.lbl_client_status.setText("客户端状态: <span style='color: green;'>已连接</span>")
            self.status_bar.showMessage("PC客户端已连接")
            self.log("PC客户端已连接到服务器", 'success')
        else:
            self.lbl_client_status.setText("客户端状态: <span style='color: red;'>未连接</span>")
            self.status_bar.showMessage("PC客户端未连接")
            self.log("PC客户端已断开连接", 'warning')

    @pyqtSlot(str)
    def on_qr_detected(self, barcode):
        """接收到二维码"""
        if barcode is not None:
            self.lbl_last_barcode.setText(barcode)

    def on_tray_icon_activated(self, reason):
        """托盘图标点击"""
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_normal()

    def show_normal(self):
        """显示窗口"""
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        """关闭事件"""
        reply = QMessageBox.question(
            self, '确认退出',
            "确定要退出H5扫码枪客户端吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # 停止服务器
            if self.server_thread.running:
                self.server_thread.stop_server()

            # 断开客户端
            self.client_worker.disconnect()

            event.accept()
        else:
            event.ignore()
            self.hide()


def main():
    """主函数"""
    app = QApplication(sys.argv)

    # 设置应用程序样式
    app.setStyle('Fusion')

    # 设置图标
    app.setWindowIcon(QIcon(str(project_dir / 'static' / 'icon.ico')))

    # 创建主窗口
    window = PCClientWindow()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
