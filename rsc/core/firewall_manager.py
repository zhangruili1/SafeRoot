#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows 防火墙管理 - 通过防火墙规则阻断域名 IP

浏览器启用 DNS-over-HTTPS (DoH) 时会绕过 hosts 文件，
此模块通过 Windows 防火墙直接阻断目标域名的 IP 地址来确保屏蔽生效。
"""

import subprocess
import socket
import json
import os
import re
from typing import List, Dict, Optional, Set


def _run_cmd(cmd, timeout=15):
    """
    安全执行子进程命令，返回 (returncode, stdout_text, stderr_text)。
    使用二进制模式读取输出后再用 utf-8 解码，避免 Python 3.8 在中文 Windows
    上因 GBK 编码问题导致 subprocess 崩溃 (UnicodeDecodeError / IndexError)。
    """
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout)
        stdout = r.stdout.decode('utf-8', errors='replace') if r.stdout else ''
        stderr = r.stderr.decode('utf-8', errors='replace') if r.stderr else ''
        return r.returncode, stdout, stderr
    except subprocess.TimeoutExpired:
        return -1, '', 'timeout'
    except Exception as e:
        return -1, '', str(e)

# SafeRoot 防火墙规则统一前缀，便于管理
RULE_PREFIX = "SafeRoot_Block_"

# 保存域名->IP 映射的文件
_IP_MAP_FILE = os.path.join(
    os.environ.get('APPDATA', os.path.expanduser('~')),
    'SafeRoot', 'ip_map.json'
)


class FirewallManager:
    """Windows 防火墙规则管理器"""

    def __init__(self):
        self._ip_map: Dict[str, Set[str]] = {}
        os.makedirs(os.path.dirname(_IP_MAP_FILE), exist_ok=True)
        self._load_ip_map()

        try:
            from src.core.logger import get_logger
            self.logger = get_logger()
        except ImportError:
            class DummyLogger:
                def debug(self, msg): pass
                def info(self, msg): pass
                def warning(self, msg): pass
                def error(self, msg): pass
            self.logger = DummyLogger()

    # ========== IP 映射持久化 ==========

    def _load_ip_map(self):
        """从文件加载域名->IP 映射"""
        try:
            if os.path.exists(_IP_MAP_FILE):
                with open(_IP_MAP_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self._ip_map = {k: set(v) for k, v in data.items()}
        except Exception:
            self._ip_map = {}

    def _save_ip_map(self):
        """保存域名->IP 映射到文件"""
        try:
            data = {k: list(v) for k, v in self._ip_map.items()}
            with open(_IP_MAP_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.logger.warning(f"保存 IP 映射失败: {e}")

    # ========== DNS 解析 ==========

    @staticmethod
    def resolve_domain(domain: str) -> List[str]:
        """
        解析域名的所有 IP 地址（IPv4 和 IPv6）

        使用多种策略确保能获取真实 IP，即使域名已在 hosts 文件中：
        1. nslookup 指定公共 DNS 服务器（114.114.114.114）直接查询
        2. socket.getaddrinfo 解析
        
        Args:
            domain: 域名
            
        Returns:
            IP 地址列表（去重后）
        """
        ips = set()
        LOCAL_IPS_V4 = ('127.0.0.1', '0.0.0.0', '0.0.0.1', '0.0.0.2')
        LOCAL_IPS_V6 = ('::1', '::', '::ffff:127.0.0.1')

        # 策略 1: 使用 nslookup 指定公共 DNS 服务器直接查询
        # 这是最可靠的方式，完全不受 hosts 文件影响
        public_dns_servers = ['114.114.114.114', '223.5.5.5', '8.8.8.8']
        for dns_server in public_dns_servers:
            try:
                _, output, _ = _run_cmd(
                    ['nslookup', domain, dns_server], timeout=10
                )
                
                # 收集该 DNS 服务器的 IP（排除它们）
                dns_server_ips = set()
                try:
                    _, dns_output, _ = _run_cmd(['nslookup', dns_server], timeout=10)
                    for m in re.finditer(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', dns_output):
                        dns_server_ips.add(m.group(1))
                except Exception:
                    pass
                dns_server_ips.add(dns_server)

                # 从整个输出提取所有 IPv4 地址，排除本地地址和 DNS 服务器自身 IP
                for m in re.finditer(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', output):
                    ip = m.group(1)
                    if ip not in LOCAL_IPS_V4 and ip not in dns_server_ips:
                        ips.add(ip)

                if ips:
                    break  # 已获取到 IP，无需尝试下一个 DNS
            except Exception:
                continue

        # 策略 2: 刷新 DNS 缓存后用 socket 解析
        try:
            subprocess.run(['ipconfig', '/flushdns'], capture_output=True, timeout=10)
        except Exception:
            pass

        try:
            results = socket.getaddrinfo(domain, None, socket.AF_INET)
            for r in results:
                ip = r[4][0]
                if ip not in LOCAL_IPS_V4:
                    ips.add(ip)
        except Exception:
            pass

        try:
            results = socket.getaddrinfo(domain, None, socket.AF_INET6)
            for r in results:
                ip = r[4][0].split('%')[0]
                if ip not in LOCAL_IPS_V6 and len(ip) > 4:
                    ips.add(ip)
        except Exception:
            pass

        return list(ips)

    # ========== 防火墙规则管理 ==========

    def block_domain(self, domain: str) -> Dict:
        """
        通过防火墙阻断域名
        
        1. 解析域名获取所有 IP
        2. 对每个 IP 添加防火墙出站阻断规则
        3. 记录域名->IP 映射
        
        Args:
            domain: 要屏蔽的域名
            
        Returns:
            dict: {'success': bool, 'ips': list, 'blocked_count': int, 'errors': list}
        """
        domain = domain.strip().lower()
        ips = self.resolve_domain(domain)
        errors = []
        blocked_count = 0

        if not ips:
            self.logger.warning(f"无法解析 {domain} 的 IP 地址，跳过防火墙阻断")
            return {'success': False, 'ips': [], 'blocked_count': 0, 'errors': ['DNS 解析失败']}

        for ip in ips:
            rule_name = f"{RULE_PREFIX}{domain}_{ip.replace('.', '_')}"
            try:
                # 检查规则是否已存在
                rc, _, _ = _run_cmd(
                    ['netsh', 'advfirewall', 'firewall', 'show', 'rule',
                     f'name={rule_name}', 'dir=out'], timeout=10
                )
                if rc == 0:
                    self.logger.debug(f"防火墙规则已存在: {rule_name}")
                    blocked_count += 1
                    continue

                # 添加出站阻断规则
                rc, stdout, stderr = _run_cmd(
                    ['netsh', 'advfirewall', 'firewall', 'add', 'rule',
                     f'name={rule_name}',
                     'dir=out',
                     'action=block',
                     'protocol=any',
                     f'remoteip={ip}',
                     'enable=yes',
                     'profile=any',
                     f'description=SafeRoot: block {domain} ({ip})'],
                    timeout=15
                )

                if rc == 0:
                    blocked_count += 1
                    self.logger.info(f"防火墙已阻断: {domain} -> {ip}")
                else:
                    error_msg = stderr.strip() or stdout.strip()
                    errors.append(f"{ip}: {error_msg}")
                    self.logger.warning(f"添加防火墙规则失败: {ip} - {error_msg}")

            except subprocess.TimeoutExpired:
                errors.append(f"{ip}: 操作超时")
            except Exception as e:
                errors.append(f"{ip}: {str(e)}")

        # 记录映射
        if domain not in self._ip_map:
            self._ip_map[domain] = set()
        self._ip_map[domain].update(ips)
        self._save_ip_map()

        success = blocked_count > 0
        return {
            'success': success,
            'ips': ips,
            'blocked_count': blocked_count,
            'errors': errors
        }

    def unblock_domain(self, domain: str) -> int:
        """
        移除域名的防火墙阻断规则
        
        Args:
            domain: 域名
            
        Returns:
            int: 成功移除的规则数量
        """
        domain = domain.strip().lower()
        ips = self._ip_map.get(domain, set())
        removed_count = 0

        # 如果没有记录的 IP，尝试通过规则名前缀查找
        if not ips:
            removed_count = self._remove_rules_by_prefix(f"{RULE_PREFIX}{domain}_")
        else:
            for ip in ips:
                rule_name = f"{RULE_PREFIX}{domain}_{ip.replace('.', '_')}"
                removed = self._remove_rule(rule_name)
                if removed:
                    removed_count += 1

        # 清除映射
        if domain in self._ip_map:
            del self._ip_map[domain]
            self._save_ip_map()

        if removed_count > 0:
            self.logger.info(f"已移除 {domain} 的 {removed_count} 条防火墙规则")

        return removed_count

    def sync_firewall_rules(self, enabled_domains: List[str]):
        """
        同步防火墙规则：确保启用的域名被阻断，禁用/删除的域名被解除阻断
        
        Args:
            enabled_domains: 当前启用的域名列表
        """
        enabled_set = {d.strip().lower() for d in enabled_domains}

        # 解除不再需要阻断的域名
        for domain in list(self._ip_map.keys()):
            if domain not in enabled_set:
                self.unblock_domain(domain)

        # 确保所有启用域名都被阻断
        for domain in enabled_domains:
            existing_ips = self._ip_map.get(domain.strip().lower(), set())
            if not existing_ips:
                # 没有 IP 记录，需要解析并阻断
                self.block_domain(domain)

    def _remove_rule(self, rule_name: str) -> bool:
        """删除单条防火墙规则"""
        try:
            rc, _, _ = _run_cmd(
                ['netsh', 'advfirewall', 'firewall', 'delete', 'rule',
                 f'name={rule_name}'], timeout=10
            )
            return rc == 0
        except Exception:
            return False

    def _remove_rules_by_prefix(self, prefix: str) -> int:
        """通过规则名前缀批量删除规则"""
        removed = 0
        try:
            # 获取所有规则
            rc, output, _ = _run_cmd(
                ['netsh', 'advfirewall', 'firewall', 'show', 'rule', 'name=all', 'dir=out'],
                timeout=30
            )
            if rc == 0:
                # 解析规则名
                rule_names = re.findall(r'Rule Name:\s*(.+)', output)
                for name in rule_names:
                    name = name.strip()
                    if name.startswith(prefix):
                        if self._remove_rule(name):
                            removed += 1
        except Exception:
            pass
        return removed

    def get_blocked_domains(self) -> Dict[str, List[str]]:
        """
        获取所有被防火墙阻断的域名及其 IP
        
        Returns:
            dict: {domain: [ip1, ip2, ...]}
        """
        return {k: list(v) for k, v in self._ip_map.items()}

    def cleanup_all(self) -> int:
        """
        清理所有 SafeRoot 创建的防火墙规则
        
        Returns:
            int: 清理的规则数量
        """
        return self._remove_rules_by_prefix(RULE_PREFIX)
