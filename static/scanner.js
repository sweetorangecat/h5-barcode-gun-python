// H5 扫码枪 - 手机端逻辑

class BarcodeScanner {
    constructor() {
        this.html5Qrcode = null;
        this.socket = null;
        this.isConnected = false;
        this.isScanning = false;
        this.pcConnected = false;

        // DOM元素
        this.elements = {
            connectionStatus: document.getElementById('connectionStatus'),
            connectionText: document.getElementById('connectionText'),
            pcStatus: document.getElementById('pcStatus'),
            startButton: document.getElementById('startButton'),
            stopButton: document.getElementById('stopButton'),
            resultPanel: document.getElementById('resultPanel'),
            resultContent: document.getElementById('resultContent'),
            notification: document.getElementById('notification'),
            reader: document.getElementById('reader'),
            scannerInfo: document.getElementById('scannerInfo')
        };

        // 配置
        this.config = {
            qrbox: {
                width: 250,
                height: 250
            },
            fps: 10,
            aspectRatio: 1.0,
            formats: [
                Html5QrcodeSupportedFormats.QR_CODE,
                Html5QrcodeSupportedFormats.CODE_128,
                Html5QrcodeSupportedFormats.CODE_39,
                Html5QrcodeSupportedFormats.EAN_13,
                Html5QrcodeSupportedFormats.EAN_8,
                Html5QrcodeSupportedFormats.ITF,
                Html5QrcodeSupportedFormats.UPC_A,
                Html5QrcodeSupportedFormats.UPC_E
            ]
        };

        this.init();
    }

    init() {
        this.initSocket();
        this.initScanner();
        this.bindEvents();
        this.checkEnvironment();
    }

    // 初始化 Socket.IO 连接
    initSocket() {
        // 连接到服务器
        this.socket = io({
            transports: ['websocket', 'polling'],
            reconnection: true,
            reconnectionAttempts: 5,
            reconnectionDelay: 1000,
            timeout: 20000
        });

        // 连接事件
        this.socket.on('connect', () => {
            console.log('已连接到服务器');
            this.isConnected = true;
            this.updateConnectionStatus(true);
            this.showNotification('已连接到服务器', 'success');

            // 发送客户端信息
            this.socket.emit('client_info', {
                type: 'mobile',
                timestamp: Date.now()
            });

            // 请求PC客户端状态
            this.socket.emit('request_pc_status');
        });

        this.socket.on('disconnect', () => {
            console.log('与服务器断开连接');
            this.isConnected = false;
            this.updateConnectionStatus(false);
            this.showNotification('与服务器断开连接', 'warning');
            this.updatePCStatus(false);
        });

        this.socket.on('connect_error', (error) => {
            console.error('连接错误:', error);
            this.showNotification('连接服务器失败', 'error');
        });

        // PC客户端状态更新
        this.socket.on('pc_status', (data) => {
            this.pcConnected = data.connected;
            this.updatePCStatus(data.connected, data.count || 0);
        });

        // 服务器响应
        this.socket.on('mobile_connected', (data) => {
            console.log('手机端已连接:', data);
        });

        this.socket.on('scan_success', (data) => {
            console.log('条码发送成功:', data);
            this.showNotification(`已发送到 ${data.sent_to_pc} 台PC`, 'success');
        });

        this.socket.on('scan_error', (data) => {
            console.error('扫描错误:', data);
            this.showNotification(data.message || '发送失败', 'error');
        });

        // 心跳响应
        this.socket.on('pong', (data) => {
            console.log('收到心跳响应:', data);
        });

        // 定期发送心跳
        setInterval(() => {
            if (this.isConnected) {
                this.socket.emit('ping');
            }
        }, 30000);
    }

    // 初始化扫描器
    async initScanner() {
        try {
            // 获取摄像头权限
            const stream = await navigator.mediaDevices.getUserMedia({
                video: true,
                audio: false
            });

            // 停止预览流
            stream.getTracks().forEach(track => track.stop());

            // 初始化 Html5Qrcode
            this.html5Qrcode = new Html5Qrcode(
                this.elements.reader.id,
                {
                    formatsToSupport: this.config.formats,
                    verbose: false
                }
            );

            console.log('扫描器初始化成功');
            this.elements.scannerInfo.innerHTML = '<p>摄像头已就绪</p>';
            this.elements.startButton.disabled = false;

        } catch (error) {
            console.error('扫描器初始化失败:', error);
            this.elements.scannerInfo.innerHTML = `
                <p style="color: #f44336;">摄像头初始化失败</p>
                <p style="font-size: 12px; margin-top: 10px;">
                    请检查浏览器权限设置,确保允许访问摄像头。
                </p>
            `;
        }
    }

    // 绑定事件
    bindEvents() {
        // 开始扫描按钮
        this.elements.startButton.addEventListener('click', () => {
            this.startScanning();
        });

        // 停止扫描按钮
        this.elements.stopButton.addEventListener('click', () => {
            this.stopScanning();
        });

        // 监听窗口大小变化
        window.addEventListener('resize', () => {
            if (this.isScanning) {
                this.updateScannerSize();
            }
        });

        // 监听页面隐藏/显示
        document.addEventListener('visibilitychange', () => {
            if (document.hidden && this.isScanning) {
                console.log('页面隐藏,暂停扫描');
                this.stopScanning();
            }
        });
    }

    // 检查环境
    checkEnvironment() {
        // HTTPS 检查
        if (location.protocol !== 'https:' && location.hostname !== 'localhost') {
            console.warn('未使用HTTPS,某些功能可能受限');
        }

        // 浏览器支持检查
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            this.showNotification('当前浏览器不支持摄像头功能', 'error');
        }
    }

    // 更新连接状态显示
    updateConnectionStatus(connected) {
        const statusDot = this.elements.connectionStatus;
        const statusText = this.elements.connectionText;

        statusDot.className = 'status-dot ' + (connected ? 'connected' : 'disconnected');
        statusText.textContent = connected ? '已连接到服务器' : '未连接到服务器';
    }

    // 更新PC客户端状态
    updatePCStatus(connected, count = 0) {
        const pcStatus = this.elements.pcStatus;

        if (connected) {
            pcStatus.textContent = `PC客户端: 已连接 (${count}台)`;
            pcStatus.style.color = '#4CAF50';
        } else {
            pcStatus.textContent = 'PC客户端: 未连接';
            pcStatus.style.color = '#666';
        }

        this.pcConnected = connected;
    }

    // 开始扫描
    async startScanning() {
        if (!this.html5Qrcode) {
            this.showNotification('扫描器未初始化', 'error');
            return;
        }

        if (!this.isConnected) {
            this.showNotification('请先连接到服务器', 'warning');
            return;
        }

        if (!this.pcConnected) {
            this.showNotification('没有PC客户端连接', 'warning');
        }

        try {
            // 配置扫描器
            const config = {
                fps: this.config.fps,
                qrbox: this.config.qrbox,
                aspectRatio: this.config.aspectRatio,
                disableFlip: false,
                showTorchButtonIfSupported: true,
                showZoomSliderIfSupported: true
            };

            // 开始扫描
            await this.html5Qrcode.start(
                { facingMode: "environment" },  // 使用后置摄像头
                config,
                this.onScanSuccess.bind(this),
                this.onScanFailure.bind(this)
            );

            this.isScanning = true;
            this.elements.reader.classList.remove('hidden');
            this.elements.scannerInfo.style.display = 'none';
            this.elements.startButton.disabled = true;
            this.elements.stopButton.disabled = false;

            // 更新扫描框大小
            this.updateScannerSize();

            this.showNotification('开始扫描', 'success');
            console.log('扫描已启动');

        } catch (error) {
            console.error('启动扫描失败:', error);
            this.showNotification('启动扫描失败: ' + error.message, 'error');
        }
    }

    // 停止扫描
    async stopScanning() {
        if (!this.isScanning || !this.html5Qrcode) {
            return;
        }

        try {
            await this.html5Qrcode.stop();

            this.isScanning = false;
            this.elements.reader.classList.add('hidden');
            this.elements.scannerInfo.style.display = 'flex';
            this.elements.startButton.disabled = false;
            this.elements.stopButton.disabled = true;
            this.elements.scannerInfo.innerHTML = '<p>摄像头已就绪</p>';

            this.showNotification('扫描已停止', 'info');
            console.log('扫描已停止');

        } catch (error) {
            console.error('停止扫描失败:', error);
        }
    }

    // 扫描成功回调
    onScanSuccess(decodedText, decodedResult) {
        console.log('扫码成功:', decodedText);
        console.log('结果对象:', decodedResult);

        // 显示结果
        this.showScanResult(decodedText);

        // 发送到服务器
        this.sendBarcode(decodedText, decodedResult);

        // 成功提示音(可选)
        this.playBeep();

        // 持续扫描,不停止
        // 如果需要单次扫描,可以在这里调用 this.stopScanning()
    }

    // 扫描失败回调(可用于调试)
    onScanFailure(error) {
        // 扫描失败是正常的,因为一直在尝试扫描
        // console.debug('扫描失败:', error);
    }

    // 发送条码到服务器
    sendBarcode(barcode, result) {
        if (!this.isConnected) {
            this.showNotification('未连接到服务器', 'error');
            return;
        }

        const data = {
            barcode: barcode,
            type: result?.result?.format?.formatName || 'unknown',
            timestamp: Date.now()
        };

        this.socket.emit('barcode_scan', data);
        console.log('条码已发送到服务器:', data);
    }

    // 显示扫描结果
    showScanResult(result) {
        this.elements.resultPanel.classList.add('show');
        this.elements.resultContent.textContent = result;

        // 自动隐藏结果面板(可选)
        setTimeout(() => {
            this.elements.resultPanel.classList.remove('show');
        }, 5000);
    }

    // 显示通知
    showNotification(message, type = 'info', duration = 3000) {
        const notification = this.elements.notification;

        notification.textContent = message;
        notification.className = `notification ${type} show`;

        // 自动隐藏
        setTimeout(() => {
            notification.classList.remove('show');
        }, duration);
    }

    // 播放提示音
    playBeep() {
        try {
            const context = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = context.createOscillator();
            const gainNode = context.createGain();

            oscillator.connect(gainNode);
            gainNode.connect(context.destination);

            oscillator.frequency.value = 800;
            oscillator.type = 'sine';

            gainNode.gain.setValueAtTime(0.3, context.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, context.currentTime + 0.1);

            oscillator.start(context.currentTime);
            oscillator.stop(context.currentTime + 0.1);
        } catch (error) {
            console.warn('无法播放提示音:', error);
        }
    }

    // 更新扫描器大小
    updateScannerSize() {
        if (!this.html5Qrcode || !this.isScanning) {
            return;
        }

        const container = document.querySelector('.scanner-placeholder');
        const width = container.clientWidth - 40;
        const height = container.clientHeight - 40;
        const size = Math.min(width, height, 500);

        this.config.qrbox.width = size;
        this.config.qrbox.height = size;

        // 重新应用配置
        this.html5Qrcode.updateConfig({
            qrbox: this.config.qrbox
        });
    }
}

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    // 检查浏览器支持
    if (!window.io) {
        alert('Socket.IO 库加载失败,请检查网络连接');
        return;
    }

    if (!window.Html5Qrcode) {
        alert('二维码扫描库加载失败,请检查网络连接');
        return;
    }

    // 创建扫码器实例
    const scanner = new BarcodeScanner();

    // 全局错误处理
    window.addEventListener('error', (event) => {
        console.error('全局错误:', event.error);
    });

    // 页面卸载时清理
    window.addEventListener('beforeunload', () => {
        if (scanner.html5Qrcode && scanner.isScanning) {
            scanner.html5Qrcode.stop();
        }
        if (scanner.socket) {
            scanner.socket.disconnect();
        }
    });

    console.log('H5 扫码枪已初始化');
});
