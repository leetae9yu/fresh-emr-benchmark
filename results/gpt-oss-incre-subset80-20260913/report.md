# GPT-OSS IncreQA subset-80 결과

실행 상태: **완료**

분석 단위: MIMIC-IV 40문제 + eICU 40문제를 IncreQA 안에서 합산

실험 규모: GPT-OSS 20B/120B × 80 tasks × Original/Star × 3 arms × k=1 = **960 slots**

## 결론

- 네 최종 config는 모두 완료됐고, **960/960 scored slots**와 80-task pairing을 확인했다.
- Full Tools는 SQL-only Available보다 Original에서 두 모델 모두 5건 높았다. Star에서는 20B가 2건 높고 120B는 동률이었다.
- SQL-only Available은 210/320, Unavailable은 6/320으로 Metadata Availability 차이가 매우 컸다.
- GPT-OSS 20B와 120B의 합산 성능은 거의 같았다. Full은 112/160 대 110/160, SQL Available은 양쪽 모두 105/160이었다.
- 다만 schema별 방향은 반대였다. 20B는 Star가 높았고, 120B는 Original이 높거나 같았다.
- Star trajectory에서 Full Tools의 Original-only 이름 사용은 20B 1회, 120B 0회였다. SQL-only에서는 특히 Unavailable 조건에서 Original-only 이름 사용이 크게 늘었다.

## 실험 설정

- Agent:
  - `openrouter/openai/gpt-oss-20b`
  - `openrouter/openai/gpt-oss-120b`
- 알려진 크기:
  - 20B: 약 21B total / 3.6B active
  - 120B: 약 117B total / 5.1B active
- Provider: CoreWeave 고정
- Quantization: FP4
- Fallback 없음
- `require_parameters=false`
  - CoreWeave가 `parallel_tool_calls=false`를 strict-supported parameter로 광고하지 않아 strict filtering만 해제했다.
  - Provider와 FP4 routing은 계속 고정했다.
- User: Gemini 2.5 Flash-Lite, temperature 1, `nested-reflection`
- Validator: Gemini 2.5 Flash, n=1
- Agent temperature 0
- k=1, detailed feedback
- 최대 30 agent turns, simulation retry 최대 10회, task timeout 600초
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
- 기존 FAISS cache를 재사용했다.

Task ID는 Ministral subset80과 동일하다. MIMIC-IV와 eICU에서 각각 40개이며, 모든 모델·arm·schema가 같은 task를 사용한다.

## 성능

각 칸은 성공 / 80이다.

| 모델 | Full Available Original | Full Available Star | SQL Available Original | SQL Available Star | SQL Unavailable Original | SQL Unavailable Star |
|---|---:|---:|---:|---:|---:|---:|
| 20B | 52/80 (65.00%) | 60/80 (75.00%) | 47/80 (58.75%) | 58/80 (72.50%) | 1/80 (1.25%) | 0/80 |
| 120B | 58/80 (72.50%) | 52/80 (65.00%) | 53/80 (66.25%) | 52/80 (65.00%) | 5/80 (6.25%) | 0/80 |
| 합계 | 110/160 (68.75%) | 112/160 (70.00%) | 100/160 (62.50%) | 110/160 (68.75%) | 6/160 (3.75%) | 0/160 |

전체 성공은 **438/960 (45.625%)**다.

### Full Tools 대 SQL-only Available

| 모델 | Schema | Full | SQL | 차이 | Full-only / SQL-only |
|---|---|---:|---:|---:|---:|
| 20B | Original | 52 | 47 | +5 | 15 / 10 |
| 20B | Star | 60 | 58 | +2 | 12 / 10 |
| 120B | Original | 58 | 53 | +5 | 15 / 10 |
| 120B | Star | 52 | 52 | 0 | 14 / 14 |

Full Tools는 네 모델×schema 셀에서 SQL-only보다 낮지 않았다. 그러나 120B Star에서는 합계와 paired 전환이 모두 동률이므로, 모든 셀에서 일관된 우위라고 표현하지 않는다.

### Original 대 Star

`Star rescue`는 Original 실패·Star 성공, `Star regression`은 Original 성공·Star 실패다.

| 모델 | Arm | 둘 다 성공 | Star rescue | Star regression | 둘 다 실패 |
|---|---|---:|---:|---:|---:|
| 20B | Full Available | 43 | 17 | 9 | 11 |
| 20B | SQL Available | 40 | 18 | 7 | 15 |
| 20B | SQL Unavailable | 0 | 0 | 1 | 79 |
| 120B | Full Available | 40 | 12 | 18 | 10 |
| 120B | SQL Available | 39 | 13 | 14 | 14 |
| 120B | SQL Unavailable | 0 | 0 | 5 | 75 |

20B는 Full과 SQL Available 모두 Star 성공이 더 높았고, 120B는 Original이 높거나 같았다. 따라서 renaming 효과의 방향은 모델에 따라 달랐다.

### SQL-only Metadata Availability

| 모델 | Schema | Available | Unavailable | 차이 | Available-only / Unavailable-only |
|---|---|---:|---:|---:|---:|
| 20B | Original | 47 | 1 | +46 | 47 / 1 |
| 20B | Star | 58 | 0 | +58 | 58 / 0 |
| 120B | Original | 53 | 5 | +48 | 48 / 0 |
| 120B | Star | 52 | 0 | +52 | 52 / 0 |

SQL Available은 **210/320 (65.63%)**, SQL Unavailable은 **6/320 (1.88%)**이었다. Unavailable의 성공 6건은 모두 Original에 있고 Star는 두 모델 모두 0건이었다.

### 모델 크기

| Arm | 20B | 120B | 120B - 20B |
|---|---:|---:|---:|
| Full Available 전체 | 112/160 | 110/160 | -2 |
| SQL Available 전체 | 105/160 | 105/160 | 0 |
| SQL Unavailable 전체 | 1/160 | 5/160 | +4 |

총 파라미터 차이는 크지만 active parameter 차이는 3.6B 대 5.1B이고, 두 모델은 MoE 구성도 완전히 동일한 크기 확장만은 아니다. 이번 결과는 3-point scaling이 아니라 같은 GPT-OSS family의 two-point replication으로 해석한다.

## Star trajectory의 스키마 이름 사용

집계는 기존 `naming_audit` 핵심 모듈과 supplementary metadata reviewer를 수정 없이 사용했다.

- Original에는 있고 Star에는 없는 이름과 Star에만 있는 이름을 테이블·컬럼별로 정확히 대조한다.
- 대소문자를 무시하되 underscore를 제거하거나 의미적 유사성을 사용하지 않는다.
- SQL의 물리 참조와 `column_search`·value-search의 명시적 스키마 인자를 포함한다.
- alias, CTE, derived output, 자연어, 임상 문자열 값과 `table_search` 입력은 제외한다.
- 메타데이터 탐색과 parser·lineage 불확실성은 primary 확정 참조에 더하지 않는다.
- 실패 SQL과 reward 0은 포함한다.
- 각 job에서 filename timestamp가 가장 최신인 cumulative snapshot만 사용한다.

`Original table/column`의 분모는 해당 그룹의 전체 primary 테이블/컬럼 참조다. `Star-only`는 테이블+컬럼 occurrence 합계다.

| 모델 | Arm | 관찰 대화 | Original table | Original column | Original 합계 | Star-only 합계 | Original 영향 대화 |
|---|---|---:|---:|---:|---:|---:|---:|
| 20B | Full Available | 80 | 0/895 | 1/2,634 | **1** | 3,302 | 1/80 |
| 20B | SQL Available | 80 | 24/796 | 1/3,016 | **25** | 3,222 | 22/80 |
| 20B | SQL Unavailable | 80 | 142/1,135 | 52/1,145 | **194** | 304 | 58/80 |
| 120B | Full Available | 80 | 0/714 | 0/2,139 | **0** | 2,694 | 0/80 |
| 120B | SQL Available | 80 | 12/473 | 1/1,934 | **13** | 2,177 | 10/80 |
| 120B | SQL Unavailable | 80 | 151/1,566 | 76/759 | **227** | 252 | 64/80 |

전체 480개 scored Star trajectory 모두에서 대화가 관찰됐다. 총 **5,816 tool calls**와 **5,078 SQL calls**를 분석했다.

- Primary Original-only:
  - 테이블 329회
  - 컬럼 131회
  - 합계 **460회**
  - 349 calls / 155 trajectories
- Primary Star-only:
  - 테이블 2,664회
  - 컬럼 9,287회
  - 합계 **11,951회**
  - 2,118 calls / 373 trajectories
- Supplementary metadata Original-only:
  - **22회 / 22 calls / 21 trajectories**
  - 모두 테이블 이름이며 primary 표에 더하지 않았다.

Parser failure는 1 call, parser 또는 lineage unresolved는 30 calls였다. 두 수는 중첩될 수 있으며 clean zero로 취급하지 않았다. Supplementary metadata 검토에서는 ambiguous 5 occurrences와 excluded 2,725 occurrences를 확정 이름 사용에서 제외했다.

12개 tool call은 `sql_execute<|channel|>` 또는 `sql_execute<|channel|>commentary`라는 malformed tool name을 사용했다. 전체 tool-call 분모에는 보존했지만 정확한 `sql_execute` 호출에는 포함하지 않았다.

Full Tools에서는 Original-only 사용이 20B 1회, 120B 0회로 거의 사라졌다. SQL Available에서도 25회와 13회로 낮았지만, SQL Unavailable에서는 194회와 227회로 크게 증가했다. 두 Unavailable Star 성능이 모두 0/80이므로, Original schema 이름을 많이 재사용하는 것만으로는 Star 문제 해결로 이어지지 않았다.

## Motivation 정합성

### Motivation 1

Metadata Available에서 Original/Star와 Full Tools/SQL-only 성능을 모두 비교했다. Full 120B까지 완료되어 두 크기 모두 완전한 Motivation 1 행렬을 갖는다. Star trajectory의 Original-only/Star-only 이름 사용도 동일 analyzer로 측정했다.

### Motivation 2

SQL-only에서 Available과 Unavailable을 동일한 80 tasks로 비교했다. Available 210/320 대 Unavailable 6/320이라는 큰 차이가 두 모델에서 반복됐다. Original Unavailable의 6건과 Star Unavailable의 0건 차이는 익숙한 Original schema 이름에 대한 사전지식 가능성과 연결되는 관찰이다.

### Motivation 3

Motivation 1 설정을 알려진 크기의 GPT-OSS 20B와 120B에 반복했다. 큰 모델이 항상 더 높은 성능을 보이지 않았고, 20B와 120B 사이에서 Original/Star 방향이 뒤집혔다. 이 결과는 모델 크기 효과를 단일 방향으로 가정하지 않고 모델×schema 상호작용을 비교해야 함을 보여준다.

## 시도·비용·시간

- 저장 시도: **1,175건**
- scored: **960건**
- reward 1: 438건
- reward 0: 522건
- 제외된 reward-null: user_error 213건 + other 2건
- reward 0으로 보존한 agent timeout: 1건
- stored cost:
  - Agent: $3.13059222
  - User: $3.82811510
  - Validator: $0.92490930
  - 합계: **$7.88361662**
- 실제 OpenRouter key usage 차액: **$7.50684732**
- OpenRouter 중단 상한: $18
- Tavily: 538 → 538, **+0**
- preflight부터 최종 summary까지: **약 9.85시간**

청구 총액은 OpenRouter key usage 차액을 기준으로 한다. Stored cost는 checkpoint에 남은 LiteLLM 진단값이며, 중단 중 in-flight 요청과 response-cost 제공 범위 때문에 실제 key 차액과 일치하지 않는다.

## 실행·복구 기록

- SQL 20B는 최초 319/320에서 `mimic_iv_star / Available / task 87`을 동일 config `--resume`로 복구했다.
- SQL 120B는 320/320으로 완료됐다.
- Full 20B는 `parallel_cells=1`로 160/160 완료했다.
- Full 120B는 사용자 요청으로 74/160에서 일시중단했다.
- 이후 config와 result root를 바꾸지 않고 세 manifest job을 병렬 재개했다.
  - MIMIC Star 남은 6개
  - eICU Original 40개
  - eICU Star 40개
- eICU Star가 39/40으로 끝난 뒤 task 65를 동일 config `--resume`로 복구해 160/160을 만들었다.
- 병렬성은 속도·자원 운영 설정으로만 변경했으며 task/prompt/tool/scoring 조건은 바꾸지 않았다.

## 보존·검증

- 네 config summary: 320 + 320 + 160 + 160 = **960/960**
- 24개 jobs의 missing, duplicate, checkpoint error: 모두 0
- Selection SHA-256:
  `ce8004340915d22ee82392ef4c3f940344ccf2268c00c27150813cbcf31958b0`
- Catalog SHA-256:
  - MIMIC-IV: `3fa31ebfef07962c00ac1b41a03fbec667d1c40400ac1c602ffa1f805fbb2d73`
  - eICU: `78b2b07e34f23446330a5edb1ff9573a7319d55933fac1b0775d7639929a748f`
- 모든 config의 source digest:
  `b75f8761d83c5df93b444d8f2a40dbdbf13520ad2b709537dfad98e65c38e145`
- FAISS index hash와 document/vector 수:
  - MIMIC Original: 196,674
  - MIMIC Star: 196,674
  - eICU Original: 4,041
  - eICU Star: 4,041
- Naming analyzer tests: **68 passed**
- 최종 실험 프로세스: 0

FAISS `index.faiss` bytes, vector 수, document mapping 수는 preflight와 일치했다. Preflight에는 `index.pkl` hash가 없었으므로 pickle 내용의 전후 byte identity까지 주장하지 않는다.

## 보고 범위

이 결과는 고정된 IncreQA 80-task subset의 k=1 기술 통계다. p-value는 산출하지 않았으며 task별 반복 신뢰도나 모집단 추론을 의미하지 않는다.
