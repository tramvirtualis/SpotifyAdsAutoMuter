"""
Spotify Ads Mute - Phiên bản với System Tray Icon
Chạy ẩn trong system tray, dễ dàng bật/tắt

Yêu cầu thêm: pip install pystray Pillow
"""

import time
import threading
import sys
import logging
from datetime import datetime

# Windows COM libraries
try:
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
    import win32gui
    import win32process
    import psutil
except ImportError as e:
    print(f"Lỗi: Thiếu thư viện cần thiết: {e}")
    print("Hãy chạy: pip install pycaw comtypes pywin32 psutil pystray Pillow")
    sys.exit(1)

try:
    import pystray
    from PIL import Image, ImageDraw
except ImportError:
    print("Lỗi: Thiếu thư viện cho System Tray!")
    print("Hãy chạy: pip install pystray Pillow")
    sys.exit(1)


# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('spotify_mute.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class SpotifyAdsMuteTray:
    """
    Phiên bản chạy trong System Tray
    """
    
    AD_KEYWORDS = ['advertisement', 'quảng cáo', 'spotify', 'ad']
    
    def __init__(self):
        self.is_muted = False
        self.last_title = ""
        self.running = True
        self.enabled = True
        self.ad_count = 0
        self.song_count = 0
        self.icon = None
        
    def create_icon_image(self, color='green'):
        """Tạo icon cho system tray"""
        size = 64
        image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # Vẽ hình tròn
        if color == 'green':
            fill_color = (30, 215, 96)  # Spotify green
        elif color == 'red':
            fill_color = (255, 100, 100)  # Muted red
        else:
            fill_color = (128, 128, 128)  # Disabled gray
            
        draw.ellipse([4, 4, size-4, size-4], fill=fill_color)
        
        # Vẽ icon loa
        draw.rectangle([20, 24, 28, 40], fill='white')
        draw.polygon([(28, 20), (44, 12), (44, 52), (28, 44)], fill='white')
        
        if self.is_muted:
            # Vẽ dấu X khi muted
            draw.line([(48, 22), (58, 42)], fill='white', width=3)
            draw.line([(48, 42), (58, 22)], fill='white', width=3)
            
        return image
    
    def get_spotify_window_title(self) -> str:
        """Lấy tiêu đề cửa sổ Spotify"""
        def callback(hwnd, titles):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
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
            
        for title in titles:
            if title and title.strip():
                return title
        return ""
    
    def is_ad_playing(self, window_title: str) -> bool:
        """Kiểm tra đang phát quảng cáo"""
        if not window_title:
            return False
            
        title_lower = window_title.lower().strip()
        
        if ' - ' in window_title:
            return False
            
        for keyword in self.AD_KEYWORDS:
            if keyword.lower() in title_lower:
                return True
                
        if title_lower in ['spotify', 'spotify premium', 'spotify free'] or len(title_lower) < 3:
            return True
            
        return False
    
    def get_spotify_audio_session(self):
        """Lấy audio session của Spotify"""
        try:
            sessions = AudioUtilities.GetAllSessions()
            for session in sessions:
                if session.Process and 'spotify' in session.Process.name().lower():
                    return session
        except Exception as e:
            logger.error(f"Lỗi khi lấy audio session: {e}")
        return None
    
    def mute_spotify(self) -> bool:
        """Tắt tiếng Spotify"""
        try:
            session = self.get_spotify_audio_session()
            if session:
                volume = session._ctl.QueryInterface(ISimpleAudioVolume)
                volume.SetMute(1, None)
                self.is_muted = True
                logger.info("🔇 Đã tắt tiếng Spotify")
                self.update_icon()
                return True
        except Exception as e:
            logger.error(f"Lỗi khi mute: {e}")
        return False
    
    def unmute_spotify(self) -> bool:
        """Bật tiếng Spotify"""
        try:
            session = self.get_spotify_audio_session()
            if session:
                volume = session._ctl.QueryInterface(ISimpleAudioVolume)
                volume.SetMute(0, None)
                self.is_muted = False
                logger.info("🔊 Đã bật tiếng Spotify")
                self.update_icon()
                return True
        except Exception as e:
            logger.error(f"Lỗi khi unmute: {e}")
        return False
    
    def update_icon(self):
        """Cập nhật icon khi trạng thái thay đổi"""
        if self.icon:
            if not self.enabled:
                self.icon.icon = self.create_icon_image('gray')
            elif self.is_muted:
                self.icon.icon = self.create_icon_image('red')
            else:
                self.icon.icon = self.create_icon_image('green')
    
    def toggle_enabled(self, icon, item):
        """Bật/tắt chức năng"""
        self.enabled = not self.enabled
        if not self.enabled and self.is_muted:
            self.unmute_spotify()
        self.update_icon()
        logger.info(f"Chức năng: {'Bật' if self.enabled else 'Tắt'}")
    
    def quit_app(self, icon, item):
        """Thoát ứng dụng"""
        self.running = False
        if self.is_muted:
            self.unmute_spotify()
        icon.stop()
    
    def monitor_loop(self):
        """Vòng lặp monitor chạy trong thread riêng"""
        while self.running:
            if self.enabled:
                window_title = self.get_spotify_window_title()
                
                if window_title != self.last_title:
                    self.last_title = window_title
                    
                    if window_title:
                        is_ad = self.is_ad_playing(window_title)
                        
                        if is_ad and not self.is_muted:
                            self.ad_count += 1
                            logger.info(f"📢 Quảng cáo #{self.ad_count}: '{window_title}'")
                            self.mute_spotify()
                            
                        elif not is_ad and self.is_muted:
                            self.song_count += 1
                            logger.info(f"🎶 Bài hát: '{window_title}'")
                            self.unmute_spotify()
            
            time.sleep(0.3)
    
    def run(self):
        """Chạy ứng dụng với System Tray"""
        # Tạo menu
        menu = pystray.Menu(
            pystray.MenuItem(
                lambda text: "✓ Đang hoạt động" if self.enabled else "✗ Đã tắt",
                self.toggle_enabled
            ),
            pystray.MenuItem(
                lambda text: f"Đã chặn: {self.ad_count} quảng cáo",
                None,
                enabled=False
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Thoát", self.quit_app)
        )
        
        # Tạo icon
        self.icon = pystray.Icon(
            "Spotify Ads Mute",
            self.create_icon_image('green'),
            "Spotify Ads Mute",
            menu
        )
        
        # Chạy monitor trong thread riêng
        monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        monitor_thread.start()
        
        # Chạy icon (blocking)
        logger.info("🎵 Spotify Ads Mute đã khởi động (System Tray)")
        self.icon.run()


def main():
    print("🎵 Spotify Ads Mute - System Tray Version")
    print("Ứng dụng sẽ chạy trong khay hệ thống (system tray)")
    print("Click phải vào icon để xem menu\n")
    
    app = SpotifyAdsMuteTray()
    app.run()


if __name__ == "__main__":
    main()
