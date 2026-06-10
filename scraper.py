import requests
from bs4 import BeautifulSoup
import pandas as pd
import datetime
import time
import random
import os
import sys
import re

def analyze_adari_sentiment(text):
    # 🤬 1점: 극단적 부정 (보정/주작 확신 및 게임 삭제 수준)
    extreme_negative = [
        '주작', '조작', '보정', '서버조작', '엔진', '망겜', '좆', '개씨발', '개좆', '씹창', 
        '삭제', '접는다', '지운다', '빡종', '정무사퇴', '주작겜', '현질안함', '씨발', '병신', '쓰레기'
    ]
    
    # 😠 2점: 일반적 부정 (인게임 현상 불만: 세컨볼, 루즈볼, 골대 등 짜증)
    negative = [
        '억까', '얼탱', '빡치', '개같', '노답', '시발', '키씹', '골대', '튕겨', '세컨볼', 
        '루즈볼', '팅겨', '팅김', '패스미스', '어이', '지랄', '우웩', '킹받', '짜증', '밀린다'
    ]
    
    # 😇 4~5점: 긍정 (아다리 완화 인정, 굴절 패치 찬양 및 만족)
    positive = [
        '고쳐', '줄었', '적어졌', '갓패치', '정상화', '수정', '개선', '피드백', '부드럽', 
        '갓정무', '빛정무', '만족', '좋아', '할만', '킹정', '깔끔', '개꿀', '찬양'
    ]
    
    has_ext_neg = any(kw in text for kw in extreme_negative)
    has_neg = any(kw in text for kw in negative)
    has_pos = any(kw in text for kw in positive)
    
    # 🎯 감성 점수 판독 레이어
    if has_ext_neg: 
        return 1
    elif has_neg and not has_pos: 
        return 2
    elif has_pos and not (has_ext_neg or has_neg):
        if any(kw in text for kw in ['고쳐졌', '갓패치', '정상화', '갓정무']): 
            return 5
        return 4
    elif has_pos and has_neg: 
        return 4  # 완화 의견이 포함된 복합 감정
        
    return 3  # 😐 3점: 중립 (비난도 찬양도 없는 단순 질문이나 정보 공유 글)

def parse_board_date(date_text):
    now = datetime.datetime.now()
    today_date = now.date()
    date_text = date_text.strip()
    try:
        if ":" in date_text and len(date_text) <= 5: 
            return today_date
        standard_match = re.search(r'(20\d{2})[-.](\d{1,2})[-.](\d{1,2})', date_text)
        if standard_match: 
            return datetime.date(int(standard_match.group(1)), int(standard_match.group(2)), int(standard_match.group(3)))
        short_match = re.search(r'(\d{1,2})[-./](\d{1,2})', date_text)
        if short_match: 
            return datetime.date(2026, int(short_match.group(1)), int(short_match.group(2)))
        if "분 전" in date_text or "시간 전" in date_text: 
            return today_date
    except Exception: 
        pass
    return today_date

def crawl_search_engine(site_name, keyword, info, target_start_date, target_end_date):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"}
    data_list = []
    page = 1
    stop_crawling = False
    
    print(f"   -> [{site_name}] '{keyword}' 검색 (범위: {target_start_date} ~ {target_end_date})")
    
    while not stop_crawling:
        if site_name == "에펨코리아":
            url = f"{info['base_url']}&search_keyword={keyword}&page={page}"
        elif site_name == "인벤":
            url = f"{info['base_url']}&query={keyword}&p={page}"
        elif site_name == "디시인사이드":
            url = f"{info['base_url']}&s_keyword={keyword}&page={page}"
        elif site_name == "공식홈페이지":
            url = f"{info['base_url']}&search_keyword={keyword}&page={page}"
            
        try:
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code != 200: break
            soup = BeautifulSoup(response.text, 'html.parser')
            rows = soup.select(info["selectors"]["container"])
            if not rows: break
            
            for row in rows:
                try:
                    title_el = row.select_one(info["selectors"]["title"])
                    date_el = None
                    for selector in info["selectors"]["date_selectors"]:
                        date_el = row.select_one(selector)
                        if date_el: break
                        
                    if not title_el or not date_el: continue
                    
                    title_text = title_el.get_text(strip=True)
                    post_date = parse_board_date(date_el.get_text(strip=True))
                    
                    # 🛑 [종료] 대시보드 설정 시작일보다 더 과거 글로 넘어가면 서치 즉시 중단
                    if post_date < target_start_date:
                        stop_crawling = True
                        break
                        
                    # 🎯 [검증] 대시보드 필터 날짜 도장이 정확히 찍혀 있는 글만 수집
                    if target_start_date <= post_date <= target_end_date:
                        score = analyze_adari_sentiment(title_text)
                        data_list.append({
                            "날짜": post_date.strftime("%Y-%m-%d"),
                            "사이트": site_name,
                            "제목": title_text,
                            "감성점수": score,
                            "수집시간": datetime.datetime.now().strftime("%H:%M:%S")
                        })
                except Exception:
                    continue
            
            page += 1
            time.sleep(random.uniform(0.3, 0.5))
        except Exception:
            break
            
    return data_list

def main():
    new_collected = []
    
    # 💡 대시보드가 넘겨주는 인자값 [시작일] [종료일]을 칼같이 인식
    if len(sys.argv) > 2:
        target_start_date = datetime.datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
        target_end_date = datetime.datetime.strptime(sys.argv[2], "%Y-%m-%d").date()
    elif len(sys.argv) > 1:
        target_start_date = datetime.datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
        target_end_date = datetime.date.today()
    else:
        target_start_date = datetime.date(2026, 6, 1)
        target_end_date = datetime.date.today()
        
    # 💡 공홈을 포함한 4대 타깃 검색창 완벽 매핑
    targets = {
        "에펨코리아": {
            "base_url": "https://www.fmkorea.com/search.php?mid=fifa_online&search_target=title_content",
            "selectors": {"container": "tr.lt", "title": "td.title a.title", "date_selectors": ["td.time", "td.date"]}
        },
        "인벤": {
            "base_url": "https://www.inven.co.kr/board/fo4/5256?searchtype=subject",
            "selectors": {"container": "tbody tr", "title": "td.tit .sj", "date_selectors": ["td.date"]}
        },
        "디시인사이드": {
            "base_url": "https://m.dcinside.com/board/fifaonline4?s_type=subject_m",
            "selectors": {"container": "ul.gall-detail-lst li", "title": ".gall-detail-lnktit", "date_selectors": [".gdate"]}
        },
        "공식홈페이지": {
            "base_url": "https://fconline.nexon.com/Community/Free/List?search_type=1",
            "selectors": {"container": "div.board_list ul li", "title": "span.title", "date_selectors": ["span.date"]}
        }
    }
    
    keywords = ["아다리", "굴절"]
    
    print(f"🚀 [통합 엔진 가동] 4대 커뮤니티 검색창 정밀 조준 ({target_start_date} ~ {target_end_date})")
    
    for site_name, info in targets.items():
        for kw in keywords:
            site_data = crawl_search_engine(site_name, kw, info, target_start_date, target_end_date)
            new_collected.extend(site_data)
        
    current_dir = os.path.dirname(os.path.abspath(__file__))
    csv_file = os.path.join(current_dir, "adari_data.csv")
    
    if new_collected:
        new_df = pd.DataFrame(new_collected)
        if os.path.exists(csv_file):
            old_df = pd.read_csv(csv_file)
            combined_df = pd.concat([old_df, new_df], ignore_index=True).drop_duplicates(subset=["사이트", "제목"], keep="first")
        else:
            combined_df = new_df
        combined_df.to_csv(csv_file, index=False, encoding="utf-8-sig")
        print(f"\n🎯 [대성공] 대시보드 범위 내 날짜 검증된 진짜 글 {len(new_collected)}개 보관소 적립 완료!")
    else:
        print(f"\n💡 확인 완료: 현재 설정하신 필터 범위 내에는 조건에 맞는 새 글이 없습니다.")

if __name__ == "__main__":
    main()
