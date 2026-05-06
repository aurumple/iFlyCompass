# iFlyCompass 开发文档

## 版本更新

### REL2.5.2

**mitmproxy 优化 + FFmpeg 恢复**

#### 一、mitmproxy 运行方式优化

- **问题背景**：
  - 本地内置的 mitmdump.exe 内部硬编码了开发环境的 Python 路径
  - 生产环境路径不同，导致无法创建进程
  - 错误：`Fatal error in launcher: Unable to create process`
  - `python -m mitmproxy.tools.dump` 模块方式会立即退出

- **解决方案**：
  - 删除本地内置的 mitmproxy 和所有依赖库（tools/mitmproxy/）
  - 改用系统安装的 mitmproxy（`pip install mitmproxy`）
  - 使用 `mitmdump` 命令直接运行
  - 使用 `CREATE_NEW_CONSOLE` 创建独立的控制台窗口

- **代码变更**：
  - 删除 `_check_local_mitmproxy()` 函数
  - 简化 `_check_mitmproxy()` 只检查系统安装
  - 修改 `start_proxy_server()`：
    * 使用 `mitmdump` 命令
    * 使用 `CREATE_NEW_CONSOLE` 创建新窗口
    * 不重定向 stdout/stderr，让日志显示在独立窗口
    * 移除 `console_eventlog_verbosity` 和 `termlog_verbosity` 参数

- **删除文件**：
  - `tools/mitmproxy/` 目录（包含 mitmdump.exe 和所有依赖库）
  - `tools/install_mitmproxy.py`（安装脚本）
  - `tools/test_mitmproxy.py`（测试脚本）
  - `tools/diagnose_mitmproxy.py`（诊断工具）

- **优势**：
  | 特性 | 说明 |
  |------|------|
  | 进程可见 | 独立窗口显示 mitmproxy 日志 |
  | 易于调试 | 实时查看所有请求和错误 |
  | 代码简洁 | 减少 44 行代码 |
  | 稳定运行 | 使用正确的 mitmdump 命令 |

- **使用方法**：
  ```bash
  # 安装 mitmproxy
  pip install mitmproxy

  # 启动应用
  python app.py

  # mitmproxy 会在独立窗口中运行
  ```

#### 二、FFmpeg 恢复

- **问题**：
  - 之前误删了整个 tools/ 目录
  - 导致 ffmpeg.exe 和 ffprobe.exe 丢失
  - B站视频缓存功能无法使用

- **修复**：
  - 从 Git 历史恢复 `tools/ffmpeg/` 目录
  - 恢复 ffmpeg.exe 和 ffprobe.exe

#### 三、代码简化

- **proxy_server.py**：
  - 从 233 行减少到 189 行
  - 删除本地内置相关的所有逻辑
  - 删除 PYTHONPATH 设置
  - 删除复杂的路径查找

- **.gitignore**：
  - 删除 mitmproxy 相关注释

### REL2.5.1_fix1

**mitmproxy 本地内置 + 跨平台 FFmpeg 支持**

#### 一、mitmproxy 完全本地内置

- **问题背景**：
  - 网页代理功能依赖系统安装的 mitmproxy，部署时需要额外配置
  - 不同环境的 mitmproxy 版本可能导致兼容性问题
  - 目标机器可能没有安装 mitmproxy 或权限不足
- **新增 `tools/mitmproxy/` 目录**：
  - 完整内置 mitmproxy 可执行文件（mitmdump.exe）
  - 内置所有依赖库（28个包，约 30-50MB）到 `tools/mitmproxy/libs/`
  - 包含：aioquic, cryptography, OpenSSL, flask, tornado, h2, h11 等
- **新增工具脚本**：
  - `tools/install_mitmproxy.py` — 一键安装脚本，从 Python 环境复制所有依赖
    - 自动检测 site-packages 路径
    - 智能处理不同包名变体（如 pyOpenSSL → OpenSSL）
    - 创建启动器（.bat/.sh）和版本信息文件
  - `tools/test_mitmproxy.py` — 测试脚本，验证本地 mitmproxy 是否可用
    - 检查可执行文件是否存在
    - 验证依赖库完整性
    - 测试 mitmdump 运行和模块导入
  - `tools/mitmproxy/run_mitmdump.bat` — Windows 启动器（自动设置 PYTHONPATH）
- **修改 `modules/proxy/proxy_server.py`**：
  - 新增 `_get_local_mitmdump_path()` — 检测本地内置的 mitmdump 路径
  - 重构 `_find_mitmdump()` — 返回 `(路径, 是否为本地版本)` 元组
  - 修改 `start_proxy_server()` — 使用本地版本时自动设置 PYTHONPATH
  - **查找优先级**：本地内置 → 系统 Python Scripts → PATH 环境变量
- **架构优势**：
  | 特性 | 说明 |
  |------|------|
  | 完全自包含 | 不依赖系统安装的 mitmproxy |
  | 版本锁定 | 使用固定版本的依赖，避免兼容性问题 |
  | 零配置 | 自动检测并使用本地版本 |
  | 向后兼容 | 如果本地版本不存在，自动回退到系统版本 |
  | 易于维护 | 提供安装/测试脚本，一键重建 |
- **变更文件**：
  - **新增**：`tools/install_mitmproxy.py`, `tools/test_mitmproxy.py`
  - **新增**：`tools/mitmproxy/` （完整目录结构及 README.md）
  - **修改**：`modules/proxy/proxy_server.py` （优先使用本地版本 + PYTHONPATH 设置）
  - **修改**：`.gitignore` （添加 mitmproxy 相关注释）
- **使用方法**：
  ```bash
  # 安装（首次或更新时）
  python tools/install_mitmproxy.py

  # 测试
  python tools/test_mitmproxy.py

  # 正常使用（自动检测）
  python app.py  # 网页代理会自动使用本地 mitmproxy
  ```

#### 二、跨平台 FFmpeg 支持

- **问题背景**：
  - 项目捆绑的 FFmpeg 为 Windows 可执行文件（`tools/ffmpeg/ffmpeg.exe`），Linux 无法使用
  - `modules/bili/download_service.py` 硬编码 `.exe` 路径，Linux 上 B站视频缓存功能不可用
- **新增 `utils/ffmpeg.py` 工具模块**：
  - `get_ffmpeg_path()` — 跨平台 FFmpeg 路径解析，检查顺序：捆绑二进制 → 系统 PATH
  - `get_ffprobe_path()` — 同上，用于 FFprobe
  - `ensure_ffmpeg()` — 统一入口，找不到时在 Linux/macOS 上自动下载静态构建
  - `_download_ffmpeg_linux()` — 从 `johnvansickle.com` 下载静态 FFmpeg（~40MB tar.xz），解压到 `tools/ffmpeg/`
  - `verify_ffmpeg()` — 验证 FFmpeg 可执行性并返回版本
- **路径规则**：
  | 平台 | 捆绑路径 | 回退 |
  |------|---------|------|
  | Windows | `tools/ffmpeg/ffmpeg.exe` | `shutil.which('ffmpeg')` |
  | Linux | `tools/ffmpeg/ffmpeg` | `shutil.which('ffmpeg')` → 自动下载 |
  | macOS | `tools/ffmpeg/ffmpeg` | `shutil.which('ffmpeg')` → 自动下载 |
- **变更文件**：
  - **新增**：`utils/ffmpeg.py`
  - **修改**：`modules/bili/download_service.py`（`check_ffmpeg()` 改用 `ensure_ffmpeg()`，移除硬编码路径和冗余代码）
  - **修改**：`utils/__init__.py`（导出 FFmpeg 工具函数）
  - **更新**：`.gitignore`（忽略 Linux/macOS 捆绑二进制和下载缓存）
- **行为变化**：
  - Windows：行为不变，仍然使用捆绑的 `ffmpeg.exe`
  - Linux/macOS：首次运行 B站功能时自动下载 FFmpeg（如系统未安装），后续直接使用

### REL2.5.1

**Bug 修复**

- **注册页面闪存消息缺失**：
  - 注册失败时 `flash()` 的错误消息无法显示
  - `templates/register.html` 缺少 `{% with messages = get_flashed_messages() %}` 块
  - 修复：在注册表单前添加 flash 消息渲染块（与 login.html 一致）
  - 现在「无效的Passkey」「密码必须包含数字」等错误正确显示在注册页面
- **登录后 `next` 参数被忽略**：
  - `login()` 路由始终重定向到 `main.board`，忽略 `?next=` 参数
  - 例如 `/login?next=%2Fboard%2Fsettings` 登录后会跳转到 `/board` 而非 `/board/settings`
  - 修复三处：
    - `routes.py` login() POST：读取 `next` 表单字段，校验为相对路径后重定向
    - `routes.py` login() GET：读取 `next` 查询参数并传入模板
    - `templates/login.html`：添加隐藏字段 `<input type="hidden" name="next" value="{{ next }}">`
  - 安全防护：校验 `next` 以 `/` 开头且不以 `//` 开头，防止开放重定向攻击

**小说模块 v2 重构（整本书缓存架构）**

- **重构目标**：将小说阅读从章节级缓存升级为整本书缓存，实现完全的离线阅读能力
- **小说列表重构**：
  - 拆分为**本地列表**（IndexedDB 中已缓存的书，服务端关闭也能读）和**云端列表**（服务端存放的书）
  - 云端列表提供**刷新按钮**，通知服务端扫描小说目录
  - 即使服务端删除小说文件，浏览器端本地列表保留已缓存的书
- **缓存方式重构**：
  - 不再逐章缓存，改为**一次性缓存整本书**（原始 `.txt` 文件），然后浏览器端解析章节
  - 下载时显示**缓存进度条**（总文件大小 / 已缓存大小）
  - 支持 **HTTP Range 断点续传**：下载中断后自动从断点继续
  - 若检测到服务端文件更新，提示用户是否更新（**是 / 否 / 不再提示**），点击「不再提示」后仍可手动点击更新按钮
- **阅读进度**：
  - 移除服务端 `NovelReadingProgress` 模型，进度全部存储在浏览器 IndexedDB 中
  - 不再需要云端阅读进度同步
- **服务端 API 变更**：
  - 新增：`GET /api/novels/<name>/info` — 返回文件大小、修改时间、编码
  - 新增：`GET /api/novels/<name>/file` — 流式传输原始文件（支持 Range）
  - 移除：`GET /api/novels/<name>/chapters`、`/chapters/<index>`、`/download-all`、`/progress`（GET+POST）
  - `GET /api/novels` 返回简化（仅云端列表元数据）
- **IndexedDB 重构**（NovelCacheDB v2）：
  - `novelFiles` store：存储整本书原始字节和解码文本、文件大小、编码、服务端修改时间
  - `readingProgress` store：本地阅读进度（章节索引、滚动位置）
  - `userSettings` store：用户设置（跳过更新提示等）
  - 移除旧的 `chapterLists`、`chapterContents` stores（v1）
- **浏览器端章节解析**：
  - 新增 `assets/js/chapter-parser.js`，将章节解析逻辑从 Python 移植到 JavaScript
  - 支持中文数字章节（第X章、第X回）、阿拉伯数字、英文章节、特殊章节（序言/楔子/后记/番外）
  - 带散文检测，避免正文行被误识别为章节标题
- **变更文件**：
  - **重写**：`modules/novel/api.py`、`assets/js/novel-cache.js`、`templates/novel_reader.html`、`templates/immersive_reader.html`
  - **新增**：`assets/js/chapter-parser.js`
  - **删除**：`models/novel.py`（NovelReadingProgress）、`modules/novel/parser.py`（服务端章节解析，不再需要）
  - **更新**：`models/__init__.py`（移除 NovelReadingProgress）、`assets/js/sw.js`（添加 chapter-parser.js 预缓存）

**沉浸式阅读器融合到小说阅读器**

- **目标**：实现浏览器端无缝进入/退出沉浸式阅读，不出现 URL 变更或页面跳转
- **架构变更**：
  - 将沉浸式阅读器的 CSS/HTML/JS 全部融合到 `novel_reader.html` 中
  - 沉浸式阅读器作为**全屏覆盖层**（z-index: 5000），点击按钮显示/隐藏
  - 进入：`openImmersive()` 显示覆盖层 → 隐藏 body 滚动 → 从当前章节开始沉浸式阅读
  - 退出：`closeImmersive()` 隐藏覆盖层 → 恢复 body 滚动 → 同步章节回普通阅读器
  - 共享状态：chapters、currentChapter、currentNovel、currentNovelContent
  - 沉浸式状态以 `imm` 前缀隔离（immPages、immCurrentPage、immSettings 等）
  - 键盘事件区分模式：普通模式左右键翻章，沉浸模式左右键翻页、Esc 退出
- **Bug 修复：章节切换时上一章文本残留**：
  - `immLoadChapter()`：加载新章节时**立即清空两个页面层**（top + bottom），再渲染内容
  - `immRenderPage()`：每次渲染页面时**强制清空 bottom 层**，防止动画残留
  - `immAnimatePage()` 的 `finish()` 回调：动画结束后清空 bottom 层
  - `immLoadChapter()` 新增 `targetPage` 参数（`'last'` / 数字），简化向上翻章边界处理

### REL2.5.0

**网页代理工具（Web Proxy）**

- **功能概述**：
  - 基于 mitmproxy 的反向代理工具，允许内网设备通过跳板机访问外网
  - 运行在 5003 端口，支持 URL 格式：`http://{proxy}:5003/https/{target}`
  - 自动重写所有链接和资源路径，确保所有请求通过代理
- **双层拦截架构**：
  - **Service Worker 模式**（优先）：浏览器底层拦截所有网络请求，100% 可靠
    - 使用 `self.addEventListener('fetch', ...)` 拦截
    - 自动添加 `X-Proxy-Token` 和 `X-Proxy-Base` 认证头
    - 错误回退机制：代理失败时返回原始请求
  - **Hook 模式**（备用）：当 SW 不可用时自动启用
    - Hook XMLHttpRequest、fetch、window.open、history API、EventSource
    - Hook Image 构造函数和 `HTMLImageElement.prototype.src`
    - Hook DOM 元素创建（createElement）和 MutationObserver 监听
    - Hook 内联样式 cssText 属性
- **Python 服务端处理**：
  - **HTML 属性重写** (`_rewrite_html_attrs`)：
    - 替换 `<a href>`, `<img src>`, `<link href>`, `<script src>` 等属性
    - 替换内联样式 `style="background: url(...)"` 中的 URL
  - **内联脚本重写** (`_rewrite_inline_scripts`)：
    - 处理 HTML 中 `<script>` 标签内的内容
    - 只替换绝对 URL，保留相对路径给 webpack 处理
  - **JS 文件重写** (`_rewrite_js`)：
    - **关键修复**：替换 `__webpack_public_path__` 为代理路径
      - 解决 Next.js chunk 加载双重前缀问题
      - 示例：`r.p = "https://cdn.com/_next/"` → `r.p = "http://192.168.1.4:5003/https/cdn.com/_next/"`
    - 处理 `self.__next_f.push([...])` 中的绝对 URL
    - 处理 `:HL[...]` CSS 预加载链接格式
  - **CSS 重写** (`_rewrite_css`)：
    - 替换 `url()` 中的相对和绝对路径
    - 替换 `@import` 语句
  - **请求头修正** (`request`)：
    - 从 `X-Proxy-Base` 或 Referer 推断原始 Origin
    - 强制设置正确的 Origin 和 Referer 头
    - 解决 CDN 防盗链导致的 403 Forbidden 问题
- **URL 格式统一**：
  - 统一使用 `http://{proxy}:{port}/{protocol}/{host}/{path}` 格式
  - 所有资源（页面、CSS、JS、图片、音频、视频、字体）都通过此格式访问
- **Next.js 兼容性**：
  - 自动识别并处理 `self.__next_f.push([...])` 动态加载模式
  - 替换 webpack runtime 中的 `__webpack_public_path__`
  - 处理 `:HL[...]` CSS 预加载链接
  - 兼容所有基于 Next.js 的网站
- **新增模块**：
  - `modules/proxy/__init__.py` - 代理模块定义和 Blueprint 注册
  - `modules/proxy/proxy_addon.py` - mitmproxy 插件核心逻辑（~650 行）
  - `modules/proxy/hook.js` - 浏览器端拦截脚本（~350 行）
  - `modules/proxy/proxy_server.py` - 代理服务器管理
  - `modules/proxy/api.py` - 代理控制 API
- **新增页面**：
  - `templates/web_proxy.html` - 网页代理工具界面
- **新增 API**：
  - `GET /api/proxy/status` - 获取代理状态
  - `POST /api/proxy/start` - 启动代理服务
  - `POST /api/proxy/stop` - 停止代理服务
- **PWA 适配**（本地合并时补充）：
  - `templates/web_proxy.html` 添加 `_pwa_head.html`、`_pwa_register.html`、`offline-handler.js`
  - `templates/tools.html` 合并上游新增的「网页代理」入口，保留所有 PWA 特性
  - `assets/js/sw.js` 添加 `/tools/webproxy` 到离线缓存路由列表
- **新增依赖**：
  - `mitmproxy` - HTTP/HTTPS 代理引擎
  - `aioquic` - QUIC/HTTP3 协议支持（mitmproxy 依赖）
- **解决的问题**：
  | 问题 | 原因 | 解决方案 |
  |------|------|---------|
  | Next.js chunk 加载失败 | webpack 双重前缀 | 替换 `__webpack_public_path__` |
  | 图片/音频/视频 403 | 未被 hook 拦截或 Origin 不对 | 新增 Image/src 拦截 + 服务端强制设置正确头 |
  | CSS background-image 未替换 | 内联样式未处理 | 增加 style 属性处理 |
  | `/rp/xxx.png` 路径错误 | fakeOrigin 为空时解析错误 | 增加 baseScheme 变量保护 |

### REL2.4.2

**NCM API 客户端统一重构**

- **问题背景**：
  - 网易云音乐 API 请求函数在 3 个文件中重复定义（`modules/ncm/api.py`、`utils/music_cache.py`、`utils/ncm_api.py`）
  - 同一功能 `ncm_api_request` 存在 3 份不同实现，日志格式和错误处理不一致
  - `utils/music_cache.py` 职责混乱，同时包含缓存逻辑和 API 调用逻辑
- **创建统一 NCM API 客户端**：
  - 重写 `utils/ncm_api.py`，引入 `NCMAPIClient` 类
  - 统一的 `request()` 方法，包含完善的错误处理（超时、网络异常、未知错误）
  - 8 个语义化的 API 方法：`search`、`get_song_url`、`get_song_detail`、`get_lyric`、`get_personalized`、`get_personalized_newsong`、`get_playlist_detail`、`get_hot_search`
  - 全局单例 `ncm_client`，方便各模块直接使用
- **重构 modules/ncm/api.py**：
  - 移除本地 `NCM_API_BASE` 常量和 `ncm_api_request()` 函数定义
  - 改用 `from utils.ncm_api import ncm_client`
  - 所有路由函数调用 `ncm_client.xxx()` 替代原来的 `ncm_api_request('/xxx', {...})`
- **重构 utils/music_cache.py**：
  - 移除 `NCM_API_BASE` 常量
  - 移除 `ncm_api_request()` 函数定义
  - 移除 8 个重复的 API 调用函数（`search_songs`、`get_song_url`、`get_song_detail`、`get_personalized`、`get_personalized_newsong`、`get_lyric`、`get_hot_search`、`get_playlist_detail`）
  - 保留纯粹的缓存功能（`get_cache_path`、`is_cached`、`get_cached_music`、`cache_music`、`cache_cover`）
- **代码量变化**：
  - `utils/ncm_api.py`：86行 → 60行（重写为类结构）
  - `modules/ncm/api.py`：213行 → 195行（移除重复定义）
  - `utils/music_cache.py`：159行 → 115行（移除 API 函数，约减少 44 行）
- **架构改进**：
  - 消除约 150 行重复代码
  - 统一 NCM API 请求入口，单点维护
  - `music_cache.py` 职责回归单一（仅负责缓存）
  - 错误处理和日志格式统一

### REL2.4.1

**视频播放器 + B站视频缓存与播放**

- **本地视频播放器**：
  - 支持多种视频格式（MP4、WebM、OGG、MKV、AVI、MOV 等）
  - 使用 Plyr 轻量级播放器，本地化部署
  - Element UI 日间风格，与项目整体风格统一
  - 视频列表、搜索过滤、自适应布局
  - HTTP Range 请求支持，可拖拽进度条
  - 带鱼屏适配，确保控件完整显示
- **B站视频缓存与播放**：
  - 首页推荐视频（热门排行榜）
  - 搜索视频、搜索UP主
  - 查看UP主视频列表
  - 视频下载服务（异步多线程、进度追踪）
  - 客户端实时显示下载进度
  - 默认 480P 画质
  - 音视频自动合并（使用内置 FFmpeg）
  - 封面图片代理（解决防盗链问题）
  - 使用 `bilibili-api-python` 库
  - 使用 `curl_cffi` 请求库（伪装浏览器指纹）
- **新增模块**：
  - `modules/video/__init__.py` - 视频播放器模块定义
  - `modules/video/routes.py` - 视频播放器路由
  - `modules/video/api.py` - 视频 API
  - `modules/bili/__init__.py` - B站视频模块定义
  - `modules/bili/routes.py` - B站播放器路由
  - `modules/bili/api.py` - B站 API
  - `modules/bili/download_service.py` - B站视频下载服务
- **新增页面**：
  - `templates/video_player.html` - 视频播放器页面
  - `templates/bili_player.html` - B站视频页面
- **新增文件**：
  - `assets/css/plyr.min.css` - Plyr 播放器样式
  - `assets/js/plyr.min.js` - Plyr 播放器脚本
  - `tools/ffmpeg/ffmpeg.exe` - FFmpeg 可执行文件
  - `tools/ffmpeg/ffprobe.exe` - FFprobe 可执行文件
- **新增 API**：
  - `GET /api/videos` - 获取视频列表
  - `GET /api/video/<filename>` - 流式播放视频
  - `GET /api/bili/recommend` - 获取首页推荐
  - `GET /api/bili/search` - 搜索视频
  - `GET /api/bili/search_user` - 搜索UP主
  - `GET /api/bili/user_videos/<mid>` - 获取UP主视频
  - `GET /api/bili/video/<bvid>` - 获取视频详情
  - `POST /api/bili/download/<bvid>` - 启动下载
  - `GET /api/bili/progress/<bvid>` - 查询下载进度
  - `GET /api/bili/downloads` - 获取所有下载任务
  - `GET /api/bili/cached` - 获取已缓存视频
  - `DELETE /api/bili/delete/<bvid>` - 删除缓存视频
  - `GET /api/bili/play/<bvid>` - 播放缓存视频
  - `GET /api/bili/cover` - 封面图片代理
- **新增依赖**：
  - `bilibili-api-python` - B站 API 库
  - `curl_cffi` - 请求库（支持 TLS 指纹伪装）

### REL2.3.1

**Drop 功能 + 聊天室多人优化 + 导航配置**

- **Drop 功能**：
  - 允许用户向所有用户发送 Drop 消息（气泡形式弹出）
  - 个人冷却 10 分钟，全服冷却 1 分钟
  - HTTP 轮询每 10 秒查询一次最新 Drop
  - 气泡显示发送者昵称和消息内容
  - 支持屏蔽用户（黑名单管理）
  - Drop 设置页面：开关接收、黑名单管理、快捷发送
  - 使用 localStorage 记录 lastId，切换页面不重复显示
- **聊天室多人优化模式**：
  - 聊天室创建者可开启"多人优化"模式
  - 列表模式显示：所有发言人都在左侧，消息内容对齐
  - 交替背景色区分不同消息行
  - 连续同用户消息隐藏昵称（保留占位）
  - 自己发送的消息用户名标蓝加粗
  - 引用消息格式：`[用户名] 消息内容`
  - 表情包和引用消息适配列表模式
- **导航配置功能**：
  - 启动时自动创建 `instance/nav.yml` 配置文件
  - 支持通过 YAML 配置添加自定义导航项
  - 导航项自动显示在小工具/小游戏页面
  - 支持外部链接（新标签页打开）和相对链接
- **新增模块**：
  - `modules/drop/__init__.py` - Drop 模块定义
  - `modules/drop/routes.py` - Drop 设置页面路由
  - `modules/drop/api.py` - Drop API
- **新增模型**：
  - `models/drop.py` - DropMessage, DropSettings, DropBlacklist 模型
- **新增页面**：
  - `templates/drop_settings.html` - Drop 设置页面
- **新增工具**：
  - `utils/nav.py` - 导航配置工具
- **新增文件**：
  - `assets/js/drop.js` - Drop 前端脚本
  - `assets/css/drop.css` - Drop 样式
- **新增 API**：
  - `POST /api/drop/send` - 发送 Drop
  - `GET /api/drop/poll` - 轮询 Drop
  - `GET /api/drop/status` - 获取冷却状态
  - `GET /api/drop/settings` - 获取 Drop 设置
  - `PUT /api/drop/settings` - 更新 Drop 设置
  - `POST /api/drop/blacklist` - 添加黑名单
  - `DELETE /api/drop/blacklist` - 移除黑名单
  - `GET /api/drop/users/search` - 搜索用户
  - `GET /api/nav/items` - 获取导航项
- **数据库变更**：
  - 新增 `drop_message` 表
  - 新增 `drop_settings` 表
  - 新增 `drop_blacklist` 表
  - ChatRoom 表新增 `multi_user_mode` 字段

### REL2.3.0

**公告系统**

- **公告类型**：
  - 横幅公告：在控制台首页标题栏下方显示，同时只能存在一个
  - 通知公告：支持弹窗提醒，可存在多个
- **公告优先级**：
  - 重要：红色背景，无法关闭，每次进入控制台弹出（通知公告）
  - 一般：黄色背景，可确认或不再提示
  - 次要：蓝色背景，仅在公告中心显示
- **样式设计**：
  - 重要公告：背景色 `#fef0f0`，字体色 `#f56c6c`
  - 一般公告：背景色 `#fdf6ec`，字体色 `#e6a23c`
  - 次要公告：背景色 `#ecf5ff`，字体色 `#409eff`
  - 使用 Element UI Tag 配色方案
- **弹窗逻辑**：
  - 多条未读通知时显示数量，点击跳转公告中心
  - 单条通知显示完整内容，标题加粗，分隔线区分正文
  - 重要通知可关闭但下次仍弹出
  - 一般通知确认后本次会话不再弹出
- **角标显示**：
  - 感叹号：有重要公告
  - 数字：有未确认的一般公告数量
  - 红点：有未读的次要公告
- **权限控制**：
  - 超级管理员：可创建所有类型公告
  - 管理员：可创建一般横幅、一般通知、次要通知
  - 普通用户：无管理权限
- **新增模块**：
  - `modules/announcement/__init__.py` - 公告模块定义
  - `modules/announcement/routes.py` - 公告页面路由
  - `modules/announcement/api.py` - 公告 API
- **新增模型**：
  - `models/announcement.py` - Announcement, UserAnnouncementStatus 模型
- **新增页面**：
  - `templates/announcement_manage.html` - 公告管理页面
  - `templates/announcement_center.html` - 公告中心页面
- **新增 API**：
  - `GET /api/announcements` - 获取所有公告
  - `GET /api/announcements/banner` - 获取横幅公告
  - `GET /api/announcements/notifications/popup` - 获取弹窗通知
  - `GET /api/announcements/badge` - 获取公告角标状态
  - `POST /api/announcements/<id>/dismiss` - 关闭公告
  - `POST /api/announcements/<id>/confirm` - 确认公告
  - `POST /api/announcements/<id>/never-show` - 不再提示
  - `GET /api/announcements/manage` - 获取所有公告（管理）
  - `POST /api/announcements/manage` - 创建公告
  - `PUT /api/announcements/manage/<id>` - 更新公告
  - `DELETE /api/announcements/manage/<id>` - 删除公告
- **数据库变更**：
  - 新增 `announcement` 表
  - 新增 `user_announcement_status` 表

### REL2.2.1

**沉浸式阅读器优化 + 音乐播放器优化**

- **沉浸式阅读器分页优化**：
  - 所有设备统一应用高 DPI 优化（减少 5% 行数和字符数）
  - 每页行数额外减少 3 行，进一步防止文字溢出边界
  - 添加续段处理：被截断到新页面的内容标记为续段
  - 续段内容不缩进，直接紧贴开头显示
  - 正常段落保持首行缩进 2em（空两格）
- **音乐播放器搜索优化**：
  - 搜索结果即时显示，无需等待封面加载
  - 封面图片后台异步分批加载（每批 10 张）
  - 使用本地缓存路径直接显示，加载失败时显示默认图片
  - 移除封面加载进度显示，提升用户体验

### REL2.2.0

**系统设置 + 配置重构**

- **系统设置模块**：
  - 新增 `modules/settings/` 系统设置模块
  - 管理员/超级管理员可在系统设置页面配置各项功能
  - 支持通用设置和安全设置两大分类
- **通用设置**：
  - 首页显示设置：切换显示昵称或用户名
  - 用户设置：允许设置昵称、昵称长度限制（5-20字）
  - 导航设置：导航栏默认展开、工具/游戏卡片布局（1×3、1×4、2×3）
- **安全设置**：
  - 用户名设置：手动添加和自助注册的用户名长度限制
  - 密码设置：密码强度要求（4个等级）、允许弱密码、允许改密码
  - 安全问题：允许自助找回密码、设置安全问题
- **忘记密码功能**：
  - 登录页面添加"忘记密码"链接
  - 三步验证流程：输入用户名 → 回答安全问题 → 重置密码
  - 支持通过安全问题自助重置密码
- **个人设置增强**：
  - 根据系统设置动态显示/隐藏昵称输入框
  - 根据系统设置控制密码修改权限
  - 安全问题设置（启用自助找回密码后可见）
- **注册验证增强**：
  - 用户名长度验证（根据系统设置）
  - 密码强度验证（根据系统设置）
  - 弱密码检测
- **用户管理验证**：
  - 手动添加用户时的用户名长度验证
  - 昵称设置验证
- **配置文件重构**：
  - 删除 `config.py` 中的硬编码配置
  - 新增 `instance/config.yml` YAML 配置文件
  - 系统设置与 Flask 配置统一存储在 YAML 文件中
  - 删除 `instance/system_settings.json`，合并到 config.yml
  - 添加 PyYAML 依赖
- **新增文件**：
  - `modules/settings/__init__.py` - 系统设置模块定义
  - `modules/settings/routes.py` - 系统设置页面路由
  - `modules/settings/api.py` - 系统设置 API
  - `templates/system_settings.html` - 系统设置页面
  - `templates/forgot_password.html` - 忘记密码页面
  - `utils/system_settings.py` - 系统设置工具（从 YAML 读取）
  - `utils/validators.py` - 验证工具（密码强度、用户名、昵称）
  - `instance/config.yml` - YAML 配置文件
- **新增 API**：
  - `GET /api/settings` - 获取所有系统设置
  - `PUT /api/settings/general` - 更新通用设置
  - `PUT /api/settings/security` - 更新安全设置
  - `POST /api/settings/reset` - 重置设置为默认值
  - `POST /api/auth/forgot-password/check` - 检查用户名
  - `POST /api/auth/forgot-password/verify` - 验证安全问题答案
  - `POST /api/auth/forgot-password/reset` - 重置密码
- **数据库变更**：
  - User 表新增 `security_question` 字段
  - User 表新增 `security_answer_hash` 字段

### REL2.1.3

**手势防御系统 + 随身听优化**

- **防御层 5：absolute 定位 + body 缓冲垫**：
  - 解决宿主 App 全局手势劫持页面滚动的问题
  - 通过 `#touch-buffer` 元素创建可滚动的 body 区域
  - 欺骗浏览器认为页面可滚动，从而让内部内容区域正常滚动
  - 支持四方向滚动（上、下、左、右）
  - 侧边栏和标题栏通过反向 transform 固定位置
- **CSS 实现**：
  - `html.touch-defense-5`：禁用 overscroll-behavior
  - `body.touch-defense-5`：设置 overflow: auto，允许滚动
  - `.touch-defense-5 #scroll-wrap`：absolute 定位，跟随 body 滚动
  - `.touch-defense-5 .console-content`：设置 touch-action: pan-x pan-y
- **JavaScript 滚动同步**：
  - 监听 window scroll 事件
  - 主容器通过 transform 跟随 body 滚动
  - 侧边栏和标题栏通过反向 transform 固定位置
- **滑动测试页面**：
  - 新增 `/board/swipe-test` 路由
  - 仅管理员和超级管理员可访问
  - 从用户下拉菜单进入（个人设置下方）
  - 测试四方向滑动功能
- **随身听优化**：
  - 搜索结果调用 `/api/ncm/song/detail` 获取完整歌曲信息
  - 修复搜索结果封面显示默认图片、歌手显示未知的问题
  - 新增封面缓存 API `/api/ncm/cache-cover`
  - 移除播放列表功能，改为单曲播放模式
  - 点击新歌曲时替换当前播放的歌曲
- **新增 API**：
  - `POST /api/ncm/cache-cover` - 缓存封面图片
  - `GET /music/cache/covers/<filename>` - 提供缓存的封面文件
- **新增文件**：
  - `templates/swipe_test.html` - 滑动测试页面

### EVA2.1.2

**沉浸式阅读器兼容性修复**

- **修复分页逻辑bug**：
  - 修复第一章第一页标题和正文重叠的问题
  - 优化 `while` 循环中的分页逻辑，正确处理标题占用空间
  - 分页后正确计算剩余内容行数
- **低版本 WebView 兼容性处理**：
  - 检测 `localStorage` 是否存在，不存在则创建 mock 对象
  - 检测 `localStorage` 是否可用，失败则替换为 mock
  - 提供 `getItem`, `setItem`, `removeItem`, `clear` 方法
  - 解决旧版 WebView 中 `Cannot read property 'getItem' of null` 错误
- **ES5 语法兼容**：
  - 将所有箭头函数 `=>` 替换为传统 `function` 语法
  - 将 `const`/`let` 替换为 `var`
  - 将模板字符串 `` `...${}...` `` 替换为字符串拼接
  - 将 `for...of` 循环替换为传统 `for` 循环
  - 将可选链操作符 `?.` 替换为 `&&` 判断
  - 将对象展开运算符 `{ ...obj }` 替换为逐个属性赋值

### EVA2.1.1

**随身听兼容性修复**

- **修复 APlayer API 错误**：
  - 将 `this.aplayer.skip(index)` 改为 `this.aplayer.list.switch(index) + this.aplayer.play()`
  - APlayer 正确的方法是使用 `list.switch(index)` 切换歌曲
- **添加旧版 WebView 兼容性处理**：
  - 检测 `localStorage` 是否存在，不存在则创建 mock 对象
  - 检测 `localStorage` 是否可用，失败则替换为 mock
  - 提供 `getItem`, `setItem`, `removeItem`, `clear` 方法
  - 解决旧版 WebView 中 `Cannot read property 'getItem' of null` 错误
- **播放器操作容错处理**：
  - 添加空值检查：`this.aplayer.list` 和 `this.aplayer.list.audios`
  - 添加 try-catch 保护，播放器操作失败时自动尝试重新创建
  - 双重保护机制，即使初始化失败也会尝试再次创建
- **错误提示优化**：
  - 播放失败时显示具体原因
  - `无法获取播放地址: 歌曲暂无播放地址` / `API返回错误码: xxx`
  - `缓存音乐失败: xxx`（后端返回的具体错误信息）
  - `播放失败: xxx`（JavaScript 异常的消息）
- **添加详尽的日志记录**：
  - 前端日志：`[NCM]` 前缀的各步骤日志
  - 后端日志：`[NCM API]` / `[MusicCache]` 前缀的详细日志

### EVA2.1.0

**性能优化 + 随身听功能**

- **小说缓存优化**：
  - 新增 `utils/novel_cache.py` 小说缓存服务
  - 启动时预扫描所有小说，缓存书名、作者、最新章节
  - API 响应从数秒优化到毫秒级
  - 支持手动刷新缓存 `/api/novels/refresh-cache`
- **随身听功能**：
  - 新增 `modules/ncm/` 随身听模块
  - 网易云音乐播放器，支持搜索、推荐歌单、热门搜索
  - 内网缓存播放：音乐文件先缓存到本地 `temp/music/`
  - APlayer 播放器本地化部署，无需外网 CDN
  - 与聊天室、小说阅读器保持一致的设计风格
- **新增文件**：
  - `utils/novel_cache.py` - 小说缓存服务
  - `utils/music_cache.py` - 音乐缓存服务
  - `utils/ncm_api.py` - 网易云音乐 API 封装
  - `modules/ncm/__init__.py` - 随身听模块定义
  - `modules/ncm/routes.py` - 播放器页面路由
  - `modules/ncm/api.py` - NCM API 接口
  - `templates/ncm_player.html` - 播放器前端页面
  - `assets/css/aplayer.min.css` - APlayer 样式
  - `assets/js/aplayer.min.js` - APlayer 脚本
- **新增 API**：
  - `GET /api/ncm/search` - 搜索歌曲
  - `GET /api/ncm/song/url` - 获取歌曲播放地址
  - `GET /api/ncm/personalized` - 获取推荐歌单
  - `GET /api/ncm/hot-search` - 获取热搜列表
  - `GET /api/ncm/playlist/detail` - 获取歌单详情
  - `POST /api/ncm/cache-music` - 缓存音乐到本地
  - `GET /music/<filename>` - 提供缓存的音乐文件

### REL2.0.2

**用户管理系统优化**

- **用户管理简化**：
  - 取消编辑用户对话框，管理员开关直接在表格中切换
  - 用户名不可修改，仅作为登录标识
  - 密码修改通过"重置密码"按钮单独操作
- **昵称功能**：
  - 新增 `nickname` 字段，用户可设置昵称
  - 所有页面优先显示昵称，无昵称时显示用户名
  - 用户可在"个人设置"中修改自己的昵称
- **超级管理员密码修改**：
  - 超级管理员可在"个人设置"中修改自己的密码
- **下拉菜单优化**：
  - 所有页面下拉菜单统一风格
  - 显示大字昵称 + 小字用户名
  - 添加"个人设置"入口
- **Bug修复**：
  - 修复控制台欢迎页面用户名不显示的问题
  - 数据库自动迁移：启动时检查并添加 `nickname` 字段

### REL2.0.1

**小说阅读器增强**

- **智能章节解析算法 V3.1**：
  - 采用锚点学习 + 统计验证的五阶段检测算法
  - Phase 1 - 发现：使用锚点规则和宽松规则发现章节候选
  - Phase 2 - 模式学习：从锚点学习标题长度、前缀模式、间距等特征
  - Phase 3 - 模式扩展：用学习到的模式搜索遗漏的章节
  - Phase 4 - 统计验证：两阶段间距验证，过滤误检
  - Phase 5 - 层级推断：识别卷/章/节层级
  - 支持中英文多种章节格式（第一章、Chapter 1、1. 等）
  - 章节标题前空行强制校验，避免正文中关键词误识别
  - 新增 `utils/chapter_parser.py` 作为独立章节解析库
- **沉浸式阅读器主题系统**：
  - 日间模式 5 种主题：牛奶白、卷轴黄、小草绿、基佬紫、云雾蓝
  - 夜间模式 2 种主题：星空黑、玄素灰
  - 一键切换日间/夜间模式
  - 设置面板风格与阅读器主题同步
- **翻页动画系统重构**：
  - 双层页面结构，动画过程中可同时看到两页
  - 滑动动画：当前页向左滑出，下一页从右边滑入
  - 滚动动画：当前页向上滚出，下一页从下边滚入
  - 淡入淡出动画：页面渐隐渐现
  - 无动画选项：直接切换
  - 所有设置自动保存到 localStorage

### REL2.0.0

**重大架构重构**

- **模块化重构**：将 1680 行的 app.py 拆分为清晰的模块化结构
  - 创建 models/ 目录，按业务领域组织数据库模型
  - 创建 utils/ 目录，统一管理工具函数
  - 创建 modules/ 目录，按业务领域组织功能模块
  - app.py 从 1680 行减少到 43 行（减少 97.4%）
- **架构改进**：
  - 采用 Flask Blueprint 进行模块化设计
  - 遵循单一职责原则，每个模块专注于单一业务领域
  - 提高代码的可维护性、可测试性和可扩展性
  - 改善多人协作，减少合并冲突
- **新增模块**：
  - **models/** - 数据库模型层
    - user.py：User, Passkey 模型
    - chat.py：ChatRoom 模型
    - sticker.py：UserSticker, PackSticker 模型
    - novel.py：NovelReadingProgress 模型
  - **utils/** - 工具函数层
    - common.py：通用工具函数（壁纸、诗词、Passkey 生成等）
    - file.py：文件处理工具（编码检测、文件读取、图片下载等）
  - **modules/** - modules/ - 业务模块层
    - auth/：用户认证模块（登录、注册、用户管理、Passkey 管理）
    - chat/：聊天室模块（聊天室管理、WebSocket 事件处理）
    - novel/：小说阅读器模块（小说列表、章节解析、阅读进度）
    - sticker/：表情包管理模块（表情商城、个人收藏、表情包合集）
    - main/：主页面模块（首页、控制面板、工具页面）
    - drop/：Drop 消息模块（Drop 消息发送、接收、设置）
- **代码质量提升**：
  - 配置集中管理（config.py）
  - 扩展统一初始化（extensions.py）
  - 清晰的模块边界和职责划分
  - 更好的代码复用性

### REL1.3.4\_fix1

- **修复**：沉浸式阅读器章节切换bug
  - 修复章节结尾快速点击导致跳过多章的问题
  - 添加章节加载锁，在章节切换过程中屏蔽点击换页功能

### REL1.3.4

- **新增**：沉浸式阅读器功能
  - 在小说阅读器章节导航右侧添加全屏图标按钮
  - 创建独立的沉浸式阅读器页面
  - 点击屏幕左侧翻到上一页，点击右侧翻到下一页
  - 点击屏幕中间弹出/收回顶部和底部菜单栏
  - 一章读完后自动进入下一章
  - 根据浏览器窗口实际宽高动态计算文字显示范围和分页
  - 支持高DPI设备，宁可少显示一行也不让文字溢出屏幕
  - 每章第一页顶部显示章节名称标题
  - 左下角显示当前时间、书名、章节名称、页数信息
  - 后台预加载后两章节，提升阅读体验
- **更新**：依赖库版本
  - Flask 2.0.1 → 3.1.2
  - Flask-SQLAlchemy 2.5.1 → 3.1.1
  - Flask-Login 0.5.0 → 0.6.3
  - Flask-SocketIO 5.1.1 → 5.6.1
  - requests 2.26.0 → 2.32.5
  - Werkzeug 2.0.1 → 3.1.4
  - python-socketio 5.5.0 → 5.16.1
  - python-engineio 4.3.0 → 4.13.1
  - chardet 5.2.0 → 7.4.0.post2
  - 新增 flask-cors 6.0.2

## 1. 项目架构

### 1.1 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                        Flask Application                     │
│                         (app.py - 43行)                      │
└─────────────────────────────────────────────────────────────┘
                              │
                ┌─────────────┼─────────────┐
                │             │             │
                ▼             ▼             ▼
        ┌───────────┐  ┌───────────┐  ┌───────────┐
        │  Config   │  │Extensions │  │  Models   │
        │ (config.py)│  │(extensions)│  │ (models/) │
        └───────────┘  └───────────┘  └───────────┘
                                           │
                              ┌────────────┼────────────┐
                              │            │            │
                              ▼            ▼            ▼
                        ┌─────────┐  ┌─────────┐  ┌─────────┐
                        │  User   │  │  Chat   │  │ Sticker │
                        │ Passkey │  │  Room   │  │  Models │
                        └─────────┘  └─────────┘  └─────────┘
                
                ┌─────────────────────────────────────┐
                │         Business Modules            │
                │           (modules/)                │
                └─────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  Auth Module  │    │  Chat Module  │    │ Novel Module  │
│   (auth/)     │    │   (chat/)     │    │  (novel/)     │
│               │    │               │    │               │
│ - routes.py   │    │ - routes.py   │    │ - routes.py   │
│ - api.py      │    │ - api.py      │    │ - api.py      │
│               │    │ - websocket.py│    │ (browser-side │
│               │    │               │    │  chap-parse)  │
└───────────────┘    └───────────────┘    └───────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
                              ▼
                    ┌───────────────┐
                    │Sticker Module │
                    │  (sticker/)   │
                    │               │
                    │ - routes.py   │
                    │ - api.py      │
                    └───────────────┘
```

### 1.2 前端架构

- **框架**：Vue.js 2.x
- **UI 库**：Element UI
- **通信**：Socket.IO 客户端
- **构建**：原生 HTML/CSS/JavaScript，无构建工具

### 1.3 后端架构

#### 1.3.1 核心组件

- **app.py**：应用入口，负责创建和配置 Flask 应用
- **config.py**：配置管理，集中管理所有配置项
- **extensions.py**：扩展初始化，统一初始化 Flask 扩展

#### 1.3.2 模块化设计

采用 Flask Blueprint 进行模块化设计，每个模块独立管理路由和业务逻辑：

- **auth 模块**：用户认证和管理
  - routes.py：登录、注册、用户管理页面
  - api.py：用户和 Passkey 管理 API
- **chat 模块**：聊天室功能
  - routes.py：聊天室页面路由
  - api.py：聊天室管理 API
  - websocket.py：WebSocket 事件处理
- **novel 模块**：小说阅读器
  - routes.py：小说阅读器页面路由
  - api.py：小说文件流 API（整本书缓存模式，支持 Range 断点续传）
  - 浏览器端章节解析（`assets/js/chapter-parser.js`），无需服务端参与
  - 沉浸式阅读器融合在 `novel_reader.html` 中，浏览器端无缝切换
- **sticker 模块**：表情包管理
  - routes.py：表情包文件服务
  - api.py：表情包管理 API
- **ncm 模块**：随身听
  - routes.py：播放器页面路由
  - api.py：网易云音乐 API（使用统一 NCMAPIClient 客户端）
- **video 模块**：视频播放器
  - routes.py：播放器页面路由
  - api.py：视频流 API
- **bili 模块**：B站视频
  - routes.py：播放器页面路由
  - api.py：B站 API
  - download_service.py：视频下载服务
- **proxy 模块**：网页代理
  - proxy_addon.py：mitmproxy 插件（URL 重写、请求头修正、内容替换）
  - hook.js：浏览器端拦截脚本（Service Worker + Hook 双模式）
  - proxy_server.py：代理服务器管理（启动、停止、状态查询）
  - api.py：代理控制 API
- **main 模块**：主页面
  - routes.py：首页、控制面板、工具页面
- **settings 模块**：系统设置
  - routes.py：系统设置页面路由
  - api.py：系统设置 API
- **announcement 模块**：公告系统
  - routes.py：公告中心页面路由
  - api.py：公告管理 API

#### 1.3.3 数据模型层

独立的数据模型层，按业务领域组织：

- **user.py**：User, Passkey
- **chat.py**：ChatRoom
- **sticker.py**：UserSticker, PackSticker
- **announcement.py**：Announcement, UserAnnouncementStatus
- **drop.py**：DropMessage, DropSettings, DropBlacklist

#### 1.3.4 工具函数层

统一的工具函数层，提供通用功能：

- **common.py**：
  - get\_bing\_wallpaper()：获取必应壁纸
  - get\_poetry()：获取今日诗词
  - generate\_passkey()：生成 Passkey
  - get\_utc\_plus\_8\_time()：获取 UTC+8 时间
- **file.py**：
  - detect\_file\_encoding()：检测文件编码
  - read\_novel\_content()：读取小说内容
  - download\_sticker\_image()：下载表情包图片
- **chapter\_parser.py**：
  - parse\_chapters\_advanced()：高级章节解析，返回章节列表
  - detect\_chapters()：从文件检测章节位置
  - detect\_chapters\_from\_lines()：从行列表检测章节
  - V3.1 锚点学习 + 统计验证算法
- **music\_cache.py**：
  - get\_cache\_path()：获取音乐缓存路径
  - is\_cached()：检查音乐是否已缓存
  - get\_cached\_music()：获取缓存的音乐文件路径
  - cache\_music()：缓存音乐文件到本地
  - cache\_cover()：缓存封面图片到本地
- **ncm\_api.py**：
  - NCMAPIClient 类：网易云音乐 API 统一客户端
  - request()：统一 API 请求方法（含超时、网络异常、未知错误处理）
  - search()：搜索歌曲
  - get\_song\_url()：获取歌曲播放地址
  - get\_song\_detail()：获取歌曲详情
  - get\_lyric()：获取歌词
  - get\_personalized()：获取推荐歌单
  - get\_personalized\_newsong()：获取推荐新歌
  - get\_playlist\_detail()：获取歌单详情
  - get\_hot\_search()：获取热搜列表
  - ncm\_client：全局单例实例
- **system\_settings.py**：
  - get\_settings()：获取系统设置
  - update\_settings()：更新系统设置
  - 从 YAML 配置文件读取系统设置
- **validators.py**：
  - validate\_password\_strength()：验证密码强度
  - is\_weak\_password()：检查是否为弱密码
  - validate\_username()：验证用户名
  - validate\_nickname()：验证昵称
- **nav.py**：
  - init\_nav\_file()：初始化导航配置文件
  - get\_nav\_items()：获取导航项列表

### 1.4 架构优势

#### 1.4.1 可维护性

- 每个模块职责单一，代码量适中（200-400行）
- 清晰的模块边界，易于定位和修改代码
- 配置集中管理，便于调整

#### 1.4.2 可测试性

- 模块独立，便于编写单元测试
- 依赖注入，便于模拟和测试
- 清晰的接口定义

#### 1.4.3 可扩展性

- 新增功能只需添加新模块
- 模块之间松耦合，便于替换和升级
- 支持水平扩展

#### 1.4.4 团队协作

- 不同开发者可以同时修改不同模块
- 减少合并冲突
- 清晰的代码结构，便于新成员上手

## 2. 数据库设计

### 2.1 用户表 (User)

| 字段名                    | 类型          | 描述             |
| ---------------------- | ----------- | -------------- |
| id                     | Integer     | 用户 ID，主键       |
| username               | String(50)  | 用户名，唯一         |
| nickname               | String(50)  | 昵称（可选）         |
| password\_hash         | String(128) | 密码哈希值          |
| is\_super\_admin       | Boolean     | 是否为超级管理员       |
| is\_admin              | Boolean     | 是否为管理员         |
| passkey\_used          | String(6)   | 注册时使用的 Passkey |
| security\_question     | String(255) | 安全问题（可选）       |
| security\_answer\_hash | String(128) | 安全问题答案哈希（可选）   |
| created\_at            | DateTime    | 创建时间           |

### 2.2 Passkey 表 (Passkey)

| 字段名            | 类型        | 描述                |
| -------------- | --------- | ----------------- |
| id             | Integer   | Passkey ID，主键     |
| key            | String(6) | Passkey 值，唯一      |
| duration\_days | Integer   | 有效期（天数），None 表示无限 |
| max\_uses      | Integer   | 最大使用次数，None 表示无限  |
| current\_uses  | Integer   | 当前使用次数            |
| is\_active     | Boolean   | 是否激活              |
| expires\_at    | DateTime  | 过期时间              |
| created\_at    | DateTime  | 创建时间              |

### 2.3 聊天室表 (ChatRoom)

| 字段名         | 类型          | 描述                  |
| ----------- | ----------- | ------------------- |
| id          | Integer     | 聊天室 ID，主键           |
| name        | String(50)  | 聊天室名称，唯一            |
| password    | String(128) | 密码哈希值，None 表示无密码    |
| created\_by | Integer     | 创建者 ID，外键关联 User.id |
| created\_at | DateTime    | 创建时间                |
| is\_active  | Boolean     | 是否激活                |

### 2.4 用户表情包表 (UserSticker)

| 字段名           | 类型          | 描述                       |
| ------------- | ----------- | ------------------------ |
| id            | Integer     | 表情包 ID，主键                |
| user\_id      | Integer     | 用户 ID，外键关联 User.id       |
| sticker\_code | String(20)  | 表情码                      |
| sticker\_type | String(20)  | 表情类型 ('single' 或 'pack') |
| sticker\_name | String(100) | 表情名称                     |
| description   | String(255) | 表情描述                     |
| local\_path   | String(255) | 本地缓存路径                   |
| created\_at   | DateTime    | 创建时间                     |

### 2.5 表情包合集中的表情表 (PackSticker)

| 字段名           | 类型          | 描述                 |
| ------------- | ----------- | ------------------ |
| id            | Integer     | 表情 ID，主键           |
| user\_id      | Integer     | 用户 ID，外键关联 User.id |
| pack\_code    | String(20)  | 所属表情包合集码           |
| sticker\_code | String(50)  | 表情码                |
| sticker\_name | String(100) | 表情名称               |
| description   | String(255) | 表情描述               |
| local\_path   | String(255) | 本地缓存路径             |
| created\_at   | DateTime    | 创建时间               |

### 2.6 小说阅读进度（已移除）

> **注意**：`NovelReadingProgress` 模型已在小说模块 v2 重构中移除。阅读进度现在完全存储在浏览器端 IndexedDB 中（`NovelCacheDB` v2 的 `readingProgress` store），不再需要服务端同步。

### 2.7 公告表 (Announcement)

| 字段名                | 类型          | 描述                                |
| ------------------ | ----------- | --------------------------------- |
| id                 | Integer     | 公告 ID，主键                          |
| title              | String(200) | 公告标题                              |
| content            | Text        | 公告内容                              |
| announcement\_type | String(20)  | 公告类型（'banner' 或 'notification'）   |
| priority           | String(20)  | 优先级（'important'、'normal'、'minor'） |
| created\_by        | Integer     | 创建者 ID，外键关联 User.id               |
| created\_at        | DateTime    | 创建时间                              |
| updated\_at        | DateTime    | 更新时间                              |
| is\_active         | Boolean     | 是否激活                              |

### 2.8 用户公告状态表 (UserAnnouncementStatus)

| 字段名                | 类型       | 描述                         |
| ------------------ | -------- | -------------------------- |
| id                 | Integer  | 状态 ID，主键                   |
| user\_id           | Integer  | 用户 ID，外键关联 User.id         |
| announcement\_id   | Integer  | 公告 ID，外键关联 Announcement.id |
| is\_dismissed      | Boolean  | 是否永久关闭                     |
| dismissed\_at      | DateTime | 关闭时间                       |
| session\_dismissed | Boolean  | 本次会话是否已关闭                  |

### 2.9 Drop 消息表 (DropMessage)

| 字段名          | 类型          | 描述                  |
| ------------ | ----------- | ------------------- |
| id           | Integer     | 消息 ID，主键            |
| sender\_id   | Integer     | 发送者 ID，外键关联 User.id |
| sender\_name | String(50)  | 发送者昵称               |
| content      | String(200) | 消息内容                |
| created\_at  | DateTime    | 创建时间                |

### 2.10 Drop 设置表 (DropSettings)

| 字段名            | 类型       | 描述                 |
| -------------- | -------- | ------------------ |
| id             | Integer  | 设置 ID，主键           |
| user\_id       | Integer  | 用户 ID，外键关联 User.id |
| enabled        | Boolean  | 是否接收 Drop 消息       |
| last\_drop\_at | DateTime | 最后发送时间             |

### 2.11 Drop 黑名单表 (DropBlacklist)

| 字段名               | 类型       | 描述                    |
| ----------------- | -------- | --------------------- |
| id                | Integer  | 记录 ID，主键              |
| user\_id          | Integer  | 用户 ID，外键关联 User.id    |
| blocked\_user\_id | Integer  | 被屏蔽用户 ID，外键关联 User.id |
| created\_at       | DateTime | 创建时间                  |

## 3. API 接口

### 3.1 用户认证相关

#### 3.1.1 注册

- **URL**：`/register`
- **方法**：POST
- **参数**：
  - username: 用户名
  - password: 密码
  - confirm\_password: 确认密码
  - passkey: 邀请码（可选，首个用户不需要）
- **返回**：重定向到登录页面

#### 3.1.2 登录

- **URL**：`/login`
- **方法**：POST
- **参数**：
  - username: 用户名
  - password: 密码
- **返回**：重定向到控制面板

#### 3.1.3 退出登录

- **URL**：`/logout`
- **方法**：GET
- **返回**：重定向到首页

### 3.2 用户管理 API

#### 3.2.1 获取用户列表

- **URL**：`/api/users`
- **方法**：GET
- **权限**：管理员或超级管理员
- **返回**：用户列表 JSON

#### 3.2.2 创建用户

- **URL**：`/api/users`
- **方法**：POST
- **权限**：管理员或超级管理员
- **参数**：
  - username: 用户名
  - password: 密码
  - is\_admin: 是否为管理员（仅超级管理员可设置）
- **返回**：新用户信息 JSON

#### 3.2.3 更新用户

- **URL**：`/api/users`
- **方法**：PUT
- **权限**：管理员或超级管理员
- **参数**：
  - id: 用户 ID
  - password: 密码（可选）
  - is\_admin: 是否为管理员（仅超级管理员可设置）
- **返回**：更新后的用户信息 JSON

#### 3.2.4 删除用户

- **URL**：`/api/users`
- **方法**：DELETE
- **权限**：管理员或超级管理员
- **参数**：
  - id: 用户 ID
- **返回**：成功/失败信息 JSON

#### 3.2.5 获取个人资料

- **URL**：`/api/user/profile`
- **方法**：GET
- **权限**：登录用户
- **返回**：用户资料 JSON（包含系统设置相关权限）

#### 3.2.6 更新个人资料

- **URL**：`/api/user/profile`
- **方法**：PUT
- **权限**：登录用户
- **参数**：
  - nickname: 昵称（可选）
  - password: 新密码（可选）
  - security\_question: 安全问题（可选）
  - security\_answer: 安全问题答案（可选）
- **返回**：成功/失败信息 JSON

#### 3.2.7 忘记密码 - 检查用户名

- **URL**：`/api/auth/forgot-password/check`
- **方法**：POST
- **权限**：公开
- **参数**：
  - username: 用户名
- **返回**：安全问题 JSON

#### 3.2.8 忘记密码 - 验证答案

- **URL**：`/api/auth/forgot-password/verify`
- **方法**：POST
- **权限**：公开
- **参数**：
  - username: 用户名
  - answer: 安全问题答案
- **返回**：成功/失败信息 JSON

#### 3.2.9 忘记密码 - 重置密码

- **URL**：`/api/auth/forgot-password/reset`
- **方法**：POST
- **权限**：公开
- **参数**：
  - username: 用户名
  - answer: 安全问题答案
  - new\_password: 新密码
- **返回**：成功/失败信息 JSON

### 3.3 Passkey 管理 API

#### 3.3.1 获取 Passkey 列表

- **URL**：`/api/passkeys`
- **方法**：GET
- **权限**：超级管理员
- **返回**：Passkey 列表 JSON

#### 3.3.2 创建 Passkey

- **URL**：`/api/passkeys`
- **方法**：POST
- **权限**：超级管理员
- **参数**：
  - duration\_days: 有效期（天数，可选）
  - max\_uses: 最大使用次数（可选）
- **返回**：新 Passkey 信息 JSON

#### 3.3.3 删除 Passkey

- **URL**：`/api/passkeys`
- **方法**：DELETE
- **权限**：超级管理员
- **参数**：
  - id: Passkey ID
- **返回**：成功/失败信息 JSON

### 3.4 聊天室相关 API

#### 3.4.1 获取聊天室列表

- **URL**：`/api/chatrooms`
- **方法**：GET
- **权限**：登录用户
- **返回**：聊天室列表 JSON

#### 3.4.2 创建聊天室

- **URL**：`/api/chatrooms`
- **方法**：POST
- **权限**：登录用户
- **参数**：
  - name: 聊天室名称
  - password: 密码（可选）
- **返回**：新聊天室信息 JSON

#### 3.4.3 编辑聊天室

- **URL**：`/api/chatrooms`
- **方法**：PUT
- **权限**：聊天室创建者或管理员
- **参数**：
  - id: 聊天室 ID
  - name: 聊天室名称
  - password: 密码（可选，空字符串表示清空密码）
- **返回**：更新后的聊天室信息 JSON

#### 3.4.4 删除聊天室

- **URL**：`/api/chatrooms/{room_id}`
- **方法**：DELETE
- **权限**：聊天室创建者或管理员
- **返回**：成功/失败信息 JSON

#### 3.4.5 加入聊天室

- **URL**：`/api/chatroom/join`
- **方法**：POST
- **权限**：登录用户
- **参数**：
  - room\_id: 聊天室 ID
  - password: 密码（如果需要）
- **返回**：成功/失败信息 JSON

### 3.5 小说阅读器相关 API（v2 整本书缓存架构）

#### 3.5.1 获取云端小说列表

- **URL**：`/api/novels`
- **方法**：GET
- **权限**：登录用户
- **返回**：云端小说列表 JSON（name, filename, author, latest_chapter）

#### 3.5.2 刷新小说缓存

- **URL**：`/api/novels/refresh-cache`
- **方法**：POST
- **权限**：登录用户
- **返回**：扫描计数 JSON

#### 3.5.3 获取小说文件信息

- **URL**：`/api/novels/{novel_name}/info`
- **方法**：GET
- **权限**：登录用户
- **返回**：文件信息 JSON（size, modified, filename, encoding）

#### 3.5.4 下载小说文件

- **URL**：`/api/novels/{novel_name}/file`
- **方法**：GET
- **权限**：登录用户
- **返回**：原始 .txt 文件流（支持 HTTP Range 断点续传，返回 206 Partial Content）

> **已移除的端点**（小说模块 v2 重构后）：
> - `GET /api/novels/{novel_name}/chapters` — 章节解析已移至浏览器端
> - `GET /api/novels/{novel_name}/chapters/{chapter_index}` — 不再逐章传输
> - `GET /api/novels/{novel_name}/download-all` — 改为 `/file` 端点整本传输
> - `GET/POST /api/novels/{novel_name}/progress` — 阅读进度改为本地 IndexedDB 存储

### 3.6 表情包相关 API

#### 3.6.1 获取表情商城列表

- **URL**：`/api/stickers/hub`
- **方法**：GET
- **权限**：登录用户
- **参数**：
  - type: 表情类型 ('single' 或 'pack')
  - page: 页码（可选）
- **返回**：表情列表 JSON

#### 3.6.2 获取我的表情包

- **URL**：`/api/stickers/mine`
- **方法**：GET
- **权限**：登录用户
- **参数**：
  - type: 表情类型 ('single' 或 'pack')
- **返回**：我的表情包列表 JSON

#### 3.6.3 添加表情包

- **URL**：`/api/stickers/add`
- **方法**：POST
- **权限**：登录用户
- **参数**：
  - code: 表情码
  - type: 表情类型 ('single' 或 'pack')
- **返回**：成功/失败信息 JSON

#### 3.6.4 移除表情包

- **URL**：`/api/stickers/remove`
- **方法**：POST
- **权限**：登录用户
- **参数**：
  - id: 表情包 ID
- **返回**：成功/失败信息 JSON

#### 3.6.5 获取表情包分类

- **URL**：`/api/stickers/categories`
- **方法**：GET
- **权限**：登录用户
- **返回**：表情包分类列表 JSON

#### 3.6.6 获取表情包合集中的表情

- **URL**：`/api/stickers/pack/{code}`
- **方法**：GET
- **权限**：登录用户
- **参数**：
  - code: 表情包合集码
- **返回**：表情合集中的表情列表 JSON

### 3.7 系统设置相关 API

#### 3.7.1 获取系统设置

- **URL**：`/api/settings`
- **方法**：GET
- **权限**：管理员或超级管理员
- **返回**：系统设置 JSON（包含 general、security、password\_strength\_options、card\_layout\_options）

#### 3.7.2 更新通用设置

- **URL**：`/api/settings/general`
- **方法**：PUT
- **权限**：管理员或超级管理员
- **参数**：
  - home\_display: 首页显示（'nickname' 或 'username'）
  - allow\_nickname: 是否允许设置昵称
  - nickname\_min\_length: 昵称最小长度
  - nickname\_max\_length: 昵称最大长度
  - sidebar\_default\_expanded: 导航栏默认展开
  - card\_layout: 卡片布局（'1x3'、'1x4'、'2x3'）
- **返回**：成功/失败信息 JSON

#### 3.7.3 更新安全设置

- **URL**：`/api/settings/security`
- **方法**：PUT
- **权限**：管理员或超级管理员（超级管理员可修改所有设置，管理员只能修改部分）
- **参数**：
  - username\_manual\_min: 手动添加用户名最小长度（仅超管）
  - username\_manual\_max: 手动添加用户名最大长度（仅超管）
  - username\_register\_min: 自助注册用户名最小长度
  - username\_register\_max: 自助注册用户名最大长度
  - password\_strength: 密码强度（1-4）
  - allow\_weak\_password: 是否允许弱密码
  - allow\_self\_password\_reset: 是否允许自助找回密码
  - allow\_change\_password: 是否允许改密码
- **返回**：成功/失败信息 JSON

#### 3.7.4 重置系统设置

- **URL**：`/api/settings/reset`
- **方法**：POST
- **权限**：超级管理员
- **返回**：成功/失败信息 JSON

### 3.8 随身听相关 API

#### 3.8.1 搜索歌曲

- **URL**：`/api/ncm/search`
- **方法**：GET
- **权限**：登录用户
- **参数**：
  - keywords: 搜索关键词
  - limit: 返回数量（可选，默认 30）
- **返回**：歌曲列表 JSON

#### 3.8.2 获取歌曲详情

- **URL**：`/api/ncm/song/detail`
- **方法**：GET
- **权限**：登录用户
- **参数**：
  - ids: 歌曲 ID（多个用逗号分隔）
- **返回**：歌曲详情列表 JSON

#### 3.8.3 获取歌曲播放地址

- **URL**：`/api/ncm/song/url`
- **方法**：GET
- **权限**：登录用户
- **参数**：
  - id: 歌曲 ID
- **返回**：播放地址 JSON

#### 3.8.4 获取推荐歌单

- **URL**：`/api/ncm/personalized`
- **方法**：GET
- **权限**：登录用户
- **参数**：
  - limit: 返回数量（可选，默认 10）
- **返回**：推荐歌单列表 JSON

#### 3.8.5 获取热搜列表

- **URL**：`/api/ncm/hot-search`
- **方法**：GET
- **权限**：登录用户
- **返回**：热搜列表 JSON

#### 3.8.6 获取歌单详情

- **URL**：`/api/ncm/playlist/detail`
- **方法**：GET
- **权限**：登录用户
- **参数**：
  - id: 歌单 ID
- **返回**：歌单详情 JSON

#### 3.8.7 缓存音乐到本地

- **URL**：`/api/ncm/cache-music`
- **方法**：POST
- **权限**：登录用户
- **参数**：
  - id: 歌曲 ID
- **返回**：缓存文件路径 JSON

#### 3.8.8 缓存封面图片

- **URL**：`/api/ncm/cache-cover`
- **方法**：POST
- **权限**：登录用户
- **参数**：
  - url: 封面图片 URL
- **返回**：缓存文件路径 JSON

#### 3.8.9 获取缓存的音乐文件

- **URL**：`/music/<filename>`
- **方法**：GET
- **权限**：登录用户
- **返回**：音乐文件

#### 3.8.10 获取缓存的封面文件

- **URL**：`/music/cache/covers/<filename>`
- **方法**：GET
- **权限**：登录用户
- **返回**：封面图片文件

### 3.9 视频播放器相关 API

#### 3.9.1 获取视频列表

- **URL**：`/api/videos`
- **方法**：GET
- **权限**：登录用户
- **返回**：视频列表 JSON（name, size, size\_display）

#### 3.9.2 流式播放视频

- **URL**：`/api/video/<filename>`
- **方法**：GET
- **权限**：登录用户
- **返回**：视频文件流（支持 HTTP Range 请求）

### 3.10 B站视频相关 API

#### 3.10.1 获取首页推荐

- **URL**：`/api/bili/recommend`
- **方法**：GET
- **权限**：登录用户
- **返回**：推荐视频列表 JSON

#### 3.10.2 搜索视频

- **URL**：`/api/bili/search`
- **方法**：GET
- **权限**：登录用户
- **参数**：
  - keyword: 搜索关键词
  - page: 页码（可选）
- **返回**：搜索结果 JSON

#### 3.10.3 搜索UP主

- **URL**：`/api/bili/search_user`
- **方法**：GET
- **权限**：登录用户
- **参数**：
  - keyword: 搜索关键词
  - page: 页码（可选）
- **返回**：UP主列表 JSON

#### 3.10.4 获取UP主视频

- **URL**：`/api/bili/user_videos/<mid>`
- **方法**：GET
- **权限**：登录用户
- **参数**：
  - page: 页码（可选）
  - ps: 每页数量（可选）
- **返回**：UP主视频列表 JSON

#### 3.10.5 获取视频详情

- **URL**：`/api/bili/video/<bvid>`
- **方法**：GET
- **权限**：登录用户
- **返回**：视频详情 JSON

#### 3.10.6 启动下载

- **URL**：`/api/bili/download/<bvid>`
- **方法**：POST
- **权限**：登录用户
- **返回**：下载任务信息 JSON

#### 3.10.7 查询下载进度

- **URL**：`/api/bili/progress/<bvid>`
- **方法**：GET
- **权限**：登录用户
- **返回**：下载进度 JSON

#### 3.10.8 获取所有下载任务

- **URL**：`/api/bili/downloads`
- **方法**：GET
- **权限**：登录用户
- **返回**：下载任务列表 JSON

#### 3.10.9 获取已缓存视频

- **URL**：`/api/bili/cached`
- **方法**：GET
- **权限**：登录用户
- **返回**：已缓存视频列表 JSON

#### 3.10.10 删除缓存视频

- **URL**：`/api/bili/delete/<bvid>`
- **方法**：DELETE
- **权限**：登录用户
- **返回**：成功/失败信息 JSON

#### 3.10.11 播放缓存视频

- **URL**：`/api/bili/play/<bvid>`
- **方法**：GET
- **权限**：登录用户
- **返回**：视频文件流

#### 3.10.12 封面图片代理

- **URL**：`/api/bili/cover`
- **方法**：GET
- **权限**：登录用户
- **参数**：
  - url: 封面图片 URL
- **返回**：图片文件

### 3.11 公告相关 API

#### 3.11.1 获取所有公告

- **URL**：`/api/announcements`
- **方法**：GET
- **权限**：登录用户
- **参数**：
  - type: 公告类型（'all'、'banner'、'notification'，可选，默认 'all'）
- **返回**：公告列表 JSON（包含用户阅读状态）

#### 3.11.2 获取横幅公告

- **URL**：`/api/announcements/banner`
- **方法**：GET
- **权限**：登录用户
- **返回**：当前激活的横幅公告 JSON

#### 3.11.3 获取弹窗通知

- **URL**：`/api/announcements/notifications/popup`
- **方法**：GET
- **权限**：登录用户
- **返回**：需要弹窗显示的通知公告列表 JSON

#### 3.11.4 获取公告角标状态

- **URL**：`/api/announcements/badge`
- **方法**：GET
- **权限**：登录用户
- **返回**：角标状态 JSON（type: 'exclamation'/'number'/'dot'/'none'，count: 数字）

#### 3.11.5 关闭公告

- **URL**：`/api/announcements/<id>/dismiss`
- **方法**：POST
- **权限**：登录用户
- **返回**：成功/失败信息 JSON

#### 3.11.6 确认公告

- **URL**：`/api/announcements/<id>/confirm`
- **方法**：POST
- **权限**：登录用户
- **返回**：成功/失败信息 JSON

#### 3.11.7 不再提示

- **URL**：`/api/announcements/<id>/never-show`
- **方法**：POST
- **权限**：登录用户
- **返回**：成功/失败信息 JSON

#### 3.11.8 获取所有公告（管理）

- **URL**：`/api/announcements/manage`
- **方法**：GET
- **权限**：管理员或超级管理员
- **返回**：所有公告列表 JSON

#### 3.11.9 创建公告

- **URL**：`/api/announcements/manage`
- **方法**：POST
- **权限**：管理员或超级管理员
- **参数**：
  - title: 公告标题
  - content: 公告内容
  - announcement\_type: 公告类型（'banner' 或 'notification'）
  - priority: 优先级（'important'、'normal'、'minor'）
- **返回**：新公告信息 JSON

#### 3.11.10 更新公告

- **URL**：`/api/announcements/manage/<id>`
- **方法**：PUT
- **权限**：管理员或超级管理员
- **参数**：
  - title: 公告标题（可选）
  - content: 公告内容（可选）
  - priority: 优先级（可选）
- **返回**：更新后的公告信息 JSON

#### 3.11.11 删除公告

- **URL**：`/api/announcements/manage/<id>`
- **方法**：DELETE
- **权限**：管理员或超级管理员
- **返回**：成功/失败信息 JSON

### 3.12 Drop 相关 API

#### 3.12.1 发送 Drop

- **URL**：`/api/drop/send`
- **方法**：POST
- **权限**：登录用户
- **参数**：
  - content: 消息内容（最多 200 字）
- **返回**：Drop 信息 JSON

#### 3.12.2 轮询 Drop

- **URL**：`/api/drop/poll`
- **方法**：GET
- **权限**：登录用户
- **参数**：
  - last\_id: 上次获取的最后 ID（可选）
- **返回**：新 Drop 列表 JSON

#### 3.12.3 获取冷却状态

- **URL**：`/api/drop/status`
- **方法**：GET
- **权限**：登录用户
- **返回**：冷却状态 JSON（global\_cooldown, user\_cooldown, can\_send）

#### 3.12.4 获取 Drop 设置

- **URL**：`/api/drop/settings`
- **方法**：GET
- **权限**：登录用户
- **返回**：Drop 设置 JSON（enabled, blocked\_users）

#### 3.12.5 更新 Drop 设置

- **URL**：`/api/drop/settings`
- **方法**：PUT
- **权限**：登录用户
- **参数**：
  - enabled: 是否接收 Drop 消息
- **返回**：成功/失败信息 JSON

#### 3.12.6 添加黑名单

- **URL**：`/api/drop/blacklist`
- **方法**：POST
- **权限**：登录用户
- **参数**：
  - user\_id: 要屏蔽的用户 ID
- **返回**：成功/失败信息 JSON

#### 3.12.7 移除黑名单

- **URL**：`/api/drop/blacklist`
- **方法**：DELETE
- **权限**：登录用户
- **参数**：
  - user\_id: 要解除屏蔽的用户 ID
- **返回**：成功/失败信息 JSON

#### 3.12.8 搜索用户

- **URL**：`/api/drop/users/search`
- **方法**：GET
- **权限**：登录用户
- **参数**：
  - keyword: 搜索关键词
- **返回**：用户列表 JSON

### 3.13 导航相关 API

#### 3.13.1 获取导航项

- **URL**：`/api/nav/items`
- **方法**：GET
- **权限**：登录用户
- **参数**：
  - category: 分类（'tools' 或 'games'）
- **返回**：导航项列表 JSON

### 3.14 网页代理相关 API

#### 3.14.1 获取代理状态

- **URL**：`/api/proxy/status`
- **方法**：GET
- **权限**：登录用户
- **返回**：代理状态 JSON（running, port, host）

#### 3.14.2 启动代理服务

- **URL**：`/api/proxy/start`
- **方法**：POST
- **权限**：管理员或超级管理员
- **返回**：启动结果 JSON

#### 3.14.3 停止代理服务

- **URL**：`/api/proxy/stop`
- **方法**：POST
- **权限**：管理员或超级管理员
- **返回**：停止结果 JSON

## 4. WebSocket 事件

### 4.1 客户端发送事件

#### 4.1.1 加入房间

- **事件名**：`join_room`
- **参数**：
  - room: 房间名称
  - username: 用户名

#### 4.1.2 离开房间

- **事件名**：`leave_room`
- **参数**：
  - room: 房间名称
  - username: 用户名

#### 4.1.3 发送消息

- **事件名**：`send_message`
- **参数**：
  - room: 房间名称
  - username: 用户名
  - message: 消息内容

#### 4.1.4 获取消息历史

- **事件名**：`get_message_history`
- **参数**：
  - room: 房间名称
  - username: 用户名

### 4.2 服务器发送事件

#### 4.2.1 新消息

- **事件名**：`new_message`
- **参数**：
  - username: 发送者用户名
  - message: 消息内容
  - timestamp: 时间戳
  - is\_self: 是否为自己发送的消息

#### 4.2.2 用户加入

- **事件名**：`user_joined`
- **参数**：
  - username: 加入的用户名
  - message: 系统消息
  - timestamp: 时间戳

#### 4.2.3 用户离开

- **事件名**：`user_left`
- **参数**：
  - username: 离开的用户名
  - message: 系统消息
  - timestamp: 时间戳

#### 4.2.4 用户列表

- **事件名**：`user_list`
- **参数**：
  - room: 房间名称
  - users: 在线用户列表

#### 4.2.5 消息历史

- **事件名**：`message_history`
- **参数**：
  - room: 房间名称
  - messages: 消息历史列表

## 5. 开发流程

### 5.1 环境搭建

1. 克隆项目代码
2. 安装依赖：`pip install -r requirements.txt`
3. 启动开发服务器：`python app.py`
4. 访问 `http://127.0.0.1:5002`

### 5.2 代码规范

- **Python**：遵循 PEP 8 规范
- **JavaScript**：使用 ES6+ 语法
- **CSS**：使用 BEM 命名规范
- **HTML**：使用语义化标签
- **模块化**：遵循单一职责原则，每个模块专注于单一业务领域

### 5.3 模块开发指南

#### 5.3.1 新增业务模块

1. 在 `modules/` 目录下创建新模块目录
2. 创建 `__init__.py`，定义 Blueprint
3. 创建 `routes.py`，定义页面路由
4. 创建 `api.py`，定义 API 接口
5. 在 `app.py` 中注册 Blueprint

#### 5.3.2 新增数据模型

1. 在 `models/` 目录下创建新的模型文件
2. 定义模型类，继承 `db.Model`
3. 在 `models/__init__.py` 中导出模型

#### 5.3.3 新增工具函数

1. 在 `utils/` 目录下创建或编辑工具文件
2. 在 `utils/__init__.py` 中导出函数

### 5.4 测试

- **手动测试**：通过浏览器访问各个功能页面
- **API 测试**：使用 Postman 或类似工具测试 API 接口
- **WebSocket 测试**：使用浏览器开发者工具测试 WebSocket 连接
- **单元测试**：为每个模块编写独立的单元测试

### 5.5 部署

#### 5.5.1 本地部署

```bash
python app.py
```

#### 5.5.2 打包为 EXE

```bash
pyinstaller --onefile --name iFlyCompass app.py
```

#### 5.5.3 生产部署

建议使用 Gunicorn 作为 WSGI 服务器，Nginx 作为反向代理：

```bash
pip install gunicorn

gunicorn -w 4 -b 0.0.0.0:5002 app:app
```

## 6. 常见问题及解决方案

### 6.1 数据库连接问题

- **问题**：无法连接数据库
- **解决方案**：确保 `instance` 目录存在且可写

### 6.2 WebSocket 连接问题

- **问题**：WebSocket 连接失败
- **解决方案**：检查网络连接，确保服务器正在运行

### 6.3 权限问题

- **问题**：无法访问某些页面或功能
- **解决方案**：确保用户具有相应的权限，超级管理员可以在用户管理页面修改权限

### 6.4 Passkey 相关问题

- **问题**：Passkey 无效
- **解决方案**：检查 Passkey 是否已过期或达到最大使用次数

### 6.5 模块导入问题

- **问题**：模块导入失败
- **解决方案**：确保所有模块都正确导出，检查 `__init__.py` 文件

### 6.6 Blueprint 路由冲突

- **问题**：路由冲突或 404 错误
- **解决方案**：检查 Blueprint 的 url\_prefix 设置，确保路由定义正确

### 6.7 网页代理相关问题

- **问题**：代理服务无法启动
  - **解决方案**：检查 mitmproxy 是否已安装（`pip install mitmproxy`），确认端口 5003 未被占用
- **问题**：访问代理页面显示 403 Forbidden
  - **解决方案**：检查 Origin/Referer 头是否被正确设置，查看 `proxy_addon.py` 中的请求头修正逻辑
- **问题**：Next.js 网站 chunk 加载失败
  - **解决方案**：确认 `_rewrite_js` 方法中的 `__webpack_public_path__` 替换逻辑正常工作
- **问题**：图片或音频资源加载失败
  - **解决方案**：检查 hook.js 是否正确拦截了 Image/src 属性，确认 Service Worker 或 Hook 模式已启动

## 7. 贡献指南

### 7.1 代码提交

1. Fork 项目
2. 创建功能分支
3. 提交代码
4. 创建 Pull Request

### 7.2 代码审查

- 确保代码符合项目规范
- 确保所有测试通过
- 确保文档更新

### 7.3 版本发布

- 遵循语义化版本规范
- 更新 CHANGELOG
- 创建 Git 标签

