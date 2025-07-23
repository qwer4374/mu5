import os
from typing import Optional
from .platforms.youtube import YoutubeDownloader
from .platforms.tiktok import TikTokDownloader
from .platforms.facebook import FacebookDownloader
from .platforms.instagram import InstagramDownloader
from .platforms.snapchat import SnapchatDownloader
from .platforms.pinterest import PinterestDownloader

class DownloadService:
    """
    خدمة تحميل موحدة تستخدم كلاس منفصل لكل منصة (YouTube, TikTok, Facebook)
    """
    def __init__(self, download_dir: str, instagram_cookies: Optional[str] = None, snapchat_cookies: Optional[str] = None):
        self.download_dir = download_dir
        # تعيين مسارات الكوكيز الافتراضية إذا لم يتم تمريرها
        if instagram_cookies is None:
            default_insta = os.path.join('data', 'cookies', 'instagram_cookies.txt')
            instagram_cookies = default_insta if os.path.exists(default_insta) else None
        if snapchat_cookies is None:
            default_snap = os.path.join('data', 'cookies', 'snapchat_cookies.txt')
            snapchat_cookies = default_snap if os.path.exists(default_snap) else None
        self.platforms = [
            YoutubeDownloader(download_dir),
            TikTokDownloader(download_dir),
            FacebookDownloader(download_dir),
            InstagramDownloader(download_dir, instagram_cookies),
            SnapchatDownloader(download_dir, snapchat_cookies),
            PinterestDownloader(download_dir),
        ]

    def _get_platform(self, url: str):
        url = url.lower()
        if 'youtube.com' in url or 'youtu.be' in url:
            return self.platforms[0]
        if 'tiktok.com' in url:
            return self.platforms[1]
        if 'facebook.com' in url or 'fb.watch' in url:
            return self.platforms[2]
        if 'instagram.com' in url:
            return self.platforms[3]
        if 'snapchat.com' in url:
            return self.platforms[4]
        if 'pinterest.com' in url or 'pin.it' in url:
            return self.platforms[5]
        # يمكن إضافة منصات أخرى هنا
        return None

    def extract_info(self, url: str, process: bool = False) -> dict:
        platform = self._get_platform(url)
        if platform:
            return platform.extract_info(url, process)
        raise ValueError('Unsupported platform')

    def get_formats(self, url: str, info: dict) -> list:
        platform = self._get_platform(url)
        if platform:
            return platform.get_formats(info)
        raise ValueError('Unsupported platform')

    def download(self, url: str, audio_only: bool = False):
        for platform in self.platforms:
            if platform.can_handle(url):
                return platform.download(url, audio_only)
        return None

    def list_playlist(self, info: dict):
        """
        إرجاع قائمة عناصر التشغيل (url, title, duration) من info['entries']
        فقط الفيديوهات الحقيقية (تجاهل playlists أو placeholders)
        """
        if not info or 'entries' not in info:
            return []
        items = []
        for entry in info['entries']:
            if not entry:
                continue
            # تجاهل العناصر التي ليست فيديوهات مباشرة
            if entry.get('_type') not in (None, 'video'):
                continue
            if not entry.get('url') or not entry.get('title'):
                continue
            items.append({
                'url': entry.get('url'),
                'title': entry.get('title', 'بدون عنوان'),
                'duration': entry.get('duration'),
            })
        return items

def get_youtube_playlist_items(playlist_id, max_results=50):
    """
    جلب عناصر قائمة تشغيل يوتيوب باستخدام YouTube Data API v3.
    """
    from googleapiclient.discovery import build
    api_key = "AIzaSyDgoXauA-36GGWEbFqPvp35RNBqRN7jPWo"
    youtube = build('youtube', 'v3', developerKey=api_key)
    request = youtube.playlistItems().list(
        part="snippet",
        playlistId=playlist_id,
        maxResults=max_results
    )
    response = request.execute()
    items = []
    for item in response['items']:
        title = item['snippet']['title']
        video_id = item['snippet']['resourceId']['videoId']
        items.append({
            'title': title,
            'url': f"https://www.youtube.com/watch?v={video_id}"
        })
    return items

def get_youtube_search_results(query, max_results=5, page_token=None):
    from googleapiclient.discovery import build
    api_key = "AIzaSyDgoXauA-36GGWEbFqPvp35RNBqRN7jPWo"
    youtube = build('youtube', 'v3', developerKey=api_key)
    request = youtube.search().list(
        part="snippet",
        q=query,
        type="video",
        maxResults=max_results,
        pageToken=page_token or ""
    )
    response = request.execute()
    results = []
    for item in response.get('items', []):
        title = item['snippet']['title']
        video_id = item['id']['videoId']
        results.append({'title': title, 'video_id': video_id})
    next_page_token = response.get('nextPageToken')
    return results, next_page_token

def get_youtube_video_details(video_id):
    from googleapiclient.discovery import build
    api_key = "AIzaSyDgoXauA-36GGWEbFqPvp35RNBqRN7jPWo"
    youtube = build('youtube', 'v3', developerKey=api_key)
    request = youtube.videos().list(
        part="snippet,statistics,contentDetails",
        id=video_id
    )
    response = request.execute()
    if not response['items']:
        return None
    item = response['items'][0]
    snippet = item['snippet']
    statistics = item.get('statistics', {})
    content_details = item.get('contentDetails', {})
    # حساب مدة الفيديو كنص
    import isodate
    duration = isodate.parse_duration(content_details.get('duration', 'PT0S'))
    duration_str = f"{duration.seconds//60}:{duration.seconds%60:02d}"
    return {
        'title': snippet['title'],
        'channel': snippet['channelTitle'],
        'views': statistics.get('viewCount', '0'),
        'duration': duration_str,
        'thumbnail': snippet['thumbnails']['high']['url'],
        'video_id': video_id
    }
