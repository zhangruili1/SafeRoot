#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
域名智能采集模块

通过多种来源自动发现与关键词相关的域名：
1. crt.sh 证书透明度日志 — 免费、无需 API Key、数据量大
2. 常见子域名字典 — 对主域名生成常见子域名
3. 本地 hosts 文件匹配 — 查找已有规则中的相关域名
"""

import re
import socket
import time
import json
import os
import urllib.request
import urllib.parse
import urllib.error
from typing import List, Set, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from src.core.logger import get_logger
except ImportError:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    try:
        from src.core.logger import get_logger
    except ImportError:
        class _L:
            def info(self, m): pass
            def warning(self, m): pass
            def error(self, m): pass
            def debug(self, m): pass
        get_logger = lambda: _L()


# ========== 常见子域名字典 ==========
COMMON_SUBDOMAINS = [
    'www', 'm', 'mobile', 'wap', 'api', 'app', 'admin', 'manage', 'manager',
    'login', 'signin', 'sso', 'passport', 'account', 'user', 'member',
    'mail', 'email', 'imap', 'smtp', 'pop', 'webmail', 'mx', 'oa',
    'blog', 'news', 'forum', 'bbs', 'community', 'sns', 'social',
    'shop', 'store', 'mall', 'pay', 'payment', 'trade', 'order', 'cart',
    'cdn', 'static', 'assets', 'img', 'image', 'images', 'pic', 'picture',
    'video', 'media', 'upload', 'download', 'file', 'files', 'fs',
    'dev', 'test', 'staging', 'beta', 'alpha', 'demo', 'preview',
    'doc', 'docs', 'wiki', 'help', 'support', 'service', 'faq',
    'search', 'find', 's', 'so',
    'map', 'maps', 'location', 'gps', 'geo',
    'data', 'bigdata', 'analytics', 'track', 'log', 'logs', 'stat',
    'cloud', 'server', 'node', 'proxy', 'gateway', 'lb', 'nginx',
    'internal', 'intranet', 'vpn', 'remote', 'gateway',
    'hr', 'crm', 'erp', 'edi',
    'recruit', 'job', 'jobs', 'career', 'join',
    'edu', 'training', 'course', 'learn', 'study',
    'game', 'games', 'play', 'entertainment', 'fun',
    'music', 'video', 'tv', 'live', 'stream', 'radio',
    'health', 'medical', 'doctor', 'pharmacy',
    'finance', 'bank', 'loan', 'insurance', 'fund', 'stock',
    'travel', 'hotel', 'flight', 'booking', 'ticket',
    'food', 'restaurant', 'dining', 'meal',
    'auto', 'car', 'vehicle', 'driver',
    'safe', 'security', 'trust', 'verify', 'cert',
    'push', 'notify', 'notification', 'msg', 'message', 'sms',
    'open', 'developer', 'dev', 'sdk', 'platform',
    'partner', 'agent', 'dealer', 'distributor',
    'report', 'monitor', 'alert', 'status', 'health',
    'backup', 'db', 'mysql', 'redis', 'mongo', 'elastic',
    'git', 'ci', 'cd', 'jenkins', 'sonar', 'docker',
    'ftp', 'ssh', 'telnet', 'rdp', 'vnc',
    'print', 'scan', 'copy', 'share',
    'tv', 'ott', 'iptv', 'vod',
    'book', 'read', 'novel', 'comic',
    'tool', 'tools', 'util', 'utility',
    'short', 'url', 'link', 'redirect', 't',
    'feedback', 'suggest', 'comment', 'rating', 'review',
    'privacy', 'terms', 'legal', 'about', 'contact',
    'vip', 'premium', 'plus', 'pro',
    'update', 'upgrade', 'version', 'release',
    'new', 'old', 'v2', 'v3', 'api2', 'api3',
    'hk', 'tw', 'sg', 'jp', 'us', 'eu', 'global', 'intl', 'en', 'cn',
    'bao', 'yun', 'ai', 'iot',
]

# 已知不需要屏蔽的公共域名
SAFE_DOMAINS = {
    'localhost', 'example.com', 'example.org', 'example.net',
    'windows.com', 'microsoft.com', 'google.com',
}


class DomainCollector:
    """域名智能采集器"""

    def __init__(self):
        self.logger = get_logger()
        self._cancel = False

    def cancel(self):
        """取消采集"""
        self._cancel = True

    def is_cancelled(self):
        return self._cancel

    def reset(self):
        self._cancel = False

    def collect(self, keyword: str, use_crtsh: bool = True,
                use_subdict: bool = True, use_hosts: bool = True,
                progress_callback=None) -> Tuple[List[str], List[str]]:
        """
        根据关键词采集域名

        Args:
            keyword: 搜索关键词（域名或关键词片段）
            use_crtsh: 是否使用 crt.sh 证书透明度查询
            use_subdict: 是否使用子域名字典枚举
            use_hosts: 是否搜索本地 hosts 文件
            progress_callback: 进度回调函数 callback(message, current, total)

        Returns:
            (valid_domains, errors): 有效域名列表和错误信息列表
        """
        self.reset()
        self.logger.info(f"开始域名采集: keyword={keyword}")

        # 标准化关键词：去掉协议和路径
        keyword = self._normalize_keyword(keyword)

        all_domains: Set[str] = set()
        errors: List[str] = []
        total_steps = sum([use_crtsh, use_subdict, use_hosts])
        current_step = 0

        # 1. crt.sh 证书透明度查询
        if use_crtsh and not self.is_cancelled():
            current_step += 1
            if progress_callback:
                progress_callback("正在查询证书透明度日志 (crt.sh)...", current_step, total_steps)
            try:
                domains = self._collect_from_crtsh(keyword)
                all_domains.update(domains)
                self.logger.info(f"crt.sh 采集到 {len(domains)} 个域名")
            except Exception as e:
                msg = f"crt.sh 查询失败: {e}"
                errors.append(msg)
                self.logger.warning(msg)

        # 2. 子域名字典枚举
        if use_subdict and not self.is_cancelled():
            current_step += 1
            if progress_callback:
                progress_callback("正在枚举常见子域名...", current_step, total_steps)
            try:
                domains = self._collect_from_subdict(keyword, progress_callback)
                all_domains.update(domains)
                self.logger.info(f"子域名枚举采集到 {len(domains)} 个域名")
            except Exception as e:
                msg = f"子域名枚举失败: {e}"
                errors.append(msg)
                self.logger.warning(msg)

        # 3. 本地 hosts 文件搜索
        if use_hosts and not self.is_cancelled():
            current_step += 1
            if progress_callback:
                progress_callback("正在搜索本地 hosts 文件...", current_step, total_steps)
            try:
                domains = self._collect_from_hosts(keyword)
                all_domains.update(domains)
                self.logger.info(f"hosts 文件搜索到 {len(domains)} 个域名")
            except Exception as e:
                msg = f"hosts 搜索失败: {e}"
                errors.append(msg)
                self.logger.warning(msg)

        # 过滤无效域名
        valid = self._filter_domains(all_domains, keyword)
        self.logger.info(f"采集完成: 有效域名 {len(valid)} 个")

        return sorted(valid), errors

    # ========== 数据源 ==========

    def _collect_from_crtsh(self, keyword: str) -> Set[str]:
        """从 crt.sh 证书透明度日志查询域名"""
        domains = set()

        try:
            from constants import HOSTS_PATH
            hosts_dir = os.path.dirname(HOSTS_PATH)
        except ImportError:
            hosts_dir = r"C:\Windows\System32\drivers\etc"

        url = f"https://crt.sh/?q=%.{keyword}&output=json"
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
        )

        # 增加超时和重试，crt.sh 在国内网络不稳定
        max_retries = 3
        timeout = 30
        last_error = None

        for attempt in range(1, max_retries + 1):
            if self.is_cancelled():
                return domains
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    data = json.loads(resp.read().decode('utf-8', errors='replace'))

                for entry in data:
                    name_value = entry.get('name_value', '')
                    for name in name_value.split('\n'):
                        name = name.strip().lower()
                        # 跳过通配符
                        if name.startswith('*'):
                            name = name[2:]  # *.example.com -> example.com
                        if name and self._is_valid_domain(name):
                            domains.add(name)

                return domains  # 成功则直接返回

            except socket.timeout:
                last_error = "crt.sh 请求超时，请检查网络连接"
                if attempt < max_retries:
                    self.logger.info(f"crt.sh 超时，第 {attempt}/{max_retries} 次重试...")
                    time.sleep(2)
                    continue
                raise Exception(last_error)
            except urllib.error.URLError as e:
                if 'timed out' in str(e.reason).lower() or isinstance(e.reason, socket.timeout):
                    last_error = "crt.sh 请求超时，请检查网络连接"
                    if attempt < max_retries:
                        self.logger.info(f"crt.sh 超时，第 {attempt}/{max_retries} 次重试...")
                        time.sleep(2)
                        continue
                    raise Exception(last_error)
                raise Exception(f"网络请求失败: {e.reason}")
            except json.JSONDecodeError:
                raise Exception("crt.sh 返回数据格式错误")
            except Exception as e:
                if 'timed out' in str(e).lower():
                    last_error = "crt.sh 请求超时，请检查网络连接"
                    if attempt < max_retries:
                        self.logger.info(f"crt.sh 超时，第 {attempt}/{max_retries} 次重试...")
                        time.sleep(2)
                        continue
                    raise Exception(last_error)
                raise

        raise Exception(last_error or "crt.sh 查询失败")

        return domains

    def _collect_from_subdict(self, keyword: str, progress_callback=None) -> Set[str]:
        """通过常见子域名字典枚举域名"""
        domains = set()
        resolved_count = 0

        # 提取主域名
        main_domain = self._extract_main_domain(keyword)
        if not main_domain:
            return domains

        total = len(COMMON_SUBDOMAINS)

        def check_subdomain(sub):
            fqdn = f"{sub}.{main_domain}"
            try:
                socket.getaddrinfo(fqdn, None, socket.AF_INET, socket.SOCK_STREAM)
                return fqdn
            except (socket.gaierror, socket.herror, OSError):
                return None

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = {executor.submit(check_subdomain, sub): sub for sub in COMMON_SUBDOMAINS}
            done = 0
            for future in as_completed(futures):
                done += 1
                if self.is_cancelled():
                    executor.shutdown(wait=False, cancel_futures=True)
                    break
                result = future.result()
                if result:
                    domains.add(result)
                    resolved_count += 1
                if progress_callback and done % 50 == 0:
                    progress_callback(
                        f"子域名枚举: {done}/{total} (已发现 {len(domains)} 个)",
                        0, 0  # 不更新总进度
                    )

        return domains

    def _collect_from_hosts(self, keyword: str) -> Set[str]:
        """从本地 hosts 文件中搜索匹配的域名"""
        domains = set()

        try:
            from constants import HOSTS_PATH
        except ImportError:
            return domains

        try:
            with open(HOSTS_PATH, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    # 提取域名部分
                    parts = line.split()
                    if len(parts) >= 2:
                        domain = parts[1].lower().split('#')[0].strip()
                        if keyword.lower() in domain:
                            domains.add(domain)
        except Exception:
            pass

        return domains

    # ========== 工具方法 ==========

    def _normalize_keyword(self, keyword: str) -> str:
        """标准化关键词：去掉协议、路径、www 前缀"""
        keyword = keyword.strip().lower()
        # 去掉协议
        for prefix in ['https://', 'http://']:
            if keyword.startswith(prefix):
                keyword = keyword[len(prefix):]
        # 去掉路径
        keyword = keyword.split('/')[0]
        # 去掉端口
        keyword = keyword.split(':')[0]
        return keyword.strip()

    def _extract_main_domain(self, keyword: str) -> str:
        """从关键词中提取主域名
        
        例如: www.360.cn -> 360.cn
              360.cn -> 360.cn
              baidu -> (empty, 无法提取)
        """
        # 如果是 IP 地址则跳过
        if re.match(r'^\d{1,3}(\.\d{1,3}){3}$', keyword):
            return ''

        # 如果包含点，取最后两段或三段
        parts = keyword.split('.')
        if len(parts) >= 2:
            # 去掉 www 前缀
            if parts[0] == 'www':
                parts = parts[1:]
            if len(parts) >= 2:
                return '.'.join(parts)

        return keyword  # 返回原始关键词，可能是 "360" 这种片段

    def _is_valid_domain(self, domain: str) -> bool:
        """验证域名格式"""
        if not domain or len(domain) > 253:
            return False
        # 基本格式检查
        if not re.match(r'^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$', domain):
            return False
        parts = domain.split('.')
        if len(parts) < 2:
            return False
        # TLD 至少 2 个字符
        if len(parts[-1]) < 2:
            return False
        return True

    def _filter_domains(self, domains: Set[str], keyword: str) -> List[str]:
        """过滤域名列表

        规则：
        1. 必须包含关键词
        2. 排除公共域名
        3. 排除纯 IP 地址
        4. 去重
        """
        keyword = keyword.lower().strip()
        # 提取关键词核心部分用于匹配
        # "360" 应该匹配 "360.cn", "www.360.cn", "so.360.com" 等
        keyword_parts = keyword.split('.')
        # 核心关键词（去掉 www, com, cn 等通用后缀）
        generic_tlds = {'www', 'com', 'cn', 'net', 'org', 'gov', 'edu', 'io', 'co'}
        core_keywords = [p for p in keyword_parts if p and p not in generic_tlds and len(p) > 1]

        valid = []
        seen = set()

        for domain in sorted(domains):
            domain_lower = domain.lower()

            # 去重（裸域名和 www 域名视为同一个）
            dedup_key = domain_lower
            if dedup_key.startswith('www.'):
                dedup_key = dedup_key[4:]
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            # 必须包含至少一个核心关键词
            if core_keywords and not any(kw in domain_lower for kw in core_keywords):
                continue
            # 如果没有核心关键词（如搜索 "example.com"），直接包含关键词即可
            elif not core_keywords and keyword not in domain_lower:
                continue

            # 排除公共域名
            if domain_lower in SAFE_DOMAINS:
                continue

            # 排除 IP 地址
            if re.match(r'^\d{1,3}(\.\d{1,3}){3}$', domain_lower):
                continue

            valid.append(domain_lower)

        return valid

    @staticmethod
    def quick_validate(domain: str) -> bool:
        """快速验证单个域名是否有 DNS 记录"""
        try:
            socket.getaddrinfo(domain, None, socket.AF_INET, socket.SOCK_STREAM)
            return True
        except (socket.gaierror, socket.herror, OSError):
            return False
