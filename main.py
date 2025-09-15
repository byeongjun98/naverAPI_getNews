import os
import re
import requests
import psycopg2
from fastapi import FastAPI, HTTPException, Query
from typing import Literal, List
from config import DB_CONFIG, NAVER_CLIENT_ID, NAVER_CLIENT_SECRET
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from konlpy.tag import Okt
from collections import Counter
from datetime import datetime, timedelta

# FastAPI 앱을 초기화합니다.
app = FastAPI()

def create_news_table():
    """뉴스 저장을 위한 데이터베이스 테이블을 생성합니다."""
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS news (
                id SERIAL PRIMARY KEY,
                title VARCHAR(255),
                link VARCHAR(255) UNIQUE,
                description TEXT,
                pub_date TIMESTAMP
            )
        """)
        conn.commit()
        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()

def save_news_to_db(news_items):
    """뉴스 아이템을 데이터베이스에 저장합니다."""
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        for item in news_items:
            # 데이터베이스에 이미 존재하는 링크인지 확인
            cur.execute("SELECT link FROM news WHERE link = %s", (item['originallink'],))
            if cur.fetchone() is None:
                # 존재하지 않으면 데이터 삽입
                cur.execute(
                    "INSERT INTO news (title, link, description, pub_date) VALUES (%s, %s, %s, %s)",
                    (item['title'], item['originallink'], item['description'], item['pubDate'])
                )
        conn.commit()
        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()

def def_html_tags(text):
    """HTML 태그를 제거하는 함수"""
    return re.sub(r'<[^>]+>', '', text)

@app.get("/")
def read_root():
    """루트 엔드포인트"""
    return {"message": "네이버 뉴스 API 서버"}

@app.get("/api/news")
async def get_news(
        query: str = Query(..., min_length=1, description="검색할 쿼리"),
        display: int = Query(10, ge=1, le=100, description="한 번에 표시할 검색 결과 개수 (1~100)"),
        start: int = Query(1, ge=1, le=1000, description="검색 시작 위치 (1~1000)"),
        sort: Literal['sim', 'date'] = Query('sim', description="정렬 옵션: sim (유사도순), date (날짜순)"),
        save_to_db: bool = True  # DB 저장 여부 파라미터 추가
):
    """
    네이버 뉴스 API를 호출하여 뉴스 검색 결과를 반환하고 데이터베이스에 저장합니다.
    """
    # API 자격 증명이 설정되었는지 확인합니다.
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="네이버 API 환경변수가 설정되지 않았습니다.")

    # 네이버 뉴스 검색 API URL
    NAVER_API_URL = "https://openapi.naver.com/v1/search/news.json"

    # API 요청에 필요한 헤더
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }

    # API 요청에 필요한 파라미터
    params = {
        "query": query,
        "display": display,
        "start": start,
        "sort": sort
    }

    # 네이버 API에 GET 요청을 보냅니다.
    response = requests.get(NAVER_API_URL, headers=headers, params=params)

    # 응답 상태 코드가 200 (성공)인 경우, JSON 응답을 반환합니다.
    if response.status_code == 200:
        data = response.json()
        news_items = data.get("items", [])
        
        # title과 description에서 HTML 태그 제거
        for item in news_items:
            item["title"] = def_html_tags(item["title"])
            item["description"] = def_html_tags(item["description"])
        
        # save_to_db가 True일 경우에만 뉴스 데이터를 데이터베이스에 저장
        if save_to_db:
            save_news_to_db(news_items)
        
        return data
    # 그렇지 않은 경우, HTTP 예외를 발생시킵니다.
    else:
        raise HTTPException(status_code=response.status_code, detail=response.json())

async def fetch_and_extract_keywords(keywords: List[str]) -> List[str]:
    """
    키워드 리스트를 받아 뉴스를 검색하고, 형태소 분석을 통해 새로운 키워드 리스트를 반환합니다.
    """
    print(f"Analyzing keywords: {keywords}")
    okt = Okt()
    all_news_text = ""

    for keyword in keywords:
        print(f"--- 키워드 '{keyword}' 뉴스 검색 중 ---")
        try:
            # DB 저장 없이 뉴스 검색
            news_data = await get_news(query=keyword, display=10, start=1, sort='date', save_to_db=False)
            news_items = news_data.get("items", [])

            if not news_items:
                print("검색된 뉴스가 없습니다.")
                continue

            # 제목과 설명을 출력하고, 전체 텍스트에 합침
            for item in news_items:
                title = item.get('title', '')
                description = item.get('description', '')
                print(f"  - 제목: {title}")
                print(f"    설명: {description}")
                all_news_text += title + " " + description + " "

        except Exception as e:
            print(f"Error fetching news for keyword '{keyword}': {e}")

    if not all_news_text:
        return []

    # 명사 추출
    nouns = okt.nouns(all_news_text)
    meaningful_nouns = [n for n in nouns if len(n) > 1]
    counter = Counter(meaningful_nouns)
    top_keywords = counter.most_common(20)

    # 카운트를 제외하고 키워드(문자열)만 반환
    return [kw for kw, count in top_keywords]

@app.get("/api/news/analyze-recursive")
async def analyze_news_recursively(depth: int = Query(2, ge=1, le=5, description="분석 깊이 (1-5)")):
    """
    재귀적으로 뉴스 분석을 수행합니다.
    초기 키워드 셋으로 뉴스를 검색하고, 새로운 키워드를 추출하여 
    'depth' 횟수만큼 이 과정을 반복합니다.
    """
    print(f"=== Recursive Keyword Analysis Started (depth={depth}) ===")

    # 초기 키워드
    current_keywords = [
        "지진", "홍수", "태풍", "산불", "폭설",
        "감염병", "미세먼지", "가뭄", "화산", "쓰나미"
    ]
    
    all_results = {"depth_0": current_keywords}
    print(f"--- Depth 0 Keywords ---")
    print(current_keywords)

    for i in range(depth):
        print(f"--- Analyzing Depth {i + 1} ---")
        new_keywords = await fetch_and_extract_keywords(current_keywords)

        if not new_keywords:
            print("No new keywords found. Stopping analysis.")
            break
        
        current_keywords = new_keywords
        all_results[f"depth_{i+1}"] = current_keywords
        print(f"--- Depth {i + 1} Extracted Keywords ---")
        print(current_keywords)

    print("=== Recursive Keyword Analysis Complete ===")
    return {"final_keywords": current_keywords, "all_depth_results": all_results}

async def fetch_and_analyze_disaster_news():
    """매일 재난 관련 키워드로 뉴스를 검색하고, 추출된 키워드로 다시 검색하는 심층 분석을 수행합니다."""
    depth = 2  # 총 2단계 분석 수행
    print(f"=== 매일 재난 관련 사회현안 키워드 심층 분석 시작 (depth={depth}) ===")

    # 초기 키워드
    current_keywords = [
        "지진", "홍수", "태풍", "산불", "폭설",
        "감염병", "미세먼지", "가뭄", "화산", "쓰나미"
    ]
    
    print(f"--- Depth 0 Keywords ---")
    print(current_keywords)

    for i in range(depth):
        print(f"--- Analyzing Depth {i + 1} ---")
        # fetch_and_extract_keywords 함수는 내부적으로 뉴스 제목/설명을 출력합니다.
        new_keywords = await fetch_and_extract_keywords(current_keywords)

        if not new_keywords:
            print("No new keywords found. Stopping analysis.")
            break
        
        current_keywords = new_keywords
        print(f"--- Depth {i + 1} Extracted Keywords ---")
        print(current_keywords)

    print("\n=== 작업 완료 ===")

@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 실행될 이벤트"""
    create_news_table()
    
    # 스케줄러 설정
    scheduler = AsyncIOScheduler(daemon=True, timezone='Asia/Seoul')
    
    # 매일 새벽 3시에 'fetch_and_analyze_disaster_news' 함수 실행
    scheduler.add_job(fetch_and_analyze_disaster_news, 'cron', hour=3, minute=0)
    
    # 테스트를 위해 앱 시작 후 10초 뒤에 1회 실행
    run_time = datetime.now() + timedelta(seconds=10)
    scheduler.add_job(fetch_and_analyze_disaster_news, 'date', run_date=run_time)

    scheduler.start()