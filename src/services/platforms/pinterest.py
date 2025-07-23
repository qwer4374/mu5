from .base import PlatformDownloader
from typing import Optional, List, Dict
import os, json

class PinterestDownloader(PlatformDownloader):
    def __init__(self, download_dir: str):
        self.download_dir = download_dir
        os.makedirs(self.download_dir, exist_ok=True)

    def extract_info(self, url: str, process: bool = False) -> dict:
        import yt_dlp
        ydl_opts = {'quiet': True, 'extract_flat': 'in_playlist', 'skip_download': not process}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=process)
            print("[yt-dlp INFO][Pinterest] extract_info info_dict:", json.dumps(info, ensure_ascii=False, indent=2))
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
        return 'pinterest.com' in url or 'pin.it' in url

    def download(self, url: str, audio_only: bool = False):
        try:
            import yt_dlp
            import os
            import io
            abs_download_dir = os.path.abspath(self.download_dir)
            # استخراج info_dict أولاً لمعرفة الصيغ المتاحة
            with yt_dlp.YoutubeDL({'quiet': True, 'skip_download': True}) as ydl:
                info = ydl.extract_info(url, download=False)
            formats = info.get('formats', [])
            # تحقق هل هناك صيغة فيديو وصوت منفصلين
            best_video_id = None
            best_audio_id = None
            best_height = 0
            for fmt in formats:
                if fmt.get('vcodec', 'none') != 'none' and fmt.get('ext') == 'mp4' and fmt.get('protocol', '').startswith('m3u8'):
                    height = fmt.get('height', 0) or 0
                    if height > best_height:
                        best_height = height
                        best_video_id = fmt['format_id']
                if fmt.get('acodec', 'none') != 'none' and fmt.get('ext') == 'mp4' and fmt.get('protocol', '').startswith('m3u8'):
                    best_audio_id = fmt['format_id']
            # إذا وجد فيديو وصوت منفصلين، استخدم دمج yt-dlp
            if best_video_id and best_audio_id:
                format_selector = f"{best_video_id}+{best_audio_id}/{best_video_id}"
            elif best_video_id:
                format_selector = best_video_id
            else:
                print("[yt-dlp ERROR][Pinterest] No suitable video format found!")
                return None
            outtmpl = os.path.join(abs_download_dir, '%(title)s [%(id)s].%(ext)s')
            print(f"[yt-dlp DEBUG][Pinterest] outtmpl: {outtmpl}, format: {format_selector}")
            ydl_opts = {
                'outtmpl': outtmpl,
                'quiet': True,
                'merge_output_format': 'mp4',
                'noplaylist': True,
                'format': format_selector,
            }
            # تحميل الفيديو
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                result = ydl.download([url])
            # ابحث عن أحدث ملف mp4 في المجلد
            mp4_files = [f for f in os.listdir(abs_download_dir) if f.lower().endswith('.mp4')]
            if mp4_files:
                latest_file = max([os.path.join(abs_download_dir, f) for f in mp4_files], key=os.path.getctime)
                print(f"[yt-dlp DEBUG][Pinterest] Latest mp4 file after download: {latest_file}")
                with open(latest_file, 'rb') as f:
                    file_data = io.BytesIO(f.read())
                os.remove(latest_file)
                file_data.seek(0)
                return file_data
            print("[yt-dlp ERROR][Pinterest] No new file found after download!")
            return None
        except Exception as e:
            print(f"[yt-dlp ERROR][Pinterest] Unexpected exception in download: {e}")
            return None
