# Naver News Search API Server

이 프로젝트는 FastAPI를 사용하여 네이버 뉴스 검색 API를 호출하고, 그 결과를 PostgreSQL 데이터베이스에 저장하는 간단한 API 서버입니다.

## 주요 기능

- 키워드를 통해 네이버 뉴스를 검색합니다.
- 검색된 뉴스 결과를 JSON 형태로 반환합니다.
- 검색된 뉴스 데이터를 PostgreSQL 데이터베이스에 저장합니다.

## 요구사항

- Python 3.8+
- PostgreSQL

이 프로젝트는 다음 라이브러리를 사용합니다:

- `fastapi`
- `uvicorn`
- `requests`
- `psycopg2-binary`
- `beautifulsoup4`

## 설치 및 설정

1. **GitHub 리포지토리 클론:**

   ```bash
   git clone https://github.com/byeongjun98/naverAPI_getNews.git
   cd <repository-name>
   ```

2. **필요한 라이브러리 설치:**

   ```bash
   pip install -r requirements.txt
   ```

3. **설정 파일 생성:**

   `config.py.example` 파일을 복사하여 `config.py` 파일을 생성합니다.

   ```bash
   cp config.py.example config.py
   ```

4. **설정 파일 수정:**

   `config.py` 파일을 열어 본인의 환경에 맞게 데이터베이스 정보와 네이버 API 키를 입력합니다.

   ```python
   DB_CONFIG = {
       "host": "localhost",
       "port": 5432,
       "dbname": "newsDatabase",
       "user": "your_db_user",
       "password": "your_db_password"
   }

   NAVER_CLIENT_ID = "YOUR_NAVER_CLIENT_ID"
   NAVER_CLIENT_SECRET = "YOUR_NAVER_CLIENT_SECRET"
   ```

## 사용법

다음 명령어를 사용하여 FastAPI 서버를 실행합니다.

```bash
uvicorn main:app --reload
```

서버가 실행되면 http://127.0.0.1:8000/docs 에서 API 문서를 확인할 수 있습니다.

## API 엔드포인트

### GET /api/news

네이버 뉴스 검색 결과를 반환하고 데이터베이스에 저장합니다.

#### 쿼리 파라미터

- `query` (필수): 검색할 키워드 (문자열)
- `display` (선택): 한 번에 표시할 검색 결과 개수 (기본값: 10, 1~100)
- `start` (선택): 검색 시작 위치 (기본값: 1, 1~1000)
- `sort` (선택): 정렬 옵션 (기본값: `sim`)
  - `sim`: 유사도순
  - `date`: 날짜순

#### 예시 요청

```
http://127.0.0.1:8000/api/news?query=주식
```
