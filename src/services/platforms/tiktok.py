from .base import PlatformDownloader
from typing import Optional, List, Dict, Union
import os, json

class TikTokDownloader(PlatformDownloader):
    def __init__(self, download_dir: str):
        self.download_dir = download_dir
        os.makedirs(self.download_dir, exist_ok=True)

    def extract_info(self, url: str, process: bool = False) -> dict:
        import yt_dlp
        ydl_opts = {'quiet': True, 'extract_flat': 'in_playlist', 'skip_download': not process}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=process)
            print("[yt-dlp INFO][TikTok] extract_info info_dict:", json.dumps(info, ensure_ascii=False, indent=2))
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
            abs_download_dir = os.path.abspath(self.download_dir)
            outtmpl = os.path.join(abs_download_dir, '%(title)s.%(ext)s')
            print(f"[yt-dlp DEBUG][TikTok] outtmpl: {outtmpl}")
            # 1. استخرج info_dict فقط (بدون تحميل)
            ydl_opts_info = {
                'quiet': True,
                'skip_download': True,
                'noplaylist': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
                info = ydl.extract_info(url, download=False)
            formats = info.get('formats', [])
            # 2. ابحث عن صيغة بدون watermark
            no_wm_formats = [f for f in formats if f.get('format_id') != 'download' and 'watermark' not in (f.get('format_note') or '').lower()]
            if not no_wm_formats:
                return {'error': 'no_nowatermark', 'details': 'لا توجد صيغة بدون علامة مائية متاحة لهذا الفيديو.'}
            # 3. جرب تحميل كل صيغة بدون watermark
            for fmt in no_wm_formats:
                try:
                    ydl_opts = {
                        'outtmpl': outtmpl,
                        'format': fmt['format_id'],
                        'quiet': True,
                        'noplaylist': True,
                        'merge_output_format': 'mp4',
                        'retries': 2,
                    }
                    before_files = set(glob(os.path.join(abs_download_dir, '*.mp4')))
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        result = ydl.download([url])
                    after_files = set(glob(os.path.join(abs_download_dir, '*.mp4')))
                    mp4_files = list(glob(os.path.join(abs_download_dir, '*.mp4')))
                    if not mp4_files:
                        continue
                    latest_file = max(mp4_files, key=os.path.getmtime)
                    print(f"[yt-dlp DEBUG][TikTok] Latest mp4 file after download: {latest_file}")
                    with open(latest_file, 'rb') as f:
                        file_data = io.BytesIO(f.read())
                    os.remove(latest_file)
                    file_data.seek(0)
                    return file_data
                except Exception as e:
                    print(f"[yt-dlp ERROR][TikTok] Failed to download format {fmt['format_id']}: {e}")
            return {'error': 'download_failed', 'details': 'فشل تحميل جميع الصيغ بدون علامة مائية.'}
        except Exception as e:
            print(f"[yt-dlp ERROR][TikTok] Exception: {e}")
            return {'error': 'exception', 'details': str(e)}

    def can_handle(self, url: str) -> bool:
        return 'tiktok.com' in url
