# Experiment 1: Gemini 3.8 Flash (pilot)

대상 모델은 Gemini 3.8 Flash다. 아래 IncreQA는 **2026-09-09 완료된 공식 사용자
시뮬레이터 A/B 재실행**, AdaptQA는 **별도 과거 소규모 파일럿**이다.
두 실행의 표본과 이력이 다르므로 한 실험의 합산 점수로 묶지 않는다.

메타데이터 Available은 `allowed + benchmark`, Nonavailable은
`blocked + identifier_free`다. 즉 메타데이터 접근뿐 아니라 식별자 가이드도 함께 달라진다.
두 조건 모두 SQL-only이며 상세 오류 피드백을 제공한다.

## [SR-1]

SR-1은 태스크·스키마·정보 조건마다 채택된 한 평가 결과(k=1)의 성공률이다.
사용자 오류로 거부된 시도는 제외하지만, 유효한 에이전트 실패는 0점으로 포함한다.
최초 API 호출의 성공률이나 최초 원시 대화만의 성공률을 뜻하지 않는다.
각 실행에 저장된 reward를 그대로 사용하며, 현재 코드로 재채점하지 않았다.
논문 원본 채점기와 완전히 동일한 재현이라고 주장하지 않는다.

### IncreQA

MIMIC-IV 16개와 eICU 16개를 합쳐 **각 행의 분모는 32개**다.
네 SQL-only 조건의 동일한 32개 태스크를 대응시켰으며 총 128개 평가가 완료됐다.

| DB | Tools | metadata | SR-1 |
| --- | --- | --- | ---: |
| Original | Full Tools | Available | — |
| Star | Full Tools | Available | — |
| Original | sql execute only | Available | **81.25% (26/32)** |
| Star | sql execute only | Available | **78.13% (25/32)** |
| Original | sql execute only | Nonavailable | **71.88% (23/32)** |
| Star | sql execute only | Nonavailable | **0.00% (0/32)** |

`—`는 0점이 아니라 **이 비교에 넣을 수 있는 완료된 풀툴 대조군이 없음**을 뜻한다.
이전 CDEF 실행은 256개 중 43개에서 중단됐고 사용자 시뮬레이터 이력도 달라 합치지 않았다.

→ Available에서는 Original과 Star의 차이가 **3.13%p**로 작다.

→ Nonavailable에서는 Original은 71.88%지만 Star는 0%로 떨어진다.
Original−Star 격차가 **3.13%p → 71.88%p**, 반올림 전 차이 기준 **68.75%p 증가**한다.

→ 따라서 이 파일럿에서는 정보 제공 여부에 따른 Star 성능 차이가 크다.
다만 메타데이터와 가이드가 동시에 변하므로 메타데이터만의 인과효과로 단정하지 않는다.
풀툴 대조군이 없으므로 도구 제공 효과와의 크기 비교도 하지 않는다.

### AdaptQA — 별도 과거 파일럿

과거 파일럿에서 MIMIC-IV와 eICU 각각 태스크 0, 20, 35를 사용했다.
**각 행의 분모는 6개**, 네 조건 총 24개 평가다.
이는 위 IncreQA 128개 재실행의 일부가 아니다.

| DB | Tools | metadata | SR-1 |
| --- | --- | --- | ---: |
| Original | Full Tools | Available | — |
| Star | Full Tools | Available | — |
| Original | sql execute only | Available | **83.33% (5/6)** |
| Star | sql execute only | Available | **83.33% (5/6)** |
| Original | sql execute only | Nonavailable | **50.00% (3/6)** |
| Star | sql execute only | Nonavailable | **0.00% (0/6)** |

→ Available에서는 두 스키마 모두 5/6을 해결했다.

→ Nonavailable에서는 Original 3/6, Star 0/6으로 차이가 나타났다.

→ 다만 원래 태스크가 6개뿐인 과거 파일럿이다. 위 IncreQA와 같은 표본 규모의
재실행이나 전체 AdaptQA 성능으로 해석하지 않는다.

### Total

| 자료 | 성공 / 평가 수 | 집계 성공률 |
| --- | ---: | ---: |
| 최신 IncreQA A/B 재실행, 네 조건 합계 | 74/128 | 57.81% |
| 과거 AdaptQA 파일럿, 네 조건 합계 | 13/24 | 54.17% |

두 행은 **각 실행 내부의 운영상 합계**다. 서로 다른 표본·실행을 합친 Total SR-1은
만들지 않는다. 성능 해석에는 위 조건별 표를 사용한다.

---

## [Original names in Star]

**이하 이름 사용과 도구 호출 표는 모두 최신 IncreQA의 Star 대화만 대상으로 한다.**
Available 32개와 Nonavailable 32개이며 성공·실패를 모두 포함한다.
AdaptQA나 거부된 사용자 시뮬레이션의 호출은 포함하지 않는다.

두 조건에 같은 분석기와 스키마 이름 집합을 적용했다. Original DB에는 있지만
Star DB에는 없는 테이블·컬럼의 **SQL 내 물리적 참조**를 센다.
반복 참조는 반복 집계하며, 별칭·CTE·파생 이름·문자열 언급과 메타데이터 탐색 대상은
주 참조 횟수와 구분한다. 따라서 모든 문자열 등장 횟수는 아니다.

### Full Tools

비교 가능한 완료 대조군이 없어 이름 사용량과 풀툴 호출 분포는 제시하지 않는다.

### SQL-only

전체 테이블·컬럼 참조 수는 각각 Original 전용 + Star 전용 + 공통 + 미확인 이름의
확정된 물리 참조 합계다. 미확인 이름은 양쪽 스키마 어디에도 없는 이름을 뜻한다.

| Tools | metadata | SQL 호출 시도 수 | Original 테이블 등장 | Original 컬럼 등장 | Original 이름을 사용한 대화 |
| --- | --- | ---: | ---: | ---: | ---: |
| sql execute only | Available | **333** | **1/423 (0.24%)** | **0/1,801 (0.00%)** | **1/32 (3.13%)** |
| sql execute only | Nonavailable | **937** | **181/788 (22.97%)** | **18/82 (21.95%)** | **32/32 (100.00%)** |

분모 구성:

- Available 테이블: 1 + 386 + 36 + 0 = **423**.
- Nonavailable 테이블: 181 + 87 + 48 + 472 = **788**.
- Available 컬럼: 0 + 1,702 + 80 + 19 = **1,801**.
- Nonavailable 컬럼: 18 + 13 + 1 + 50 = **82**.

| Tools | metadata | Original 이름을 참조한 SQL / 전체 SQL |
| --- | --- | ---: |
| sql execute only | Available | **1/333 (0.30%)** |
| sql execute only | Nonavailable | **191/937 (20.38%)** |

하나의 SQL에 여러 이름이 있으면 등장 횟수는 여러 번 세지만, 이름을 사용한 SQL과
대화는 각각 한 번만 센다. Original 전용과 Star 전용 이름을 함께 사용하는 SQL도 있다.

→ Nonavailable에서는 SQL 호출이 **333 → 937회**, 약 **2.81배**로 증가한다.

→ 호출 수가 늘어나는 동시에 Original 이름을 참조한 SQL 비율도 **0.30% → 20.38%**,
해당 대화 비율도 **3.13% → 100%**로 증가한다.

→ 반면 Star 전용 컬럼 참조는 **1,702 → 13회**로 줄어든다.
단순히 쿼리를 적게 작성한 문제가 아니라, 사용할 스키마 이름을 찾고 활용하는 과정의
어려움과 일치하는 관측이다. 이름 사용만으로 학습 데이터 암기나 실패의 단독 원인을
증명하지는 않는다.

### Tools in SQL-only condition

| 도구 | Available 호출 수 | Nonavailable 호출 수 |
| --- | ---: | ---: |
| sql_execute | 333 | 937 |
| nonavailable tools | 0 | 0 |
| total | 333 | 937 |

→ 두 조건 모두 도구 호출의 **100%가 sql_execute**다.
별도의 table_search나 column_search는 제공하지 않았고, 메타데이터도 SQL로 탐색했다.

### 메타데이터 탐색과 집계 불확실성

| 항목 | Available | Nonavailable |
| --- | ---: | ---: |
| 메타데이터 탐색 SQL 호출 | 101 | 152 |
| 메타데이터 탐색 대상에서의 Original 전용 이름 등장 | 2 | 15 |
| SQL을 한 번도 호출하지 않은 대화 | 1/32 | 0/32 |
| SQL 파싱 실패 호출 | 0 | 1 |
| 파싱·스코프 해석이 불확실한 호출, 파싱 실패 포함 | 2 | 8 |

메타데이터 탐색에서의 이름 등장은 위 물리 참조 횟수와 별도다.
Nonavailable의 탐색 호출에는 **차단된 시도**도 포함되므로 성공한 탐색 횟수가 아니다.
파싱이 실패하거나 해석이 불확실한 SQL도 호출 분모에 남겨두고, 그 안의 참조를
확정된 Original 이름이나 이름 사용이 없는 사례로 억지 분류하지 않았다.

Experiment 0의 과거 SQL-only AST 집계와는 처리 규칙이 다르므로, 이 표와 그 표의
이름 비율을 직접 빼서 모델 차이로 해석하지 않는다. **이 표 안의 A/B는 동일 기준이다.**

---

## 표본·실행 이력과 해석 범위

| 자료 | 원래 태스크 수 | 평가 결과 | 저장된 시도 | 사용자 오류로 거부 |
| --- | ---: | ---: | ---: | ---: |
| 최신 IncreQA A/B 재실행 | 32 | 128 | 145 | 17 |
| 과거 AdaptQA 파일럿만 | 6 | 24 | 33 | 9 |

두 자료의 평가 결과는 모두 검증 상태가 `no_error`인 기록이다.
재시도 후 채택된 평가 결과와 거부된 시도를 구분하며, 거부 시도를 0점으로 바꾸지 않았다.
원래 태스크가 스키마·정보 조건별로 반복되므로 128개나 24개를 독립 질문 수로 보지 않는다.
k=1의 선정 파일럿이므로 p-value나 모집단 일반화 주장은 제시하지 않는다.

최신 IncreQA의 Star Nonavailable 32개는 모두 사용자 종료 표식 없이 점수 0으로 끝났고,
각각 에이전트 메시지 30개를 사용했다. 이 결과는 턴 한도 내 대화 완결 실패를 포함하며
단순한 최종 답 한 번의 오답 32개와 동일시하지 않는다.

사용자 모델은 2.5 Flash-Lite, 에이전트는 3.8 Flash, 검증 모델은 2.5 Flash다.
최신 IncreQA 재실행은 공식 사용자 모듈과의 일치를 검증했지만, 그 사실을 과거 AdaptQA의
소스 동일성 증거로 소급 적용하지 않는다. 과거 파일럿 매니페스트는 시작일을 2026-09-03으로
기록하고 체크포인트 파일명은 20260904 시각을 포함한다.

최신 IncreQA 실행은 약 **22분 47초**, OpenRouter 키 사용량 관측 차액은
**$6.439793275**다. 이는 위 IncreQA 재실행 비용이며 과거 AdaptQA 비용을 더한 값이 아니다.

## 근거

- [최신 IncreQA A/B 상세 보고서](gemini38-incre-ab-official-rerun-report.md)
- [표의 계산 근거](experiment-1-gemini38-flash-pilot-metrics.json)
- 최신 집계 원본: `results/gemini38-incre-ab-rerun-report-audit/`.
- 과거 AdaptQA 원본: `EHR-ChatQA/results/gemini_3.8_flash_incre_adapt_pilot/RUN_MANIFEST.md`
  및 같은 디렉터리의 AdaptQA 체크포인트 8개.

마지막 두 항목의 원시 자료는 로컬 감사 자료다. 이 요약을 위해 새 모델 실행이나
기존 결과·점수의 변경은 하지 않았다.
