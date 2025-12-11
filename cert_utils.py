#!/usr/bin/env python3
"""
证书自动管理工具
自动创建、配置和使用SSL证书
"""

import os
import sys
from pathlib import Path
import subprocess
import logging

logger = logging.getLogger(__name__)


class CertManager:
    """证书管理器"""

    def __init__(self, app_dir=None):
        """
        初始化证书管理器
        :param app_dir: 应用程序目录（如果是打包后的文件）
        """
        if app_dir:
            self.cert_dir = Path(app_dir)
        else:
            # 开发环境
            self.cert_dir = Path(__file__).parent

        self.cert_file = self.cert_dir / "server.crt"
        self.key_file = self.cert_dir / "server.key"
        self.cert_generated = False

    def check_and_create_cert(self):
        """
        检查证书是否存在，如果不存在则自动创建
        :return: True 如果证书已准备好
        """
        # 检查证书文件
        if self.cert_file.exists() and self.key_file.exists():
            logger.info("证书文件已存在")
            return True

        logger.info("证书文件不存在，正在生成...")

        # 尝试生成证书
        try:
            # 方法1：使用 pyOpenSSL（如果可用）
            if self._try_generate_with_pyopenssl():
                self.cert_generated = True
                return True

            # 方法2：使用系统 openssl
            if self._try_generate_with_openssl():
                self.cert_generated = True
                return True

            logger.error("无法生成SSL证书")
            return False

        except Exception as e:
            logger.error(f"生成证书失败: {e}")
            return False

    def _try_generate_with_pyopenssl(self):
        """尝试使用 pyOpenSSL 生成证书"""
        try:
            from OpenSSL import crypto

            logger.info("使用 pyOpenSSL 生成证书...")

            # 生成私钥
            k = crypto.PKey()
            k.generate_key(crypto.TYPE_RSA, 2048)

            # 生成证书
            cert = crypto.X509()
            cert.get_subject().C = "CN"
            cert.get_subject().ST = "Local"
            cert.get_subject().L = "Local"
            cert.get_subject().O = "H5 Barcode Gun"
            cert.get_subject().OU = "Development"
            cert.get_subject().CN = "*"  # 支持所有域名

            cert.set_serial_number(1000)
            cert.gmtime_adj_notBefore(0)
            cert.gmtime_adj_notAfter(10*365*24*60*60)

            cert.set_issuer(cert.get_subject())
            cert.set_pubkey(k)
            cert.sign(k, 'sha256')

            # 写入文件
            with open(self.cert_file, "wb") as f:
                f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))

            with open(self.key_file, "wb") as f:
                f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, k))

            logger.info("✅ SSL证书生成成功")
            return True

        except ImportError:
            logger.info("pyOpenSSL 未安装，尝试使用系统 openssl")
            return False
        except Exception as e:
            logger.error(f"pyOpenSSL 生成证书失败: {e}")
            return False

    def _try_generate_with_openssl(self):
        """尝试使用系统 openssl 生成证书"""
        try:
            # 检查 openssl 是否可用
            result = subprocess.run(
                ["openssl", "version"],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                logger.warning("系统未安装 openssl")
                return False

            logger.info("使用系统 openssl 生成证书...")

            # 生成证书
            cmd = [
                "openssl", "req", "-x509", "-newkey", "rsa:2048",
                "-keyout", str(self.key_file),
                "-out", str(self.cert_file),
                "-days", "3650",
                "-nodes",
                "-subj", "/CN=*"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info("✅ SSL证书生成成功")
                return True
            else:
                logger.error(f"openssl 生成证书失败: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"系统 openssl 调用失败: {e}")
            return False

    def get_ssl_context(self):
        """
        获取SSL上下文（用于Flask）
        :return: SSLContext对象或None
        """
        if not self.check_and_create_cert():
            return None

        try:
            # 使用标准库ssl模块
            import ssl

            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(str(self.cert_file), str(self.key_file))

            return context

        except Exception as e:
            logger.error(f"创建SSL上下文失败: {e}")
            return None

    def show_cert_info(self):
        """显示证书信息"""
        if self.cert_file.exists():
            print(f"证书路径: {self.cert_file}")
            print(f"私钥路径: {self.key_file}")

            # 显示证书详情
            try:
                from OpenSSL import crypto
                with open(self.cert_file, 'r') as f:
                    cert = crypto.load_certificate(crypto.FILETYPE_PEM, f.read())

                print(f"\n证书信息:")
                print(f"  主题: {cert.get_subject()}")
                print(f"  颁发者: {cert.get_issuer()}")
                print(f"  序列号: {cert.get_serial_number()}")
                print(f"  有效期:")
                print(f"    开始: {cert.get_notBefore()}")
                print(f"    结束: {cert.get_notAfter()}")
            except:
                print("  详细信息需要 pyOpenSSL")
        else:
            print("证书文件不存在")


def test_cert_manager():
    """测试证书管理器"""
    logging.basicConfig(level=logging.INFO)

    print("=" * 60)
    print("SSL证书管理器测试")
    print("=" * 60)

    # 创建管理器
    manager = CertManager()

    # 检查并创建证书
    if manager.check_and_create_cert():
        print("\n✅ 证书已准备好")
        manager.show_cert_info()
    else:
        print("\n❌ 证书准备失败")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='证书管理器')
    parser.add_argument('--install', action='store_true', help='安装证书（自动生成）')
    parser.add_argument('--gen', action='store_true', help='仅生成证书')
    parser.add_argument('--info', action='store_true', help='显示证书信息')

    args = parser.parse_args()

    if args.install or args.gen:
        # 生成证书
        manager = CertManager()
        if manager.check_and_create_cert():
            print("证书生成成功")
            sys.exit(0)
        else:
            print("证书生成失败")
            sys.exit(1)

    if args.info:
        manager = CertManager()
        manager.show_cert_info()

    else:
        test_cert_manager()
