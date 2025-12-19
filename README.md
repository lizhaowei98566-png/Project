# YouTuber Monitor & AI Analyst 🤖📺

这是一个全自动化的 YouTube 频道监控与分析工具。它能够自动检测指定频道的更新，下载视频音频，使用 OpenAI Whisper 进行语音转文字，然后调用 Google Gemini AI 对内容进行深度分析（包括核心观点、提及股票、关键事件等），最后生成一份精美的 HTML 报告并通过邮件发送给你。

## ✨ 功能特性

*   **🔍 自动监控**: 定期检查 YouTube RSS Feed，发现新视频发布。
*   **🎧 音频处理**: 自动下载视频音频并分割处理，支持长视频。
*   **📝 语音转写**: 集成 `openai-whisper` 模型，本地进行高精度语音转文字（支持繁简转换）。
*   **🧠 AI 深度分析**: 使用 Google Gemini模型生成结构化的分析报告。
*   **📧 邮件推送**: 将分析报告以 HTML 格式直接发送到你的邮箱，排版精美，易于阅读。

## 🛠️ 环境要求

*   **Python 3.8+**
*   **FFmpeg**: 用于音频格式转换和分割。
    *   macOS: `brew install ffmpeg`
    *   Windows: 下载并添加到系统 PATH 环境变量中。
    *   Linux: `sudo apt install ffmpeg`

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone <your-repo-url>
cd youtuber-monitor
```

### 2. 安装依赖

建议使用虚拟环境：

```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows
```

安装 Python 库：

```bash
pip install -r requirements.txt
```

### 3. 配置设置

你可以通过设置环境变量来配置项目，或者直接修改 `main.py` 中的默认值。

**必需的环境变量：**

| 变量名 | 描述 | 示例 |
|--------|------|------|
| `MAIL_USER` | 发件人邮箱地址 (推荐网易 163/126) | `example@163.com` |
| `MAIL_PASS` | 邮箱 SMTP 授权码 (非登录密码) | `your_auth_code` |
| `TARGET_MAIL` | 接收报告的邮箱地址 | `target@example.com` |
| `GEMINI_API_KEY` | Google Gemini API 密钥 | `AIzaSy...` |

**修改监控频道：**

打开 `main.py`，找到以下行修改 `CHANNEL_ID`：

```python
CHANNEL_ID = "UCFQsi7WaF5X41tcuOryDk8w"  # 替换为你关注的 YouTube 频道 ID
```

### 4. 运行项目

```bash
python main.py
```

程序运行逻辑：
1.  检查 RSS 是否有新视频。
2.  对比 `last_video_id.txt` 中的记录。
3.  如果是新视频：下载 -> 转写 -> 分析 -> 发邮件 -> 更新本地记录。
4.  如果是旧视频：直接跳过。

## ⏰ 自动化部署 (Cron Job)

为了实现自动监控，你可以使用系统的定时任务（如 macOS/Linux 的 Crontab）。

1.  打开 Crontab 编辑器：
    ```bash
    crontab -e
    ```

2.  添加一行配置（例如每小时执行一次）：
    ```bash
    0 * * * * /path/to/your/venv/bin/python /path/to/youtuber-monitor/main.py >> /path/to/youtuber-monitor/run.log 2>&1
    ```
    *请确保将路径替换为你实际的绝对路径。*

## 📂 项目结构

*   `main.py`: 主程序入口，包含所有核心逻辑。
*   `requirements.txt`: 项目依赖列表。
*   `last_video_id.txt`: 记录上一次处理的视频 ID，用于去重。
*   `downloads/`: 存放下载的音频、分割片段和生成的字幕/报告文件。

## ⚠️ 注意事项

*   **API 配额**: Gemini API 有免费额度限制，请留意使用情况。
*   **网络环境**: 访问 YouTube 和 Google API 可能需要适当的网络环境配置。
*   **Whisper 模型**: 首次运行会下载 Whisper 模型（默认 `base`），请保持网络畅通。


