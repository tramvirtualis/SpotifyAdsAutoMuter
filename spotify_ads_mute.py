"""
Spotify Ads Mute - Tự động tắt tiếng Spotify khi có quảng cáo
Author: AI Assistant
Version: 1.0.0

Cách hoạt động:
- Monitor tiêu đề cửa sổ Spotify liên tục
- Khi phát hiện quảng cáo (Advertisement) -> tự động mute Spotify
- Khi hết quảng cáo (có tên bài hát) -> tự động unmute Spotify
"""

import time
import ctypes
from ctypes import POINTER, cast
import logging
from datetime import datetime
import sys

# Windows COM libraries
try:
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
except ImportError:
    print("Lỗi: Thiếu thư viện cần thiết!")
    print("Hãy chạy: pip install pycaw comtypes")
    sys.exit(1)

try:
    import win32gui
    import win32process
    import psutil
except ImportError:
    print("Lỗi: Thiếu thư viện cần thiết!")
    print("Hãy chạy: pip install pywin32 psutil")
    sys.exit(1)


# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('spotify_mute.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class SpotifyAdsMute:
    """
    Class chính để quản lý việc mute/unmute Spotify khi có quảng cáo
    """
    
    # Các từ khóa để nhận diện quảng cáo
    AD_KEYWORDS = [
        'advertisement',
        'quảng cáo',
        'spotify',  # Khi chỉ hiện "Spotify" không có tên bài hát
        'ad',
    ]
    
    # Các pattern cho biết đang phát nhạc (không phải quảng cáo)
    MUSIC_INDICATORS = [
        ' - ',  # Thường có format "Artist - Song Title"
    ]
    
    def __init__(self, check_interval: float = 0.5):
        """
        Khởi tạo SpotifyAdsMute
        
        Args:
            check_interval: Thời gian giữa các lần kiểm tra (giây)
        """
        self.check_interval = check_interval
        self.is_muted = False
        self.last_title = ""
        self.running = True
        
    def get_spotify_window_title(self) -> str:
        """
        Lấy tiêu đề cửa sổ Spotify
        
        Returns:
            Tiêu đề cửa sổ Spotify hoặc chuỗi rỗng nếu không tìm thấy
        """
        def callback(hwnd, titles):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                # Tìm cửa sổ Spotify
                try:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    process = psutil.Process(pid)
                    if 'spotify' in process.name().lower():
                        titles.append(title)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            return True
        
        titles = []
        try:
            win32gui.EnumWindows(callback, titles)
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách cửa sổ: {e}")
            
        # Tìm tiêu đề có nội dung (không phải chuỗi rỗng)
        for title in titles:
            if title and title.strip():
                return title
                
        return ""
    
    def is_ad_playing(self, window_title: str) -> bool:
        """
        Kiểm tra xem đang phát quảng cáo hay không
        
        Args:
            window_title: Tiêu đề cửa sổ Spotify
            
        Returns:
            True nếu đang phát quảng cáo, False nếu không
        """
        if not window_title:
            return False
            
        title_lower = window_title.lower().strip()
        
        # Nếu có format "Artist - Song", đây là nhạc
        if ' - ' in window_title:
            return False
            
        # Kiểm tra các từ khóa quảng cáo
        for keyword in self.AD_KEYWORDS:
            if keyword.lower() in title_lower:
                return True
                
        # Nếu tiêu đề chỉ là "Spotify" hoặc "Spotify Premium" hoặc rỗng/ngắn
        if title_lower in ['spotify', 'spotify premium', 'spotify free'] or len(title_lower) < 3:
            return True
            
        return False
    
    def get_spotify_audio_session(self):
        """
        Lấy audio session của Spotify
        
        Returns:
            Audio session hoặc None nếu không tìm thấy
        """
        try:
            sessions = AudioUtilities.GetAllSessions()
            for session in sessions:
                if session.Process and 'spotify' in session.Process.name().lower():
                    return session
        except Exception as e:
            logger.error(f"Lỗi khi lấy audio session: {e}")
            
        return None
    
    def mute_spotify(self) -> bool:
        """
        Tắt tiếng Spotify
        
        Returns:
            True nếu thành công, False nếu thất bại
        """
        try:
            session = self.get_spotify_audio_session()
            if session:
                volume = session._ctl.QueryInterface(ISimpleAudioVolume)
                volume.SetMute(1, None)
                self.is_muted = True
                logger.info("🔇 Đã tắt tiếng Spotify (phát hiện quảng cáo)")
                return True
        except Exception as e:
            logger.error(f"Lỗi khi mute Spotify: {e}")
            
        return False
    
    def unmute_spotify(self) -> bool:
        """
        Bật tiếng Spotify
        
        Returns:
            True nếu thành công, False nếu thất bại
        """
        try:
            session = self.get_spotify_audio_session()
            if session:
                volume = session._ctl.QueryInterface(ISimpleAudioVolume)
                volume.SetMute(0, None)
                self.is_muted = False
                logger.info("🔊 Đã bật tiếng Spotify (hết quảng cáo)")
                return True
        except Exception as e:
            logger.error(f"Lỗi khi unmute Spotify: {e}")
            
        return False
    
    def run(self):
        """
        Vòng lặp chính để monitor Spotify
        """
        logger.info("="*50)
        logger.info("🎵 SPOTIFY ADS MUTE - BẮT ĐẦU CHẠY")
        logger.info("="*50)
        logger.info("Nhấn Ctrl+C để dừng chương trình")
        logger.info("")
        
        ad_count = 0
        song_count = 0
        
        try:
            while self.running:
                # Lấy tiêu đề cửa sổ Spotify
                window_title = self.get_spotify_window_title()
                
                # Chỉ xử lý nếu tiêu đề thay đổi
                if window_title != self.last_title:
                    self.last_title = window_title
                    
                    if window_title:
                        is_ad = self.is_ad_playing(window_title)
                        
                        if is_ad and not self.is_muted:
                            # Đang phát quảng cáo -> Mute
                            ad_count += 1
                            logger.info(f"📢 Phát hiện quảng cáo #{ad_count}: '{window_title}'")
                            self.mute_spotify()
                            
                        elif not is_ad and self.is_muted:
                            # Hết quảng cáo -> Unmute
                            song_count += 1
                            logger.info(f"🎶 Đang phát bài: '{window_title}'")
                            self.unmute_spotify()
                            
                        elif not is_ad:
                            logger.info(f"🎶 Đang phát: '{window_title}'")
                    else:
                        logger.debug("Không tìm thấy cửa sổ Spotify")
                
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            logger.info("")
            logger.info("="*50)
            logger.info("👋 DỪNG CHƯƠNG TRÌNH")
            logger.info(f"📊 Thống kê: Đã chặn {ad_count} quảng cáo")
            logger.info("="*50)
            
            # Unmute khi thoát để tránh bị mute vĩnh viễn
            if self.is_muted:
                self.unmute_spotify()


def print_banner():
    """In banner khi khởi động"""
    banner = """
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║     🎵 SPOTIFY ADS MUTE 🎵                               ║
    ║                                                           ║
    ║     Tự động tắt tiếng khi Spotify phát quảng cáo         ║
    ║     Tự động bật tiếng khi hết quảng cáo                  ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """
    print(banner)


def check_spotify_running() -> bool:
    """
    Kiểm tra Spotify có đang chạy không
    """
    for proc in psutil.process_iter(['name']):
        try:
            if 'spotify' in proc.info['name'].lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return False


def main():
    """Hàm main"""
    print_banner()
    
    # Kiểm tra Spotify có đang chạy không
    if not check_spotify_running():
        logger.warning("⚠️ Spotify chưa được mở!")
        logger.info("Hãy mở Spotify trước khi chạy chương trình này.")
        logger.info("Chương trình sẽ tự động phát hiện khi Spotify được mở...")
        print()
        
    # Khởi tạo và chạy
    muter = SpotifyAdsMute(check_interval=0.3)  # Kiểm tra mỗi 0.3 giây
    muter.run()


if __name__ == "__main__":
    main()
