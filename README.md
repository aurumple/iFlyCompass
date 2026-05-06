# iFlyCompass

## 项目简介

**版本：REL2.5.2**

iFlyCompass 是一个多功能的 Web 应用平台，采用模块化架构设计，提供了多种实用工具和功能，包括：

- **网页代理**：基于 mitmproxy 的反向代理工具，支持 URL 重写、请求头修正、Service Worker + Hook 双模式拦截
  - **双层拦截机制**：Service Worker（底层拦截所有网络请求）+ Hook 模式（API 层拦截）
  - **智能 URL 重写**：统一格式 `http://{proxy}:{port}/{protocol}/{host}/{path}`
  - **Next.js 兼容**：自动替换 `__webpack_public_path__`、处理 `self.__next_f.push` 动态加载
  - **请求头修正**：自动推断并设置正确的 Origin/Referer，解决 403 Forbidden
  - **全面资源覆盖**：HTML/CSS/JS/图片/音频/视频/字体等所有静态资源
- **聊天室功能**：支持创建、加入、管理聊天室，实时消息通信，多人优化模式
- **小说阅读器**：整本书缓存架构，本地/云端双列表，断点续传，浏览器端章节解析，完全离线阅读
  - **沉浸式阅读器**：与小说阅读器融合，浏览器端无缝切换，主题切换、翻页动画、分页引擎
- **随身听**：网易云音乐播放器，支持搜索、推荐歌单、音乐播放（内网缓存）
- **视频播放器**：本地视频播放，支持多种格式，Plyr 播放器，Element UI 风格
- **B站视频**：B站视频缓存与播放，支持首页推荐、搜索视频、搜索UP主，480P画质
- **表情包管理**：表情商城、个人收藏、表情包合集管理
- **公告系统**：横幅公告、通知公告、公告中心，支持多优先级和权限管理
- **Drop 功能**：向所有用户发送 Drop 消息，支持黑名单管理
- **用户管理**：支持用户注册、登录、权限管理
- **Passkey 管理**：支持生成和管理注册邀请码
- **手势防御**：防御层 5 技术，防止宿主 App 全局手势劫持页面滚动
- **系统设置**：管理员可配置首页显示、昵称设置、导航栏、密码强度、安全问题等
- **导航配置**：支持通过 nav.yml 自定义添加小工具/小游戏导航项

## 技术栈

- **前端**：Vue.js 2.x、Element UI、Socket.IO 客户端
- **后端**：Flask 3.x、Python 3.8+
- **数据库**：SQLAlchemy ORM + SQLite
- **实时通信**：Flask-SocketIO
- **认证**：Flask-Login
- **架构**：Flask Blueprint 模块化设计
- **配置**：YAML 配置文件（`instance/config.yml`）
- **代理引擎**：mitmproxy（网页代理功能）

## 架构特点

### 模块化设计

项目采用 Flask Blueprint 进行模块化设计，每个业务领域独立成模块：

- **models/** - 数据库模型层
- **utils/** - 工具函数层
- **modules/** - 业务模块层
  - **auth/** - 用户认证模块
  - **chat/** - 聊天室模块
  - **novel/** - 小说阅读器模块
  - **sticker/** - 表情包管理模块
  - **ncm/** - 随身听模块（网易云音乐）
  - **video/** - 视频播放器模块
  - **bili/** - B站视频模块
  - **proxy/** - 网页代理模块（mitmproxy 反向代理）
  - **main/** - 主页面模块
  - **settings/** - 系统设置模块
  - **announcement/** - 公告系统模块

### 单一职责原则

每个模块专注于单一业务领域，代码结构清晰，易于维护和扩展。

### 高内聚低耦合

模块之间通过清晰的接口进行通信，降低了代码的耦合度，提高了可测试性。

## 功能特点

### 聊天室功能

- 支持创建带密码和不带密码的聊天室
- 实时消息通信，支持多人聊天
- 显示在线用户列表
- 聊天消息历史记录（最近20条）
- 聊天室管理（编辑、删除）
- 表情包功能：支持添加、使用和管理表情包
  - 表情商城：浏览和添加公开表情包
  - 表情包管理：管理已添加的表情包
  - 支持单个表情和表情合集
  - 本地缓存表情包，无需网络连接

### 小说阅读器

- **整本书缓存架构（v2）**：一次性缓存整本 .txt 文件到浏览器 IndexedDB，支持完全离线阅读
- **本地/云端双列表**：本地列表显示已缓存的书（服务端关闭也能读），云端列表显示服务端存放的书
- **下载进度条**：显示总文件大小和已缓存大小，支持 HTTP Range 断点续传
- **更新检测**：服务端文件更新时提示用户（是/否/不再提示），支持手动更新
- **浏览器端章节解析**：`assets/js/chapter-parser.js`，支持中文数字章节、阿拉伯数字、英文章节、特殊章节
- **本地阅读进度**：进度存储在浏览器 IndexedDB，无需服务端同步
- **智能章节解析**（服务端元数据扫描）：V3.1 锚点学习 + 统计验证算法，五阶段检测
- **启动时预扫描缓存**：启动时扫描所有小说，缓存书名、作者、最新章节
- **沉浸式阅读模式**（与小说阅读器融合，浏览器端无缝切换）：
  - 主题选择：日间 5 种主题 + 夜间 2 种主题
  - 日间/夜间模式一键切换
  - 翻页动画：滑动、滚动、淡入淡出、无动画
  - 双层页面结构，动画过程可见两页
  - 设置自动保存到本地存储

### 随身听

- **网易云音乐播放器**：搜索、推荐歌单、热门搜索
- **内网缓存播放**：音乐文件先缓存到本地，用户浏览器不直接访问外网
- **APlayer 播放器**：本地化部署，无需外网 CDN
- 支持歌词显示、播放列表管理
- 与聊天室、小说阅读器保持一致的设计风格

### 用户系统

- 用户注册和登录
- 基于 Passkey 的注册邀请机制
- 权限管理（普通用户、管理员、超级管理员）
- 永久会话（除非被其他终端顶号）

### 其他功能

- 必应每日壁纸展示
- 每日诗词推荐
- 响应式设计，支持移动端

## 安装和运行

### 环境要求

- Python 3.8 或更高版本
- pip 包管理工具

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行项目

```bash
python app.py
```

项目将在 `http://127.0.0.1:5002` 上运行（主应用），网页代理服务将在 `http://127.0.0.1:5003` 上运行。

### 打包为 EXE

```bash
pyinstaller --onefile --name iFlyCompass app.py
```

## 项目结构

```
iFlyCompass/
├── app.py                    # 应用入口
├── config.py                 # 配置管理（从 YAML 读取）
├── extensions.py             # Flask 扩展初始化
├── models/                   # 数据库模型层
│   ├── __init__.py
│   ├── user.py              # User, Passkey 模型
│   ├── chat.py              # ChatRoom 模型
│   ├── sticker.py           # UserSticker, PackSticker 模型
│   ├── announcement.py      # Announcement, UserAnnouncementStatus 模型
│   └── drop.py              # DropMessage, DropSettings, DropBlacklist 模型
├── utils/                    # 工具函数层
│   ├── __init__.py
│   ├── common.py            # 通用工具函数
│   ├── file.py              # 文件处理工具
│   ├── chapter_parser.py    # 章节解析器（V3.1算法）
│   ├── novel_cache.py       # 小说缓存服务
│   ├── music_cache.py       # 音乐缓存服务
│   ├── ncm_api.py           # 网易云音乐 API 客户端（NCMAPIClient）
│   ├── system_settings.py   # 系统设置工具
│   ├── validators.py        # 验证工具
│   └── nav.py               # 导航配置工具
├── modules/                  # 业务模块层
│   ├── auth/                # 用户认证模块
│   │   ├── __init__.py
│   │   ├── routes.py        # 认证相关路由
│   │   └── api.py           # 用户管理 API
│   ├── chat/                # 聊天室模块
│   │   ├── __init__.py
│   │   ├── routes.py        # 聊天室路由
│   │   ├── api.py           # 聊天室 API
│   │   └── websocket.py     # WebSocket 事件处理
│   ├── novel/               # 小说阅读器模块
│   │   ├── __init__.py
│   │   ├── routes.py        # 小说阅读器路由
│   │   └── api.py           # 小说文件流 API（整本书缓存模式）
│   ├── sticker/             # 表情包管理模块
│   │   ├── __init__.py
│   │   ├── routes.py        # 表情包路由
│   │   └── api.py           # 表情包 API
│   ├── ncm/                 # 随身听模块
│   │   ├── __init__.py
│   │   ├── routes.py        # 播放器路由
│   │   └── api.py           # NCM API
│   ├── video/               # 视频播放器模块
│   │   ├── __init__.py
│   │   ├── routes.py        # 播放器路由
│   │   └── api.py           # 视频 API
│   ├── bili/                # B站视频模块
│   │   ├── __init__.py       # B站视频模块定义
│   │   ├── routes.py         # B站播放器路由
│   │   ├── api.py            # B站 API
│   │   └── download_service.py # B站视频下载服务
│   ├── proxy/                # 网页代理模块
│   │   ├── __init__.py       # 代理模块定义和 Blueprint 注册
│   │   ├── proxy_addon.py    # mitmproxy 插件（URL 重写、请求头修正）
│   │   ├── hook.js           # 浏览器端拦截脚本（Service Worker + Hook）
│   │   ├── proxy_server.py   # 代理服务器管理（启动、停止）
│   │   └── api.py            # 代理控制 API（状态查询、启动停止）
│   ├── main/                # 主页面模块
│   │   ├── __init__.py
│   │   └── routes.py        # 主页面路由
│   ├── settings/            # 系统设置模块
│   │   ├── __init__.py
│   │   ├── routes.py        # 系统设置路由
│   │   └── api.py           # 系统设置 API
│   ├── announcement/        # 公告系统模块
│   │   ├── __init__.py
│   │   ├── routes.py        # 公告页面路由
│   │   └── api.py           # 公告 API
│   └── drop/                # Drop 消息模块
│       ├── __init__.py
│       ├── routes.py        # Drop 设置路由
│       └── api.py           # Drop API
├── assets/                   # 静态资源
│   ├── css/                 # CSS 文件
│   │   └── drop.css         # Drop 样式
│   ├── js/                  # JavaScript 文件
│   │   ├── novel-cache.js       # IndexedDB 小说缓存层（NovelCacheDB v2）
│   │   ├── chapter-parser.js    # 浏览器端章节解析器
│   │   ├── offline-handler.js   # 离线请求降级处理
│   │   ├── drop.js              # Drop 脚本
│   │   └── sw.js                # Service Worker（PWA 离线缓存）
│   ├── icons/               # PWA 图标
│   ├── images/              # 图片文件
│   └── manifest.json        # PWA 清单
├── templates/                # HTML 模板
│   ├── chat.html            # 聊天室页面
│   ├── chat-simple.html     # 简化版聊天页面
│   ├── novel_reader.html    # 小说阅读器（含沉浸式阅读，融合为一体）
│   ├── ncm_player.html      # 随身听页面
│   ├── video_player.html    # 视频播放器页面
│   ├── bili_player.html     # B站视频页面
│   ├── web_proxy.html        # 网页代理工具页面
│   ├── index.html           # 首页
│   ├── login.html           # 登录页面
│   ├── register.html        # 注册页面
│   ├── board.html           # 控制面板页面
│   ├── user_management.html # 用户管理页面
│   ├── passkey_management.html # Passkey 管理页面
│   ├── swipe_test.html      # 滑动测试页面
│   ├── tools.html           # 工具页面
│   ├── system_settings.html # 系统设置页面
│   ├── forgot_password.html # 忘记密码页面
│   ├── announcement_manage.html # 公告管理页面
│   ├── announcement_center.html # 公告中心页面
│   └── drop_settings.html   # Drop 设置页面
├── instance/                 # 数据文件目录
│   ├── config.yml           # 配置文件（YAML格式）
│   ├── nav.yml              # 导航配置文件
│   ├── users.db             # 用户数据库
│   └── novels/              # 小说文件目录
├── stickers/                 # 表情包缓存目录
├── temp/                     # 临时文件目录
│   ├── music/               # 音乐缓存目录
│   │   └── covers/          # 封面缓存目录
│   └── bili/                # B站视频缓存目录
└── requirements.txt          # 依赖文件
```

## 首次使用

1. 启动应用后，访问 `http://127.0.0.1:5002`
2. 点击 "注册" 按钮，创建第一个用户（自动成为超级管理员）
3. 使用创建的账号登录
4. 进入 "Passkey 管理" 页面，生成邀请码
5. 其他用户可以使用邀请码注册

## 开发指南

详细的开发文档请参阅 [DEVELOPMENT.md](DEVELOPMENT.md)。

## 许可证

本项目采用 GNU GPL v3.0 许可证。
