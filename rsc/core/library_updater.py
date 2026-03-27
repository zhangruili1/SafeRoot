#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
预设库自动更新模块

从 GitHub 仓库下载预设域名库并同步到本地，
支持增量更新（只添加新域名，不删除用户已有规则）。
"""

import os
import json
import time
import hashlib
import urllib.request
import urllib.parse
import urllib.error

try:
    from src.core.logger import get_logger
except ImportError:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    try:
        from src.core.logger import get_logger
    except ImportError:
        class _L:
            def info(self, m): pass
            def warning(self, m): pass
            def error(self, m): pass
            def debug(self, m): pass
        get_logger = lambda: _L()

try:
    from constants import APP_DATA_PATH
except ImportError:
    APP_DATA_PATH = os.path.expandvars(r"%APPDATA%\SafeRoot")


# GitHub 仓库配置
REPO_RAW_BASE = "https://raw.githubusercontent.com/zhangruili1/SafeRoot-default-library/main"
LIBRARY_FILENAME = "SafeRoot default library"
LIBRARY_REMOTE_URL = f"{REPO_RAW_BASE}/{urllib.parse.quote(LIBRARY_FILENAME)}"

# 本地预设库存储
LIBRARY_DIR = os.path.join(APP_DATA_PATH, "library")
LIBRARY_LOCAL_PATH = os.path.join(LIBRARY_DIR, "default_library.txt")
LIBRARY_META_PATH = os.path.join(LIBRARY_DIR, "meta.json")


def _safe_urlopen(url, timeout=30):
    """安全的 HTTP 请求，兼容各种编码"""
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/plain, */*',
        }
    )
    return urllib.request.urlopen(req, timeout=timeout)


def _parse_domains(text):
    """从文本中解析域名列表，过滤无效行"""
    domains = []
    for line in text.splitlines():
        line = line.strip().lower()
        # 跳过空行和注释
        if not line or line.startswith('#') or line.startswith('//'):
            continue
        # 跳过明显不是域名的行（包含特殊字符如省略号）
        if '...' in line or '..' in line:
            continue
        # 基本域名验证：至少包含一个点，且不包含空格
        if '.' in line and ' ' not in line:
            domains.append(line)
    # 去重保序
    seen = set()
    unique = []
    for d in domains:
        if d not in seen:
            seen.add(d)
            unique.append(d)
    return unique


class LibraryUpdater:
    """预设库更新器"""

    def __init__(self):
        self.logger = get_logger()
        # 确保目录存在
        os.makedirs(LIBRARY_DIR, exist_ok=True)

    def get_local_domains(self):
        """获取本地预设库中的域名列表"""
        if not os.path.exists(LIBRARY_LOCAL_PATH):
            return []
        try:
            with open(LIBRARY_LOCAL_PATH, 'r', encoding='utf-8') as f:
                return _parse_domains(f.read())
        except Exception as e:
            self.logger.warning(f"读取本地预设库失败: {e}")
            return []

    def _get_remote_hash(self):
        """获取远程文件的 ETag / 内容 hash（用于判断是否有更新）"""
        try:
            req = urllib.request.Request(
                LIBRARY_REMOTE_URL,
                headers={
                    'User-Agent': 'Mozilla/5.0',
                    'Accept': 'text/plain',
                },
                method='HEAD'
            )
            resp = urllib.request.urlopen(req, timeout=15)
            etag = resp.headers.get('ETag', '')
            last_modified = resp.headers.get('Last-Modified', '')
            # 如果 ETag 存在则用 ETag，否则用 Last-Modified
            identifier = etag or last_modified or ''
            return identifier
        except Exception:
            return ''

    def _load_meta(self):
        """加载本地元数据"""
        if not os.path.exists(LIBRARY_META_PATH):
            return {}
        try:
            with open(LIBRARY_META_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_meta(self, meta):
        """保存本地元数据"""
        try:
            with open(LIBRARY_META_PATH, 'w', encoding='utf-8') as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.warning(f"保存元数据失败: {e}")

    def has_update(self):
        """检查远程是否有更新（通过 ETag / Last-Modified 判断）"""
        meta = self._load_meta()
        old_identifier = meta.get('etag') or meta.get('last_modified') or ''

        remote_identifier = self._get_remote_hash()
        if not remote_identifier:
            # 无法获取远程信息，假设有更新
            return True

        return remote_identifier != old_identifier

    def update(self, force=False):
        """
        从远程下载并更新本地预设库

        Args:
            force: 是否强制更新（忽略 ETag 缓存）

        Returns:
            dict: {
                'success': bool,
                'total': int,          # 预设库中域名总数
                'new': int,            # 本次新增的域名数
                'new_domains': list,   # 本次新增的域名列表
                'message': str
            }
        """
        result = {
            'success': False,
            'total': 0,
            'new': 0,
            'new_domains': [],
            'message': ''
        }

        try:
            # 非强制模式下，先检查是否有更新
            if not force:
                if not self.has_update():
                    result['success'] = True
                    result['total'] = len(self.get_local_domains())
                    result['message'] = '预设库已是最新版本'
                    return result

            self.logger.info("正在从 GitHub 下载预设库...")

            # 下载远程文件
            resp = _safe_urlopen(LIBRARY_REMOTE_URL, timeout=30)
            content = resp.read().decode('utf-8', errors='replace')

            # 保存 ETag / Last-Modified
            etag = resp.headers.get('ETag', '')
            last_modified = resp.headers.get('Last-Modified', '')

            # 解析域名
            remote_domains = _parse_domains(content)

            if not remote_domains:
                result['message'] = '远程预设库为空或格式错误'
                self.logger.warning(result['message'])
                return result

            # 读取旧的本地域名
            old_domains = set(self.get_local_domains())

            # 计算新增的域名
            new_domains = [d for d in remote_domains if d not in old_domains]

            # 保存到本地
            with open(LIBRARY_LOCAL_PATH, 'w', encoding='utf-8') as f:
                for domain in remote_domains:
                    f.write(domain + '\n')

            # 更新元数据
            meta = {
                'etag': etag,
                'last_modified': last_modified,
                'last_update': time.strftime('%Y-%m-%d %H:%M:%S'),
                'total_domains': len(remote_domains),
                'source': 'https://github.com/zhangruili1/SafeRoot-default-library',
            }
            self._save_meta(meta)

            result['success'] = True
            result['total'] = len(remote_domains)
            result['new'] = len(new_domains)
            result['new_domains'] = new_domains

            if new_domains:
                result['message'] = f"预设库更新成功: 共 {len(remote_domains)} 个域名，新增 {len(new_domains)} 个"
                self.logger.info(result['message'])
            else:
                result['message'] = f"预设库已是最新: 共 {len(remote_domains)} 个域名"
                self.logger.info(result['message'])

        except urllib.error.URLError as e:
            reason = str(e.reason) if hasattr(e, 'reason') else str(e)
            result['message'] = f'网络错误: {reason}'
            self.logger.error(result['message'])
        except Exception as e:
            result['message'] = f'更新失败: {e}'
            self.logger.error(result['message'])

        return result
