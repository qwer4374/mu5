from .base import PlatformDownloader
from typing import Optional, List, Dict
import os, json

class YoutubeDownloader(PlatformDownloader):
    def __init__(self, download_dir: str):
        self.download_dir = download_dir
        os.makedirs(self.download_dir, exist_ok=True)

    def extract_info(self, url: str, process: bool = False) -> dict:
        import yt_dlp
        cookies_path = os.path.join('data', 'cookies', 'youtube_cookies.txt')
        ydl_opts = {
            'quiet': True,
            'extract_flat': 'in_playlist',
            'skip_download': not process
        }
        if os.path.exists(cookies_path):
            ydl_opts['cookiefile'] = cookies_path
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=process)
            print("[yt-dlp INFO][YouTube] extract_info info_dict:", json.dumps(info, ensure_ascii=False, indent=2))
            return info

    def get_formats(self, info: dict) -> List[Dict]:
        formats = info.get('formats', [])
        for fmt in formats:
            if not fmt.get('filesize') and not fmt.get('filesize_approx'):
                if 'url' in fmt and 'tbr' in fmt and 'duration' in info:
                    try:
                        tbr = fmt['tbr']
                        duration = info['duration']
                        size_bytes = int((tbr * 1000 / 8) * duration)
                        fmt['filesize_approx'] = size_bytes
                    except Exception:
                        pass
        return formats

    def download(self, url: str, audio_only: bool = False):
        try:
            import yt_dlp
            from glob import glob
            import io
            import os
            import subprocess
            abs_download_dir = os.path.abspath(self.download_dir)
            outtmpl = os.path.join(abs_download_dir, '%(title)s.%(ext)s')
            print(f"[yt-dlp DEBUG][YouTube] outtmpl: {outtmpl}")
            cookies_path = os.path.join('data', 'cookies', 'youtube_cookies.txt')
            ydl_opts = {
                'outtmpl': outtmpl,
                'quiet': True,
                'merge_output_format': 'mp4',
                'noplaylist': True,
                'format': 'bestvideo[height<=480]+bestaudio/best[height<=480]/best',
            }
            if os.path.exists(cookies_path):
                ydl_opts['cookiefile'] = cookies_path
            before_files = set(glob(os.path.join(abs_download_dir, '*.mp4')))
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            after_files = set(glob(os.path.join(abs_download_dir, '*.mp4')))
            mp4_files = list(glob(os.path.join(abs_download_dir, '*.mp4')))
            if not mp4_files:
                print("[yt-dlp ERROR][YouTube] No mp4 files found after download!")
                return None
            latest_file = max(mp4_files, key=os.path.getmtime)
            print(f"[yt-dlp DEBUG][YouTube] Latest mp4 file after download: {latest_file}")
            # إذا كان الملف أكبر من 50 ميجابايت، اضغطه بجودة أقل
            max_size = 50 * 1024 * 1024
            if os.path.getsize(latest_file) > max_size:
                compressed_file = latest_file.replace('.mp4', '_compressed.mp4')
                ffmpeg_path = os.path.join(os.path.dirname(__file__), '../../data/ffmpeg/ffmpeg.exe')
                ffmpeg_path = os.path.abspath(ffmpeg_path)
                print(f"[FFMPEG] Compressing video: {latest_file} -> {compressed_file}")
                cmd = [ffmpeg_path, '-i', latest_file, '-vf', 'scale=-2:480', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '32', '-c:a', 'aac', '-b:a', '96k', '-y', compressed_file]
                subprocess.run(cmd, check=True)
                os.remove(latest_file)
                latest_file = compressed_file
            with open(latest_file, 'rb') as f:
                file_data = io.BytesIO(f.read())
            os.remove(latest_file)
            file_data.seek(0)
            return file_data
        except Exception as e:
            print(f"[yt-dlp ERROR][YouTube] Unexpected exception in download: {e}")
            return None

    def can_handle(self, url: str) -> bool:
        return 'youtube.com' in url or 'youtu.be' in url
