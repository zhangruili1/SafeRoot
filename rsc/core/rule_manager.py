#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
规则管理类 - 使用 SQLite3 数据库存储用户自定义屏蔽规则
"""

import sqlite3
import os
import uuid
import csv
import re
import threading
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any

# 导入常量
try:
    from constants import APP_DATA_PATH
except ImportError:
    # 尝试从上级目录导入
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from constants import APP_DATA_PATH


def validate_domain(domain: str) -> bool:
    """
    验证域名格式
    
    Args:
        domain: 要验证的域名
        
    Returns:
        bool: 是否有效
    """
    if not domain or not isinstance(domain, str):
        return False
    
    domain = domain.strip()
    
    # 拒绝本地地址作为屏蔽目标
    local_patterns = [
        r'^localhost$',
        r'^127\.\d+\.\d+\.\d+$',
        r'^0\.0\.0\.0$',
        r'^::1$',
        r'^local$',
        r'^0$',
    ]
    
    for pattern in local_patterns:
        if re.match(pattern, domain, re.IGNORECASE):
            return False
    
    # 基本域名格式验证
    # 允许字母、数字、连字符、点号，不能以连字符或点号开头或结尾
    if len(domain) > 253:
        return False
    
    # 检查标签
    labels = domain.split('.')
    if len(labels) < 2:  # 至少需要顶级域名和二级域名
        return False
    
    domain_pattern = re.compile(
        r'^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.[A-Za-z0-9-]{1,63}(?<!-))*$'
    )
    
    if not domain_pattern.match(domain):
        return False
    
    # 检查每个标签长度
    for label in labels:
        if len(label) > 63:
            return False
    
    return True


class RuleManager:
    """规则管理器"""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        初始化 RuleManager
        
        Args:
            db_path: 数据库文件路径，默认使用 APP_DATA_PATH/saferoot.db
        """
        if db_path is None:
            db_path = os.path.join(APP_DATA_PATH, "saferoot.db")
        
        # 确保目录存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._init_tables()
    
    def _init_tables(self):
        """初始化数据库表"""
        with self._lock:
            cursor = self.conn.cursor()
            
            # 创建 rules 表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS rules (
                    id TEXT PRIMARY KEY,
                    domain TEXT NOT NULL UNIQUE,
                    redirect_to TEXT DEFAULT '127.0.0.1',
                    enabled INTEGER DEFAULT 1,
                    remark TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            ''')
            
            # 创建索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_domain ON rules(domain)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_enabled ON rules(enabled)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON rules(created_at)')
            
            self.conn.commit()
    
    def add_rule(self, domain: str, redirect_to: str = "127.0.0.1", remark: str = "") -> bool:
        """
        添加规则
        
        Args:
            domain: 域名
            redirect_to: 重定向到的 IP 地址，默认为 127.0.0.1
            remark: 备注
            
        Returns:
            bool: 是否成功
        """
        if not validate_domain(domain):
            raise ValueError(f"无效的域名格式: {domain}")
        
        # 验证 redirect_to
        if not self._is_valid_ip(redirect_to):
            raise ValueError(f"无效的 IP 地址: {redirect_to}")
        
        rule_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        try:
            with self._lock:
                cursor = self.conn.cursor()
                cursor.execute('''
                    INSERT INTO rules (id, domain, redirect_to, remark, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (rule_id, domain, redirect_to, remark, now, now))
                self.conn.commit()
            return True
            
        except sqlite3.IntegrityError:
            # 域名已存在
            return False
        except Exception as e:
            with self._lock:
                self.conn.rollback()
            raise Exception(f"添加规则失败: {e}")
    
    def remove_rule(self, rule_id: str) -> bool:
        """
        删除规则
        
        Args:
            rule_id: 规则ID
            
        Returns:
            bool: 是否成功
        """
        try:
            with self._lock:
                cursor = self.conn.cursor()
                cursor.execute('DELETE FROM rules WHERE id = ?', (rule_id,))
                self.conn.commit()
                return cursor.rowcount > 0
            
        except Exception as e:
            with self._lock:
                self.conn.rollback()
            raise Exception(f"删除规则失败: {e}")
    
    def remove_rule_by_domain(self, domain: str) -> bool:
        """
        按域名删除规则
        
        Args:
            domain: 域名
            
        Returns:
            bool: 是否成功
        """
        try:
            with self._lock:
                cursor = self.conn.cursor()
                cursor.execute('DELETE FROM rules WHERE domain = ?', (domain,))
                self.conn.commit()
                return cursor.rowcount > 0
            
        except Exception as e:
            with self._lock:
                self.conn.rollback()
            raise Exception(f"按域名删除规则失败: {e}")
    
    def update_rule(self, rule_id: str, **kwargs) -> bool:
        """
        更新规则
        
        Args:
            rule_id: 规则ID
            **kwargs: 要更新的字段，支持 domain, redirect_to, enabled, remark
            
        Returns:
            bool: 是否成功
        """
        if not kwargs:
            return False
        
        allowed_fields = {'domain', 'redirect_to', 'enabled', 'remark'}
        update_fields = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not update_fields:
            return False
        
        # 如果更新域名，需要验证
        if 'domain' in update_fields and not validate_domain(update_fields['domain']):
            raise ValueError(f"无效的域名格式: {update_fields['domain']}")
        
        # 如果更新 redirect_to，需要验证
        if 'redirect_to' in update_fields and not self._is_valid_ip(update_fields['redirect_to']):
            raise ValueError(f"无效的 IP 地址: {update_fields['redirect_to']}")
        
        # 构建更新语句
        set_clause = ', '.join([f"{field} = ?" for field in update_fields.keys()])
        set_clause += ', updated_at = ?'
        
        values = list(update_fields.values())
        values.append(datetime.now().isoformat())
        values.append(rule_id)
        
        try:
            with self._lock:
                cursor = self.conn.cursor()
                cursor.execute(f'UPDATE rules SET {set_clause} WHERE id = ?', values)
                self.conn.commit()
                return cursor.rowcount > 0
            
        except sqlite3.IntegrityError:
            # 域名冲突
            return False
        except Exception as e:
            with self._lock:
                self.conn.rollback()
            raise Exception(f"更新规则失败: {e}")
    
    def get_all_rules(self, enabled_only: bool = False) -> List[Dict]:
        """
        获取所有规则
        
        Args:
            enabled_only: 是否只获取启用的规则
            
        Returns:
            List[Dict]: 规则列表
        """
        try:
            with self._lock:
                cursor = self.conn.cursor()
                
                if enabled_only:
                    cursor.execute('SELECT * FROM rules WHERE enabled = 1 ORDER BY created_at DESC')
                else:
                    cursor.execute('SELECT * FROM rules ORDER BY created_at DESC')
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
            
        except Exception as e:
            raise Exception(f"获取规则列表失败: {e}")
    
    def get_rule_by_domain(self, domain: str) -> Optional[Dict]:
        """
        按域名查询规则
        
        Args:
            domain: 域名
            
        Returns:
            Optional[Dict]: 规则信息，不存在则返回 None
        """
        try:
            with self._lock:
                cursor = self.conn.cursor()
                cursor.execute('SELECT * FROM rules WHERE domain = ?', (domain,))
                row = cursor.fetchone()
            
            return dict(row) if row else None
            
        except Exception as e:
            raise Exception(f"查询规则失败: {e}")
    
    def enable_rule(self, rule_id: str) -> bool:
        """
        启用规则
        
        Args:
            rule_id: 规则ID
            
        Returns:
            bool: 是否成功
        """
        return self.update_rule(rule_id, enabled=1)
    
    def disable_rule(self, rule_id: str) -> bool:
        """
        禁用规则
        
        Args:
            rule_id: 规则ID
            
        Returns:
            bool: 是否成功
        """
        return self.update_rule(rule_id, enabled=0)
    
    def batch_add_rules(self, rules_list: List[Dict]) -> Tuple[int, List[str]]:
        """
        批量添加规则
        
        Args:
            rules_list: 规则列表，每个元素包含 domain, redirect_to, remark
            
        Returns:
            Tuple[int, List[str]]: (成功数量, 失败域名列表)
        """
        success_count = 0
        failed_domains = []
        
        try:
            with self._lock:
                cursor = self.conn.cursor()
                
                for rule in rules_list:
                    domain = rule.get('domain')
                    redirect_to = rule.get('redirect_to', '127.0.0.1')
                    remark = rule.get('remark', '')
                    
                    if not validate_domain(domain):
                        failed_domains.append(domain)
                        continue
                    
                    if not self._is_valid_ip(redirect_to):
                        failed_domains.append(domain)
                        continue
                    
                    rule_id = str(uuid.uuid4())
                    now = datetime.now().isoformat()
                    
                    try:
                        cursor.execute('''
                            INSERT INTO rules (id, domain, redirect_to, remark, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (rule_id, domain, redirect_to, remark, now, now))
                        success_count += 1
                        
                    except sqlite3.IntegrityError:
                        # 域名已存在
                        failed_domains.append(domain)
                    except Exception:
                        failed_domains.append(domain)
                
                self.conn.commit()
            
        except Exception as e:
            with self._lock:
                self.conn.rollback()
            raise Exception(f"批量添加规则失败: {e}")
        
        return success_count, failed_domains
    
    def batch_delete(self, rule_ids: List[str]) -> int:
        """
        批量删除规则
        
        Args:
            rule_ids: 规则ID列表
            
        Returns:
            int: 成功删除的数量
        """
        if not rule_ids:
            return 0
        
        try:
            with self._lock:
                cursor = self.conn.cursor()
                
                # 使用参数化查询，构建 IN 子句
                placeholders = ','.join(['?'] * len(rule_ids))
                cursor.execute(f'DELETE FROM rules WHERE id IN ({placeholders})', rule_ids)
                
                deleted_count = cursor.rowcount
                self.conn.commit()
            
            return deleted_count
            
        except Exception as e:
            with self._lock:
                self.conn.rollback()
            raise Exception(f"批量删除规则失败: {e}")
    
    def batch_enable(self, rule_ids: List[str]) -> int:
        """
        批量启用规则
        
        Args:
            rule_ids: 规则ID列表
            
        Returns:
            int: 成功启用的数量
        """
        return self._batch_update_enabled(rule_ids, enabled=1)
    
    def batch_disable(self, rule_ids: List[str]) -> int:
        """
        批量禁用规则
        
        Args:
            rule_ids: 规则ID列表
            
        Returns:
            int: 成功禁用的数量
        """
        return self._batch_update_enabled(rule_ids, enabled=0)
    
    def clear_all_rules(self) -> int:
        """
        清空所有规则
        
        Returns:
            int: 删除的规则数量
        """
        try:
            with self._lock:
                cursor = self.conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM rules')
                count = cursor.fetchone()[0]
                
                cursor.execute('DELETE FROM rules')
                self.conn.commit()
            
            return count
            
        except Exception as e:
            with self._lock:
                self.conn.rollback()
            raise Exception(f"清空规则失败: {e}")
    
    def get_rule_count(self, enabled_only: bool = False) -> int:
        """
        获取规则数量
        
        Args:
            enabled_only: 是否只统计启用的规则
            
        Returns:
            int: 规则数量
        """
        try:
            with self._lock:
                cursor = self.conn.cursor()
                
                if enabled_only:
                    cursor.execute('SELECT COUNT(*) FROM rules WHERE enabled = 1')
                else:
                    cursor.execute('SELECT COUNT(*) FROM rules')
                
                return cursor.fetchone()[0]
            
        except Exception as e:
            raise Exception(f"获取规则数量失败: {e}")
    
    def import_from_file(self, file_path: str) -> Tuple[int, List[str]]:
        """
        从文件导入规则（支持 TXT 和 CSV）
        
        Args:
            file_path: 文件路径
            
        Returns:
            Tuple[int, List[str]]: (成功数量, 失败域名列表)
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        rules_list = []
        
        # 根据文件扩展名选择解析方式
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == '.txt':
            # TXT 文件：每行一个域名
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    domain = line.strip()
                    if domain and not domain.startswith('#'):  # 忽略空行和注释
                        rules_list.append({'domain': domain})
        
        elif ext == '.csv':
            # CSV 文件：domain,redirect_to,remark
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    rules_list.append({
                        'domain': row.get('domain', '').strip(),
                        'redirect_to': row.get('redirect_to', '127.0.0.1').strip(),
                        'remark': row.get('remark', '').strip()
                    })
        else:
            raise ValueError(f"不支持的文件格式: {ext}")
        
        # 批量添加
        return self.batch_add_rules(rules_list)
    
    def export_to_file(self, file_path: str, rule_ids: Optional[List[str]] = None) -> bool:
        """
        导出规则到文件
        
        Args:
            file_path: 文件路径
            rule_ids: 要导出的规则ID列表，None 表示导出所有
            
        Returns:
            bool: 是否成功
        """
        try:
            # 获取规则数据
            with self._lock:
                if rule_ids:
                    # 获取指定规则
                    cursor = self.conn.cursor()
                    placeholders = ','.join(['?'] * len(rule_ids))
                    cursor.execute(f'''
                        SELECT domain, redirect_to, remark, enabled 
                        FROM rules 
                        WHERE id IN ({placeholders})
                        ORDER BY created_at DESC
                    ''', rule_ids)
                    rows = cursor.fetchall()
                    rules = [dict(row) for row in rows]
                else:
                    # 获取所有规则
                    cursor = self.conn.cursor()
                    cursor.execute('SELECT * FROM rules ORDER BY created_at DESC')
                    rows = cursor.fetchall()
                    rules = [dict(row) for row in rows]
            
            # 根据文件扩展名选择导出格式
            ext = os.path.splitext(file_path)[1].lower()
            
            if ext == '.txt':
                # TXT 文件：每行一个域名
                with open(file_path, 'w', encoding='utf-8') as f:
                    for rule in rules:
                        if rule.get('enabled', 1):
                            f.write(f"{rule['domain']}\n")
            
            elif ext == '.csv':
                # CSV 文件：domain,redirect_to,remark,enabled
                with open(file_path, 'w', encoding='utf-8', newline='') as f:
                    fieldnames = ['domain', 'redirect_to', 'remark', 'enabled']
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    
                    writer.writeheader()
                    for rule in rules:
                        writer.writerow({
                            'domain': rule.get('domain', ''),
                            'redirect_to': rule.get('redirect_to', '127.0.0.1'),
                            'remark': rule.get('remark', ''),
                            'enabled': rule.get('enabled', 1)
                        })
            else:
                raise ValueError(f"不支持的文件格式: {ext}")
            
            return True
            
        except Exception as e:
            raise Exception(f"导出规则失败: {e}")
    
    def _batch_update_enabled(self, rule_ids: List[str], enabled: int) -> int:
        """
        批量更新启用状态（内部方法）
        
        Args:
            rule_ids: 规则ID列表
            enabled: 启用状态（0或1）
            
        Returns:
            int: 成功更新的数量
        """
        if not rule_ids:
            return 0
        
        try:
            with self._lock:
                cursor = self.conn.cursor()
                now = datetime.now().isoformat()
                
                # 使用参数化查询，构建 IN 子句
                placeholders = ','.join(['?'] * len(rule_ids))
                cursor.execute(f'''
                    UPDATE rules 
                    SET enabled = ?, updated_at = ? 
                    WHERE id IN ({placeholders})
                ''', (enabled, now, *rule_ids))
                
                updated_count = cursor.rowcount
                self.conn.commit()
            
            return updated_count
            
        except Exception as e:
            with self._lock:
                self.conn.rollback()
            raise Exception(f"批量更新状态失败: {e}")
    
    def _is_valid_ip(self, ip: str) -> bool:
        """
        验证 IP 地址格式（内部方法）
        
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
    
    def close(self):
        """关闭数据库连接"""
        with self._lock:
            if self.conn:
                self.conn.close()
                self.conn = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


if __name__ == "__main__":
    # 测试代码
    manager = RuleManager()
    
    print("数据库路径:", manager.db_path)
    
    # 添加测试规则
    test_rules = [
        {"domain": "example.com", "remark": "测试网站1"},
        {"domain": "test.org", "redirect_to": "0.0.0.0", "remark": "测试网站2"},
    ]
    
    success, failed = manager.batch_add_rules(test_rules)
    print(f"批量添加结果: 成功 {success} 个, 失败 {failed}")
    
    # 获取所有规则
    rules = manager.get_all_rules()
    print(f"共有 {len(rules)} 条规则:")
    
    for rule in rules:
        print(f"  {rule['domain']} -> {rule['redirect_to']} ({'启用' if rule['enabled'] else '禁用'})")
    
    manager.close()