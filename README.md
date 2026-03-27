# SafeRoot - Windows Hosts 文件管理工具
<img width="902" height="732" alt="image" src="https://github.com/user-attachments/assets/a7c9680b-3c86-41b2-91f0-744754d9eeb8" />
<img width="902" height="732" alt="image" src="https://github.com/user-attachments/assets/de21124e-2aa7-4487-84e9-06f3935d3704" />

## 项目简介

SafeRoot 是一款开源的 Windows hosts 文件管理桌面工具。用户可以通过直观的图形界面管理域名解析规则，实现网站屏蔽、重定向等功能。

**重要声明：本程序为通用工具，不包含任何预设屏蔽地址或针对特定网站/软件的规则。所有屏蔽规则均由用户自行添加。**

## 功能特性

- 管理 hosts 文件，屏蔽或重定向指定域名
- 单条/批量添加屏蔽规则，支持从 URL 自动提取域名
- 规则启用、禁用、删除，支持批量操作
- hosts 文件备份与一键恢复
- 批量导入/导出规则（TXT / CSV）
- 写入 hosts 后自动刷新 DNS 缓存，规则立即生效
- 自动检测并请求管理员权限
- 可配置开机自启动
- 完整操作日志记录
# 更新日志

所有重要更改均会记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

---

## [1.1.0] - 2026-03-26

### 修复

#### 屏蔽核心失效问题（严重）

- **[严重] 修复本地代理/加速器导致 hosts 屏蔽完全失效的问题**
  - **根因**：默认重定向地址 `127.0.0.1` 会被本地代理/加速器（如 Steam++ 加速器）
    监听的 `0.0.0.0:80` 和 `0.0.0.0:443` 端口接收，浏览器连接到本地代理后由代理
    转发到真实服务器，屏蔽被完全绕过。
  - **修复**：将默认重定向地址从 `127.0.0.1` 改为 `0.0.0.0`。`0.0.0.0` 作为客户端
    目标地址时无效（`[WinError 10049] 地址无效`），连接会立即失败，不受本地代理影响。
  - **影响文件**：`hosts_manager.py`、`add_rule_dialog.py`、`main_window.py`
  - **自动迁移**：程序启动时自动将数据库中已有 `127.0.0.1` 的规则迁移为 `0.0.0.0`
    并同步更新 hosts 文件。

- **[严重] 修复防火墙规则从未创建成功的问题（Python 3.8 编码崩溃）**
  - **根因**：`subprocess.run(text=True)` 在 Python 3.8 + 中文 Windows 环境下，
    `netsh` 命令输出包含中文字符，subprocess 内部线程用 GBK 解码时触发
    `UnicodeDecodeError`，进而导致 `IndexError: list index out of range`，
    防火墙规则创建/删除/查询全部静默失败。
  - **修复**：新增 `_run_cmd()` 安全命令执行函数，使用二进制模式读取输出后
    手动以 UTF-8 解码（`errors='replace'`），所有 `netsh` 调用统一改用该函数。
  - **影响文件**：`firewall_manager.py`

- **[严重] 修复 DNS 解析无法获取真实 IP 的问题（nslookup 中文乱码）**
  - **根因**：`resolve_domain()` 通过 nslookup 输出中的 "名称:" 行定位地址，
    但中文 Windows 的 nslookup 输出经 UTF-8 解码后变成乱码（实际为 GBK 编码），
    正则表达式 `^(name|名称)\s*:` 无法匹配，导致地址行被跳过，返回空 IP 列表。
  - **修复**：改为使用 `nslookup domain 114.114.114.114`（指定公共 DNS 服务器
    直接查询，完全绕过 hosts 文件），然后用正则从整个输出中提取所有 IPv4 地址，
    排除本地回环地址和 DNS 服务器自身 IP。
  - **影响文件**：`firewall_manager.py`

- **[严重] 修复 DNS 缓存服务不稳定问题**
  - **根因**：`_flush_dns()` 中执行 `net stop/start Dnscache` 重启 DNS 缓存服务，
    在 Windows 10/11 上因依赖服务（如 iphlpsvc）经常失败，可能导致 DNS 服务
    进入不稳定状态。同时写入的 `NV HostsFilePriority` 注册表值非 Windows 标准，
    无任何实际效果。
  - **修复**：移除 DNS 服务重启操作和无效注册表值，改为执行两次
    `ipconfig /flushdns` 确保缓存刷新，仅保留有效的 `DisableParallelAandAAAA` 注册表项。
  - **影响文件**：`hosts_manager.py`

#### 防火墙同步缺失问题

- **[重要] 修复批量导入路径无防火墙保护的问题**
  - `sync_hosts_with_db()` 原来只写入 hosts 文件，不创建防火墙规则，
    批量导入的域名仅靠 hosts 单层防护，DoH 开启时完全失效。现已同步防火墙规则。
  - **影响文件**：`main_window.py` (`sync_hosts_with_db`)

- **[重要] 修复清空所有规则后防火墙规则残留的问题**
  - `on_clear_all()` 清空数据库和 hosts 后，防火墙规则仍存在，导致已删除的域名
    仍被阻断。现已添加 `firewall_manager.cleanup_all()` 清理。
  - **影响文件**：`main_window.py` (`on_clear_all`)

- **[重要] 修复启用/禁用规则时未同步防火墙的问题**
  - `on_toggle_rule()` 启用规则时未创建防火墙阻断规则，禁用规则时未移除防火墙规则。
  - **影响文件**：`main_window.py` (`on_toggle_rule`)

- **[重要] 修复 hosts 重置为默认时防火墙规则未清理的问题**
  - **影响文件**：`main_window.py` (`on_hosts_reset_to_default`)

#### IPv6 绕过问题

- **[重要] 修复 IPv6 连接绕过 hosts 屏蔽的问题**
  - hosts 文件原来只添加 IPv4 条目（`127.0.0.1 domain`），未添加 IPv6 条目。
    当浏览器优先使用 IPv6 时，DNS 返回 AAAA 记录的真实 IP，绕过 hosts 屏蔽。
  - **修复**：添加规则时同时写入 IPv6 屏蔽条目（`::1 domain` 或 `:: domain`），
    并更新规则匹配正则以支持 IPv6 地址格式。
  - **影响文件**：`hosts_manager.py`（`RULE_PATTERN`、`add_rule`、`remove_rule`）

### 新增

- 启动时自动同步防火墙规则与数据库状态，确保一致性
  （防止意外删除或服务重启导致防火墙规则丢失）
- 启动时自动检测并迁移旧版 `127.0.0.1` 重定向规则为 `0.0.0.0`
- `resolve_domain()` 支持 IPv6 (AAAA) 记录解析，防火墙规则同时阻断 IPv4 和 IPv6
- `resolve_domain()` 支持指定公共 DNS 服务器直接查询（114.114.114.114 / 223.5.5.5 / 8.8.8.8）

### 技术细节

- 新增 `_run_cmd()` 安全命令执行函数，统一处理 subprocess 编码问题
- `resolve_domain()` 使用三级 DNS 解析策略：公共 DNS nslookup → socket IPv4 → socket IPv6
- 默认重定向地址 `0.0.0.0` 对应 IPv6 `::`，保证 IPv4/IPv6 双栈一致性

---

## [1.0.0] - 2026-03-26

### 新增
- 初始版本发布
- 基于 PyQt5 的图形用户界面
- hosts 文件安全管理（原子写入，防止数据损坏）
- 规则管理（添加、删除、启用、禁用、批量操作）
- 单条/批量添加屏蔽规则，支持从 URL 自动提取域名
- hosts 文件备份与恢复功能
- 批量导入/导出规则（支持 TXT 和 CSV 格式）
- SQLite 数据库存储规则，支持快速查询和管理
- 自动检测并请求管理员权限
- 可配置的开机自启动
- 自动更新检查
- 完整的操作日志记录
- 系统设置页面

### 修复
- **[严重]** 修复设置页中同步 HTTP 更新检查导致 GUI 主线程阻塞无响应的问题，
  将网络请求移至 QThread 后台线程执行。
- **[严重]** 修复 SQLite 数据库在多线程环境下无锁访问可能导致数据损坏或
  死锁的问题，为所有数据库操作添加 `threading.Lock` 同步。
- **[严重]** 修复添加规则时在主线程同步执行数据库写入和 hosts 文件 I/O
  导致 GUI 无响应的问题，新增 `AddRuleWorker` 后台线程处理。
- 修复窗口关闭时未正确等待后台线程退出可能导致资源泄漏的问题。
- 修复 QThread 对象未调用 `deleteLater()` 可能导致内存泄漏的问题。
- 修复批量操作完成后操作名称映射错误（`'disable'` 误映射为 `'delete'`）。
- 修复从 URL 提取域名时错误剥离 `www.` 前缀导致子域名屏蔽失效的问题。
- **[重要]** 修复写入 hosts 文件后未刷新系统 DNS 缓存导致屏蔽规则不立即
  生效的问题，写入后自动执行 `ipconfig /flushdns`。

### 技术细节
- 使用 `threading.Lock()` 保护 SQLite 跨线程访问
- 所有耗时 I/O 操作均通过 QThread 后台线程执行，通过信号/槽与 GUI 通信
- hosts 文件写入采用原子操作（临时文件 + `os.replace`）
- 管理员权限通过 Windows Shell API (`IsUserAnAdmin` / `ShellExecuteW`) 检测和请求

---

## [Unreleased]

### 计划中
- PyInstaller 打包为独立可执行文件
- 规则分组/标签功能
- 定时启用/禁用规则（日程管理）
- 多语言支持（英文界面）
- 系统托盘最小化
- 从在线规则源订阅/更新规则
## 系统要求

- Windows 7 / 8 / 10 / 11（64 位）
- 管理员权限（运行时需要）

## 安装与运行

### 方法一：直接运行 EXE（免安装，小白推荐）

直接双击 **`dist\SafeRoot.exe`** 即可运行，无需安装 Python 或任何依赖。

> 开发者可通过运行 **`打包为EXE.bat`** 重新生成 EXE 文件。

### 方法二：一键脚本安装

1. 确保电脑已安装 [Python 3.6+](https://www.python.org/downloads/)（安装时勾选 **Add Python to PATH**）
2. 双击运行 **`安装并启动.bat`**，脚本会自动完成以下操作：
   - 检测 Python 环境
   - 安装所需依赖
   - 启动程序（自动请求管理员权限）
3. （可选）双击 **`创建桌面快捷方式.bat`**，在桌面生成快捷方式图标

### 方法三：命令行安装

```bash
# 1. 克隆项目
git clone <repo-url>
cd 屏蔽器

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行（需管理员权限）
python main.py
```

## 使用说明

1. **添加屏蔽规则**：在"屏蔽列表"页点击"添加网址"，输入域名或完整 URL，确认即可。
2. **管理规则**：通过复选框选择规则，可批量启用、禁用或删除。
3. **备份恢复**：在"备份管理"页可创建、恢复或删除 hosts 文件备份。
4. **系统设置**：在"系统设置"页可配置自启动、更新检查等选项。

## 项目结构

```
SafeRoot/
├── main.py                 # 应用程序入口（管理员权限检测）
├── constants.py            # 常量定义
├── requirements.txt        # Python 依赖
├── 打包为EXE.bat            # 一键打包为独立 EXE（免 Python 运行）
├── 安装并启动.bat            # 一键安装依赖并启动程序
├── 启动SafeRoot.bat          # 静默启动（无命令行窗口）
├── 创建桌面快捷方式.bat       # 在桌面创建快捷方式
├── LICENSE                 # MIT 开源协议 + 法律免责声明
├── CHANGELOG.md            # 开发日志
├── README.md               # 项目说明
├── .gitignore              # Git 忽略规则
└── src/
    ├── __init__.py
    ├── core/
    │   ├── __init__.py
    │   ├── hosts_manager.py   # hosts 文件读写管理
    │   ├── rule_manager.py    # 规则数据库管理（SQLite）
    │   └── logger.py          # 日志模块
    └── ui/
        ├── __init__.py
        ├── main_window.py     # 主窗口
        ├── add_rule_dialog.py # 添加规则对话框
        ├── backup_tab.py      # 备份管理标签页
        └── settings_tab.py    # 系统设置标签页

## 免责声明

1. **本程序为通用 hosts 文件管理工具**，不包含任何预设的屏蔽地址、黑名单或针对特定网站/软件的规则。程序中所有屏蔽规则均由用户自行输入和添加。

2. **本程序未恶意针对任何网站、软件、企业或个人。** 程序的用途完全取决于用户自身的选择和行为。

3. 用户应确保其使用本程序的行为符合所在地区的法律法规。因用户不当使用本程序而产生的一切法律后果，均由用户自行承担。

4. 修改系统 hosts 文件可能影响网络功能，用户应在充分了解后果并做好备份后使用。

5. 本程序以 MIT 协议开源发布，仅供学习和合法用途使用。详见 [LICENSE](LICENSE)。

## 许可证

[MIT License](LICENSE)
