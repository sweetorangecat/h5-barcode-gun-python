// H5 扫码枪 - 终极整合版
// 结合自定义UI + Html5QrcodeScanner + 本地库的所有优点

class BarcodeScanner {
    constructor() {
        this.html5QrcodeScanner = null;
        this.socket = null;
        this.isConnected = false;
        this.pcConnected = false;
        this.isScanning = false;

        // DOM元素（简洁版，只保留必要的状态显示）
        this.elements = {
            connectionStatus: document.getElementById('connectionStatus'),
            connectionText: document.getElementById('connectionText'),
            pcStatus: document.getElementById('pcStatus')
        };

        this.init();
    }

    init() {
        this.initSocket();
        this.initScanner();
    }

    // 初始化 Socket.IO 连接
    initSocket() {
        // 使用参考项目的方式 - 简洁配置
        this.socket = io({
            transports: ['websocket', 'polling']
        });

        this.socket.on('connect', () => {
            console.log('已连接到服务器');
            this.isConnected = true;
            this.updateConnectionStatus(true);

            this.socket.emit('client_info', {
                type: 'mobile'
            });
            this.socket.emit('request_pc_status');
        });

        this.socket.on('disconnect', () => {
            console.log('与服务器断开连接');
            this.isConnected = false;
            this.updateConnectionStatus(false);
            this.updatePCStatus(false);
        });

        this.socket.on('pc_status', (data) => {
            this.pcConnected = data.connected;
            this.updatePCStatus(data.connected, data.count || 0);
        });

        this.socket.on('scan_success', (data) => {
            console.log('条码发送成功:', data);
        });

        // 简单的定时心跳，无需复杂配置
        setInterval(() => {
            if (this.isConnected) {
                this.socket.emit('ping');
            }
        }, 30000);
    }

    // 初始化扫描器 - 完全参考参考项目的方式
    initScanner() {
        try {
            // 自适应扫描框函数（参考项目）
            const qrboxFunction = (viewfinderWidth, viewfinderHeight) => {
                const minEdgeSizeThreshold = 250;
                const edgeSizePercentage = 0.75;
                const minEdgeSize = Math.min(viewfinderWidth, viewfinderHeight);
                let qrboxEdgeSize = Math.floor(minEdgeSize * edgeSizePercentage);

                if (qrboxEdgeSize < minEdgeSizeThreshold) {
                    if (minEdgeSize < minEdgeSizeThreshold) {
                        return {width: minEdgeSize, height: minEdgeSize};
                    } else {
                        return {
                            width: minEdgeSizeThreshold,
                            height: minEdgeSizeThreshold
                        };
                    }
                }
                return {width: qrboxEdgeSize, height: qrboxEdgeSize};
            };

            // 配置 - 结合参考项目的最佳实践
            const config = {
                fps: 10,
                qrbox: qrboxFunction,  // 自适应扫描框
                formatsToSupport: [
                    Html5QrcodeSupportedFormats.QR_CODE,
                    Html5QrcodeSupportedFormats.CODE_128,
                    Html5QrcodeSupportedFormats.CODE_39,
                    Html5QrcodeSupportedFormats.EAN_13,
                    Html5QrcodeSupportedFormats.EAN_8,
                    Html5QrcodeSupportedFormats.ITF,
                    Html5QrcodeSupportedFormats.UPC_A,
                    Html5QrcodeSupportedFormats.UPC_E
                ],
                // 参考项目的优秀特性
                rememberLastUsedCamera: true,      // 记住上次使用的摄像头
                showTorchButtonIfSupported: true,  // 显示手电筒按钮
                // 实验性特性
                experimentalFeatures: {
                    useBarCodeDetectorIfSupported: true  // 使用浏览器原生API加速
                },
                // 按照参考项目，不显示任何形式的选择器
                // 所有摄像头选择和权限请求都由Html5QrcodeScanner自动处理
                verbose: false  // 关闭详细日志以提升性能
            };

            // 使用参考项目的方式：直接渲染，不显示选择器
            this.html5QrcodeScanner = new Html5QrcodeScanner("reader", config);

            const self = this;
            let lastMessage = null;
            let codeId = 0;

            function onScanSuccess(decodedText, decodedResult) {
                if (lastMessage !== decodedText) {
                    lastMessage = decodedText;
                    console.log(`[${codeId}] 扫码成功:`, decodedText, decodedResult);

                    // 发送到服务器
                    self.socket.emit('barcode_scan', {
                        barcode: decodedText,
                        type: decodedResult?.result?.format?.formatName || 'unknown',
                        timestamp: Date.now()
                    });

                    codeId++;
                }
            }

            // 核心：参考项目直接渲染，没有摄像头选择步骤
            // Html5QrcodeScanner会自动处理权限和摄像头选择
            this.html5QrcodeScanner.render(onScanSuccess);

            console.log('✅ 扫描器已启动 - 使用Html5QrcodeScanner自动管理摄像头');

            // 标记为扫描中（虽然实际上由Html5QrcodeScanner管理）
            this.isScanning = true;

        } catch (error) {
            console.error('启动扫描器失败:', error);
            // Html5QrcodeScanner会在reader元素中显示错误信息
        }
    }

    updateConnectionStatus(connected) {
        const statusDot = this.elements.connectionStatus;
        const statusText = this.elements.connectionText;
        statusDot.className = 'status-dot ' + (connected ? 'connected' : 'disconnected');
        statusText.textContent = connected ? '已连接到服务器' : '未连接到服务器';
    }

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

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    new BarcodeScanner();
});
