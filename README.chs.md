<div align="center">

<h1>小奥录音 OddMinutes</h1>

<p>
  <strong>让沟通的每一分钟，都被听见、被记录、被理解</strong>
</p>

<p>
  录音 · 转录 · 摘要 — 您的私有 AI 会议助手
</p>

<p>
  <a href="https://www.oddmeta.net" target="_blank">🏠 官方网站</a> ·
  <a href="https://minutes.oddmeta.net" target="_blank">🌐 在线演示</a> ·
  <a href="https://oddmeta.net/docs/oddminutes" target="_blank">📖 文档中心</a>
</p>

<p>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.12+-blue.svg" alt="Python 3.12+"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
  <a href="https://pypi.org/project/oddminutes/"><img src="https://img.shields.io/badge/pypi-oddminutes-blue.svg" alt="PyPI" /></a>
</p>

<p>
  <a href="README.md">English</a> <a href="README.chs.md">中文</a>
</p>

</div>

---

## ✨ 功能特性

- 🎙️ **双轨录音** — 同时录制麦克风 + 系统音频，带自动增益控制（AGC）
- 📝 **AI 实时转录** — 对接 OddASR，字级时间戳输出，首字时延低至 500ms
- 📑 **同声字幕** — 悬浮字幕窗口，支持拖动位置（默认关闭）
- 🤖 **智能摘要** — 支持 Ollama / OpenAI / Claude / Groq 多种 LLM 提供商
- 🔗 **音字联动** — 点击文字跳转音频对应位置，播放时高亮当前文字
- 📤 **多格式导出** — 音频、转录 PDF、摘要 PDF，打包 ZIP 下载，PDF 带水印
- 🗣️ **说话人编辑** — 编辑说话人名称，批量替换同会议中相同说话人
- 🔍 **全文搜索** — 跨会议转录内容全文检索
- ⏱️ **录音暂停/恢复** — 支持录音过程中随时暂停和恢复
- 🎨 **多主题** — 现代亮色、科技暗色、温暖办公、专注暗色四种主题
- 🔔 **通知系统** — 桌面通知 + 通知历史管理
- 👤 **用户认证** — 基于 Token 的用户认证体系
- 📋 **系统托盘** — Windows 系统托盘集成，快捷操作
- 🔄 **版本检查** — 自动检测 PyPI 新版本

---

## 🚀 快速开始

### 方式一：PyPI 安装（推荐）

```bash
# 基础安装
pip install OddMinutes

# Windows 用户（含系统托盘和快捷键支持）
pip install "OddMinutes[windows]"

# 启动
OddMinutes
```

### 方式二：源码运行

```bash
git clone https://github.com/oddmeta/oddminutes.git
cd oddminutes
pip install -r requirements.txt
copy .env.example .env
# 编辑 .env 配置 OddASR 和 LLM
python manage.py migrate
python manage.py init_defaults
python launcher.py
```

访问 `http://127.0.0.1:9011`

---

## 📐 技术架构

```
┌────────────────────────────────────┐
│  Vue 3 前端 / 原生 HTML/JS 前端     │
│  会议管理 · 录音控制 · 音字联动      │
│  AI 摘要 · 主题切换 · 通知系统      │
└──────────────┬─────────────────────┘
               │ HTTP / WebSocket
┌──────────────▼─────────────────────┐
│        Django 5 + DRF + Channels   │
│  core │ meetings │ recording       │
│  transcription │ summary │ users   │
│  system_app                      │
└──────────────┬─────────────────────┘
               │
┌──────────────▼─────────────────────┐
│  OddASR (语音识别)  │  Ollama/     │
│  127.0.0.1:9002    │  OpenAI/     │
│                    │  Claude      │
│                    │  (LLM 摘要)   │
└────────────────────────────────────┘
```

---

## 🛠️ 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | Django 5.0.7 |
| API | Django REST Framework 3.15.2 |
| WebSocket | Django Channels 4.1.0 + Daphne 4.1.2 |
| 前端 | Vue 3.4 / HTML5 + CSS3 + JavaScript |
| 语音识别 | OddASR（OpenAI 兼容接口）|
| AI 摘要 | pydantic-ai-slim（Ollama / OpenAI / Claude / Groq）|
| 音频处理 | pydub + numpy + scipy + FFmpeg |
| 数据库 | SQLite（默认）|
| 系统托盘 | pystray + pywin32 |

---

## 📋 外部依赖

| 服务 | 用途 | 状态 |
|------|------|------|
| **OddASR** | 语音识别转录 | **必需** |
| **FFmpeg** | 音频格式转换 | **必需** |
| **Ollama / LLM** | AI 摘要生成 | 可选 |

安装 OddASR：

```bash
pip install oddasr
oddasr-server
```

---

## ⚙️ 配置

关键环境变量（`.env`）：

```ini
DJANGO_SECRET_KEY=your-secret-key
ODDASR_URL=https://asr.oddmeta.net
ODDASR_API_KEY=your-key
ODDASR_MODEL=oddasr2_paraformer
AI_MODEL_CONFIGS=[{"provider":"ollama","model_name":"qwen3:8b","base_url":"http://localhost:11434"}]
```

更多配置详见 [文档中心](https://oddmeta.net/docs/oddminutes)。

---

## 📦 打包分发

### Windows 独立安装包

```bash
# 构建完整安装包（需安装 NSIS）
python build_installer.py

# 仅生成可执行文件夹
pyinstaller OddMinutes.spec --clean -y
```

---

## 📁 项目结构

```
OddMinutes/
├── core/                 # 首页、基础模型、音频工具
├── meetings/             # 会议 CRUD、搜索、导出
├── recording/            # 录音控制、WebSocket 电平推送
├── transcription/        # ASR 转录、实时转写
├── summary/              # AI 摘要、模板配置
├── system_app/           # 系统设置、托盘、通知
├── users/                # 用户认证
├── utils/                # PDF 生成、音频处理、标点恢复
├── meeting_minutes/      # Django 项目配置
├── oddminutes-frontend/  # Vue 3 前端
└── docs/                 # 文档与手册
```

---

## 📂 用户数据目录

通过 PyPI 安装后，用户数据和配置文件存储在以下位置：

| 系统 | 路径 |
|------|------|
| **Windows** | `%APPDATA%\Local\OddMeta\OddMinutes` |
| **Linux** | `~/.local/share/OddMeta/OddMinutes` |
| **macOS** | `~/Library/Application Support/OddMeta/OddMinutes` |

该目录包含：
- `.env` — 环境变量配置文件
- `db.sqlite3` — SQLite 数据库文件
- `media/` — 音频文件存储目录
- `logs/` — 日志文件目录

开发时可设置 `ODDMINUTES_DATA_DIR` 指定项目根目录。

---

## 🖥️ 前端功能

### 音字联动

前端实现了音频播放与文字的双向联动：
- **播放时高亮** — 音频播放到某个时间点，自动高亮对应的 word 和 segment
- **点击跳转** — 点击某个 word，音频跳转到对应时间点并开始播放
- **拖动同步** — 拖动音频进度条，自动滚动到对应的文字位置

### 转录编辑模式

- 逐段编辑转录文本（悬浮显示编辑按钮）
- 修改发言人名称，支持批量替换同一会议中的相同说话人
- 批量保存修改

### 实时电平监测

通过 WebSocket 实时显示麦克风和系统音频的电平：
- 实时电平条显示
- AGC 增益信息提示
- 峰值监测

### 搜索功能

支持在所有会议的转录内容中进行全文搜索，返回匹配的会议列表和上下文。

### 主题系统

- **modern-light** — 现代亮色主题
- **tech-dark** — 科技暗色主题
- **warm-office** — 温暖办公主题
- **focus-dark** — 专注暗色主题

### 通知系统

- 桌面通知（页面不可见时）
- 通知历史记录（最多保存 200 条）
- 未读通知计数，支持标记已读/全部已读
- 通知标题带会议名称前缀，方便定位

### 同声字幕

录音过程中可开启实时字幕功能：
- 结合 OddASR 实时转写，首字时延低至 500ms
- 悬浮字幕窗口，支持拖动调整位置
- 三行滚动显示，区分已确认文本和识别中文本
- 默认关闭，需在系统设置中开启（`ENABLE_LIVE_CAPTION`）

### 导出功能

- 音频文件（MP3）
- 转录文本 PDF（带产品水印和页眉页脚）
- AI 摘要 PDF（带产品水印和页眉页脚）
- 智能检查已有 PDF 缓存，避免重复生成
- 自动打包成 ZIP 下载，文件名使用会议名称
- 导出接口需登录后才能操作

---

## 📋 系统托盘功能

Windows 系统托盘支持以下操作：
- **显示窗口** — 打开浏览器访问应用
- **新建会议** — 创建新的会议记录
- **开始录音** — 启动录音（自动创建会议）
- **暂停录音** — 暂停当前录音
- **恢复录音** — 恢复暂停的录音
- **停止录音** — 停止录音并处理音频
- **退出** — 停止服务并退出

---

## ⚠️ 注意事项

1. **OddASR 服务**：使用前请确保 OddASR 服务已启动并正常运行
2. **FFmpeg**：安装 pydub 前需确保 FFmpeg 已安装并添加到系统 PATH
3. **Ollama**：使用本地 LLM 生成摘要时，需先 `ollama pull qwen3:8b` 下载模型
4. **音频设备权限**：首次使用录音功能时需授予麦克风权限
5. **系统音频录制**：Windows 下录制系统音频需要启用立体声混音设备或使用虚拟音频线缆
6. **数据目录**：默认数据存储在用户目录，开发时可设置 `ODDMINUTES_DATA_DIR` 指定项目根目录
7. **开发模式**：使用 `python manage.py runserver` 时建议添加 `--noreload` 参数避免多进程状态问题

---

## 📬 联系我们

| 渠道 | 账号 |
|------|------|
| 微信公众号 | 奥德元 |
| 微信 | oddmeta |
| 微博 | [oddmeta](https://weibo.com/oddmeta) |
| Twitter / X | [oddmet](https://x.com/oddmet) |

---

## 📄 License

MIT License

---

<div align="center">

Made with ❤️ by [OddMeta](https://oddmeta.net)

</div>

