import os
import time
from playwright.sync_api import Page
from src.config import CHARGE_PIN

def parse_keypad(page: Page) -> dict:
    """
    랜덤 숫자 키패드(가상 키보드)를 OCR로 분석하여 각 숫자의 위치(element)를 파악합니다.
    Tesseract 엔진이 시스템에 설치되어 있어야 합니다.
    """
    import pytesseract
    from PIL import Image, ImageEnhance
    import io

    # Tesseract 경로 자동 감지
    tesseract_cmd = os.environ.get('TESSERACT_PATH')
    if not tesseract_cmd:
        common_paths = [
            "/usr/local/bin/tesseract", 
            "/opt/homebrew/bin/tesseract", 
            "/usr/bin/tesseract",
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Tesseract-OCR\tesseract.exe")
        ]
        for path in common_paths:
            if os.path.exists(path):
                tesseract_cmd = path
                break
    
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    else:
        import platform
        os_name = platform.system()
        msg = "시스템에 Tesseract OCR이 설치되어 있지 않거나 경로를 찾을 수 없습니다.\n"
        if os_name == "Darwin": # Mac
            msg += "Mac: 터미널에서 'brew install tesseract'를 실행해주세요."
        elif os_name == "Windows":
            msg += "Windows: https://github.com/UB-Mannheim/tesseract/wiki 에서 설치 파일을 다운로드해주세요."
        elif os_name == "Linux":
            msg += "Linux (Ubuntu/Debian): 'sudo apt-get install tesseract-ocr'를 실행해주세요."
        else:
            msg += "Tesseract OCR 공식 가이드를 참고하여 설치해주세요."
        
        raise Exception(msg)

    keypad_selector = ".nppfs-keypad"
    try:
        page.wait_for_selector(keypad_selector, state="visible", timeout=15000)
    except Exception:
        raise Exception("보안 키패드가 화면에 나타나지 않았습니다.")
    
    # 버튼별 위치 정보 수집
    buttons = page.locator("img.kpd-data")
    count = buttons.count()
    if count == 0:
        raise Exception("보안 키패드 버튼(img.kpd-data)을 해석할 수 없습니다.")

    button_positions = []
    for i in range(count):
        btn = buttons.nth(i)
        box = btn.bounding_box()
        if box and box['width'] > 0:
            button_positions.append({'element': btn, 'x': box['x'], 'y': box['y'], 'w': box['width'], 'h': box['height']})

    # 전체 키패드 영역 스크린샷 캡처
    time.sleep(1) # 키보드 렌더링 대기
    keypad_layer = page.locator(keypad_selector)
    keypad_box = keypad_layer.bounding_box()
    screenshot_bytes = page.screenshot(clip=keypad_box)
    keypad_img = Image.open(io.BytesIO(screenshot_bytes))

    number_map = {}
    
    for idx, btn_info in enumerate(button_positions):
        # 전체 키패드 박스 기준의 상대 좌표 계산
        lx = btn_info['x'] - keypad_box['x']
        ly = btn_info['y'] - keypad_box['y']
        
        # 각 버튼 영역만 잘라내기
        button_img = keypad_img.crop((lx, ly, lx + btn_info['w'], ly + btn_info['h']))
        
        # 전처리: 흑백 변환 및 대비 향상 (OCR 인식률 극대화)
        gray = button_img.convert('L')
        enhanced = ImageEnhance.Contrast(gray).enhance(2.0)
        binary = enhanced.point(lambda p: p > 128 and 255)
        
        # OCR 시도 (가장 정확한 옵션부터)
        configs = [
            r'--oem 3 --psm 10 -c tessedit_char_whitelist=0123456789', 
            r'--oem 3 --psm 8 -c tessedit_char_whitelist=0123456789'
        ]
        
        found_text = None
        for config in configs:
            result = pytesseract.image_to_string(binary, config=config).strip()
            if result.isdigit() and len(result) == 1:
                found_text = result
                break
        
        if found_text and found_text not in number_map:
            number_map[found_text] = btn_info['element']

    # 모든 숫자가 매핑되었는지는 호출부에서 검증
    return number_map

def charge_deposit(page: Page, amount: int = 10000) -> bool:
    """
    [간편충전] 기능을 사용하여 매개변수 금액만큼 충전(결제)을 시도합니다.
    * K-Bank 계좌가 동행복권에 미리 연동되어 있어야 동작합니다.
    """
    if not CHARGE_PIN:
        print("에러: 간편결제 비밀번호가 .env에 세팅되지 않았습니다. (CHARGE_PIN=123456)")
        return False

    if len(CHARGE_PIN) != 6:
        print("에러: CHARGE_PIN은 6자리 숫자여야 합니다.")
        return False

    print(f"간편 충전 페이지 이동 중... ({amount:,}원)")
    
    # 동행복권 간편 충전 모바일 페이지 (결제가 용이함)
    CHARGE_URL = "https://m.dhlottery.co.kr/mypage/mndpChrg"
    page.goto(CHARGE_URL, timeout=15000)
    
    # 로그인 검증
    if "/login" in page.url:
        print("로그인이 풀렸습니다. 충전을 시작할 수 없습니다.")
        return False

    # 충전 금액 매핑 유효성 검사
    amount_map = {
        1000: "1,000", 2000: "2,000", 3000: "3,000", 4000: "4,000", 
        5000: "5,000", 10000: "10,000", 20000: "20,000", 30000: "30,000", 50000: "50,000"
    }
    if amount not in amount_map:
        print(f"충전 불가 금액입니다. 지원되는 금액: {sorted(list(amount_map.keys()))}")
        return False
        
    try:
        page.select_option("select#EcAmt", label=f"{amount_map[amount]}원")
    except Exception as e:
        print(f"결제 금액 선택란(select#EcAmt)을 찾을 수 없습니다: {e}")
        return False
    
    print("충전하기 버튼 클릭...")
    try:
        page.click("button.btn-rec01:visible", timeout=10000)
    except Exception:
        print("충전 버튼(button.btn-rec01) 클릭 실패")
        return False
    
    print("가상 키패드 해독 진행 중 (Tesseract)...")
    try:
        number_map = parse_keypad(page)
    except Exception as e:
        print(f"키패드 인식 오류: {e}")
        return False

    if len(number_map) < 10:
        print(f"경고: 키패드를 완벽히 인식하지 못했습니다 ({len(number_map)}/10개 발견)")
        print(f"찾은 번호 매핑: {sorted(list(number_map.keys()))}")

    print("비밀번호(CHARGE_PIN) 터치 중...")
    for digit in CHARGE_PIN:
        if digit in number_map:
            box = number_map[digit].bounding_box()
            # 모바일 환경이므로 mouse.click보다 touchscreen.tap이 더 확실할 수 있음
            page.touchscreen.tap(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            time.sleep(0.5) # 입력 딜레이 필수
        else:
            print(f"분석 실패: 인식된 키패드에 '{digit}' 숫자가 없어 클릭할 수 없습니다.")
            return False
            
    print("PIN 입력 완료. 최종 결제 승인 확인 대기...")
    
    try:
        # 결제 완료 텍스트 및 레이어 대기
        success_selector = "button#btnAlertPop, .btn_confirm, :text('완료되었습니다'), :text('OK')"
        page.wait_for_selector(success_selector, state="visible", timeout=20000)
        
        body_text = page.locator("body").inner_text()
        if "완료" in body_text or "result=OK" in page.url:
            print("예치금 충전 성공!")
            if page.locator("button#btnAlertPop").is_visible():
                page.click("button#btnAlertPop")
            return True
        else:
            print("충전 성공 메시지를 찾을 수 없습니다.")
            return False
    except Exception as e:
        print(f"최종 결과 타임아웃 오류: {e}")
        page.screenshot(path="charge_failed_verify.png", full_page=True)
        print("📸 에러 원인 파악을 위해 화면을 'charge_failed_verify.png'에 저장했습니다.")
        if "result=OK" in page.url:
            print("URL로 미루어 보아 결제는 성공했을 확률이 높습니다.")
            return True
        return False
