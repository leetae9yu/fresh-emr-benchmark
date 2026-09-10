# Experiment 2: Ministral model family (pilot)

Ministral 3B·8B·14B를 **동일한 MIMIC-IV 공통 표본**으로 비교한다.
마감 요청에 따라 실행을 중단하고, 세 모델·두 스키마에서 평가가 끝난 결과의 교집합을
선택했다. **모델당 28개, 총 84개**이며 새로 84개를 재실행한 것은 아니다.

본 비교는 **sql execute only + metadata Available** 조건이다.
Full Tools는 중단됐고, Nonavailable은 이 공통 표본에 없으므로 해당 성능을 0으로 표시하지 않는다.
eICU의 미완료 표본도 본 비교에 섞지 않았다.

## [SR-1]

SR-1은 각 태스크·스키마에서 채택한 한 평가 결과(k=1)의 성공률이다.
사용자 오류로 거부된 시도는 제외하고 유효 실패와 점수화된 시간 초과는 0점으로 포함한다.
저장된 reward를 사용했으며 현재 코드로 다시 채점하지 않았다.

### IncreQA

각 행은 **동일한 MIMIC-IV 태스크 7개**다.

| Model | DB | Tools | metadata | SR-1 |
| --- | --- | --- | --- | ---: |
| Ministral 3B | Original | sql execute only | Available | **14.29% (1/7)** |
| Ministral 3B | Star | sql execute only | Available | **14.29% (1/7)** |
| Ministral 8B | Original | sql execute only | Available | **42.86% (3/7)** |
| Ministral 8B | Star | sql execute only | Available | **28.57% (2/7)** |
| Ministral 14B | Original | sql execute only | Available | **85.71% (6/7)** |
| Ministral 14B | Star | sql execute only | Available | **42.86% (3/7)** |

→ 이 공통 표본에서는 모델 크기가 커질수록 Original·Star 모두 성공 수가 증가한다.

→ Original−Star 격차는 3B **0.00%p**, 8B **14.29%p**, 14B **42.86%p**다.
큰 모델에서도 이름 변경에 따른 성능 차이가 남는다.

→ 3B는 양쪽 모두 1/7로 낮다. 격차가 0이라고 이름 변경에 강하다는 뜻은 아니다.

### AdaptQA

각 행은 동일한 AdaptQA 태스크 7개이며, IncreQA와는 다른 태스크다.

| Model | DB | Tools | metadata | SR-1 |
| --- | --- | --- | --- | ---: |
| Ministral 3B | Original | sql execute only | Available | **0.00% (0/7)** |
| Ministral 3B | Star | sql execute only | Available | **0.00% (0/7)** |
| Ministral 8B | Original | sql execute only | Available | **0.00% (0/7)** |
| Ministral 8B | Star | sql execute only | Available | **0.00% (0/7)** |
| Ministral 14B | Original | sql execute only | Available | **0.00% (0/7)** |
| Ministral 14B | Star | sql execute only | Available | **42.86% (3/7)** |

→ 3B·8B는 공통 표본에서 성공이 없고, 14B는 Star에서만 3개를 해결했다.

→ IncreQA와 스키마 차이의 방향이 다르다. AdaptQA의 작은 표본과 확률적인 사용자
상호작용을 고려하면 Star가 일반적으로 더 쉽다고 결론내릴 수 없다.

### Total

| Model | IncreQA | AdaptQA | 두 흐름 합산, 참고 |
| --- | ---: | ---: | ---: |
| Ministral 3B | 2/14 (14.29%) | 0/14 (0.00%) | 2/28 (7.14%) |
| Ministral 8B | 5/14 (35.71%) | 0/14 (0.00%) | 5/28 (17.86%) |
| Ministral 14B | 9/14 (64.29%) | 3/14 (21.43%) | 12/28 (42.86%) |

합산은 고정한 표본 안의 참고 수치다. 흐름별 성능과 Original·Star 차이를 먼저 해석한다.

---

## [Original names in Star]

아래는 **공통 표본의 Star 대화만**, 모델·흐름별 7개를 대상으로 한다.
세 모델 모두 같은 분석기와 스키마 이름 집합을 사용했다.
Original에만 존재하는 테이블·컬럼의 SQL 내 물리 참조를 세고, 반복 참조는 반복 집계한다.
별칭·CTE·파생 이름·문자열·순수 메타데이터 탐색 대상은 주 참조 횟수와 구분한다.

전체 참조 분모는 Original 전용 + Star 전용 + 공통 + 미확인 이름의 물리 참조 합계다.
미확인 이름은 양쪽 스키마 어디에도 없는 이름이다. SQL 한 번에 여러 참조가 있을 수 있다.

### IncreQA — SQL-only

| Model | metadata | SQL 호출 시도 수 | Original 테이블 등장 | Original 컬럼 등장 | Original 이름을 사용한 대화 |
| --- | --- | ---: | ---: | ---: | ---: |
| Ministral 3B | Available | **177** | **2/219 (0.91%)** | **5/628 (0.80%)** | **3/7 (42.86%)** |
| Ministral 8B | Available | **93** | **1/140 (0.71%)** | **25/638 (3.92%)** | **3/7 (42.86%)** |
| Ministral 14B | Available | **74** | **7/97 (7.22%)** | **67/519 (12.91%)** | **7/7 (100.00%)** |

| Model | Original 이름을 참조한 SQL / 전체 SQL |
| --- | ---: |
| Ministral 3B | 7/177 (3.95%) |
| Ministral 8B | 9/93 (9.68%) |
| Ministral 14B | 20/74 (27.03%) |

→ 3B는 SQL을 가장 많이 호출했지만 성공률은 가장 낮다.

→ 14B는 SQL 호출 수가 가장 적으면서 성공률은 가장 높지만, Original 이름을 참조한
SQL·대화 비율도 가장 높다. **성능이 높다는 것과 Original 이름을 덜 쓴다는 것은 다르다.**

→ 세 모델 모두 Star 전용 이름도 7/7개 대화에서 사용했다.
Original 이름 사용이 Star 이름을 전혀 사용하지 않았다는 뜻은 아니다.

### AdaptQA — SQL-only

| Model | metadata | SQL 호출 시도 수 | Original 테이블 등장 | Original 컬럼 등장 | Original 이름을 사용한 대화 |
| --- | --- | ---: | ---: | ---: | ---: |
| Ministral 3B | Available | **123** | **6/161 (3.73%)** | **0/675 (0.00%)** | **3/7 (42.86%)** |
| Ministral 8B | Available | **69** | **3/72 (4.17%)** | **4/391 (1.02%)** | **4/7 (57.14%)** |
| Ministral 14B | Available | **73** | **2/95 (2.11%)** | **0/472 (0.00%)** | **2/7 (28.57%)** |

| Model | Original 이름을 참조한 SQL / 전체 SQL |
| --- | ---: |
| Ministral 3B | 6/123 (4.88%) |
| Ministral 8B | 7/69 (10.14%) |
| Ministral 14B | 2/73 (2.74%) |

→ AdaptQA에서는 14B의 Original 이름 사용 비율이 낮고 성공률이 높지만,
태스크가 7개뿐이다. 이를 일반적인 모델 크기 효과나 인과관계로 주장하지 않는다.

### Tools in SQL-only condition

아래도 Star 공통 표본만의 호출 수다.

| 도구 | Incre 3B | Incre 8B | Incre 14B | Adapt 3B | Adapt 8B | Adapt 14B |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| sql_execute | 177 | 93 | 74 | 123 | 69 | 73 |
| nonavailable tools | 0 | 0 | 0 | 0 | 0 | 0 |
| total | 177 | 93 | 74 | 123 | 69 | 73 |

→ 기록된 도구 호출의 **100%가 sql_execute**다. Full Tools의 호출 분포는 이 표에 포함하지 않는다.

### 메타데이터 탐색과 불확실성

| 흐름 | Model | 메타데이터 탐색 SQL | 파싱 실패 | 파싱·스코프 불확실 호출 |
| --- | --- | ---: | ---: | ---: |
| IncreQA | 3B | 28 | 6 | 17 |
| IncreQA | 8B | 25 | 0 | 6 |
| IncreQA | 14B | 24 | 0 | 3 |
| AdaptQA | 3B | 24 | 6 | 10 |
| AdaptQA | 8B | 16 | 0 | 1 |
| AdaptQA | 14B | 23 | 0 | 5 |

메타데이터 탐색 대상에서의 Original 전용 이름은 3B AdaptQA에 1회 있었으며
나머지 다섯 셀은 0회였다. 이는 위 물리 참조 집계와 별도다.
불확실 호출 수에는 파싱 실패가 포함된다. 특히 3B의 낮은 확정 이름 참조 수를
낮은 편향이라고 단정하지 않는다.

---

## 표본과 실행 한계

- IncreQA 태스크: **54, 66, 83, 84, 92, 94, 112**.
- AdaptQA 태스크: **3, 10, 13, 14, 15, 19, 25**.
- 각 흐름에서 세 모델·두 스키마에 같은 ID를 사용했다.
- IncreQA 87과 AdaptQA 12는 14B의 검증기 오류 때문에 두 스키마·세 모델 모두에서
  대칭적으로 제외했다. 성공 여부로 고르지 않았지만 **사후 완료분 선택 편향**은 남는다.
- 선택 태스크의 기록 141개 중 평가 결과는 84개다: `no_error` 79개,
  점수 0인 `agent_timeout` 5개. 나머지 57개 `user_error` 시도는 보존하되 분모에서 제외했다.
- 시간 초과 5개는 모두 3B AdaptQA이며 실패로 포함했다.
- 같은 패밀리라도 구조 세부·학습 조건·서빙 정밀도가 모두 동일하다고 확인된 것은 아니다.
  모든 모델은 Mistral 공급자로 고정했지만 정밀도는 미공개다.
- k=1의 작은 MIMIC-IV 표본이므로 p-value나 전체 벤치마크 일반화 주장을 하지 않는다.

### 중단 시 전체 결과 현황 — 성능 비교용이 아님

| Model | SQL-only 평가 완료 | Full Tools 평가 완료 |
| --- | ---: | ---: |
| Ministral 3B | 46/64 | 25/64 |
| Ministral 8B | 37/64 | 39/64 |
| Ministral 14B | 61/64 | 0/64 |

위 완료 범위는 모델마다 다르므로 이 표의 결과를 그대로 비교하지 않았다.
공통 84개 분석 밖의 결과와 중단된 기록도 보존했고, 추가 실행은 모두 멈춘 상태다.
SQLite 실행·타임아웃 취소 정체가 있었지만 본 요약을 위해 실행기나 채점을 수정하지 않았다.

전체 Ministral 배치의 OpenRouter 관측 차액은 **약 $2.68**이다.
중단한 풀툴·공통 표본 밖의 SQL-only·재시도·호환성 확인을 포함하며,
**공통 84개만의 비용이 아니다.**

## 근거

- [공통 표본 선정과 실행 이력 상세 보고서](ministral3-sql-only-deadline-pilot-report.md)
- 로컬 분석 자료: `results/ministral3-sql-only-deadline-pilot-20260910/`의
  `analysis.json`, `verification.json`, `naming-incre/summary.json`, `naming-adapt/summary.json`.

위 자료의 확인된 점수와 집계를 발표용 형식으로 정리했으며 새 모델 호출은 하지 않았다.
