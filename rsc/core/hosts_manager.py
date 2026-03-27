#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hosts 文件管理核心类
"""

import os
import re
import shutil
import subprocess
import tempfile
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple

# 导入常量
try:
    from constants import HOSTS_PATH, BACKUP_PATH
except ImportError:
    # 尝试从上级目录导入
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from constants import HOSTS_PATH, BACKUP_PATH


class HostsManager:
    """Hosts 文件管理器"""
    
    # 规则匹配正则表达式（支持 IPv4 和 IPv6）
    RULE_PATTERN = re.compile(r'^\s*(?P<disabled>#)?\s*(?P<ip>[\da-fA-F.:]+)\s+(?P<domain>\S+)(?:\s+#.*)?$')
    COMMENT_PATTERN = re.compile(r'^\s*#')
    EMPTY_PATTERN = re.compile(r'^\s*$')

    @staticmethod
    def _ipv4_to_ipv6_redirect(ipv4: str) -> str:
        """根据 IPv4 地址返回对应的 IPv6 屏蔽地址"""
        if ipv4 == '0.0.0.0':
            return '::'
        return '::1'

    def _add_hosts_entries(self, lines: list, domain: str, redirect_to: str) -> list:
        """向 hosts 行列表添加 IPv4 + IPv6 屏蔽条目（去重）"""
        existing_domains = set()
        for line in lines:
            match = self.RULE_PATTERN.match(line)
            if match and match.group('domain') == domain:
                existing_domains.add((match.group('ip'), match.group('domain')))

        added = False
        if (redirect_to, domain) not in existing_domains:
            lines.append(f"{redirect_to} {domain}")
            added = True

        ipv6 = self._ipv4_to_ipv6_redirect(redirect_to)
        if (ipv6, domain) not in existing_domains:
            lines.append(f"{ipv6} {domain}")
            added = True

        return lines, added
    
    def __init__(self):
        """初始化 HostsManager"""
        self.hosts_path = HOSTS_PATH
        self.backup_dir = BACKUP_PATH
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # 初始化日志记录器
        try:
            from src.core.logger import get_logger
            self.logger = get_logger()
        except ImportError:
            # 创建虚拟日志记录器
            class DummyLogger:
                def debug(self, msg): pass
                def info(self, msg): pass
                def warning(self, msg): pass
                def error(self, msg): pass
            self.logger = DummyLogger()
    
    def read_hosts(self) -> str:
        """
        读取 hosts 文件内容
        
        Returns:
            str: hosts 文件内容
        """
        try:
            with open(self.hosts_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # 尝试其他编码
            with open(self.hosts_path, 'r', encoding='latin-1') as f:
                return f.read()
        except Exception as e:
            raise Exception(f"读取 hosts 文件失败: {e}")
    
    def write_hosts(self, content: str) -> bool:
        """
        写入 hosts 文件（原子操作）
        
        Args:
            content: 要写入的内容
            
        Returns:
            bool: 是否成功
        """
        # 创建临时文件
        temp_fd, temp_path = tempfile.mkstemp(prefix='hosts_', suffix='.tmp', dir=os.path.dirname(self.hosts_path))
        
        try:
            # 写入临时文件
            with os.fdopen(temp_fd, 'w', encoding='utf-8', newline='\n') as f:
                f.write(content)
            
            # 原子替换原文件
            os.replace(temp_path, self.hosts_path)

            # 刷新 DNS 缓存，使 hosts 文件修改立即生效
            self._flush_dns()

            return True
            
        except Exception as e:
            # 清理临时文件
            try:
                os.unlink(temp_path)
            except:
                pass
            raise Exception(f"写入 hosts 文件失败: {e}")
    
    def backup(self) -> str:
        """
        创建 hosts 文件备份
        
        Returns:
            str: 备份文件路径
        """
        try:
            # 生成备份文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"hosts_{timestamp}.bak"
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            # 复制文件
            shutil.copy2(self.hosts_path, backup_path)
            
            # 记录备份元数据
            metadata = {
                'timestamp': timestamp,
                'datetime': datetime.now().isoformat(),
                'original_path': self.hosts_path,
                'backup_path': backup_path,
                'size': os.path.getsize(backup_path),
                'rule_count': len(self.get_rules())
            }
            
            metadata_path = backup_path + '.meta'
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
            
            return backup_path
            
        except Exception as e:
            raise Exception(f"创建备份失败: {e}")
    
    def restore_from_backup(self, backup_path: str) -> bool:
        """
        从指定备份还原 hosts 文件
        
        Args:
            backup_path: 备份文件路径
            
        Returns:
            bool: 是否成功
        """
        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"备份文件不存在: {backup_path}")
        
        try:
            # 读取备份文件内容
            with open(backup_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 写入 hosts 文件
            return self.write_hosts(content)
            
        except Exception as e:
            raise Exception(f"从备份还原失败: {e}")
    
    def get_backup_list(self) -> List[Dict]:
        """
        获取备份列表
        
        Returns:
            List[Dict]: 备份列表，每个元素包含：
                - path: 备份文件路径
                - timestamp: 时间戳 (YYYYMMDD_HHMMSS)
                - datetime: ISO 格式时间
                - size: 文件大小
                - rule_count: 规则数量
        """
        backups = []
        
        try:
            for filename in os.listdir(self.backup_dir):
                if filename.startswith('hosts_') and filename.endswith('.bak'):
                    backup_path = os.path.join(self.backup_dir, filename)
                    metadata_path = backup_path + '.meta'
                    
                    # 提取时间戳
                    timestamp = filename[6:-4]  # 移除 'hosts_' 和 '.bak'
                    
                    # 尝试读取元数据
                    metadata = {
                        'path': backup_path,
                        'timestamp': timestamp,
                        'datetime': '',
                        'size': os.path.getsize(backup_path),
                        'rule_count': 0
                    }
                    
                    if os.path.exists(metadata_path):
                        try:
                            with open(metadata_path, 'r', encoding='utf-8') as f:
                                meta = json.load(f)
                            metadata.update(meta)
                        except:
                            pass
                    
                    # 如果没有元数据中的时间，尝试从文件名解析
                    if not metadata['datetime']:
                        try:
                            dt = datetime.strptime(timestamp, '%Y%m%d_%H%M%S')
                            metadata['datetime'] = dt.isoformat()
                        except:
                            metadata['datetime'] = timestamp
                    
                    backups.append(metadata)
            
            # 按时间倒序排序（最新的在前）
            backups.sort(key=lambda x: x.get('datetime', ''), reverse=True)
            
        except Exception as e:
            raise Exception(f"获取备份列表失败: {e}")
        
        return backups
    
    def clean_old_backups(self, keep_count: int):
        """
        清理旧备份，保留指定数量的最新备份
        
        Args:
            keep_count: 要保留的备份数量
        """
        if keep_count < 0:
            raise ValueError("keep_count 不能为负数")
        
        try:
            backups = self.get_backup_list()
            
            if len(backups) <= keep_count:
                return
            
            # 要删除的备份（最旧的）
            to_delete = backups[keep_count:]
            
            for backup in to_delete:
                backup_path = backup['path']
                metadata_path = backup_path + '.meta'
                
                # 删除备份文件
                if os.path.exists(backup_path):
                    os.unlink(backup_path)
                
                # 删除元数据文件
                if os.path.exists(metadata_path):
                    os.unlink(metadata_path)
                    
        except Exception as e:
            raise Exception(f"清理备份失败: {e}")
    
    def add_rule(self, domain: str, redirect_to: str = "0.0.0.0") -> bool:
        """
        添加屏蔽规则
        
        Args:
            domain: 要屏蔽的域名
            redirect_to: 重定向到的 IP 地址，默认为 127.0.0.1
            
        Returns:
            bool: 是否成功
        """
        # 验证域名格式
        if not self._is_valid_domain(domain):
            raise ValueError(f"无效的域名格式: {domain}")
        
        # 验证 IP 地址格式
        if not self._is_valid_ip(redirect_to):
            raise ValueError(f"无效的 IP 地址: {redirect_to}")
        
        try:
            content = self.read_hosts()
            lines = content.splitlines()
            
            # 检查是否已存在相同域名的规则
            for i, line in enumerate(lines):
                match = self.RULE_PATTERN.match(line)
                if match and match.group('domain') == domain:
                    # 已存在相同域名的规则
                    ip = match.group('ip')
                    disabled = match.group('disabled') is not None
                    
                    # 如果规则被禁用，启用它
                    if disabled:
                        lines[i] = f"{redirect_to} {domain}"
                        new_content = '\n'.join(lines)
                        return self.write_hosts(new_content)
                    else:
                        # 规则已存在且已启用
                        return False
            
            # 添加新规则（IPv4 + IPv6）
            new_rule = f"{redirect_to} {domain}"
            ipv6_redirect = self._ipv4_to_ipv6_redirect(redirect_to)
            ipv6_rule = f"{ipv6_redirect} {domain}"
            lines.append(new_rule)
            lines.append(ipv6_rule)
            new_content = '\n'.join(lines)
            
            return self.write_hosts(new_content)
            
        except Exception as e:
            raise Exception(f"添加规则失败: {e}")
    
    def remove_rule(self, domain: str) -> bool:
        """
        移除屏蔽规则
        
        Args:
            domain: 要移除的域名
            
        Returns:
            bool: 是否成功
        """
        try:
            content = self.read_hosts()
            lines = content.splitlines()
            new_lines = []
            removed = False
            
            for line in lines:
                match = self.RULE_PATTERN.match(line)
                if match and match.group('domain') == domain:
                    # 跳过这个规则（移除），同时移除 IPv4 和 IPv6 条目
                    removed = True
                    continue
                new_lines.append(line)
            
            if removed:
                new_content = '\n'.join(new_lines)
                return self.write_hosts(new_content)
            else:
                return False
                
        except Exception as e:
            raise Exception(f"移除规则失败: {e}")
    
    def disable_rule(self, domain: str) -> bool:
        """
        注释掉规则（禁用）
        
        Args:
            domain: 要禁用的域名
            
        Returns:
            bool: 是否成功
        """
        return self._toggle_rule(domain, disable=True)
    
    def enable_rule(self, domain: str) -> bool:
        """
        取消注释（启用）
        
        Args:
            domain: 要启用的域名
            
        Returns:
            bool: 是否成功
        """
        return self._toggle_rule(domain, disable=False)
    
    def get_rules(self) -> List[Dict]:
        """
        解析 hosts 文件，返回规则列表
        
        Returns:
            List[Dict]: 规则列表，每个元素包含：
                - domain: 域名
                - ip: IP 地址
                - enabled: 是否启用
                - line: 原始行内容
                - line_number: 行号（从1开始）
        """
        rules = []
        
        try:
            content = self.read_hosts()
            lines = content.splitlines()
            
            for i, line in enumerate(lines, 1):
                match = self.RULE_PATTERN.match(line)
                if match:
                    rule = {
                        'domain': match.group('domain'),
                        'ip': match.group('ip'),
                        'enabled': match.group('disabled') is None,
                        'line': line,
                        'line_number': i
                    }
                    rules.append(rule)
                    
        except Exception as e:
            raise Exception(f"解析规则失败: {e}")
        
        return rules
    
    def _toggle_rule(self, domain: str, disable: bool) -> bool:
        """
        启用或禁用规则（内部方法）
        
        Args:
            domain: 域名
            disable: True 表示禁用，False 表示启用
            
        Returns:
            bool: 是否成功
        """
        try:
            content = self.read_hosts()
            lines = content.splitlines()
            changed = False
            
            for i, line in enumerate(lines):
                match = self.RULE_PATTERN.match(line)
                if match and match.group('domain') == domain:
                    ip = match.group('ip')
                    currently_disabled = match.group('disabled') is not None
                    
                    if disable and not currently_disabled:
                        # 禁用：添加注释
                        lines[i] = f"# {ip} {domain}"
                        changed = True
                    elif not disable and currently_disabled:
                        # 启用：移除注释
                        lines[i] = f"{ip} {domain}"
                        changed = True
                    break
            
            if changed:
                new_content = '\n'.join(lines)
                return self.write_hosts(new_content)
            else:
                return False
                
        except Exception as e:
            raise Exception(f"切换规则状态失败: {e}")
    
    def _flush_dns(self):
        """刷新 DNS 缓存并确保 hosts 文件优先"""
        try:
            # 多次刷新 DNS 缓存确保生效
            for _ in range(2):
                subprocess.run(
                    ['ipconfig', '/flushdns'],
                    capture_output=True,
                    timeout=10
                )
            self.logger.debug("DNS 缓存已刷新")

            # 禁用 DNS 并行解析，确保 hosts 文件优先于 DNS 服务器
            # 某些 Windows 配置下，DNS 服务器响应比 hosts 文件快，
            # 导致 hosts 规则被绕过。设置此注册表项可强制 hosts 优先。
            try:
                import winreg
                key_path = r"SYSTEM\CurrentControlSet\Services\Dnscache\Parameters"
                with winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, key_path, 0,
                                         winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY) as key:
                    # DisableParallelAandAAAA = 1 → 禁用并行 DNS/AAAA 查询
                    winreg.SetValueEx(key, "DisableParallelAandAAAA", 0, winreg.REG_DWORD, 1)
                self.logger.info("已设置 hosts 文件 DNS 优先解析")
            except Exception as e:
                self.logger.warning(f"设置 DNS 优先级失败（可能权限不足）: {e}")

        except Exception as e:
            self.logger.warning(f"刷新 DNS 缓存失败: {e}")

    def _is_valid_domain(self, domain: str) -> bool:
        """
        验证域名格式
        
        Args:
            domain: 域名
            
        Returns:
            bool: 是否有效
        """
        # 简单的域名验证
        if not domain or len(domain) > 253:
            return False
        
        # 检查是否包含非法字符
        if re.search(r'[^\w\.\-]', domain):
            return False
        
        # 检查标签长度
        labels = domain.split('.')
        for label in labels:
            if not label or len(label) > 63:
                return False
        
        return True
    
    def _is_valid_ip(self, ip: str) -> bool:
        """
        验证 IP 地址格式
        
        Args:
            ip: IP 地址
            
        Returns:
            bool: 是否有效
        """
        pattern = re.compile(r'^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$')
        match = pattern.match(ip)
        
        if not match:
            return False
        
        # 检查每个部分是否在 0-255 范围内
        for part in match.groups():
            if not 0 <= int(part) <= 255:
                return False
        
        return True


if __name__ == "__main__":
    # 测试代码
    manager = HostsManager()
    
    print("当前规则:")
    rules = manager.get_rules()
    for rule in rules:
        print(f"  {rule['domain']} -> {rule['ip']} ({'启用' if rule['enabled'] else '禁用'})")
    
    print(f"\n备份目录: {manager.backup_dir}")
    print(f"Hosts 文件: {manager.hosts_path}")