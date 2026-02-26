import os
import requests

def send_discord_message(webhook_url: str, message: str, image_path: str = None):
    """디스코드 웹훅으로 메시지와 스크린샷 캡처를 전송합니다."""
    if not webhook_url:
        return
        
    data = {"content": message}
    files = {}
    
    try:
        if image_path and os.path.exists(image_path):
            with open(image_path, "rb") as f:
                files["file"] = (os.path.basename(image_path), f.read())
            response = requests.post(webhook_url, data=data, files=files)
        else:
            response = requests.post(webhook_url, json=data)
            
        if response.status_code not in [200, 204]:
            print(f"디스코드 알림 전송 실패: {response.status_code}")
    except Exception as e:
        print(f"디스코드 알림 전송 중 오류 발생: {e}")

def send_telegram_message(bot_token: str, chat_id: str, message: str, image_path: str = None):
    """텔레그램 봇 API로 메시지와 스크린샷 캡처를 전송합니다."""
    if not bot_token or not chat_id:
        return
        
    try:
        if image_path and os.path.exists(image_path):
            url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
            data = {"chat_id": chat_id, "caption": message}
            with open(image_path, "rb") as f:
                files = {"photo": f.read()}
                response = requests.post(url, data=data, files=files)
        else:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            data = {"chat_id": chat_id, "text": message}
            response = requests.post(url, json=data)
            
        if response.status_code != 200:
            print(f"텔레그램 알림 전송 실패: {response.status_code}")
    except Exception as e:
         print(f"텔레그램 알림 전송 중 오류 발생: {e}")

def notify_result(message: str, image_path: str = None):
    """설정된 메신저들로 결과 알림을 브로드캐스팅합니다."""
    # 환경변수 동적 로드 (circular 임포트 방지)
    from src.config import DISCORD_WEBHOOK_URL, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
    
    if DISCORD_WEBHOOK_URL:
        send_discord_message(DISCORD_WEBHOOK_URL, message, image_path)
        
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        send_telegram_message(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, message, image_path)
