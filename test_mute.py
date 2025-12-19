import logging
import sys
import time

# Windows COM libraries
try:
    import pythoncom
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
except ImportError as e:
    print(f"Lỗi: Thiếu thư viện cần thiết: {e}")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

def test_mute():
    print("=== TEST MUTE SPOTIFY ===")
    
    # 1. Init COM
    pythoncom.CoInitialize()
    
    # 2. Find Session
    print("Đang tìm audio session của Spotify...")
    sessions = AudioUtilities.GetAllSessions()
    spotify_session = None
    
    for session in sessions:
        if session.Process:
            print(f"Found session: {session.Process.name()}")
            if 'spotify' in session.Process.name().lower():
                spotify_session = session
                print(">>> ĐÃ TÌM THẤY SPOTIFY SESSION!")
                break
    
    if not spotify_session:
        print("LỖI: Không tìm thấy Spotify Audio Session!")
        return

    # 3. Mute
    print("Đang thử MUTE...")
    try:
        volume = spotify_session._ctl.QueryInterface(ISimpleAudioVolume)
        volume.SetMute(1, None)
        print("SUCCESS: Đã gửi lệnh Mute!")
    except Exception as e:
        print(f"ERROR khi mute: {e}")
        
    time.sleep(2)
    
    # 4. Unmute
    print("Đang thử UNMUTE...")
    try:
        volume = spotify_session._ctl.QueryInterface(ISimpleAudioVolume)
        volume.SetMute(0, None)
        print("SUCCESS: Đã gửi lệnh Unmute!")
    except Exception as e:
        print(f"ERROR khi unmute: {e}")

if __name__ == "__main__":
    test_mute()
