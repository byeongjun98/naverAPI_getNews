import os
import re
import requests
import psycopg2
from fastapi import FastAPI, HTTPException, Query
from typing import Literal
from config import DB_CONFIG, NAVER_CLIENT_ID, NAVER_CLIENT_SECRET

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
                link VARCHAR(255),
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

@app.on_event("startup")
async def startup_event():
    create_news_table()

def save_news_to_db(news_items):
    """뉴스 아이템을 데이터베이스에 저장합니다."""
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        for item in news_items:
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
    sort: Literal['sim', 'date'] = Query('sim', description="정렬 옵션: sim (유사도순), date (날짜순)")
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
        
        # 뉴스 데이터를 데이터베이스에 저장
        save_news_to_db(news_items)
        
        return data
    # 그렇지 않은 경우, HTTP 예외를 발생시킵니다.
    else:
        raise HTTPException(status_code=response.status_code, detail=response.json())
