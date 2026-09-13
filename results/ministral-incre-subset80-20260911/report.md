# Ministral IncreQA 80-task subset 결과

실행 상태: **완료**

최종 결과 저장: 2026-09-12 19:11:03 UTC

분석 단위: MIMIC-IV 40문제 + eICU 40문제를 IncreQA 안에서 합산

## 결론

Ministral 3B·8B·14B에서 80개 동일 task를 대상으로 Original/Star와 다음 세 arm을 비교했다.

1. Full Tools + Metadata Available
2. SQL-only + Metadata Available
3. SQL-only + Metadata Unavailable

총 **1,440/1,440 scored slots**가 완료됐다. 이 중 현재 baseline과 호환되는 SQL 파일럿 192건을 보존·재사용했고, SQL extension 768건과 Full Tools 480건, 합계 **1,248건을 새로 실행**했다.

주요 관찰은 다음과 같다.

- Full Tools는 모든 모델·스키마에서 SQL-only Available보다 성공 수가 높았다.
- SQL-only Unavailable은 세 모델의 Original·Star를 합친 **0/480**이었다.
- Full Tools와 SQL-only Available 모두에서 모델 크기가 3B → 8B → 14B로 커질수록 성공 수가 증가했다.
- Star 환경의 Original-only 이름 사용은 Full Tools에서 3B 0회, 8B 5회, 14B 9회로, SQL-only Available의 84회, 237회, 360회보다 크게 적었다.
- Star가 Original보다 항상 어려운 것은 아니었다. SQL-only Available에서는 세 모델 모두 Star 성공 수가 더 높았고, Full Tools에서는 3B만 Original이 3건 높았다.

## 실험 설정

- 모델:
  - `openrouter/mistralai/ministral-3b-2512`
  - `openrouter/mistralai/ministral-8b-2512`
  - `openrouter/mistralai/ministral-14b-2512`
- Agent provider: Mistral 고정, fallback 없음, `require_parameters=false`
- User: Gemini 2.5 Flash-Lite, temperature 1, `nested-reflection`
- Validator: Gemini 2.5 Flash, n=1
- Agent temperature 0
- k=1, detailed feedback, 최대 30 turns, simulation retry 최대 10회
- Metadata Available: `allowed + benchmark guidance`
- Metadata Unavailable: `blocked + identifier-free guidance`
- Full Tools:
  - `table_search`
  - `column_search`
  - `sql_execute`
  - `value_substring_search`
  - `value_similarity_search`
  - `web_search`
- Embedding: OpenRouter `text-embedding-3-large`
- Runtime scoring·prompt·SQL timeout 정책은 변경하지 않았다.

Task 선택은 기존 파일럿 8개/DB를 유지하고, 나머지 task를 결과와 무관한 SHA-256 규칙으로 정렬해 32개/DB를 추가했다. 정확한 규칙과 ID는 `selection.json`에 있다.

## 성능

각 칸은 성공 / 80이다.

| 모델 | Full Available Original | Full Available Star | SQL Available Original | SQL Available Star | SQL Unavailable Original | SQL Unavailable Star |
|---|---:|---:|---:|---:|---:|---:|
| 3B | 25/80 (31.25%) | 22/80 (27.50%) | 7/80 (8.75%) | 12/80 (15.00%) | 0/80 | 0/80 |
| 8B | 32/80 (40.00%) | 43/80 (53.75%) | 21/80 (26.25%) | 27/80 (33.75%) | 0/80 | 0/80 |
| 14B | 42/80 (52.50%) | 44/80 (55.00%) | 32/80 (40.00%) | 34/80 (42.50%) | 0/80 | 0/80 |
| 합계 | 99/240 (41.25%) | 109/240 (45.42%) | 60/240 (25.00%) | 73/240 (30.42%) | 0/240 | 0/240 |

전체 성공은 **341/1,440 (23.68%)**다. Unavailable 480건이 전부 실패이므로, 전체 비율보다 arm별 수치를 우선해서 해석한다.

### Full Tools 대 SQL-only Available

| 모델 | 스키마 | Full 성공 | SQL 성공 | 차이 | Full-only / SQL-only paired 성공 |
|---|---|---:|---:|---:|---:|
| 3B | Original | 25 | 7 | +18 | 21 / 3 |
| 3B | Star | 22 | 12 | +10 | 15 / 5 |
| 8B | Original | 32 | 21 | +11 | 20 / 9 |
| 8B | Star | 43 | 27 | +16 | 24 / 8 |
| 14B | Original | 42 | 32 | +10 | 22 / 12 |
| 14B | Star | 44 | 34 | +10 | 17 / 7 |

Full Tools의 우위는 단순 성공 합계뿐 아니라 동일 task의 paired 전환에서도 모든 모델·스키마에서 나타났다.

### Original 대 Star paired 결과

`Star rescue`는 Original 실패·Star 성공, `Star regression`은 Original 성공·Star 실패다.

| 모델 | Arm | 둘 다 성공 | Star rescue | Star regression | 둘 다 실패 |
|---|---|---:|---:|---:|---:|
| 3B | Full Available | 14 | 8 | 11 | 47 |
| 3B | SQL Available | 1 | 11 | 6 | 62 |
| 8B | Full Available | 22 | 21 | 10 | 27 |
| 8B | SQL Available | 9 | 18 | 12 | 41 |
| 14B | Full Available | 26 | 18 | 16 | 20 |
| 14B | SQL Available | 18 | 16 | 14 | 32 |

SQL Unavailable에서는 세 모델 모두 80개 task가 Original·Star 양쪽에서 실패했다.

## Star trajectory의 스키마 이름 사용

아래 집계는 기존 `naming_audit` 핵심 모듈을 사용했다.

- Original에는 있고 Star에는 없는 이름과 Star에만 있는 이름을 테이블·컬럼별로 정확히 대조한다.
- 대소문자를 무시하되 underscore를 제거하거나 의미적 유사성을 사용하지 않는다.
- SQL의 물리 참조와 `column_search`·value-search의 명시적 스키마 인자를 포함한다.
- alias, CTE, derived output, 자연어, 임상 문자열 값과 `table_search` 입력은 제외한다.
- 메타데이터 탐색과 parser·lineage 불확실성은 확정 참조에 더하지 않는다.
- 실패 SQL과 reward 0은 포함한다.

`Original table/column`의 분모는 해당 조건에서 확인된 전체 primary 테이블/컬럼 참조다. `Star-only`는 테이블+컬럼 occurrence 합계다. 빈 timeout trajectory는 0회 사용으로 처리하지 않고 관찰 분모에서 제외했다.

| 모델 | Arm | 관찰 대화 | Original table | Original column | Original 합계 | Star-only 합계 | Original 영향 대화 |
|---|---|---:|---:|---:|---:|---:|---:|
| 3B | Full Available | 73 | 0/2,044 | 0/8,252 | **0** | 9,764 | 0/73 |
| 3B | SQL Available | 73 | 65/2,135 | 19/9,645 | **84** | 8,613 | 41/73 |
| 3B | SQL Unavailable | 76 | 158/1,438 | 147/5,519 | **305** | 975 | 36/76 |
| 8B | Full Available | 78 | 1/1,269 | 4/4,722 | **5** | 5,552 | 3/78 |
| 8B | SQL Available | 79 | 114/1,982 | 123/9,759 | **237** | 8,479 | 49/79 |
| 8B | SQL Unavailable | 79 | 98/1,293 | 134/4,544 | **232** | 901 | 49/79 |
| 14B | Full Available | 80 | 2/1,103 | 7/3,858 | **9** | 4,676 | 6/80 |
| 14B | SQL Available | 79 | 145/1,790 | 215/8,155 | **360** | 7,627 | 61/79 |
| 14B | SQL Unavailable | 78 | 206/1,927 | 261/7,454 | **467** | 1,326 | 55/78 |

이 결과는 Full Tools가 있을 때 세 모델 모두 Star 스키마에 맞춘 탐색을 수행하고 Original-only 이름 참조를 거의 제거했음을 보여준다. SQL-only Available에서는 모델 크기가 커질수록 Original-only 이름 사용도 증가하지만, 동시에 Star-only 이름 사용과 성공률도 증가한다. 따라서 Original 이름 사용은 관찰 가능한 prior-schema 재사용 신호이지만 그 자체가 최종 실패와 동의어는 아니다.

전체 720개 scored Star trajectory 중 695개에서 대화가 관찰됐다. 총 11,363개 tool call과 9,968개 SQL call을 분석했으며, 확정 Original-only 참조는 테이블 789회 + 컬럼 910회 = **1,699회**, Star-only 참조는 테이블 8,310회 + 컬럼 39,603회 = **47,913회**다. Original-only 참조는 1,050개 call, 300개 trajectory에 분포한다.

Metadata 탐색에서 명시한 Original-only 이름은 별도 검증에서 **70회 / 63 calls / 47 trajectories**로 확인됐다. 모두 테이블 이름이다. 이 수치는 위 primary 물리 참조 표에 더하지 않았으며, 합산하려면 call·trajectory identity를 중복 제거해야 한다.

기본 분석에는 parse-failure 호출 240개, parser 또는 lineage 불확실 호출 918개가 있다. 두 수는 중첩되므로 더하지 않는다. 확정하지 않은 Original 후보 87회는 위 표에 포함하지 않았다. SQLGlot 내부 `AttributeError`를 일으킨 malformed SQL 2개는 clean zero가 아니라 parse failure의 unresolved lexical evidence로 보존했다.

## Motivation 정합성

### Motivation 1

Metadata Available에서 Original/Star와 Full Tools/SQL-only의 성능 및 Star trajectory 이름 사용을 모두 비교했다. Full Tools는 여섯 모델×스키마 셀 모두 SQL-only보다 성공 수가 높았고, Original-only 이름 사용은 모든 모델에서 크게 줄었다.

### Motivation 2

SQL-only에서 Available과 Unavailable을 동일 task로 비교했다. Available은 Original 60/240, Star 73/240이었고 Unavailable은 양쪽 모두 0/240이었다. Metadata Availability가 현재 SQL-only 문제 해결의 핵심 조건이라는 패턴이 세 모델에서 동일하게 나타났다.

### Motivation 3

동일한 Motivation 1 설정을 알려진 크기의 Ministral 3B·8B·14B에 반복했다. Full 성공은 모델별 47/160 → 75/160 → 86/160, SQL Available 성공은 19/160 → 48/160 → 66/160으로 증가했다. 동시에 SQL-only Star에서 Original-only 이름 사용도 84 → 237 → 360회로 증가했다. 큰 모델이 Original 이름을 더 재사용하면서도 Star 스키마 사용과 문제 해결을 더 잘하는 패턴이다.

## 시도·비용·시간

- 저장 시도: 1,884건
- scored: 1,440건
- reward 1: 341건
- reward 0: 1,099건
- 제외된 reward-null: user_error 443건 + other 1건
- 기존 프로토콜에 따라 reward 0으로 유지한 agent timeout: 39건
- stored cost 합계: $39.33228735, 1,844/1,884 attempts에서 값 존재
- 실제 OpenRouter key usage 차액: **$13.88242720**
- OpenRouter 중단 상한: $18
- 종료 후 잔여 credit: $60.235891085
- Tavily: 526 → 536, **+10 credits**
- baseline부터 최종 summary까지: 약 **26.16시간**

청구 총액은 OpenRouter key usage 차액을 기준으로 한다. Stored cost는 LiteLLM이 각 checkpoint에 기록한 진단값이며 실제 key 차액과 일치하지 않으므로 청구액으로 사용하지 않는다.

## 실행·복구 기록

- SQL extension 768건은 config runner로 완료했다.
- 첫 Tavily usage guard가 30초 polling으로 HTTP 429를 내 안전 중단했으며, 5분 polling·비중단 Tavily query failure로 수정해 동일 config를 resume했다.
- 3B·8B·14B에서 발생한 장시간 정체는 비중단 stack으로 확인했다. SQL 정체는 종료 후 `calculate_reward_sql`의 SQL 재실행과 남은 `func_timeout` thread에서 발생했다.
- Full Tools는 이 worktree에 `text-embedding-3-large` FAISS cache가 없어 초기 생성 중 메모리 상한을 넘었다.
- Runtime 코드는 패치하지 않았다. 같은 DB 값·컬럼 순서·embedding model·batch 100을 사용하고 embedding batch를 즉시 FAISS에 추가하는 일회성 cache 준비 후, Full config를 `parallel_cells=1`로 순차 실행했다.
- 최종 Full 결과에는 config hash `99b4f477...`, `d90ad615...`, `bd0890f6...`의 roots만 사용했다. 0건 상태에서 중단된 이전 Full roots와 과거 비호환 파일럿은 제외했다.

## 보존·검증

- 신규 1,248건과 재사용 192건을 독립적으로 합쳐 1,440개 unique slot을 확인했다.
- 중복 scored slot과 중복 accepted sample ID는 0개다.
- 모든 모델·arm·schema는 동일한 80개 logical task를 가진다.
- 기존 파일럿 보호 파일 31개는 분석 전후 SHA-256이 동일하다.
- Selection artifact와 두 task catalog hash가 동일하다.
- 모든 최종 config의 source digest:
  `b75f8761d83c5df93b444d8f2a40dbdbf13520ad2b709537dfad98e65c38e145`
- FAISS cache 문서 수:
  - MIMIC Original/Star: 각각 196,674
  - eICU Original/Star: 각각 4,041
- 네 cache의 문서 수, table/column metadata 그룹과 파일 hash를 검증했다.
- 여섯 최종 config는 모두 complete이고 checkpoint error가 없다.
- 실험·예산·진행률 프로세스는 모두 종료됐다.

기계 판독 근거:

- `selection.json`
- `preflight.json`
- `performance-analysis.json`
- `naming-analysis.json`
- `verification.json`
- `recovery-1.json` ~ `recovery-5.json`

## 보안 후속 조치

실행 중 `py-spy --locals` 진단 한 번이 LiteLLM 내부의 OpenRouter API key 값을 세션 출력에 노출했다. 해당 값은 결과 artifact나 memory에 저장하지 않았고 이후 진단은 locals 없이 수행했다. 실험이 완료됐으므로 **사용 중인 OpenRouter key를 교체하는 것을 권장한다.**

이 실험은 고정된 80-task subset의 k=1 기술 통계다. 모집단 추론용 p-value나 task별 반복 신뢰도는 산출하지 않았다.
