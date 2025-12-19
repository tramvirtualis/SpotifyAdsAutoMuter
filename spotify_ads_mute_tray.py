"""
Spotify Ads Mute - Phiên bản với System Tray Icon
Chạy ẩn trong system tray, dễ dàng bật/tắt

Yêu cầu thêm: pip install pystray Pillow
"""

import time
import threading
import sys
import os
import shutil
import logging
import re
from datetime import datetime

# Hack fix cho comtypes trong PyInstaller
if getattr(sys, 'frozen', False):
    try:
        # Nếu đang chạy trong EXE
        import comtypes.client
        # Tạo thư mục cache riêng trong temp để tránh lỗi permission
        gen_path = os.path.join(os.getenv('TEMP'), 'comtypes_cache')
        if not os.path.exists(gen_path):
            os.makedirs(gen_path)
        comtypes.client.gen_dir = gen_path
        # Xóa file __init__.py trong cache nếu có để force Rebuild
        init_file = os.path.join(gen_path, '__init__.py')
        if os.path.exists(init_file):
            try:
                os.remove(init_file)
            except:
                pass
    except Exception as e:
        pass # Bỏ qua nếu lỗi, hy vọng vẫn chạy được

# Windows COM libraries
try:
    import pythoncom
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


# Cấu hình logging - in ra cả console và file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),  # In ra console
        logging.FileHandler('spotify_mute.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class SpotifyAdsMuteTray:
    """
    Phiên bản chạy trong System Tray
    """
    
    AD_KEYWORDS = ['advertisement', 'quảng cáo', 'spotify'] # 'ad' check riêng bằng regex để tránh nhầm (vd: Radiohead)
    
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
        
        # LOGIC QUAN TRỌNG:
        # Nhạc Spotify thường có dạng "Artist - Song"
        # Các dấu gạch có thể là: hyphen (-), en-dash (–), em-dash (—)
        is_music_format = False
        for sep in [' - ', ' – ', ' — ']:
            if sep in window_title:
                is_music_format = True
                break
                
        if not is_music_format:
            # Không có dấu gạch phân cách -> Khả năng cao là quảng cáo
            # Tuy nhiên vẫn kiểm tra keyword để chắc chắn hơn? 
            # Hiện tại logic cũ là return True luôn -> giữ nguyên logic này nhưng cẩn thận
            return True
            
        # Nếu có định dạng nhạc, vẫn kiểm tra keyword nhưng chặt chẽ hơn
        # 1. Kiểm tra các từ khóa dài (substring match ok)
        for keyword in self.AD_KEYWORDS:
            if keyword.lower() in title_lower:
                return True
        
        return False
    
    def get_spotify_audio_session(self):
        """Lấy audio session của Spotify"""
        try:
            sessions = AudioUtilities.GetAllSessions()
            for session in sessions:
                # Log các session tìm thấy để debug
                if session.Process:
                    # logger.info(f"Found audio session: {session.Process.name()}")
                    if 'spotify' in session.Process.name().lower():
                        return session
        except Exception as e:
            logger.error(f"Lỗi khi lấy audio session: {e}")
        return None
    
    def mute_spotify(self) -> bool:
        """Tắt tiếng TẤT CẢ session của Spotify"""
        try:
            logger.info("Đang quét và mute TẤT CẢ session Spotify...")
            sessions = AudioUtilities.GetAllSessions()
            muted_count = 0
            
            for session in sessions:
                if session.Process and 'spotify' in session.Process.name().lower():
                    try:
                        volume = session._ctl.QueryInterface(ISimpleAudioVolume)
                        volume.SetMute(1, None)
                        muted_count += 1
                        # logger.info(f"Muted session: {session.Process.name()}")
                    except Exception as e:
                        logger.error(f"Lỗi mute session con: {e}")
            
            if muted_count > 0:
                logger.info(f"🔇 Đã tắt tiếng {muted_count} session của Spotify")
                self.is_muted = True
                self.update_icon()
                return True
            else:
                logger.error("KHÔNG tìm thấy Session nào của Spotify để mute!")
                
        except Exception as e:
            logger.error(f"Lỗi khi mute tổng: {e}")
        return False
    
    def unmute_spotify(self) -> bool:
        """Bật tiếng TẤT CẢ session của Spotify"""
        try:
            sessions = AudioUtilities.GetAllSessions()
            unmuted_count = 0
            
            for session in sessions:
                if session.Process and 'spotify' in session.Process.name().lower():
                    try:
                        volume = session._ctl.QueryInterface(ISimpleAudioVolume)
                        volume.SetMute(0, None)
                        unmuted_count += 1
                    except:
                        pass
                        
            if unmuted_count > 0:
                logger.info(f"🔊 Đã bật tiếng {unmuted_count} session")
                self.is_muted = False
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
        # Khởi tạo COM cho thread này (dùng comtypes vì pycaw dùng comtypes)
        import comtypes
        try:
            comtypes.CoInitialize()
        except:
            pass # Có thể đã init rồi
            
        logger.info("Bắt đầu monitor Spotify (Thread started)...")
        check_count = 0
        try:
            while self.running:
                if self.enabled:
                    window_title = self.get_spotify_window_title()
                    check_count += 1
                    
                    # Log mỗi 5 giây
                    if check_count % 15 == 0:
                        if window_title:
                            # Debug: In ra trạng thái hiện tại
                            logger.info(f"Monitor: '{window_title}' | Muted: {self.is_muted}")
                    
                    if window_title != self.last_title:
                        logger.info(f"Title changed: '{self.last_title}' -> '{window_title}'")
                        self.last_title = window_title
                        
                        if window_title:
                            is_ad = self.is_ad_playing(window_title)
                            logger.info(f"Check Ad: '{window_title}' -> IsAd: {is_ad}")
                            
                            if is_ad:
                                # Luôn gọi mute để đảm bảo, vì Spotify có thể reset session/volume giữa các ads
                                if not self.is_muted:
                                    self.ad_count += 1
                                    logger.info(f">>> PHÁT HIỆN QUẢNG CÁO! MUTE NGAY! (#{self.ad_count})")
                                else:
                                    logger.info(">>> Vẫn là quảng cáo... Đảm bảo Mute...")
                                
                                if self.mute_spotify(): # Luôn gọi hàm này
                                    pass # Mute thành công
                                else:
                                    logger.error(">>> MUTE THẤT BẠI")
                            
                            elif not is_ad:
                                if self.is_muted:
                                    logger.info(f">>> HẾT QUẢNG CÁO! UNMUTE! ('{window_title}')")
                                    if self.unmute_spotify():
                                        logger.info(">>> UNMUTE THÀNH CÔNG")
                                    else:
                                        logger.error(">>> UNMUTE THẤT BẠI")
                                else:
                                    logger.info(f"Đang phát nhạc: '{window_title}'")
                
                time.sleep(0.3)
        except Exception as e:
            logger.error(f"FATAL ERROR in monitor_loop: {e}")
        finally:
            try:
                comtypes.CoUninitialize()
            except:
                pass
    
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
