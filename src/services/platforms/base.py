from abc import ABC, abstractmethod
from typing import Optional, List, Dict

class PlatformDownloader(ABC):
    """
    واجهة مجردة لكل منصة تحميل (YouTube, TikTok, Facebook, ...)
    """
    @abstractmethod
    def extract_info(self, url: str, process: bool = False) -> dict:
        pass

    @abstractmethod
    def get_formats(self, info: dict) -> List[Dict]:
        pass

    @abstractmethod
    def download(self, url: str, audio_only: bool = False) -> Optional[str]:
        pass
