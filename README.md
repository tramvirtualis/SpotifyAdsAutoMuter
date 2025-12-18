# Spotify Ads Auto-Muter

Ứng dụng tự động tắt tiếng Spotify khi phát quảng cáo và bật lại khi hết quảng cáo.

## Yêu cầu

- Windows 10/11
- Spotify Desktop App (không hỗ trợ web player)

## Cách sử dụng

1. Mở Spotify Desktop App
2. Double-click vào shortcut **Spotify Ads Mute** trên Desktop (hoặc chạy `dist/SpotifyAdsMute.exe`)
3. Ứng dụng sẽ chạy ẩn trong System Tray (góc dưới bên phải màn hình)
4. Click chuột phải vào icon để bật/tắt hoặc thoát

## Tự động khởi động cùng Windows

1. Nhấn `Win + R`, gõ `shell:startup`, nhấn Enter
2. Copy shortcut từ Desktop vào thư mục vừa mở

## Lưu ý

- File exe có thể bị Windows Defender cảnh báo - bấm "More info" > "Run anyway"
- Log được lưu trong file `spotify_mute.log`

## Build từ source

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python spotify_ads_mute_tray.py
```

Build exe:
```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "SpotifyAdsMute" --icon=icon.ico spotify_ads_mute_tray.py
```

## License

MIT License
