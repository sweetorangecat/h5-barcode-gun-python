#!/usr/bin/env python3
"""
模拟键盘输入模块
基于pyautogui实现，支持跨平台操作
"""

import logging
import platform

logger = logging.getLogger(__name__)


def _setup_pyautogui():
    """配置pyautogui"""
    try:
        import pyautogui
        # 设置延迟为0以提高速度
        pyautogui.PAUSE = 0
        # 启用安全模式：将鼠标移动到左上角会触发异常
        pyautogui.FAILSAFE = True
        return pyautogui
    except ImportError as e:
        logger.error(f"无法导入pyautogui: {e}")
        raise ImportError(
            "pyautogui未安装。请使用: pip install pyautogui"
        )


def set_foreground_window():
    """
    尝试将当前活动窗口设置为前台窗口（仅Windows）
    这可以提高pyautogui的输入成功率
    """
    system = platform.system()

    if system == 'Windows':
        try:
            import win32gui
            import win32con

            # 获取当前活动窗口
            hwnd = win32gui.GetForegroundWindow()
            if hwnd:
                # 将窗口带到前台
                win32gui.SetWindowPos(
                    hwnd, win32con.HWND_TOP, 0, 0, 0, 0,
                    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE
                )
                logger.debug("已将活动窗口设置为前台")
        except ImportError:
            logger.debug("win32gui不可用，跳过窗口设置")
        except Exception as e:
            logger.debug(f"设置前台窗口失败: {e}")


def simulate_keyboard_input(text):
    """
    使用pyautogui模拟键盘输入文本并自动添加回车符

    Args:
        text: 要输入的文本字符串

    Returns:
        bool: 是否成功

    Example:
        success = simulate_keyboard_input("12345")
        # 这将在当前光标位置输入"12345"然后按回车
    """
    try:
        if not text:
            logger.warning("输入文本为空")
            return False

        # 获取pyautogui实例
        pyautogui = _setup_pyautogui()

        # 尝试将窗口设置为前台（提高输入成功率）
        try:
            set_foreground_window()
        except:
            pass

        # 输入文本（使用typewrite，特殊字符需要特殊处理）
        logger.debug(f"正在输入文本: {text}")

        # 对于一些特殊字符，使用write可能比typewrite更可靠
        # typewrite更适合模拟单个按键，而write适合直接输入字符串
        try:
            # 导入pynput库模拟键盘输入，创建键盘控制器
            from pynput.keyboard import Key, Controller
            keyboard = Controller()
            pyautogui.write(str(text), interval=0.01)
            # 使用键盘控制器对象模拟按下回车
            logger.debug("正在按下回车键")
            keyboard.press(Key.enter)
            logger.debug("释放回车键")
            keyboard.release(Key.enter)

        except:
            # 如果write失败，回退到typewrite
            pyautogui.typewrite(str(text), interval=0.01)

        logger.debug("文本输入完成")

        logger.info(f"成功输入条码: {text}")
        return True

    except Exception as e:
        logger.error(f"键盘模拟失败: {e}")
        return False


def simulate_enter_key():
    """
    模拟按下回车键

    Returns:
        bool: 是否成功
    """
    try:
        pyautogui = _setup_pyautogui()

        logger.debug("正在按下回车键")
        pyautogui.press('enter')
        logger.debug("回车键按下完成")

        return True

    except Exception as e:
        logger.error(f"回车键模拟失败: {e}")
        return False


def simulate_hotkey(key1, key2):
    """
    模拟组合键（例如Ctrl+C）

    Args:
        key1: 第一个键（如'ctrl'）
        key2: 第二个键（如'c'）

    Returns:
        bool: 是否成功
    """
    try:
        pyautogui = _setup_pyautogui()

        logger.debug(f"正在模拟组合键: {key1}+{key2}")
        pyautogui.hotkey(key1, key2)
        logger.debug("组合键模拟完成")

        return True

    except Exception as e:
        logger.error(f"组合键模拟失败: {e}")
        return False


def get_window_info():
    """
    获取当前活动窗口信息（调试用）

    Returns:
        dict: 窗口信息
    """
    system = platform.system()
    info = {
        'platform': system,
        'active_window': None
    }

    if system == 'Windows':
        try:
            import win32gui
            hwnd = win32gui.GetForegroundWindow()
            if hwnd:
                info['active_window'] = {
                    'title': win32gui.GetWindowText(hwnd),
                    'hwnd': hwnd
                }
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"获取窗口信息失败: {e}")

    return info


# 如果直接运行此脚本，进行简单测试
if __name__ == '__main__':
    import time

    # 配置日志
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    print("键盘模拟器测试")
    print("==============")
    print("请在5秒内将光标移动到文本编辑器中...")

    for i in range(5, 0, -1):
        print(f"{i}...")
        time.sleep(1)

    # 测试1：输入简单文本
    print("\n输入测试文本: TEST123")
    success = simulate_keyboard_input("TEST123")
    if success:
        print("✓ 成功")
    else:
        print("✗ 失败")

    time.sleep(1)

    # 测试2：输入条码格式
    print("\n输入条码: ABC-123-XYZ")
    success = simulate_keyboard_input("ABC-123-XYZ")
    if success:
        print("✓ 成功")
    else:
        print("✗ 失败")

    print("\n测试完成")
