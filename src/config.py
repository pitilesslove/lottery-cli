import os
from dotenv import load_dotenv

load_dotenv()

DHLOTTERY_ID = os.getenv("DHLOTTERY_ID")
DHLOTTERY_PW = os.getenv("DHLOTTERY_PW")
CHARGE_PIN = os.getenv("CHARGE_PIN")  # 간편충전용 6자리 간편결제 비밀번호

# 알림용 옵셔널 변수
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def validate_config():
    if not DHLOTTERY_ID or not DHLOTTERY_PW:
        raise ValueError(".env 파일에 DHLOTTERY_ID와 DHLOTTERY_PW를 설정해주세요.")
