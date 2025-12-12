#!/usr/bin/env python3
"""
H5 Barcode Gun - Windows PC客户端
图形界面版本，Start/Stop管理服务器
"""

import sys
import logging
from datetime import datetime
from pathlib import Path
import ctypes

# 检查Windows平台
if sys.platform != 'win32':
    print("错误：此客户端仅支持Windows平台")
    sys.exit(1)

# 定义Windows常量
ERROR_ALREADY_EXISTS = 183

# 定义单实例检查函数
def check_single_instance():
    """使用Windows mutex检查单实例"""
    mutex_name = "Global\\H5BarcodeGunClient"

    # 创建mutex
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)

    # 检查错误码
    error = ctypes.windll.kernel32.GetLastError()

    if error == ERROR_ALREADY_EXISTS:
        # mutex已存在，说明有另一个实例在运行
        ctypes.windll.kernel32.CloseHandle(mutex)
        return False

    # 保存mutex句柄，避免被垃圾回收
    # 我们将它保存在全局变量中
    global app_mutex
    app_mutex = mutex
    return True

# 导入PyQt5
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QMessageBox, QGroupBox,
    QStatusBar, QSystemTrayIcon, QMenu, QAction, QStyle
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, pyqtSlot
from PyQt5.QtGui import QIcon, QPixmap, QTextCursor

# 导入二维码库
import qrcode

# 将项目目录加入Python路径
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from utils.dual_server import DualBarcodeGunServer

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
    server_started = pyqtSignal(str, int, str)  # host, port, protocol
    server_stopped = pyqtSignal()
    status_update = pyqtSignal(dict)
    log_message = pyqtSignal(str, str)
    barcode_received = pyqtSignal(str)  # 新增：收到条码信号

    def __init__(self):
        super().__init__()
        self.server = None
        self.running = False
        self.server_thread = None


    def _run_server(self):
        """在后台线程运行服务器"""
        try:
            self.server.start()
        except Exception as e:
            logger.error(f"服务器运行出错: {e}")
            self.log_message.emit(f"服务器运行出错: {e}", "error")
            self.running = False

    @pyqtSlot()
    def stop_server(self):
        """停止服务器（安全终止）"""
        if not self.running:
            self.log_message.emit("服务器未在运行", "warning")
            return

        try:
            self.log_message.emit("正在安全地停止服务器...", "info")
            self.running = False

            # 停止定时器
            if hasattr(self, 'timer') and self.timer:
                try:
                    logger.debug("停止定时器...")
                    self.timer.stop()
                except:
                    pass

            # 停止服务器（不立即终止，避免卡死）
            if self.server:
                logger.debug("调用服务器stop方法...")
                # 调用stop时等待，避免立即终止导致卡死
                self.server.stop(wait=True)

            self.server_stopped.emit()
            self.log_message.emit("服务器已安全停止", "success")

        except Exception as e:
            logger.error(f"停止服务器失败: {e}")
            self.log_message.emit(f"停止服务器失败: {e}", "error")

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

    def _run_https_server(self, ssl_context):
        """在后台线程运行HTTPS服务器"""
        try:
            self.server.start(ssl_context=ssl_context)
        except Exception as e:
            logger.error(f"HTTPS服务器运行出错: {e}")
            self.log_message.emit(f"服务器运行出错: {e}", "error")


class PCClientWindow(QMainWindow):
    """主窗口类"""

    def __init__(self):
        super().__init__()

        self.setWindowTitle("H5 扫码枪 - Windows 客户端 v1.0")
        icon_path = project_dir / 'static' / 'scan_icon.png'
        icon = QIcon(str(icon_path))
        self.setWindowIcon(icon)
        self.setMinimumSize(900, 700)

        # 创建主Widget
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)

        # 创建布局
        self.main_layout = QHBoxLayout(self.main_widget)

        # 初始化组件
        self.init_ui()
        self.init_server_thread()
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

        # 端口设置区域
        port_group = QGroupBox("端口设置")
        port_layout = QVBoxLayout()

        # HTTP端口
        http_port_layout = QHBoxLayout()
        http_port_layout.addWidget(QLabel("HTTP端口:"))
        from PyQt5.QtWidgets import QSpinBox
        self.http_port_spin = QSpinBox()
        self.http_port_spin.setRange(1000, 65535)
        self.http_port_spin.setValue(5100)
        http_port_layout.addWidget(self.http_port_spin)
        port_layout.addLayout(http_port_layout)

        # WebSocket端口
        ws_port_layout = QHBoxLayout()
        ws_port_layout.addWidget(QLabel("WS端口:"))
        self.ws_port_spin = QSpinBox()
        self.ws_port_spin.setRange(1000, 65535)
        self.ws_port_spin.setValue(9999)
        ws_port_layout.addWidget(self.ws_port_spin)
        port_layout.addLayout(ws_port_layout)

        port_group.setLayout(port_layout)
        left_layout.addWidget(port_group)

        # 服务器控制区域
        server_group = QGroupBox("服务器控制")
        server_layout = QVBoxLayout()

        # 启动/停止服务器按钮
        self.btn_start_server = QPushButton("▶ 启动双端口服务器")
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

        # HTTP地址显示
        self.lbl_http_url = QLabel("HTTP地址: -")
        server_layout.addWidget(self.lbl_http_url)

        # WebSocket地址显示
        self.lbl_ws_url = QLabel("WebSocket地址: -")
        server_layout.addWidget(self.lbl_ws_url)

        # H5连接数显示
        self.lbl_mobile_clients = QLabel("H5连接数: 0")
        server_layout.addWidget(self.lbl_mobile_clients)

        server_group.setLayout(server_layout)
        left_layout.addWidget(server_group)

        # 二维码显示区域
        qr_group = QGroupBox("手机端访问二维码")
        qr_layout = QVBoxLayout()

        # 二维码标签
        self.lbl_qr_code = QLabel()
        self.lbl_qr_code.setAlignment(Qt.AlignCenter)
        self.lbl_qr_code.setMinimumSize(200, 200)
        self.lbl_qr_code.setStyleSheet("border: 1px dashed #ccc; background-color: #f9f9f9;")
        self.lbl_qr_code.setText("启动服务器后\n显示二维码")
        qr_layout.addWidget(self.lbl_qr_code)

        # HTTP地址显示在二维码下方
        self.lbl_http_url_simple = QLabel("-")
        self.lbl_http_url_simple.setAlignment(Qt.AlignCenter)
        self.lbl_http_url_simple.setWordWrap(True)
        self.lbl_http_url_simple.setStyleSheet("font-family: 'Courier New'; font-size: 12px; color: #333; padding: 5px;")
        qr_layout.addWidget(self.lbl_http_url_simple)

        qr_group.setLayout(qr_layout)
        left_layout.addWidget(qr_group)

        # 添加拉伸区域
        left_layout.addStretch()

        # 右侧：日志面板
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        log_group = QGroupBox("系统日志")
        log_layout = QVBoxLayout()

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
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
        self.server_thread.barcode_received.connect(self.on_barcode_received)


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
        #


        self.quit_action = QAction("退出(&Q)", self)
        self.quit_action.triggered.connect(QApplication.quit)

        # 添加到菜单
        tray_menu.addAction(self.show_action)
        tray_menu.addAction(self.hide_action)
        tray_menu.addSeparator()
        tray_menu.addAction(self.start_server_action)
        tray_menu.addAction(self.stop_server_action)
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

        # 启动HTTPS服务器
        self.log("正在生成SSL证书（如果需要）...", "info")
        try:
            # 直接调用服务器启动
            if self.server_thread.running:
                self.log("服务器已在运行", "warning")
                return

            # 检查证书
            from utils.cert_utils import CertManager
            cert_manager = CertManager()
            self.log("检查证书文件...", "info")

            if not cert_manager.check_and_create_cert():
                raise Exception("SSL证书生成失败")

            self.log("证书检查通过", "success")

            ssl_context = cert_manager.get_ssl_context()
            if not ssl_context:
                raise Exception("无法创建SSL上下文")

            self.log("正在启动HTTPS服务器...", "info")
            # 创建双端口服务器实例
            http_port = self.http_port_spin.value()
            ws_port = self.ws_port_spin.value()
            self.server_thread.server = DualBarcodeGunServer(
                http_host='0.0.0.0',
                http_port=http_port,
                ws_port=ws_port,
                barcode_callback=self.on_barcode_received
            )
            self.server_thread.running = True

            # 启动定时器
            self.server_thread.timer = QTimer()
            self.server_thread.timer.timeout.connect(self.server_thread.update_status)
            self.server_thread.timer.start(2000)

            # 在后台线程运行服务器
            import threading
            self.server_thread.server_thread = threading.Thread(
                target=self.server_thread._run_server,
                daemon=False  # 非守护线程防止auto-close
            )
            self.server_thread.server_thread.start()

            # 触发信号
            self.on_server_started('0.0.0.0', http_port, 'https')
            self.log(f"HTTPS服务器启动成功 (HTTP端口: {http_port}, WebSocket端口: {ws_port})", "success")

        except Exception as e:
            self.log(f"启动服务器失败: {e}", "error")
            import traceback
            self.log(traceback.format_exc(), "error")
            # 恢复按钮状态
            self.btn_start_server.setEnabled(True)
            self.btn_stop_server.setEnabled(False)
            self.start_server_action.setEnabled(True)
            self.stop_server_action.setEnabled(False)

    def on_stop_server_clicked(self):
        """点击停止服务器按钮"""
        self.server_thread.stop_server()

    @pyqtSlot(str, int, str)
    def on_server_started(self, host, port, protocol):
        """服务器已启动"""

        self.server_running = True
        self.lbl_server_status.setText("服务器状态: <span style='color: green;'>运行中</span>")
        info = self.server_thread.server.get_server_info()
        local_ip = info.get('ip', 'localhost')
        http_port = info.get('http_port', 5100)
        ws_port = info.get('ws_port', 9999)

        # 构建HTTP地址
        http_url = f"https://{local_ip}:{http_port}"

        self.lbl_http_url.setText(f"手机H5地址: {http_url}")
        self.lbl_ws_url.setText(f"WebSocket地址: ws://{local_ip}:{ws_port}")
        self.lbl_mobile_clients.setText(f"H5连接数: {info.get('mobile_clients', 0)}")
        self.status_bar.showMessage("服务器运行中")
        self.log(f"服务器启动成功 - HTTPS: {local_ip}:{http_port}, WebSocket: {ws_port}", 'success')

        # 生成并显示二维码
        self.generate_qr_code(http_url)

        # # 自动连接客户端

    @pyqtSlot()
    def on_server_stopped(self):
        """服务器已停止"""
        self.server_running = False
        self.btn_start_server.setEnabled(True)
        self.btn_stop_server.setEnabled(False)
        self.start_server_action.setEnabled(True)
        self.stop_server_action.setEnabled(False)
        self.lbl_server_status.setText("服务器状态: <span style='color: red;'>已停止</span>")
        self.lbl_http_url.setText("HTTP地址: -")
        self.lbl_ws_url.setText("WS地址: -")
        self.lbl_mobile_clients.setText("H5连接数: 0")
        self.status_bar.showMessage("服务器已停止")
        self.log("服务器已停止", 'warning')

        # # 断开客户端连接

    @pyqtSlot(dict)
    def on_status_update(self, info):
        """接收状态更新"""
        if info.get('running'):
            local_ip = info.get('ip', 'localhost')
            http_port = info.get('http_port', 5100)
            ws_port = info.get('ws_port', 9999)
            self.lbl_http_url.setText(f"HTTP地址: https://{local_ip}:{http_port}")
            self.lbl_ws_url.setText(f"WebSocket地址: ws://{local_ip}:{ws_port}")
            self.lbl_mobile_clients.setText(f"H5连接数: {info.get('mobile_clients', 0)}")

    @pyqtSlot(str)
    def on_qr_detected(self, barcode):
        """接收到二维码"""
        if barcode is not None:
            self.lbl_last_barcode.setText(barcode)

    @pyqtSlot(str)
    def on_barcode_received(self, barcode):
        """从服务器接收到条码数据"""
        self.log(f"收到条码: {barcode}", "success")
        self.lbl_last_barcode.setText(barcode)

    def on_tray_icon_activated(self, reason):
        """托盘图标点击"""
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_normal()

    def generate_qr_code(self, url):
        """
        生成二维码并显示在标签上

        Args:
            url: 要生成二维码的URL
        """
        try:
            logger.info(f"生成二维码: {url}")

            # 创建QR code实例
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )

            # 添加数据
            qr.add_data(url)
            qr.make(fit=True)

            # 生成图像
            img = qr.make_image(fill_color="black", back_color="white")

            # 转换为QPixmap（处理不同版本的PIL）
            try:
                # 尝试使用PIL 8.0+的方式
                from PIL.ImageQt import ImageQt
                qt_image = ImageQt(img)
                pixmap = QPixmap.fromImage(qt_image)
            except ImportError:
                # 如果导入失败，使用替代方法：将图像保存到BytesIO，再加载为QPixmap
                from io import BytesIO
                buffer = BytesIO()
                img.save(buffer, format='PNG')
                buffer.seek(0)
                pixmap = QPixmap()
                pixmap.loadFromData(buffer.getvalue())

            # 调整大小以适应标签
            scaled_pixmap = pixmap.scaled(
                self.lbl_qr_code.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )

            # 显示二维码
            self.lbl_qr_code.setPixmap(scaled_pixmap)
            self.lbl_http_url_simple.setText(url)

            logger.info("二维码生成成功")

        except Exception as e:
            logger.error(f"生成二维码失败: {e}")
            self.lbl_qr_code.setText(f"生成失败\n{e}")
            self.lbl_http_url_simple.setText(url)

    def show_normal(self):
        """显示窗口"""
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        """关闭事件 - 用户确认后安全关闭"""
        reply = QMessageBox.question(
            self, '确认退出',
            "确定要退出H5扫码枪客户端吗？\n\n注意：这将停止所有服务！",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        # 明确处理每个返回值
        if reply == QMessageBox.Yes:
            # 停止服务器（安全方式，避免立即终止导致卡死）
            if self.server_thread.running:
                logger.info("用户确认退出应用程序，正在安全关闭...")
                self.server_thread.stop_server()
                event.accept()
                # 延迟退出，让界面有时间响应和日志输出
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(200, sys.exit(0))
            else:
                event.accept()
                # 延迟退出，让界面有时间响应和日志输出
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(200, sys.exit(0))

        elif reply == QMessageBox.No:
            logger.info("用户取消退出操作")
            event.ignore()
        else:
            logger.warning(f"QMessageBox返回了未预期的值: {reply}")
            event.ignore()  # 默认不关闭


def main():
    """主函数"""
    app = QApplication(sys.argv)

    app.setStyle('Fusion')

    app.setWindowIcon(QIcon(str(project_dir / 'static' / 'icon.ico')))

    # 检查是否已有实例在运行
    if not check_single_instance():
        QMessageBox.warning(None, "警告", "H5扫码枪客户端已在运行中！")
        sys.exit(0)

    window = PCClientWindow()

    sys.exit(app.exec_())


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        with open('client_error.log', 'w', encoding='utf-8') as f:
            import traceback
            f.write(traceback.format_exc())
        print(f"程序启动失败: {e}")
        print("详细错误信息已保存到 client_error.log")
        sys.exit(1)
