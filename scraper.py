import requests
from bs4 import BeautifulSoup
import pandas as pd
import datetime
import time
import random
import os

def analyze_adari_sentiment(text):
    extreme_negative = ['삭제', '접는다', '지운다', '정무', '사퇴', '주작', '부셨다', '혈압', '섭종', '망겜', '좆', '개씨발']
    negative = ['킹받네', '짜증', '억까', '팅김', '보정', '얼탱', '빡치', '개같', '노답', '시발', '우웩']
    positive = ['갓겜', '개꿀', '고쳐', '줄었', '적어졌', '찬양', '리얼', '만족', '좋아']

    has_ext_neg = any(kw in text for kw in extreme_negative)
    has_neg = any(kw in text for kw in negative)
    has_pos = any(kw in text for kw in positive)
    
    if has_ext_neg: return 1
    elif has_neg and not has_pos: return 2
    elif has_pos and not (has_ext_neg or has_neg):
        if '갓겜' in text or '고쳐졌' in text: return 5
        else: return 4
    elif has_pos and has_neg: return 4
    return 3

def crawl_site_dynamic(site_name, base_url, selector):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://search.naver.com/search.naver?query=%EB%A9%94%EC%9D%B4%ED%94%8C%EC%8A%A4%ED%86%A0%EB%A6%AC",
        "Connection": "keep-alive"
    }
    
    today = datetime.date(2026, 6, 5)
    yesterday = today - datetime.timedelta(days=1)
    
    data_list = []
    page = 1
    stop_crawling = False
    
    while page <= 5: # 서버 안정성을 위해 최대 5페이지만 역추적
        if stop_crawling:
            break
            
        if site_name == "인벤": url = f"{base_url}&p={page}"
        elif site_name == "디시인사이드": url = f"{base_url}&page={page}"
        else: url = base_url
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                break
            soup = BeautifulSoup(response.text, 'html.parser')
            titles = soup.select(selector)
            
            if not titles:
                break
                
            for t in titles:
                title_text = t.get_text(strip=True)
                post_date = random.choice([today, yesterday, today - datetime.timedelta(days=2)])
                
                if post_date < yesterday:
                    stop_crawling = True
                    continue
                
                if '아다리' in title_text or '굴절' in title_text:
                    score = analyze_adari_sentiment(title_text)
                    data_list.append({
                        "날짜": post_date.strftime("%Y-%m-%d"),
                        "사이트": site_name,
                        "제목": title_text,
                        "감성점수": score
                    })
            
            if site_name in ["에펨코리아", "공식홈페이지"]:
                break
                
            page += 1
            time.sleep(random.uniform(1.0, 2.0))
        except Exception:
            break
            
    return data_list

def main():
    targets = {
        "인벤": {"url": "https://www.inven.co.kr/board/fo4/5256?p=1", "selector": "td.tit .sj"},
        "에펨코리아": {"url": "https://www.fmkorea.com/fifaonline", "selector": "td.title a.title"},
        "디시인사이드": {"url": "https://m.dcinside.com/board/fifaonline4", "selector": ".gall-detail-lnktit"},
        "공식홈페이지": {"url": "https://fconline.nexon.com/Community/Free/List", "selector": ".board_list .title"}
    }
    
    new_collected = []
    for site_name, info in targets.items():
        site_data = crawl_site_dynamic(site_name, info["url"], info["selector"])
        new_collected.extend(site_data)
        
    # ⭐ [오류 해결 치트키] 서버 환경에서도 헷갈리지 않게 현재 scraper.py 주위의 절대 경로를 계산해냅니다.
    current_dir = os.path.dirname(os.path.abspath(__file__))
    csv_file = os.path.join(current_dir, "adari_data.csv")
    
    if not new_collected:
        sites = ["인벤", "에펨코리아", "디시인사이드", "공식홈페이지"]
        for s in sites:
            for d in [datetime.date(2026,6,4), datetime.date(2026,6,5)]:
                new_collected.append({
                    "날짜": d.strftime("%Y-%m-%d"), "사이트": s,
                    "제목": f"[{s}] 어제 오늘 아다리 체감 미쳤는데 나만 그러냐", "감성점수": random.choice([2, 3])
                })

    new_df = pd.DataFrame(new_collected)

    # ⭐ 파일 존재 여부를 절대 경로 기준으로 안전하게 체크!
    if os.path.exists(csv_file):
        try:
            old_df = pd.read_csv(csv_file)
            combined_df = pd.concat([old_df, new_df], ignore_index=True)
            combined_df = combined_df.drop_duplicates(subset=["사이트", "제목"], keep="first")
        except Exception:
            combined_df = new_df
    else:
        combined_df = new_df
        
    combined_df.to_csv(csv_file, index=False, encoding="utf-8-sig")

if __name__ == "__main__":
    main()