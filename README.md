# 小奥会议纪要 OddMinutes - 您的会议纪要小助手

一个基于 Django 的智能会议纪要系统，支持实时录音、AI 转录、智能摘要生成和音字联动功能。

## 功能特性

- 🎙️ **麦克风 + 系统音频双轨录制** - 支持同时录制麦克风和系统音频，带自动增益控制(AGC)
- 📝 **AI 实时转录** - 对接 OddASR 服务，支持字级时间戳输出
- 🤖 **智能摘要生成** - 支持 Ollama/OpenAI/Claude/Groq 多种 LLM 提供商
- 🔗 **音字联动** - 点击文字跳转到音频对应位置，播放时高亮当前文字
- 📤 **多格式导出** - 支持 TXT、Markdown、JSON 格式导出
- 🔍 **全文搜索** - 支持转录内容搜索
- ⏱️ **录音暂停/恢复** - 支持录音过程中暂停和恢复

## 快速安装

```bash
# 基础安装
pip install OddMinutes

# Windows 用户（包含系统托盘和快捷键支持）
pip install OddMinutes[windows]

# 启动程序
OddMinutes
```

首次运行时，程序会自动初始化数据库并创建用户数据目录。

## 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                        前端 (HTML/CSS/JS)                    │
│  - 会议列表管理                                              │
│  - 录音控制面板（电平监测）                                   │
│  - 转录内容展示（音字联动）                                    │
│  - AI 摘要展示                                               │
│  - 笔记编辑                                                  │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP / WebSocket
┌──────────────────────▼──────────────────────────────────────┐
│                      Django 后端                             │
│  ┌─────────┐ ┌──────────┐ ┌────────────┐ ┌──────────┐       │
│  │  core   │ │ meetings │ │ recording  │ │summary   │       │
│  │ 首页/    │ │ 会议CRUD │ │ 音频录制   │ │ AI摘要   │       │
│  │ 路由    │ │ 搜索/导出 │ │ 电平监测   │ │ 模板配置  │       │
│  └─────────┘ └──────────┘ └────────────┘ └──────────┘       │
│  ┌──────────────┐ ┌───────────┐ ┌──────────────┐            │
│  │ transcription│ │ system_app│ │   Channels   │            │
│  │ ASR转录      │ │ 系统设置  │ │ WebSocket    │            │
│  │ 音频上传     │ │ 通知/更新 │ │ 实时电平推送  │            │
│  └──────────────┘ └───────────┘ └──────────────┘            │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP API
┌──────────────────────▼──────────────────────────────────────┐
│                    外部服务依赖                               │
│  ┌──────────────┐         ┌──────────────────┐             │
│  │   OddASR     │         │   Ollama/OpenAI  │             │
│  │ (语音识别)    │         │    (LLM 摘要)    │             │
│  │ 127.0.0.1:9002│        │ localhost:11434  │             │
│  └──────────────┘         └──────────────────┘             │
└─────────────────────────────────────────────────────────────┘
```

## 项目结构

```
OddMinutes/
├── OddMinutes/              # Python 包入口（用于 PyPI 安装）
│   ├── __init__.py          # 包初始化
│   ├── launcher.py          # 命令行启动器入口
│   ├── manage.py            # Django 管理命令（引导用）
│   └── .env.example         # 环境变量示例（引导用）
├── core/                    # 核心模块（首页、基础模型）
│   ├── models.py            # BaseModel 抽象基类
│   ├── views.py             # 首页和会议详情视图
│   ├── urls.py              # 路由配置
│   ├── audio_utils.py       # 音频转换工具（WAV→MP3）
│   └── management/commands/init_defaults.py  # 初始化命令
├── meetings/                # 会议管理模块
│   ├── models.py            # Meeting、TranscriptSegment、SummaryProcess、MeetingExport
│   ├── views.py             # 会议 CRUD、搜索、导出、清理
│   ├── urls.py              # 路由配置
│   └── serializers.py       # DRF 序列化器
├── recording/               # 录音模块
│   ├── models.py            # RecordingSession、RecordingCheckpoint、AudioDevice
│   ├── views.py             # 录音控制 API
│   ├── urls.py              # 路由配置
│   ├── audio_recorder.py    # 音频录制器（双轨、AGC、混音）
│   ├── consumers.py         # WebSocket 电平推送消费者
│   └── routing.py           # WebSocket 路由
├── transcription/           # 转录模块
│   ├── models.py            # TranscriptionJob、TranscriptionConfig
│   ├── views.py             # 转录 API（文件转录、重新转录、上传）
│   ├── urls.py              # 路由配置
│   ├── oddasr_client.py     # OddASR OpenAI 兼容客户端
│   ├── consumers.py         # WebSocket 实时转录消费者
│   └── routing.py           # WebSocket 路由
├── summary/                 # AI 摘要模块
│   ├── models.py            # SummaryTemplate、AIModelConfig、SummaryLanguagePreference
│   ├── views.py             # 摘要生成 API
│   ├── urls.py              # 路由配置
│   └── ai_processor.py      # AI 摘要处理器（支持多提供商、chunk 分段处理）
├── system_app/              # 系统设置模块
│   ├── models.py            # SystemSettings、UpdateInfo、NotificationLog
│   ├── views.py             # 系统设置、通知、更新检查 API
│   ├── urls.py              # 路由配置
│   └── tray_icon.py         # 系统托盘图标
├── meeting_minutes/         # Django 项目配置
│   ├── settings.py          # 项目配置
│   ├── urls.py              # 全局路由
│   ├── asgi.py              # ASGI 入口（支持 WebSocket）
│   ├── static/              # 静态资源
│   │   ├── css/style.css    # 样式文件
│   │   ├── js/app.js        # 前端逻辑
│   │   └── favicon.ico      # 网站图标
│   └── templates/           # HTML 模板
│       └── core/
│           ├── index.html   # 主页面
│           └── meeting_detail.html  # 会议详情页
├── media/                   # 媒体文件存储（音频文件）
├── logs/                    # 日志文件
├── .env                     # 环境变量配置
├── .env.example             # 环境变量示例
├── requirements.txt         # Python 依赖
├── launcher.py              # 根目录启动脚本
├── manage.py                # Django 管理命令
└── pyproject.toml           # PyPI 打包配置
```

## 外部服务依赖

### 1. OddASR 语音识别服务

安装 OddASR 服务

```powershell
pip install oddasr
```

运行 OddASR 服务

```powershell
oddasr-server
```

**必需** - 用于音频转录，提供 OpenAI 兼容的 `/v1/audio/transcriptions` 接口。

- 默认地址：`http://127.0.0.1:9002`
- 配置文件：`.env` 中的 `ODDASR_HOST` 和 `ODDASR_PORT`
- 支持 `verbose_json` 响应格式，返回段级和字级时间戳

### 2. Ollama / LLM 服务

**可选** - 用于 AI 摘要生成。

- 默认地址：`http://localhost:11434`（Ollama）
- 支持提供商：Ollama（本地）、OpenAI、Claude、Groq
- 通过 `pydantic-ai` 库统一调用

### 3. FFmpeg

**必需** - `pydub` 依赖 FFmpeg 进行音频格式转换。

## 安装与运行

### 环境要求

- Python 3.12+
- FFmpeg（需添加到系统 PATH）
- OddASR 服务（运行中）
- Ollama（可选，用于本地 LLM 摘要）

### PyPI 安装（推荐）

```powershell
# 基础安装
pip install OddMinutes

# Windows 用户（包含系统托盘和快捷键支持）
pip install OddMinutes[windows]
```

**启动程序**

```powershell
OddMinutes
```

首次运行时，程序会自动完成以下操作：
- 初始化数据库（自动执行 migrate）
- 创建用户数据目录（位于 `%APPDATA%\Local\OddMeta\OddMinutes` 或 `~/.local/share/OddMeta/OddMinutes`）
- 复制必要的配置文件

### 开发安装（从源码）

```powershell
git clone https://github.com/oddmeta/OddMinutes.git
cd OddMinutes

# 安装开发依赖
pip install -r requirements.txt

# 安装 Windows 额外依赖（Windows 用户）
pip install pywin32 keyboard pynput

# 配置环境变量
copy .env.example .env
```

编辑 `.env` 文件，设置关键配置：

```ini
# Django 配置
DJANGO_SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# OddASR 配置（必需）
ODDASR_HOST=127.0.0.1
ODDASR_PORT=9002

# Ollama 配置（可选，用于本地 LLM）
OLLAMA_HOST=http://localhost:11434

# 音频配置
AUDIO_SAMPLE_RATE=16000
AUDIO_CHANNELS=1
AUDIO_CHUNK_DURATION=5

# 会议设置
AUTO_CLEANUP_DAYS=7
MAX_AUDIO_FILE_SIZE=500
```

**初始化数据库**

```powershell
python manage.py migrate
python manage.py init_defaults
```

**启动服务**

```powershell
# 使用启动脚本
start.bat

# 或直接运行
python manage.py runserver 127.0.0.1:9011

# 或使用命令行入口
python launcher.py
```

服务启动后访问：`http://127.0.0.1:9011`

### 用户数据目录

通过 PyPI 安装后，用户数据和配置文件存储在以下位置：

- **Windows**: `%APPDATA%\Local\OddMeta\OddMinutes` 或 `C:\Users\<用户名>\AppData\Local\OddMeta\OddMinutes`
- **Linux**: `~/.local/share/OddMeta/OddMinutes`
- **macOS**: `~/Library/Application Support/OddMeta/OddMinutes`

该目录包含：
- `.env` - 环境变量配置文件
- `db.sqlite3` - SQLite 数据库文件
- `media/` - 音频文件存储目录
- `logs/` - 日志文件目录

## 配置说明

| 环境变量 | 默认值 | 使用模块 | 说明 |
|---------|--------|---------|------|
| `DJANGO_SECRET_KEY` | django-insecure-change-me | 全局 | Django 安全密钥 |
| `DEBUG` | True | 全局 | 调试模式 |
| `ALLOWED_HOSTS` | localhost,127.0.0.1 | 全局 | 允许的主机 |
| `ODDASR_HOST` | 127.0.0.1 | transcription | OddASR 服务主机 |
| `ODDASR_PORT` | 9002 | transcription | OddASR 服务端口 |
| `OLLAMA_HOST` | http://localhost:11434 | summary | Ollama 服务地址 |
| `AUDIO_SAMPLE_RATE` | 16000 | recording | 音频采样率 |
| `AUDIO_CHANNELS` | 1 | recording | 音频通道数 |
| `AUDIO_CHUNK_DURATION` | 5 | recording | 音频块持续时间（秒） |
| `AUTO_CLEANUP_DAYS` | 7 | meetings | 自动清理天数 |
| `MAX_AUDIO_FILE_SIZE` | 500 | 全局 | 最大音频文件大小（MB） |

## API 接口

### 会议管理 `/api/meetings/`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/meetings/` | 获取会议列表 |
| POST | `/api/meetings/` | 创建新会议 |
| GET | `/api/meetings/{id}/` | 获取会议详情 |
| PUT/PATCH | `/api/meetings/{id}/` | 更新会议信息 |
| DELETE | `/api/meetings/{id}/` | 删除会议 |
| POST | `/api/meetings/{id}/export/` | 导出会议（支持 txt/md/json） |
| POST | `/api/meetings/search/` | 搜索转录内容 |
| POST | `/api/meetings/cleanup/` | 清理旧会议 |
| PATCH | `/api/meetings/transcript-segments/{id}/` | 更新转录片段 |

### 录音控制 `/api/recording/`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/recording/devices/` | 获取音频设备列表 |
| POST | `/api/recording/start/` | 开始录音 |
| POST | `/api/recording/pause/` | 暂停录音 |
| POST | `/api/recording/resume/` | 恢复录音 |
| POST | `/api/recording/stop/` | 停止录音 |
| GET | `/api/recording/level/` | 获取当前音频电平 |
| GET | `/api/recording/status/` | 获取录音状态 |

### 转录服务 `/api/transcription/`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/transcription/transcribe/` | 转录音频文件 |
| POST | `/api/transcription/retranscribe/` | 重新转录 |
| POST | `/api/transcription/upload/` | 上传音频并转录 |
| GET | `/api/transcription/status/{id}/` | 获取转录任务状态 |
| GET/POST | `/api/transcription/config/` | 获取/设置转录配置 |
| GET | `/api/transcription/oddasr-status/` | 检查 OddASR 服务状态 |

### AI 摘要 `/api/summary/`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/summary/generate/` | 生成会议摘要 |
| GET | `/api/summary/status/{id}/` | 获取摘要状态 |
| POST | `/api/summary/regenerate/` | 重新生成摘要 |
| GET/POST | `/api/summary/templates/` | 获取/创建摘要模板 |
| GET/POST/PUT/DELETE | `/api/summary/model-config/` | AI 模型配置管理 |
| GET/POST | `/api/summary/language-preferences/` | 语言偏好设置 |
| POST | `/api/summary/stream/` | 流式生成摘要（SSE） |

### 系统设置 `/api/system/`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET/POST | `/api/system/settings/` | 获取/更新系统设置 |
| GET | `/api/system/check-updates/` | 检查更新 |
| GET | `/api/system/notifications/` | 获取通知列表 |
| POST | `/api/system/notifications/read/` | 标记通知为已读 |
| POST | `/api/system/notifications/send/` | 发送系统通知 |
| POST | `/api/system/onboarding/complete/` | 完成首次引导 |
| GET | `/api/system/info/` | 获取系统信息 |

## WebSocket 接口

### 音频电平推送

- **路径**: `ws://host:port/ws/recording/level/`
- **用途**: 实时推送麦克风和系统音频电平数据
- **推送频率**: 10 次/秒

**推送数据格式**:
```json
{
  "mic_level": 0.1234,
  "system_level": 0.0567,
  "mixed_level": 0.1234,
  "peak_mic": 0.2345,
  "peak_system": 0.0890,
  "status": "recording",
  "duration": 45.5,
  "agc": {
    "enabled": true,
    "mic_gain": 1.5,
    "system_gain": 1.0,
    "target_rms": 8000
  }
}
```

### 实时转录

- **路径**: `ws://host:port/ws/transcription/realtime/`
- **用途**: 实时音频转录

## 数据流详解

### 完整流程示例

1. **创建会议** → POST `/api/meetings/` → 创建 Meeting 记录（status=recording）

2. **开始录音** → POST `/api/recording/start/`
   - 选择麦克风设备和可选的系统音频设备
   - `AudioRecorder.start()` 启动双轨录制
   - 开启 AGC（自动增益控制），保持目标 RMS 电平 8000
   - 实时计算音频电平，通过 WebSocket 推送到前端

3. **录音过程**
   - 麦克风和系统音频分别采集（16kHz, 单声道, 16-bit）
   - 应用 AGC 增益控制
   - 混音处理（麦克风 55% + 系统音频 55%），带软压限防止削波
   - 每 5 秒生成音频块，触发转录回调

4. **停止录音** → POST `/api/recording/stop/`
   - 合并缓冲区数据，编码为 WAV 格式
   - 保存到 `media/audio/meetings/{date}/{filename}.wav`
   - 自动转换为 MP3 格式（`audio_utils.convert_audio_to_mp3`）
   - 更新 Meeting 状态为 completed

5. **转录音频** → POST `/api/transcription/transcribe/`
   - 创建 TranscriptionJob（status=processing）
   - 后台线程调用 OddASR 客户端
   - 请求格式：`model=whisper-1`, `response_format=verbose_json`, `timestamp_granularities[]=word`
   - OddASR 返回包含 `segments` 和 `words` 的 JSON 数据

6. **保存转录结果**
   - 解析 segments，每个 segment 包含 text、speaker、start、end、words
   - 创建 TranscriptSegment 记录，words 字段存储字级时间戳
   - 更新 Meeting 状态为 completed

7. **生成摘要** → POST `/api/summary/generate/`
   - 创建 SummaryProcess（status=processing）
   - 合并所有转录文本
   - 按 chunk_size=5000、overlap=1000 分段
   - 每段调用 LLM（默认 Ollama/Qwen3-8B）生成结构化摘要
   - 聚合所有 chunk 的摘要结果

8. **结构化摘要格式**
   ```json
   {
     "MeetingName": "会议名称",
     "People": {"title": "参会人员", "blocks": [...]},
     "SessionSummary": {"title": "会议概要", "blocks": [...]},
     "CriticalDeadlines": {"title": "关键截止日期", "blocks": [...]},
     "KeyItemsDecisions": {"title": "关键事项与决策", "blocks": [...]},
     "ImmediateActionItems": {"title": "立即行动项", "blocks": [...]},
     "NextSteps": {"title": "后续步骤", "blocks": [...]},
     "MeetingNotes": {"meeting_name": "...", "sections": [...]}
   }
   ```

9. **前端渲染**
   - 转录内容按 speaker 合并显示
   - 每个 word 带有 data-start/data-end 属性（音字联动）
   - 音频播放时自动高亮当前 word 和 segment
   - 点击 word 跳转到对应时间点

## 数据库模型

### 核心模型关系

```
Meeting (会议)
├── transcriptions → TranscriptSegment[] (转录片段)
├── recording → RecordingSession (录音会话)
├── transcription_jobs → TranscriptionJob[] (转录任务)
├── summary_process → SummaryProcess (摘要处理)
└── exports → MeetingExport[] (导出记录)

TranscriptSegment (转录片段)
├── meeting → Meeting (所属会议)
└── words → JSON (字级时间戳数据)

SummaryProcess (摘要处理)
└── meeting → Meeting (所属会议)

RecordingSession (录音会话)
├── meeting → Meeting (所属会议)
└── checkpoints → RecordingCheckpoint[] (检查点)
```

### 关键字段说明

#### Meeting 模型

| 字段 | 类型 | 说明 |
|------|------|------|
| title | CharField | 会议标题 |
| status | CharField | 状态：recording/paused/completed/processing |
| audio_file | FileField | 音频文件路径 |
| audio_duration | FloatField | 音频时长（秒） |
| summary | JSONField | AI 摘要结果 |
| notes | TextField | 用户笔记 |
| language | CharField | 语言：auto/zh/en |

#### TranscriptSegment 模型

| 字段 | 类型 | 说明 |
|------|------|------|
| meeting | ForeignKey | 关联会议 |
| text | TextField | 转录文本 |
| speaker | CharField | 发言人 |
| audio_start_time | FloatField | 音频开始时间（秒） |
| audio_end_time | FloatField | 音频结束时间（秒） |
| duration | FloatField | 片段时长（秒） |
| is_final | BooleanField | 是否最终结果 |
| words | JSONField | 字级时间戳（OddASR verbose_json 返回） |

### words 字段结构（字级时间戳）

```json
[
  {"word": "你好", "start": 0.5, "end": 0.8, "probability": 0.98},
  {"word": "世界", "start": 0.9, "end": 1.2, "probability": 0.95}
]
```

## 前端功能

### 音字联动

前端实现了音频播放与文字的双向联动：

1. **播放时高亮**：音频播放到某个时间点，自动高亮对应的 word 和 segment
2. **点击跳转**：点击某个 word，音频跳转到对应时间点并开始播放
3. **拖动同步**：拖动音频进度条，自动滚动到对应的文字位置

### 转录编辑模式

支持对转录内容进行编辑：
- 编辑转录文本
- 修改发言人名称
- 批量保存修改

### 实时电平监测

通过 WebSocket 实时显示麦克风和系统音频的电平：
- 实时电平条显示
- AGC 增益信息提示
- 峰值监测

### 搜索功能

支持在所有会议的转录内容中进行全文搜索，返回匹配的会议列表和上下文。

## 技术栈

| 分类 | 技术 |
|------|------|
| 后端框架 | Django 5.0.7 |
| API 框架 | Django REST Framework 3.15.2 |
| WebSocket | Django Channels 4.1.0 |
| 数据库 | SQLite（默认） |
| 音频录制 | sounddevice |
| 音频处理 | pydub、numpy、scipy |
| 语音识别 | OddASR（OpenAI 兼容） |
| AI 摘要 | pydantic-ai（Ollama/OpenAI/Claude/Groq） |
| 前端 | HTML5、CSS3、JavaScript（原生） |

## 开发命令

```powershell
# 启动开发服务器
python manage.py runserver 127.0.0.1:9011

# 创建数据库迁移
python manage.py makemigrations

# 执行数据库迁移
python manage.py migrate

# 初始化默认数据
python manage.py init_defaults

# 创建超级用户
python manage.py createsuperuser

# 进入 Django Shell
python manage.py shell

# 运行测试
python manage.py test
```

## 注意事项

1. **OddASR 服务**：使用前请确保 OddASR 服务已启动并正常运行
2. **FFmpeg**：安装 pydub 前需确保 FFmpeg 已安装并添加到系统 PATH
3. **Ollama**：使用本地 LLM 生成摘要时，需先 `ollama pull qwen3:8b` 下载模型
4. **音频设备权限**：首次使用录音功能时需授予麦克风权限
5. **系统音频录制**：Windows 下录制系统音频需要启用立体声混音设备或使用虚拟音频线缆

## License

MIT License