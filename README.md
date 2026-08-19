# FX Intelligence Dashboard

원화 기준 주요 환율의 **일별 실적**, **기간 추이**, **관련 뉴스**, **통계적 예측 구간**을 한 화면에서 보는 경영정보 대시보드입니다.

이 프로그램은 환율의 미래 값을 맞힌다고 주장하지 않습니다. 예측은 검증 오차를 기준으로 고른 통계 모델의 **중심값과 불확실성 범위**이며, 투자나 환헤지 판단의 확정 정보가 아닙니다.

## 주요 기능

- USD/KRW, EUR/KRW, JPY/KRW, CNY/KRW 선택
- 1개월 / 3개월 / 6개월 / 1년 / 전체 기간의 일별 환율 차트
- 전일 대비, 기간 최고·최저, 최근 변동성
- 7일·30일 통계 예측(Naive, 최근 Drift, 단기 평균, ARIMA 비교)
- 환율 관련 뉴스 목록과 차트 이벤트 마커 연결
- 원문 기사 새 탭 이동
- 외부 API 실패 시 저장된 데이터 또는 명시적 Mock 모드
- 이후 인건비, 원자재, 물류비 등 다른 지표를 같은 `Indicator → Observation → Event → Forecast` 구조로 확장 가능

표시 단위:

- USD/KRW: 1달러당 원화
- EUR/KRW: 1유로당 원화
- JPY/KRW: 100엔당 원화 (원천이 1엔 기준이면 저장 전에 100엔으로 변환)
- CNY/KRW: 1위안당 원화

화면에 **실시간 환율**이라는 표현은 사용하지 않습니다. 기본 공급자는 영업일 기준 일별 환율입니다.

## 아키텍처

```
외부 환율 API / RSS
        ↓
백엔드 Provider (교체 가능)
        ↓
검증·정규화 → SQLite/PostgreSQL
        ↓
분석·예측 엔진
        ↓
FastAPI REST API
        ↓
Vue 3 대시보드 (브라우저는 외부 API를 직접 호출하지 않음)
```

Provider 인터페이스:

- `ExchangeRateProvider`
- `NewsProvider`
- `ForecastProvider`
- `NewsSummarizer` (향후 요약 모델 연결용, 기본 기능의 필수 조건 아님)

## 폴더 구조

```
.
├── backend/
│   ├── app/                 # FastAPI 애플리케이션
│   │   ├── api/             # REST 라우터
│   │   ├── models/          # SQLAlchemy 모델
│   │   ├── providers/       # 환율·뉴스·예측 공급자
│   │   └── services/        # 수집, 조회, 정규화
│   ├── alembic/             # DB 마이그레이션
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/                 # Vue 3 + TypeScript 대시보드
│   └── tests/
├── docker-compose.yml
└── .env.example
```

## 요구 버전

- Python 3.12 (권장. Homebrew: `brew install python@3.12`)
- Node.js 22 이상 (Homebrew: `brew install node@22`)
- 시스템 Python이 3.14여도 가상환경은 3.12로 만드세요. 일부 패키지가 3.14 휠을 아직 제공하지 않습니다.

## macOS 로컬 실행

프로젝트 루트에서 `.env`를 만듭니다.

```bash
cd "/Users/ijunsu/Projects/exchange-rate project"
cp .env.example .env
export PATH="/opt/homebrew/opt/python@3.12/bin:/opt/homebrew/opt/node@22/bin:$PATH"
```

### 백엔드

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
mkdir -p data
alembic upgrade head
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

기본 설정에서는 서버 시작 시 환율·뉴스·예측을 한 번 수집합니다. 수동으로 다시 수집하려면:

```bash
curl -X POST http://127.0.0.1:8000/api/admin/refresh
curl -X POST http://127.0.0.1:8000/api/admin/forecast
```

확인:

```bash
curl http://127.0.0.1:8000/api/health
curl "http://127.0.0.1:8000/api/exchange-rates/latest?pair=USD_KRW"
```

### 프론트엔드

새 터미널에서:

```bash
cd frontend
npm install
npm run dev
```

브라우저에서 [http://localhost:5173](http://localhost:5173) 을 엽니다. Vite가 `/api` 요청을 `http://127.0.0.1:8000`으로 전달합니다.

## 환경변수

| 변수 | 기본값 | 설명 |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./data/fx.db` | SQLAlchemy 연결 문자열. PostgreSQL 예: `postgresql+psycopg://user:pass@localhost:5432/fx` |
| `CORS_ORIGINS` | `http://localhost:5173,...` | 허용할 브라우저 Origin (쉼표 구분) |
| `EXCHANGE_PROVIDER` | `frankfurter` | `frankfurter` 또는 `mock` |
| `NEWS_PROVIDER` | `rss` | `rss` 또는 `mock` |
| `ALLOW_MOCK_FALLBACK` | `true` | 외부 수집 실패 + 저장된 데이터 없음일 때 Mock 사용 |
| `FRANKFURTER_BASE_URL` | `https://api.frankfurter.dev/v1` | 일별 환율 API |
| `HISTORY_START_DATE` | `2020-01-01` | 환율 수집 시작일 |
| `SCHEDULER_ENABLED` | `true` | APScheduler 사용 여부 |
| `EXCHANGE_SYNC_MINUTES` | `360` | 환율 수집 주기 |
| `NEWS_SYNC_MINUTES` | `60` | 뉴스 수집 주기 |
| `FORECAST_SYNC_MINUTES` | `720` | 예측 재생성 주기 |
| `NEWS_RETENTION_DAYS` | `1200` | 오래된 뉴스 삭제 기준. 과거 환율 매핑을 위해 3년 이상 보관 |
| `NEWS_HISTORY_MONTHS` | `24` | 과거 뉴스를 되짚어 수집하는 기간 |
| `NEWS_HISTORY_BATCH_MONTHS` | `8` | 한 번의 수집에서 채울 최대 개월 수. 스케줄러가 나머지를 이어서 채움 |
| `ADMIN_API_ENABLED` | `true` | 개발용 POST 관리 API. **운영 전환 시 반드시 끄거나 인증을 추가하세요.** |
| `AUTO_INGEST_ON_STARTUP` | `true` | 서버 시작 시 초기 수집 |
| `HTTP_PROXY` / `HTTPS_PROXY` | 없음 | 사내 프록시. httpx가 표준 환경변수를 사용합니다. |
| `VITE_API_BASE_URL` | 빈 값 | 프론트엔드 API 주소. 로컬 Vite는 프록시를 쓰므로 비워 두면 됩니다. |

`.env`는 Git에 포함하지 않습니다. API 키나 DB 비밀번호를 넣었다면 커밋하지 마세요.

## DB 마이그레이션

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
```

개발 서버는 테이블이 없으면 `create_all`로도 생성합니다. 운영이나 PostgreSQL 전환 시에는 Alembic을 사용하세요.

## 초기 데이터 수집

서버를 띄운 뒤 데이터가 비어 있으면:

```bash
curl -X POST http://127.0.0.1:8000/api/admin/refresh
```

응답의 `exchange`, `news`, `forecast`에서 추가 건수와 경고를 확인합니다.

## 테스트

백엔드:

```bash
cd backend
source .venv/bin/activate
pytest -q
```

프론트엔드:

```bash
cd frontend
npm test
```

## 프론트엔드 빌드

```bash
cd frontend
npm run build
```

## Docker 실행

```bash
docker compose up --build
```

- 프론트엔드: [http://localhost:8080](http://localhost:8080)
- 백엔드: [http://localhost:8000/api/health](http://localhost:8000/api/health)

여러 개의 백엔드 컨테이너를 띄우면 APScheduler가 인스턴스마다 중복 실행됩니다. 지금은 단일 인스턴스를 가정합니다.

## 데이터 출처

### 환율

기본 공급자는 [Frankfurter](https://frankfurter.dev/v1/)입니다.

- API 키 없음
- 유럽중앙은행(ECB) 참조환율을 기반으로 한 **일별** 데이터
- 주말·휴일은 값이 없을 수 있음
- 약 16:00 CET 전후 갱신

한국수출입은행, 한국은행 ECOS 등 API 키가 필요한 공급자는 Provider만 추가하면 됩니다. 키가 없어도 전체 화면을 확인할 수 있게 Frankfurter를 기본값으로 두었습니다.

### 뉴스

- Google News RSS (최신)와 월별 `after:`/`before:` 기간 검색 (과거 구간)
- GDELT DOC API (키 없이 과거 기사 제목·링크·발행일 조회)
- BBC Business RSS (환율·금리 관련 항목만 필터)

저장하는 필드는 제목, 원문 URL, 언론사, 발행 시각, 짧은 설명, 규칙 기반 영향 방향·중요도입니다. 기사 본문은 저장하거나 재배포하지 않습니다.

## Mock 모드

다음 경우에 Mock이 사용됩니다.

1. `EXCHANGE_PROVIDER=mock` 또는 `NEWS_PROVIDER=mock`
2. 외부 호출이 실패했고, 저장된 데이터가 없으며, `ALLOW_MOCK_FALLBACK=true`

Mock 데이터는 화면과 API에서 `is_mock=true`와 **Mock 데이터 사용 중** 배지로 구분합니다. 실제 환율이나 실제 기사처럼 보이지 않도록 출처와 제목에 샘플임을 표시합니다.

이미 저장된 실제 데이터가 있으면 외부 실패 시 그 데이터를 반환하고, 마지막 갱신 시각과 실패 경고를 함께 보여 줍니다.

강제 Mock 실행 예:

```bash
EXCHANGE_PROVIDER=mock NEWS_PROVIDER=mock uvicorn app.main:app --reload --port 8000
```

## 예측 모델의 한계

- 최소 90영업일의 일별 데이터가 있어야 예측합니다.
- 최근 3개 주(영업일 7일씩)를 걸어가며 검증하고, MAE가 비슷하면 더 단순한 모델을 고릅니다.
- 후보: Naive(직전 종가 유지), Drift(최근 21영업일 평균 기울기), LocalMean(최근 5일 평균), ARIMA(AIC로 (1,1,0)/(0,1,1)/(1,1,1)/(2,1,1) 중 선택).
- 구간은 검증 잔차와 최근 수익률 변동성 중 더 넓은 쪽으로 잡고, 기간이 길수록 √h 로 넓어집니다.
- 결과는 중심값과 95% 근사 구간입니다.
- 구조 변화, 정책 충격, 주말 공백을 설명하지 않습니다.
- 데이터가 부족하거나 모델 적합이 실패하면 예측값을 만들지 않고 사유만 표시합니다.

## 뉴스 저작권 및 이용 조건

- RSS가 제공하는 제목, 링크, 짧은 설명만 사용합니다.
- 원문은 각 언론사 사이트에서 확인하세요.
- 사내 배포 전에 Google News, BBC 등 각 매체의 이용 조건을 확인하세요.
- 생성형 AI로 기사 본문이나 사내 데이터를 보내지 않습니다.

## 회사 환경에서 확인할 사항

- 아웃바운드 HTTPS가 `api.frankfurter.dev`, `news.google.com`, `feeds.bbci.co.uk`에 열려 있는지
- 프록시가 있으면 `HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY` 설정
- CORS Origin을 실제 프론트 주소로 제한
- `ADMIN_API_ENABLED`는 개발에서만 켜 두고, 운영에서는 인증을 추가
- 로그에 API 키를 출력하지 않음
- 애플리케이션을 여러 프로세스로 띄우면 스케줄러가 중복 실행됨

## REST API

- `GET /api/health`
- `GET /api/indicators`
- `GET /api/exchange-rates/latest?pair=USD_KRW&period=1Y`
- `GET /api/exchange-rates/history?pair=USD_KRW&period=1Y`
- `GET /api/news?pair=USD_KRW&limit=20`
- `GET /api/forecasts?pair=USD_KRW&horizon=30`
- `POST /api/admin/refresh`
- `POST /api/admin/forecast`
- `GET /api/admin/status`

공통적으로 가능한 경우 `source`, `last_updated_at`, `unit`, `is_mock`, `warnings`를 `meta`에 포함합니다.

## 향후 경영정보 플랫폼 확장

같은 테이블로 다음 지표를 붙일 수 있습니다.

- 인건비
- 원자재 구매단가
- 물류비
- 매출 / 판매량
- 에너지 가격

공통 흐름은 `지표 → 실적 → 계획 → 예측 → 영향 이벤트 → 알림`입니다. 새 지표는 `Indicator` 행과 Provider 구현만 추가하면 됩니다.
