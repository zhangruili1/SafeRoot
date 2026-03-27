#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DoH (DNS-over-HTTPS) 控制器

通过 Windows 注册表策略强制关闭所有主流浏览器的 DoH，
使浏览器必须使用系统 DNS（尊重 hosts 文件）。

正确的策略注册表结构（已验证）：
- Chrome:  HKLM\\SOFTWARE\\Policies\\Google\\Chrome → DnsOverHttpsMode = "off" (REG_SZ)
- Edge:    HKLM\\SOFTWARE\\Policies\\Microsoft\\Edge → DnsOverHttpsMode = "off" (REG_SZ)
- Firefox: HKLM\\SOFTWARE\\Policies\\Mozilla\\Firefox\\DNSOverHTTPS → Enabled = 0 (REG_DWORD)
"""

import winreg
import subprocess


class DohController:
    """浏览器 DoH 控制器"""

    BROWSERS = [
        {
            'name': 'Google Chrome',
            'key': r'SOFTWARE\Policies\Google\Chrome',
            # 直接在 key 下写值 DnsOverHttpsMode = "off"
            'value_name': 'DnsOverHttpsMode',
            'disable_value': ('off', winreg.REG_SZ),
            'check_enabled_values': ['automatic', 'secure'],
        },
        {
            'name': 'Microsoft Edge',
            'key': r'SOFTWARE\Policies\Microsoft\Edge',
            'value_name': 'DnsOverHttpsMode',
            'disable_value': ('off', winreg.REG_SZ),
            'check_enabled_values': ['automatic', 'secure'],
        },
        {
            'name': 'Mozilla Firefox',
            'key': r'SOFTWARE\Policies\Mozilla\Firefox\DNSOverHTTPS',
            # 子键 DNSOverHTTPS 下写 Enabled = 0
            'value_name': 'Enabled',
            'disable_value': (0, winreg.REG_DWORD),
            'check_enabled_values': [1],
        },
    ]

    def __init__(self):
        try:
            from src.core.logger import get_logger
            self.logger = get_logger()
        except ImportError:
            class _L:
                def info(self, m): pass
                def warning(self, m): pass
                def error(self, m): pass
                def debug(self, m): pass
            self.logger = _L()

    def _set_registry_value(self, key_path, value_name, value_data, value_type):
        """设置注册表值（winreg 优先，失败则用 reg 命令）"""
        # 方法 1: winreg API
        try:
            with winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, key_path, 0,
                                     winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY) as key:
                winreg.SetValueEx(key, value_name, 0, value_type, value_data)
            return True
        except Exception:
            pass

        # 方法 2: reg add 命令（后备）
        try:
            if value_type == winreg.REG_SZ:
                type_str = 'REG_SZ'
            elif value_type == winreg.REG_DWORD:
                type_str = 'REG_DWORD'
            else:
                type_str = 'REG_SZ'

            reg_path = f'HKLM\\{key_path}'
            result = subprocess.run(
                ['reg', 'add', reg_path, '/v', value_name, '/t', type_str,
                 '/d', str(value_data), '/f'],
                capture_output=True, timeout=10
            )
            return result.returncode == 0
        except Exception as e:
            self.logger.warning(f"reg add 也失败: {e}")
            return False

    def _delete_registry_value(self, key_path, value_name):
        """删除注册表值"""
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0,
                                winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY) as key:
                winreg.DeleteValue(key, value_name)
        except WindowsError:
            pass
        except Exception:
            pass

    def _read_registry_value(self, key_path, value_name):
        """读取注册表值"""
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0,
                                winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
                value, _ = winreg.QueryValueEx(key, value_name)
                return value
        except WindowsError:
            return None
        except Exception:
            return None

    def disable_all(self):
        """强制关闭所有浏览器的 DoH"""
        results = {}
        for browser in self.BROWSERS:
            value_data, value_type = browser['disable_value']
            success = self._set_registry_value(
                browser['key'], browser['value_name'], value_data, value_type
            )
            if success:
                self.logger.info(f"[DoH] 已关闭 {browser['name']} 的安全 DNS")
            results[browser['name']] = success
        return results

    def restore_all(self):
        """恢复所有浏览器的 DoH（删除策略值，恢复默认）"""
        results = {}
        for browser in self.BROWSERS:
            self._delete_registry_value(browser['key'], browser['value_name'])
            self.logger.info(f"[DoH] 已恢复 {browser['name']} 的 DNS 设置")
            results[browser['name']] = True
        return results

    def get_status(self):
        """获取各浏览器 DoH 状态"""
        results = {}
        for browser in self.BROWSERS:
            value = self._read_registry_value(browser['key'], browser['value_name'])
            value_data, _ = browser['disable_value']

            if value is None:
                state = 'default'
            elif value == value_data:
                state = 'disabled'
            elif value in browser['check_enabled_values']:
                state = 'enabled'
            else:
                state = 'unknown'

            results[browser['name']] = state
        return results

    def is_any_browser_doh_enabled(self):
        """检查是否有浏览器 DoH 未被禁用"""
        status = self.get_status()
        for name, state in status.items():
            if state != 'disabled':
                return True, name, state
        return False, '', ''
