import os
from playwright.sync_api import sync_playwright, Page, BrowserContext
import time
from datetime import datetime
import re

# DB 로직
from src.db import insert_purchase

# 동행복권 URL 상수 (모바일 기준)
URL_LOGIN = "https://m.dhlottery.co.kr/login"
URL_BUY_LOTTO = "https://ol.dhlottery.co.kr/olotto/game_mobile/game645.do"
URL_BALANCE_CHECK = "https://m.dhlottery.co.kr/mypage/home"
URL_BUY_LIST = "https://www.dhlottery.co.kr/mypage/selectMyLotteryledger.do" # API Endpoints may remain same

SESSION_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'session.json')

class LottoScraper:
    def __init__(self, user_id: str, user_pw: str, headless: bool = True):
        self.user_id = user_id
        self.user_pw = user_pw
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    def __enter__(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        
        # 세션(쿠키)이 존재하면 로드하여 브라우저 컨텍스트 생성
        storage_state = SESSION_PATH if os.path.exists(SESSION_PATH) else None
        
        # Mobile Context Emulation (iPhone 12/13 style)
        self.context = self.browser.new_context(
            locale="ko-KR",
            timezone_id="Asia/Seoul",
            storage_state=storage_state,
            viewport={"width": 390, "height": 844},
            is_mobile=True,
            has_touch=True,
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1"
        )
        self.page = self.context.new_page()
        
        # 팝업 및 Alert 디폴트 승인 처리
        self.page.on("dialog", lambda dialog: dialog.accept())
        
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.context:
            self.context.storage_state(path=SESSION_PATH)
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def is_logged_in(self) -> bool:
        """세션 쿠키를 통해 이미 로그인이 되어있는지 확인"""
        self.page.goto(URL_BALANCE_CHECK, timeout=15000)
        # myPage로 갔을 때 로그인 페이지로 리다이렉트 안 당하고 사용자 이름이나 총 예치금이 보이면 성공
        try:
            if "/login" in self.page.url:
                return False
            # 모바일 마이페이지 잔액 element 확인
            self.page.wait_for_selector(".pntDpstAmt, #navTotalAmt, .header_money", timeout=5000)
            return True
        except Exception:
            return False

    def login(self) -> bool:
        """동행복권 사이트에 로그인합니다. (세션이 있으면 생략)"""
        print("로그인 상태 확인 및 진행...")
        if self.is_logged_in():
            print("기존 세션으로 로그인 성공!")
            return True
            
        self.page.goto(URL_LOGIN)
        
        try:
            # Mobile Login Selectors
            self.page.wait_for_selector("#inpUserId", state="visible", timeout=5000)
            self.page.fill("#inpUserId", self.user_id)
            self.page.fill("#inpUserPswdEncn", self.user_pw)
            self.page.click("#btnLogin") # 또는 Enter
            
            # 로그인 완료 대기 (마이페이지 또는 메인으로 이동)
            self.page.wait_for_url("**/mypage/**", timeout=10000)
            print("새 계정 정보로 로그인 성공!")
            return True
        except Exception as e:
            print(f"로그인 실패! 에러: {e}")
            # 한번 더 체크
            if self.is_logged_in():
                 print("...하지만 로그인 확인됨.")
                 return True
            return False

    def get_balance(self) -> str:
        """현재 예치금 잔액을 조회합니다."""
        print("예치금 잔액 조회 중...")
        self.page.goto(URL_BALANCE_CHECK)
        try:
            # Mobile Selectors for Balance
            # .pntDpstAmt or #navTotalAmt
            el = self.page.locator(".pntDpstAmt, #navTotalAmt").first
            el.wait_for(state="visible", timeout=5000)
            return el.inner_text().strip()
        except Exception as e:
            print(f"잔액 조회 실패: {e}")
            return "조회 불가"

    def buy_auto(self, amount: int = 1) -> bool:
        """지정된 개수(amount)만큼 자동으로 로또를 구매하고 DB에 기록합니다."""
        print(f"로또 자동 {amount}게임 구매 시도 중...")
        if amount < 1 or amount > 5:
            print("한 번에 1~5게임만 구매 가능합니다.")
            return False
            
        GAME_URL = "https://ol.dhlottery.co.kr/olotto/game_mobile/game645.do"
        self.page.goto(GAME_URL, wait_until="domcontentloaded")
        time.sleep(1)
        
        # '자동 1매 추가' 버튼
        auto_btn = self.page.locator("button:has-text('자동 1매 추가')")
        for i in range(amount):
            if auto_btn.is_visible(timeout=3000):
                auto_btn.click()
                time.sleep(0.5)
            else:
                print(f"자동 추가 버튼을 찾을 수 없습니다 ({i+1}번째)")
                return False

        # 구매하기 버튼 클릭
        buy_btn = self.page.locator("#btnBuy, button:has-text('구매하기')").first
        if buy_btn.is_visible(timeout=5000):
            buy_btn.click()
        else:
            print("구매하기 버튼을 찾을 수 없습니다.")
            return False

        # 구매 확인 팝업 승인
        confirm_btn = self.page.locator("#popupLayerConfirm .buttonOk, #popupLayerConfirm button:has-text('확인')").first
        try:
            confirm_btn.wait_for(state="visible", timeout=5000)
            confirm_btn.click()
            print("구매 최종 승인 버튼 클릭됨.")
        except Exception as e:
            print(f"구매 승인 팝업 클릭 실패: {e}")
            return False

        # 결과 확인
        try:
            self.page.wait_for_selector("#report:visible, #popupLayerAlert:visible, #popupLayerConfirm:visible", timeout=15000)
            
            if self.page.locator("#report").is_visible():
                print("구매 성공 영수증 확인 완료!")
                # 구매 회차 파싱 (임시로 현재 주차를 구하거나 0으로 세팅, 실 구현에서는 영수증 텍스트 파싱)
                mock_round = 0 
                now = datetime.now()
                for _ in range(amount):
                    insert_purchase(round_number=mock_round, purchase_date=now, mode="자동", numbers="확인필요", cost=1000)
                return True
            
            # 알럿 텍스트 체크 (잔액 부족 등)
            alert_text = ""
            if self.page.locator("#popupLayerAlert").is_visible():
                alert_text = self.page.locator("#popupLayerAlert").inner_text()
            
            if "구매가 완료되었습니다" in alert_text or "구매를 완료하였습니다" in alert_text:
                print("알림창을 통한 구매 성공 확인 완료!")
                mock_round = 0 
                now = datetime.now()
                for _ in range(amount):
                    insert_purchase(round_number=mock_round, purchase_date=now, mode="자동", numbers="확인필요", cost=1000)
                return True
                
            print(f"구매 실패 알림: {alert_text}")
            return False
            
        except Exception as e:
            print(f"결과 확인 중 오류: {e}")
            return False

    def buy_manual(self, numbers: list[int]) -> bool:
        """사용자가 지정한 6개의 번호로 수동 로또를 1게임 구매합니다."""
        print(f"수동 번호 {numbers} 구매 시작...")
        if len(numbers) != 6:
            print("수동 번호는 정확히 6개여야 합니다.")
            return False
            
        GAME_URL = "https://ol.dhlottery.co.kr/olotto/game_mobile/game645.do"
        self.page.goto(GAME_URL, wait_until="domcontentloaded")
        time.sleep(1)
        
        # '번호 선택하기' 열기
        open_btn = self.page.locator("button:has-text('번호 선택하기')").first
        if open_btn.is_visible(timeout=3000):
            open_btn.click()
            time.sleep(1)
        else:
            print("'번호 선택하기' 팝업 버튼을 찾을 수 없습니다.")
            return False
            
        # 초기화 버튼 클릭 (안전장치)
        reset_btn = self.page.locator("#btnInit, button:has-text('초기화')").first
        if reset_btn.is_visible(timeout=2000):
            reset_btn.click()
            time.sleep(0.5)

        # 각 번호 클릭
        for num in numbers:
            num_el = self.page.locator(f"xpath=//div[contains(@class, 'lt-num') and text()='{num}']").first
            if num_el.is_visible(timeout=2000):
                num_el.click()
                time.sleep(0.1)
            else:
                print(f"번호 {num}을(를) 찾을 수 없습니다.")
                return False

        # 선택완료 클릭
        select_done = self.page.locator("#btnSelectNum, button:has-text('선택완료')").first
        if select_done.is_visible(timeout=2000):
            select_done.click()
            time.sleep(1)
        else:
            print("선택완료 버튼을 찾을 수 없습니다.")
            return False
            
        # 기존 로직: 구매하기 버튼 클릭
        buy_btn = self.page.locator("#btnBuy, button:has-text('구매하기')").first
        if buy_btn.is_visible(timeout=5000):
            buy_btn.click()
        else:
            print("구매하기 버튼을 찾을 수 없습니다.")
            return False

        # 구매 확인 팝업 승인
        confirm_btn = self.page.locator("#popupLayerConfirm .buttonOk, #popupLayerConfirm button:has-text('확인')").first
        try:
            confirm_btn.wait_for(state="visible", timeout=5000)
            confirm_btn.click()
            print("구매 최종 승인 버튼 클릭됨.")
        except Exception as e:
            print(f"구매 승인 팝업 클릭 실패: {e}")
            return False

        # 결과 확인
        try:
            self.page.wait_for_selector("#report:visible, #popupLayerAlert:visible, #popupLayerConfirm:visible", timeout=15000)
            
            if self.page.locator("#report").is_visible():
                print("수동 구매 성공 영수증 확인 완료!")
                mock_round = 0 
                insert_purchase(round_number=mock_round, purchase_date=datetime.now(), mode="수동", numbers=",".join(map(str, sorted(numbers))), cost=1000)
                return True
            
            alert_text = ""
            if self.page.locator("#popupLayerAlert").is_visible():
                alert_text = self.page.locator("#popupLayerAlert").inner_text()
            
            if "완료" in alert_text:
                print("알림창을 통한 수동 구매 성공 확인 완료!")
                mock_round = 0 
                insert_purchase(round_number=mock_round, purchase_date=datetime.now(), mode="수동", numbers=",".join(map(str, sorted(numbers))), cost=1000)
                return True
                
            print(f"구매 실패 알림: {alert_text}")
            return False
            
        except Exception as e:
            print(f"결과 확인 중 오류: {e}")
            return False

    def buy_720(self) -> bool:
        """연금복권 720+를 자동으로 구매합니다. (모든 조 1세트 = 5,000원)"""
        print("연금복권 720+ (모든 조, 자동) 1세트 구매 시도 중...")
        GAME_URL = "https://el.dhlottery.co.kr/game_mobile/pension720/game.jsp"
        
        self.page.goto(GAME_URL, wait_until="domcontentloaded")
        time.sleep(1)
        
        # 1. 번호 선택하기 진입
        try:
            select_btn = self.page.locator("a.btn_gray_st1.large.full, a:has-text('번호 선택하기')").first
            select_btn.wait_for(state="visible", timeout=10000)
            select_btn.click()
            time.sleep(1)
        except Exception as e:
            print(f"'번호 선택하기' 버튼 진입 실패: {e}")
            return False
            
        # 2. '모든조' 선택 및 '자동번호' 클릭
        try:
            all_jo = self.page.locator("li:has-text('모든조'), span.group.all").first
            if all_jo.is_visible(timeout=3000):
                all_jo.click()
                time.sleep(0.5)
                
            self.page.locator("a.btn_wht.xsmall:has-text('자동번호'), a:has-text('자동번호')").first.click()
            self.page.wait_for_selector("text=통신중입니다", state="hidden", timeout=5000)
            time.sleep(0.5)
        except Exception as e:
            print(f"자동번호 생성 오류: {e}")
            return False
            
        # 3. 선택완료 및 구매하기
        try:
            self.page.locator("a.btn_blue.full.large:has-text('선택완료'), a:has-text('선택완료')").first.click()
            time.sleep(1)
            
            self.page.locator("a.btn_blue.large.full:has-text('구매하기'), a:has-text('구매하기')").first.click()
        except Exception as e:
            print(f"구매하기 버튼 클릭 오류: {e}")
            return False
            
        # 4. 결과 확인
        try:
            final_confirm = self.page.locator("a.btn_lgray.medium:has-text('확인'), a.btn_blue:has-text('확인'), a:has-text('확인')").first
            if final_confirm.is_visible(timeout=10000):
                final_confirm.click()
                print("연금복권 720+ 구매 성공 (UI 확인 완료)!")
                
                # 가상의 회차 및 내역을 DB에 저장
                mock_round = 0 
                now = datetime.now()
                insert_purchase(round_number=mock_round, purchase_date=now, mode="연금자동", numbers="확인필요", cost=5000)
                return True
            else:
                # 팝업 알럿 확인
                alert_text = ""
                if self.page.locator("#popupLayerAlert").is_visible():
                    alert_text = self.page.locator("#popupLayerAlert").inner_text()
                    if "완료" in alert_text:
                        print("연금복권 720+ 구매 성공 (알림창 확인)!")
                        mock_round = 0 
                        insert_purchase(round_number=mock_round, purchase_date=datetime.now(), mode="연금자동", numbers="확인필요", cost=5000)
                        return True
                    print(f"구매 실패 알림: {alert_text}")
                return False
        except Exception as e:
             print(f"결과 확인 타임아웃 오류: {e}")
             return False

    def update_buy_list(self) -> list:
        """당첨 내역을 조회해서 결과를 파싱하여 반환합니다"""
        print("당첨 내역 조회 중...")
        # 마이페이지 복권 내역 프레임 접근
        self.page.goto("https://www.dhlottery.co.kr/mypage/mylotteryledger")
        
        # Playwright의 request를 이용하여 브라우저 쿠키가 실린 채로 API 호출
        end_dt = datetime.now()
        from datetime import timedelta
            
        start_dt = end_dt - timedelta(days=30) # 최근 1달 조회
        
        params = {
            "srchStrDt": start_dt.strftime("%Y%m%d"),
            "srchEndDt": end_dt.strftime("%Y%m%d"),
            "pageNum": "1",
            "recordCountPerPage": "100",
        }
        
        headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://www.dhlottery.co.kr/mypage/mylotteryledger",
        }
        
        resp = self.page.request.get(
            "https://www.dhlottery.co.kr/mypage/selectMyLotteryledger.do", 
            params=params, 
            headers=headers
        )
        
        if not resp.ok:
            print("API 응답 오류:", resp.status)
            return []
            
        data = resp.json()
        items = data.get("data", {}).get("list", [])
        
        results = []
        for item in items:
            lottery_name = item.get("ltGdsNm", "")
            if lottery_name == "로또6/45":
                round_no = item.get("ltEpsdView", "") # 회차
                win_result = item.get("ltWnResult", "") # 당첨결과 (미추첨, 낙첨, 당첨)
                win_amt = item.get("ltWnAmt", 0) or 0
                results.append({
                    "round": round_no,
                    "result": win_result,
                    "win_amount": int(win_amt)
                })
        return results
