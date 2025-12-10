// H5 扫码枪 - 参考项目风格 + 自定义UI
// 使用 Html5Qrcode（非Html5QrcodeScanner）+ 本地html5-qrcode.min.js

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

        // 配置（参考项目风格）
        this.config = {
            fps: 10,
            qrbox: this.calculateQrBox(),  // 自适应扫描框
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
    }

    // 自适应扫描框大小（参考项目风格）
    calculateQrBox() {
        const containerWidth = window.innerWidth - 40;
        const containerHeight = window.innerHeight * 0.6;
        const minSize = Math.min(containerWidth, containerHeight, 400);
        return { width: minSize * 0.7, height: minSize * 0.7 };
    }

    // 初始化 Socket.IO 连接
    initSocket() {
        this.socket = io({
            transports: ['websocket', 'polling']
        });

        this.socket.on('connect', () => {
            console.log('已连接到服务器');
            this.isConnected = true;
            this.updateConnectionStatus(true);

            this.socket.emit('client_info', { type: 'mobile' });
            this.socket.emit('request_pc_status');
        });

        this.socket.on('disconnect', () => {
            console.log('与服务器断开连接');
            this.isConnected = false;
            this.updateConnectionStatus(false);
            this.updatePCStatus(false);

            // 停止扫描
            if (this.isScanning) {
                this.stopScanning();
            }
        });

        this.socket.on('pc_status', (data) => {
            this.pcConnected = data.connected;
            this.updatePCStatus(data.connected, data.count || 0);
        });

        this.socket.on('scan_success', (data) => {
            console.log('条码发送成功:', data);
            this.showNotification(`已发送到 ${data.sent_to_pc} 台PC`, 'success');
        });

        setInterval(() => {
            if (this.isConnected) {
                this.socket.emit('ping');
            }
        }, 30000);
    }

    // 初始化扫描器
    async initScanner() {
        try {
            console.log('正在初始化摄像头...');

            // 检查环境
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                throw new Error('浏览器不支持摄像头API');
            }

            // 初始化 Html5Qrcode
            this.html5Qrcode = new Html5Qrcode(
                this.elements.reader.id,
                {
                    formatsToSupport: this.config.formats,
                    verbose: false
                }
            );

            console.log('扫描器初始化成功');
            this.elements.scannerInfo.innerHTML = '<p>点击"开始扫描"按钮启动摄像头</p>';
            this.elements.startButton.disabled = false;

        } catch (error) {
            console.error('扫描器初始化失败:', error);
            this.elements.scannerInfo.innerHTML = `
                <p style="color: #f44336;">摄像头初始化失败</p>
                <p style="font-size: 12px; margin-top: 10px;">
                    ${error.message}
                </p>
            `;
        }
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

        if (this.isScanning) {
            return;
        }

        try {
            // 请求摄像头权限
            const stream = await navigator.mediaDevices.getUserMedia({ video: true });
            stream.getTracks().forEach(track => track.stop());

            // 获取摄像头列表并让用户选择
            const devices = await navigator.mediaDevices.enumerateDevices();
            const cameras = devices.filter(device => device.kind === 'videoinput');

            if (cameras.length === 0) {
                throw new Error('未找到可用的摄像头');
            }

            // 如果有多个摄像头，询问用户选择
            let selectedCameraId = null;
            if (cameras.length > 1) {
                // 优先选择后置摄像头
                const backCamera = cameras.find(camera => {
                    const label = camera.label || '';
                    return label.toLowerCase().includes('back') ||
                           label.toLowerCase().includes('rear') ||
                           label.toLowerCase().includes('environment');
                });

                if (backCamera) {
                    selectedCameraId = backCamera.deviceId;
                    console.log('自动选择后置摄像头:', backCamera.label);
                } else {
                    // 让用户选择
                    selectedCameraId = await this.askUserToSelectCamera(cameras);
                }
            } else {
                selectedCameraId = cameras[0].deviceId;
            }

            if (!selectedCameraId) {
                return; // 用户取消选择
            }

            // 开始扫描
            await this.html5Qrcode.start(
                selectedCameraId,
                {
                    fps: this.config.fps,
                    qrbox: this.calculateQrBox(),
                    aspectRatio: 1.0,
                    disableFlip: false
                },
                this.onScanSuccess.bind(this),
                this.onScanFailure.bind(this)
            );

            this.isScanning = true;
            this.elements.reader.classList.remove('hidden');
            this.elements.scannerInfo.style.display = 'none';
            this.elements.startButton.disabled = true;
            this.elements.stopButton.disabled = false;

            this.showNotification('开始扫描', 'success');

        } catch (error) {
            console.error('启动扫描失败:', error);
            this.showNotification('启动失败: ' + error.message, 'error');
        }
    }

    // 让用户选择摄像头
    async askUserToSelectCamera(cameras) {
        return new Promise((resolve) => {
            const optionsHtml = cameras.map((camera, index) => {
                const label = camera.label || `摄像头 ${index + 1}`;
                const isBack = label.toLowerCase().includes('back') ||
                              label.toLowerCase().includes('rear') ||
                              label.toLowerCase().includes('environment');
                const type = isBack ? '后置' : '前置';
                return `<option value="${camera.deviceId}">${label} (${type})</option>`;
            }).join('');

            this.elements.scannerInfo.innerHTML = `
                <div style="text-align: center; padding: 20px;">
                    <p style="margin-bottom: 15px; font-weight: bold;">请选择要使用的摄像头:</p>
                    <select id="cameraSelect" style="width: 100%; padding: 10px; margin-bottom: 15px;">
                        ${optionsHtml}
                    </select>
                    <button id="confirmCameraBtn" class="btn btn-primary" style="width: 100%; padding: 10px;">确认</button>
                </div>
            `;
            this.elements.scannerInfo.style.display = 'flex';

            const select = document.getElementById('cameraSelect');
            const button = document.getElementById('confirmCameraBtn');

            button.onclick = () => {
                const selectedId = select.value;
                this.elements.scannerInfo.innerHTML = '<p>摄像头已就绪</p>';
                this.elements.scannerInfo.style.display = 'flex';
                resolve(selectedId);
            };
        });
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
            this.elements.scannerInfo.innerHTML = '<p>点击"开始扫描"按钮启动摄像头</p>';
            this.elements.startButton.disabled = false;
            this.elements.stopButton.disabled = true;

            this.showNotification('扫描已停止', 'info');
        } catch (error) {
            console.error('停止扫描失败:', error);
        }
    }

    // 扫描成功回调
    onScanSuccess(decodedText, decodedResult) {
        if (decodedText !== this.lastScanned) {
            this.lastScanned = decodedText;
            console.log('扫码成功:', decodedText);

            // 显示结果
            this.showScanResult(decodedText);

            // 发送到服务器
            this.sendBarcode(decodedText, decodedResult);

            // 成功提示音
            this.playBeep();
        }
    }

    // 扫描失败回调
    onScanFailure(error) {
        // 无需处理，这是正常的扫描过程
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

        // 5秒后自动隐藏
        setTimeout(() => {
            this.elements.resultPanel.classList.remove('show');
        }, 5000);
    }

    // 显示通知
    showNotification(message, type = 'info', duration = 3000) {
        const notification = this.elements.notification;
        notification.textContent = message;
        notification.className = `notification ${type} show`;

        setTimeout(() => {
            notification.classList.remove('show');
        }, duration);
    }

    // 播放提示音
    playBeep() {
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();

            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);

            oscillator.frequency.value = 800;
            oscillator.type = 'sine';

            gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.1);

            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.1);
        } catch (error) {
            console.warn('无法播放提示音:', error);
        }
    }

    // 更新连接状态
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
}

// 绑定事件
document.addEventListener('DOMContentLoaded', () => {
    const scanner = new BarcodeScanner();

    // 绑定按钮事件
    document.getElementById('startButton').addEventListener('click', () => {
        scanner.startScanning();
    });

    document.getElementById('stopButton').addEventListener('click', () => {
        scanner.stopScanning();
    });

    // 窗口大小变化时更新扫描框
    window.addEventListener('resize', () => {
        // TODO: 动态更新扫描框大小
    });

    console.log('H5 扫码枪已初始化');
});
