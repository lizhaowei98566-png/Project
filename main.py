import os
import sys
import shutil
import subprocess
import warnings
import smtplib
import feedparser
import yt_dlp
import google.generativeai as genai
import whisper
from opencc import OpenCC
from email.mime.text import MIMEText
from email.header import Header
from email.mime.multipart import MIMEMultipart

# --- 配置区域 ---

# 1. 邮件配置
MAIL_USER = os.environ.get("MAIL_USER","li_hheng@163.com")
MAIL_PASS = os.environ.get("MAIL_PASS","UECmF7A9r4x3yvvS")
# 目标邮箱，多个邮箱请用英文逗号分隔
TARGET_MAIL = os.environ.get("TARGET_MAIL","li_hheng@163.com,li_hheng@qq.com")
SMTP_SERVER = "smtp.163.com"
SMTP_PORT = 465

# 2. YouTube 配置
CHANNEL_ID = "UCFQsi7WaF5X41tcuOryDk8w"
RSS_URL = f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}"
LOG_FILE = "last_video_id.txt"
DOWNLOAD_DIR = "downloads"

# 3. Gemini 配置
# 建议使用环境变量，这里保留你之前的硬编码作为备选
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyCW1aplCpsNscOF4w4xccglw9F8drYCMFI")
# 使用更稳定的模型名称
GEMINI_MODEL_NAME = 'gemini-3-pro-preview' 

# 忽略警告
warnings.filterwarnings("ignore")

# --- 功能模块 ---

def download_audio(video_url, video_id):
    """下载 YouTube 视频音频"""
    print(f"🚀 [下载] 开始下载: {video_url}")
    
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)

    output_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.mp3")
    
    if os.path.exists(output_path):
        print(f"⚠️ [下载] 文件已存在，跳过下载: {output_path}")
        return output_path

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': os.path.join(DOWNLOAD_DIR, '%(id)s.%(ext)s'),
        'ignoreerrors': True,
        'quiet': True, 
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        
        if os.path.exists(output_path):
            print(f"✅ [下载] 完成: {output_path}")
            return output_path
        else:
            print("❌ [下载] 文件未生成")
            return None
    except Exception as e:
        print(f"❌ [下载] 出错: {e}")
        return None

def split_audio(input_file, output_dir, segment_time=300):
    """使用 ffmpeg 分割音频"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    output_pattern = os.path.join(output_dir, "segment_%03d.mp3")
    
    cmd = [
        'ffmpeg', '-y', '-i', input_file, '-f', 'segment',
        '-segment_time', str(segment_time), '-reset_timestamps', '1',
        output_pattern
    ]
    
    # print(f"✂️ [分割] 正在分割音频...")
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    
    return sorted([os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.startswith("segment_")])

def transcribe_audio(mp3_path, txt_path):
    """使用 Whisper 转录音频"""
    print(f"🎧 [转录] 开始转录: {mp3_path}")
    
    if os.path.exists(txt_path):
        print(f"⚠️ [转录] 字幕文件已存在，跳过: {txt_path}")
        return True

    temp_dir = os.path.join(DOWNLOAD_DIR, "temp_segments")
    
    try:
        # 1. 分割音频
        segments = split_audio(mp3_path, temp_dir)
        
        # 2. 加载模型
        print("🤖 [转录] 加载 Whisper 模型 (base)...")
        model = whisper.load_model("base")
        cc = OpenCC('t2s')
        
        full_text = ""
        
        total = len(segments)
        for i, seg in enumerate(segments):
            print(f"   -> 处理片段 {i+1}/{total}...")
            result = model.transcribe(seg, initial_prompt="简体中文")
            text = cc.convert(result["text"])
            full_text += text + "\n"
            
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(full_text)
            
        print(f"✅ [转录] 完成，已保存: {txt_path}")
        return True
        
    except Exception as e:
        print(f"❌ [转录] 失败: {e}")
        return False
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

def analyze_content(transcript_path):
    """使用 Gemini 分析字幕"""
    print(f"🧠 [分析] 开始分析字幕...")
    
    if not GEMINI_API_KEY:
        print("❌ [分析] 缺少 API Key")
        return None

    genai.configure(api_key=GEMINI_API_KEY)
    
    try:
        model = genai.GenerativeModel(GEMINI_MODEL_NAME)
        
        with open(transcript_path, 'r', encoding='utf-8') as f:
            text = f.read()
            
        if not text.strip():
            return "字幕文件为空，无法分析。"

        prompt = f"""
        请分析以下 YouTube 视频的字幕内容，并生成一份详细的中文报告。
        
        **重要要求：请直接输出 HTML 代码。** 
        不要输出 Markdown，不要输出 ```html 代码块标记。
        只输出 HTML 标签内容（例如 <h3>, <p>, <ul>, <li>, <strong> 等），以便我直接嵌入到邮件正文中。
        
        报告应包含以下部分（请使用 HTML 标题标签 <h3> 或 <h4>）：
        1.  核心纲要 (Executive Summary): 简要总结视频的主要观点和结论。
        2.  关键事件 (Key Events): 列出视频中提到的重要新闻、事件或数据发布。
        3.  提及股票 (Stocks Mentioned): 列出所有提到的股票代码或公司名称，并简述博主对它们的看法（看多/看空/中性）及理由。
        4.  详细分析 (Detailed Analysis): 对视频内容的深入解读。

        字幕内容如下：
        {text} 
        """        
        response = model.generate_content(prompt)
        report = response.text
        print("✅ [分析] 报告生成成功")
        return report
        
    except Exception as e:
        print(f"❌ [分析] 失败: {e}")
        return f"分析过程中发生错误: {e}"

def send_email(video_title, video_link, report_content):
    """发送带有分析报告的邮件"""
    print("📧 [邮件] 正在发送邮件...")
    
    if not (MAIL_USER and MAIL_PASS and TARGET_MAIL):
        print("❌ [邮件] 邮箱配置缺失，无法发送。")
        return False

    # LLM 直接生成了 HTML，无需转换
    html_report = report_content
    
    # 构建美化后的 HTML 邮件内容
    html_content = f"""
    <html>
      <head>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; }}
            h1, h2, h3 {{ color: #2c3e50; margin-top: 20px; }}
            ul, ol {{ padding-left: 20px; }}
            li {{ margin-bottom: 8px; }}
            p {{ margin-bottom: 10px; }}
            strong {{ color: #d35400; }}
            blockquote {{ border-left: 4px solid #ddd; padding-left: 15px; color: #777; }}
            .report-container {{ background-color: #f9f9f9; padding: 20px; border-radius: 8px; border: 1px solid #e1e1e1; }}
            .header {{ margin-bottom: 20px; }}
            .footer {{ font-size: 12px; color: #999; margin-top: 30px; text-align: center; border-top: 1px solid #eee; padding-top: 10px; }}
            a {{ color: #3498db; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
        </style>
      </head>
      <body>
        <div class="header">
            <h2>👋 新视频发布: {video_title}</h2>
            <p><b>观看链接:</b> <a href="{video_link}">{video_link}</a></p>
        </div>
        
        <h3>🤖 AI 分析报告</h3>
        <div class="report-container">
            {html_report}
        </div>
        
        <div class="footer">
            <p>Generated by YouTuber Monitor Bot</p>
        </div>
      </body>
    </html>
    """
    
    # 处理多收件人 (支持逗号分隔)
    target_emails = [email.strip() for email in TARGET_MAIL.split(',') if email.strip()]

    msg = MIMEMultipart()
    msg['Subject'] = Header(f"【AI日报】{video_title}", 'utf-8')
    msg['From'] = MAIL_USER
    msg['To'] = ", ".join(target_emails)
    
    msg.attach(MIMEText(html_content, 'html', 'utf-8'))

    try:
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        server.login(MAIL_USER, MAIL_PASS)
        server.sendmail(MAIL_USER, target_emails, msg.as_string())
        server.quit()
        print(f"✅ [邮件] 发送成功！收件人: {target_emails}")
        return True
    except Exception as e:
        print(f"❌ [邮件] 发送失败: {e}")
        return False

def main():
    # 1. 检查更新
    print(f"🔍 正在检查 RSS 更新: {RSS_URL}")
    try:
        feed = feedparser.parse(RSS_URL)
    except Exception as e:
        print(f"❌ RSS 解析失败: {e}")
        return

    if not feed.entries:
        print("⚠️ 未获取到 RSS 数据")
        return

    latest_video = feed.entries[0]
    video_id = latest_video.yt_videoid
    video_title = latest_video.title
    video_link = latest_video.link
    
    print(f"📅 最新视频: {video_title} (ID: {video_id})")

    # 读取本地记录
    old_id = ""
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            old_id = f.read().strip()
            
    if video_id == old_id:
        print("✅ 已经是最新视频，无需处理。")
        # 为了测试方便，如果你想强制运行，可以注释掉下面这行
        return 

    print("🆕 发现新视频，开始处理流程...")

    # 2. 下载音频
    mp3_path = download_audio(video_link, video_id)
    if not mp3_path:
        return

    # 3. 转录文字
    txt_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.txt")
    if not transcribe_audio(mp3_path, txt_path):
        return

    # 4. AI 分析
    report = analyze_content(txt_path)
    if not report:
        report = "分析失败，请检查日志。"
        
    # 保存报告到本地备份
    report_path = os.path.join(DOWNLOAD_DIR, f"{video_id}_report.md")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)

    # 5. 发送邮件
    if send_email(video_title, video_link, report):
        # 只有邮件发送成功才更新 ID，防止漏发
        with open(LOG_FILE, "w") as f:
            f.write(video_id)
        print("🎉 流程结束，本地记录已更新。")
    else:
        print("⚠️ 流程结束，但邮件发送失败。")

if __name__ == "__main__":
    main()
