from .base import PlatformDownloader
from typing import Optional, List, Dict
import os, json

class SnapchatDownloader(PlatformDownloader):
    def __init__(self, download_dir: str, cookies_path: Optional[str] = None):
        self.download_dir = download_dir
        self.cookies_path = cookies_path
        os.makedirs(self.download_dir, exist_ok=True)

    def extract_info(self, url: str, process: bool = False) -> dict:
        import yt_dlp
        ydl_opts = {'quiet': True, 'extract_flat': 'in_playlist', 'skip_download': not process}
        if self.cookies_path:
            ydl_opts['cookiefile'] = self.cookies_path
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=process)
            print("[yt-dlp INFO][Snapchat] extract_info info_dict:", json.dumps(info, ensure_ascii=False, indent=2))
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

    def can_handle(self, url: str) -> bool:
        return 'snapchat.com' in url or 'snapcdn.io' in url

    def download(self, url: str, audio_only: bool = False):
        try:
            import yt_dlp
            from glob import glob
            import io
            abs_download_dir = os.path.abspath(self.download_dir)
            outtmpl = os.path.join(abs_download_dir, '%(title)s.%(ext)s')
            print(f"[yt-dlp DEBUG][Snapchat] outtmpl: {outtmpl}")
            ydl_opts = {
                'outtmpl': outtmpl,
                'quiet': True,
                'merge_output_format': 'mp4',
                'noplaylist': True,
                'format': 'best',
            }
            if self.cookies_path:
                ydl_opts['cookiefile'] = self.cookies_path
            before_files = set(glob(os.path.join(abs_download_dir, '*.mp4')))
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            after_files = set(glob(os.path.join(abs_download_dir, '*.mp4')))
            mp4_files = list(glob(os.path.join(abs_download_dir, '*.mp4')))
            if not mp4_files:
                print("[yt-dlp ERROR][Snapchat] No mp4 files found after download!")
                return None
            latest_file = max(mp4_files, key=os.path.getmtime)
            print(f"[yt-dlp DEBUG][Snapchat] Latest mp4 file after download: {latest_file}")
            with open(latest_file, 'rb') as f:
                file_data = io.BytesIO(f.read())
            os.remove(latest_file)
            file_data.seek(0)
            return file_data
        except Exception as e:
            print(f"[yt-dlp ERROR][Snapchat] Unexpected exception in download: {e}")
            return None
