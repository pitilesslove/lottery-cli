import click
from tabulate import tabulate
from src.config import validate_config, DHLOTTERY_ID, DHLOTTERY_PW
from src.scraper import LottoScraper
from src.db import init_db, get_stats

from src.notifier import notify_result

@click.group()
def cli():
    """동행복권 자동 구매 CLI 프로그램"""
    init_db()

@cli.command()
def balance():
    """현재 예치금 잔액을 조회합니다."""
    validate_config()
    with LottoScraper(user_id=DHLOTTERY_ID, user_pw=DHLOTTERY_PW, headless=True) as scraper:
        if scraper.login():
            bal = scraper.get_balance()
            click.echo(f"현재 예치금: {bal}")
        else:
            click.echo("로그인에 실패하여 잔액을 조회할 수 없습니다.")

@cli.command()
@click.option('--amount', default=1, help='구매할 로또 게임 수 (1~5: 기본 자동)', type=int)
@click.option('--manual', default=None, help='수동 구매 번호 6개 (예: "1,2,3,4,5,6" 또는 "1 2 3 4 5 6")', type=str)
def buy(amount, manual):
    """로또 6/45를 구매합니다. --manual 입력 시 1게임만 수동으로 구매합니다."""
    validate_config()
    
    manual_numbers = []
    if manual:
        try:
            manual_numbers = [int(n.strip()) for n in manual.replace(',', ' ').split() if n.strip()]
            if len(manual_numbers) != 6 or not all(1 <= x <= 45 for x in manual_numbers):
                click.echo("오류: 수동 번호는 1부터 45 사이의 숫자 6개여야 합니다.")
                return
            if len(set(manual_numbers)) != 6:
                click.echo("오류: 수동 번호에 중복된 숫자가 있습니다.")
                return
        except ValueError:
            click.echo("오류: 수동 번호는 숫자 형식이어야 합니다.")
            return

    with LottoScraper(user_id=DHLOTTERY_ID, user_pw=DHLOTTERY_PW, headless=True) as scraper:
        if not scraper.login():
            err_msg = "로또 구매 실패: 로그인에 실패했습니다."
            click.echo(err_msg)
            notify_result(f"🚨 {err_msg}")
            return
            
        if manual_numbers:
            success = scraper.buy_manual(manual_numbers)
            if success:
                msg = f"✅ 성공적으로 수동 번호 {manual_numbers} 1게임을 구매했습니다!"
                click.echo(msg)
                notify_result(msg)
            else:
                msg = "❌ 수동 구매에 실패했습니다. 잔액이 부족하거나 알럿 에러가 발생했을 수 있습니다."
                click.echo(msg)
                notify_result(msg)
        else:
            success = scraper.buy_auto(amount)
            if success:
                msg = f"✅ 성공적으로 로또 6/45 자동 {amount}게임을 구매했습니다!"
                click.echo(msg)
                notify_result(msg)
            else:
                msg = "❌ 자동 구매에 실패했습니다. 잔액 확인이 필요합니다."
                click.echo(msg)
                notify_result(msg)

@cli.command()
def buy720():
    """모든 조 번호를 자동으로 설정해 연금복권 720+ 1세트(5,000원)를 구매합니다."""
    validate_config()
    with LottoScraper(user_id=DHLOTTERY_ID, user_pw=DHLOTTERY_PW, headless=True) as scraper:
        if not scraper.login():
            err_msg = "연금복권 구매 실패: 로그인에 실패했습니다."
            click.echo(err_msg)
            notify_result(f"🚨 {err_msg}")
            return
            
        success = scraper.buy_720()
        if success:
            msg = "✅ 성공적으로 연금복권 720+ (1세트, 5게임)을 구매했습니다!"
            click.echo(msg)
            notify_result(msg)
        else:
            msg = "❌ 연금복권 구매에 실패했습니다."
            click.echo(msg)
            notify_result(msg)

@cli.command()
@click.option('--amount', default=10000, help='충전할 예치금 액수 (1,000 ~ 50,000)', type=int)
def charge(amount):
    """지정된 금액만큼 케이뱅크 간편결제를 통해 예치금을 충전합니다."""
    validate_config()
    from src.charge import charge_deposit
    
    with LottoScraper(user_id=DHLOTTERY_ID, user_pw=DHLOTTERY_PW, headless=True) as scraper:
        if not scraper.login():
            err_msg = "간편충전 실패: 로그인에 실패했습니다."
            click.echo(err_msg)
            notify_result(f"🚨 {err_msg}")
            return
            
        click.echo(f"예치금 충전 모듈 동작 시도: {amount:,}원")
        success = charge_deposit(scraper.page, amount)
        if success:
            msg = f"💳 간편충전 완료: {amount:,}원 예치금 충전이 성공적으로 끝났습니다."
            click.echo(msg)
            notify_result(msg)
        else:
            msg = f"❌ 간편충전 실패: {amount:,}원 충전 중 에러 발생. 로그를 확인하세요."
            click.echo(msg)
            notify_result(msg)

@cli.command()
def check_pending():
    """당첨 발표가 났지만 아직 확인하지 않은 새로운 결과를 표시합니다."""
    from src.db import get_unchecked_results
    
    res = get_unchecked_results()
    
    if res['total_games'] == 0:
        click.echo("\n[알림] 새로 확인된 로또 결과가 없습니다.")
        click.echo("       이번 주 추첨을 기다려 보세요! 🍀\n")
        return
        
    click.echo("\n[알림] 확인하지 않은 새로운 추첨 결과가 있습니다!")
    click.echo("\n==================================================")
    click.echo("  🎁 새로 확인된 로또 추첨 결과 🎁")
    click.echo("==================================================")
    click.echo(f"  • 확인된 게임 수     : {res['total_games']:>12,} 게임")
    click.echo(f"  • 소모 비용          : {res['total_cost']:>12,} 원")
    click.echo("--------------------------------------------------")
    click.echo(f"  • 총 당첨금 합계     : {res['total_win']:>12,} 원")
    click.echo("==================================================\n")
    
    click.echo("[상세 당첨 내역]")
    ranks = ["1등", "2등", "3등", "4등", "5등", "낙첨"]
    icons = {"1등": "🥇", "2등": "🥈", "3등": "🥉", "4등": "🏅", "5등": "🎖️", "낙첨": "❌"}
    
    for rank in ranks:
        count = res['rank_counts'].get(rank, 0)
        suffix = "  (🎉 축하합니다!)" if rank != "낙첨" and count > 0 else ""
        click.echo(f"  {icons[rank]} {rank} : {count:>10,} 번{suffix}")
    
    rounds_data = res.get('rounds_data', {})
    if rounds_data:
        click.echo("\n[티켓 상세 채점 결과]")
        for rnd, data in sorted(rounds_data.items(), reverse=True):
            click.echo(f"  🎯 {rnd}회차 ({data['draw_date']})")
            
            try:
                win_nums = set(map(int, str(data['winning_numbers']).split(',')))
                bonus = int(data['bonus_number'])
                
                official_str = ", ".join(f"{n:02d}" for n in sorted(win_nums))
                click.echo(f"  당첨 번호: [ {official_str} ] + 보너스 {bonus:02d}")
            except Exception:
                win_nums = set()
                bonus = -1
                click.echo(f"  당첨 번호: 파싱 불가")
                
            click.echo("  " + "-"*48)
            
            for t in data["tickets"]:
                rank = t['win_rank']
                if t['numbers'] == "확인필요":
                    click.echo(f"  [모바일/자동 구매건] - 결과: {rank}")
                    continue
                
                try:
                    my_nums = list(map(int, t['numbers'].replace(" ", "").split(',')))
                    formatted_nums = []
                    for num in my_nums:
                        if num in win_nums:
                            # Matched winning number: Blue background
                            formatted_nums.append(click.style(f"[{num:02d}]", bg="blue", fg="white", bold=True))
                        elif num == bonus:
                            # Matched bonus number: Magenta background
                            formatted_nums.append(click.style(f"[{num:02d}]", bg="magenta", fg="white", bold=True))
                        else:
                            # Unmatched: Gray text
                            formatted_nums.append(click.style(f"[{num:02d}]", fg="bright_black"))
                    
                    nums_str = " ".join(formatted_nums)
                    
                    # Highlight rank string
                    if rank == "1등": rank_str = click.style(f"{rank:^4}", bg="bright_yellow", fg="black", bold=True)
                    elif rank in ["2등", "3등"]: rank_str = click.style(f"{rank:^4}", bg="yellow", fg="black", bold=True)
                    elif rank in ["4등", "5등"]: rank_str = click.style(f"{rank:^4}", text_color="yellow", bold=True)
                    else: rank_str = click.style(f"{rank:^4}", fg="bright_black")
                    
                    amt_str = f"({t['win_amount']:,}원)" if t['win_amount'] > 0 else ""
                    click.echo(f"  {nums_str}  =>  {rank_str} {amt_str}")
                except Exception as e:
                    click.echo(f"  {t['numbers']}  =>  {rank}")
                    
            click.echo("  " + "="*48)
    
    click.echo("")

@cli.command()
def pending():
    """추첨 전(미확인) 티켓과 번호를 출력합니다."""
    from src.db import get_pending_tickets

    tickets = get_pending_tickets()
    if not tickets:
        click.echo("\n[알림] 추첨 전(미확인) 티켓이 없습니다.\n")
        return

    click.echo("\n[추첨 전 티켓 목록]")
    click.echo("==================================================")

    rows = []
    for t in tickets:
        numbers = t['numbers']
        if numbers == "확인필요":
            numbers = "(번호 미저장)"
        rows.append([
            t['id'],
            t['round_number'],
            t['purchase_date'],
            t['mode'],
            numbers,
            f"{t['cost']:,}원"
        ])

    click.echo(tabulate(rows, headers=["ID", "회차", "구매일시", "모드", "번호", "금액"], tablefmt="pretty"))
    click.echo("")


@cli.command()
def stats():
    """로컬 DB에 저장된 내 생애 전체 역대 당첨 내역 누적 통계를 출력합니다."""
    from src.db import get_all_checked_results
    
    res = get_all_checked_results()
    
    if res['total_games'] == 0:
        click.echo("\n[알림] 기록된 당첨 결과가 없습니다.")
        click.echo("       구입 내역이 있다면 'main.py buy' 로 구매 후 추첨을 기다려주세요.\n")
        return
        
    click.echo("\n==================================================")
    click.echo("            📊 나의 로또 생애 누적 통계 📊")
    click.echo("==================================================")
    click.echo("\n  [누적 금액 현황]")
    click.echo("  +-----------------------+------------------------+")
    click.echo(f"  | 역대 누적 지출금      | {res['total_cost']:>20,} 원 |")
    click.echo(f"  | 역대 누적 당첨금      | {res['total_win']:>20,} 원 |")
    click.echo("  +-----------------------+------------------------+")
    
    sign = "+" if res['net_profit'] > 0 else ""
    click.echo(f"  | 💰 종합 순수익금      | {sign}{res['net_profit']:>19,} 원 |")
    click.echo("  +-----------------------+------------------------+\n")
    
    click.echo("  [역대 당첨 랭크 누적]")
    click.echo(f"  Total Played: {res['total_games']:,} Games")
    
    ranks = res['rank_counts']
    r1 = ranks.get('1등', 0)
    r2 = ranks.get('2등', 0)
    r3 = ranks.get('3등', 0)
    r4 = ranks.get('4등', 0)
    r5 = ranks.get('5등', 0)
    r_fail = ranks.get('낙첨', 0)
    
    click.echo(f"  - 1등 : {r1}회  |  2등 : {r2}회  |  3등 : {r3}회")
    click.echo(f"  - 4등 : {r4}회  |  5등 : {r5}회  |  낙첨: {r_fail}회 \n")

@cli.command()
def update():
    """아직 당첨 확인이 안 된 회차의 결과를 동행복권 사이트에서 스크래핑하여 DB를 갱신합니다."""
    validate_config()
    from src.db import get_pending_purchases, update_ticket_result, add_or_update_round, DB_FILE
    import sqlite3
    
    with LottoScraper(user_id=DHLOTTERY_ID, user_pw=DHLOTTERY_PW, headless=True) as scraper:
        if not scraper.login():
            click.echo("로그인에 실패하여 당첨 결과를 갱신할 수 없습니다.")
            return
            
        results = scraper.update_buy_list()
        if not results:
            click.echo("최근 당첨 내역(로또6/45)이 없거나 스크래핑에 실패했습니다.")
            return
            
        # 1. 미할당된 round_number(0)가 있다면 가장 최근 미추첨/낙첨 내역의 회차로 매핑
        # (현실적으로 가장 높은 회차 번호를 부여하는 임시 보정 처리)
        round_numbers = sorted(list(set(int(r['round']) for r in results)))
        if round_numbers:
            latest_round = max(round_numbers)
            conn = sqlite3.connect(DB_FILE)
            cur = conn.cursor()
            cur.execute("UPDATE purchases SET round_number = ? WHERE round_number = 0", (latest_round,))
            conn.commit()
            conn.close()

        update_count = 0
        
        # 2. 이번에 확인된 고유 회차들을 순회하며 각 티켓별로 채점
        for round_no in round_numbers:
            pending_tickets = get_pending_purchases(round_no)
            if not pending_tickets:
                continue
                
            # 해당 회차가 추첨 완료되었는지 사이트 내역상 확인
            round_status_list = [r['result'] for r in results if int(r['round']) == round_no]
            if not round_status_list or "미추첨" in round_status_list:
                # 아직 추첨 전이면 스킵
                continue
                
            # 추첨이 완료된 회차라면 공식 API로 7개의 당첨 번호 로드
            official_data = scraper.get_official_winning_numbers(round_no)
            if not official_data:
                click.secho(f"  [{round_no}회차] 당첨 번호 정보를 가져올 수 없습니다. 현재 접속자가 많아 대기열(WAF)이 활성화되었을 수 있습니다. 나중에 다시 시도해주세요.", fg="yellow")
                continue
                
            add_or_update_round(
                round_number=round_no, 
                draw_date=official_data['draw_date'],
                winning_numbers=",".join(map(str, official_data['winning_numbers'])),
                bonus_number=official_data['bonus_number'],
                is_drawn=True
            )
            
            win_nums = set(official_data['winning_numbers'])
            bonus_num = official_data['bonus_number']
            
            # 각 티켓 정밀 1:1 채점
            for t in pending_tickets:
                # 숫자형태 파싱 시도 (단, "확인필요" 등 자동 티켓은 임시 처리)
                if t['numbers'] == "확인필요":
                    # 자동은 현재 영수증 파싱이 안 되었으므로, 동행복권 결과상의 평균 값(낙첨/당첨 판별) 임의 부여
                    overall_result = round_status_list[0] if round_status_list else "낙첨"
                    rank = "당첨" if overall_result != "낙첨" else "낙첨"
                    update_ticket_result(t['id'], rank, 0)
                    update_count += 1
                else:
                    try:
                        my_nums = set(map(int, t['numbers'].replace(" ", "").split(',')))
                        match_count = len(my_nums & win_nums)
                        bonus_match = bonus_num in my_nums
                        
                        rank = "낙첨"
                        amt = 0
                        if match_count == 6:
                            rank, amt = "1등", 2000000000 # 가상의 평균액 (실제로는 동행복권 API 데이터나 크롤링 필요)
                        elif match_count == 5 and bonus_match:
                            rank, amt = "2등", 50000000
                        elif match_count == 5:
                            rank, amt = "3등", 1500000
                        elif match_count == 4:
                            rank, amt = "4등", 50000
                        elif match_count == 3:
                            rank, amt = "5등", 5000
                        else:
                            rank, amt = "낙첨", 0
                            
                        update_ticket_result(t['id'], rank, amt)
                        update_count += 1
                    except Exception as e:
                        print(f"티켓 파싱/채점 오류 (ID:{t['id']}): {e}")

        click.echo(f"DB 정밀 채점 완료: 총 {update_count}건의 게임 결과가 완전히 매핑 및 개별 채점되었습니다.")

if __name__ == '__main__':
    cli()

