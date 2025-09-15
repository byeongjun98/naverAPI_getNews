# Naver News Search and Analysis API Server

FastAPI로 구축된 이 프로젝트는 네이버 뉴스를 검색하고, 그 내용을 분석하며, 결과를 PostgreSQL 데이터베이스에 저장하는 API 서버입니다.

매일 정해진 키워드로 뉴스를 자동으로 수집하고 분석하는 기능이 포함되어 있습니다.

## 주요 기능

- **네이버 뉴스 검색**: API 엔드포인트를 통해 키워드로 뉴스를 검색합니다.
- **중복 저장 방지**: 기사 링크를 기준으로 동일한 뉴스가 중복으로 데이터베이스에 저장되는 것을 방지합니다.
- **매일 자동 분석**:
    - 매일 새벽 3시(KST)에 "지진", "홍수" 등 미리 정의된 재난 관련 키워드로 뉴스를 자동으로 수집합니다.
    - 수집된 뉴스를 `konlpy`로 형태소 분석하여 핵심 명사를 추출합니다.
    - 분석 결과는 서버 콘솔에 출력됩니다.
- **데이터베이스 저장**: 검색된 뉴스 중 새로운 기사들을 PostgreSQL 데이터베이스에 저장합니다.

## 사전 요구사항

- Python 3.11+
- PostgreSQL
- **Java 11 (JDK)**: `konlpy` 라이브러리 구동에 필요합니다.

## 설치 및 설정

1. **GitHub 리포지토리 클론:**

    ```bash
    git clone https://github.com/byeongjun98/naverAPI_getNews.git
    cd naverAPI_getNews
    ```

2. **(권장) 가상 환경 생성 및 활성화:**

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3. **의존성 라이브러리 설치:**

    ```bash
    pip install -r requirements.txt
    ```

    > **macOS (Apple Silicon M1/M2/M3) 사용자 참고:**
    > `konlpy` 라이브러리는 의존성이 복잡하여 설치가 까다로울 수 있습니다. 위 명령어가 실패할 경우, 아래 단계를 따라 수동으로 설치를 진행해 주세요.
    >
    > 1.  **Xcode 커맨드 라인 도구 설치:**
    >     ```bash
    >     xcode-select --install
    >     ```
    > 2.  **호환되는 Java JDK 설치 (Java 11 권장):**
    >     ```bash
    >     brew install openjdk@11
    >     ```
    > 3.  **`JAVA_HOME` 환경 변수 설정:**
    >     ```bash
    >     export JAVA_HOME=$(/usr/libexec/java_home -v 11)
    >     ```
    >     (이 설정을 영구적으로 적용하려면 `~/.zshrc` 또는 `~/.bash_profile` 파일에 위 라인을 추가하세요.)
    > 4.  **GitHub에서 `konlpy` 직접 설치:**
    >     ```bash
    >     pip install git+https://github.com/konlpy/konlpy.git
    >     ```

4. **설정 파일 생성:**

    `config.py.example` 파일을 복사하여 `config.py` 파일을 생성합니다.

    ```bash
    cp config.py.example config.py
    ```

5. **설정 파일 수정:**

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

## 애플리케이션 실행

`uvicorn`을 사용하여 FastAPI 서버를 실행합니다.

```bash
uvicorn main:app --reload
```

서버가 시작되면 `http://127.0.0.1:8000/docs`에서 API 문서를 확인할 수 있습니다.
매일 실행되는 분석 작업은 서버 시작 10초 후(테스트용)에 한 번 실행된 후, 매일 새벽 3시에 자동으로 실행됩니다. 결과는 `uvicorn`을 실행한 콘솔에 출력됩니다.

## API 엔드포인트

### `GET /api/news`

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