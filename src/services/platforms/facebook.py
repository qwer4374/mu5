from .base import PlatformDownloader
from typing import Optional, List, Dict
import os, json

class FacebookDownloader(PlatformDownloader):
    def __init__(self, download_dir: str):
        self.download_dir = download_dir
        os.makedirs(self.download_dir, exist_ok=True)

    def extract_info(self, url: str, process: bool = False) -> dict:
        import yt_dlp
        ydl_opts = {'quiet': True, 'extract_flat': 'in_playlist', 'skip_download': not process}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=process)
            print("[yt-dlp INFO][Facebook] extract_info info_dict:", json.dumps(info, ensure_ascii=False, indent=2))
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

    def download(self, url: str, audio_only: bool = False) -> Optional[bytes]:
        try:
            import yt_dlp
            import subprocess
            import io
            # إعداد yt-dlp ليخرج إلى stdout
            ydl_cmd = [
                'yt-dlp',
                '-f', 'best',
                '-o', '-',
                url
            ]
            print(f"[yt-dlp DEBUG][Facebook] Running: {' '.join(ydl_cmd)}")
            process = subprocess.Popen(ydl_cmd, stdout=subprocess.PIPE)
            file_data = io.BytesIO(process.stdout.read())
            process.stdout.close()
            file_data.seek(0)
            return file_data
        except Exception as e:
            print(f"[yt-dlp ERROR][Facebook] Unexpected exception in download: {e}")
            return None

    def can_handle(self, url: str) -> bool:
        return 'facebook.com' in url or 'fb.watch' in url
