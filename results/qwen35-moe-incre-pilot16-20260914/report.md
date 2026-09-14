# Qwen3.5 MoE IncreQA 16-task pilot 결과

실행 상태: **완료**

분석 단위: MIMIC-IV 8문제 + eICU 8문제를 IncreQA 안에서 합산

실험 규모: Qwen3.5 MoE 3개 모델 × 16 tasks × Original/Star × 3 arms × k=1 = **288 canonical slots**

## 결론

- 여섯 최종 config가 모두 완료됐고 **288/288 canonical scored slots**와 task pairing을 확인했다.
- Full Tools Available은 80/96, SQL-only Available은 77/96으로 전체 차이는 3건이었다. Full의 효과는 모델과 스키마에 따라 달랐다.
- SQL-only Available은 77/96, Unavailable은 5/96이었다. Unavailable 성공 5건은 전부 Original에서 나왔고 Star Unavailable은 0/48이었다.
- Full Tools의 Original-only 이름 사용은 Star trajectory 전체에서 2회뿐이었다. SQL Available은 32회, SQL Unavailable은 279회였다.
- 모델 크기 증가에 따라 모든 조건의 성능이나 Original 이름 사용이 단조롭게 증가하지 않았다. Full 총성공은 26 → 26 → 28, SQL Available은 23 → 29 → 25, SQL Unavailable은 0 → 1 → 4였다.
- OpenRouter 실제 사용 증가액은 **$20.17806387**로 $28 guard보다 $7.82193613 낮았다.

## 실험 설정

### 모델

| 모델 | 총 파라미터 | Active 파라미터 |
|---|---:|---:|
| Qwen3.5 35B-A3B | 35B | 3B |
| Qwen3.5 122B-A10B | 122B | 10B |
| Qwen3.5 397B-A17B | 397B | 17B |

세 모델 모두 Qwen3.5 MoE 계열이다. 35B와 122B는 256 experts/top-8이고 397B는 512 experts/top-10이므로, 동일 family의 크기 비교이지만 expert 구성이 완전히 고정된 size-only 비교는 아니다.

### 공통 조건

- Agent provider: AtlasCloud 고정
- Quantization: FP8
- Fallback 없음
- `require_parameters=false`
- User: OpenRouter Gemini 2.5 Flash-Lite, temperature 1, `nested-reflection`
- Validator: OpenRouter Gemini 2.5 Flash, n=1
- Agent temperature 0
- k=1, detailed feedback
- 최대 30 agent turns, simulation retry 최대 10회, task timeout 600초
- Metadata Available: `metadata_access=allowed` + benchmark schema guidance
- Metadata Unavailable: `metadata_access=blocked` + identifier-free schema guidance
- Embedding: OpenRouter `text-embedding-3-large`

### Arms

1. Full Tools + Metadata Available
2. SQL-only + Metadata Available
3. SQL-only + Metadata Unavailable

Full Tools는 `table_search`, `column_search`, `sql_execute`, `value_substring_search`, `value_similarity_search`, `web_search`를 노출했다. 기존 FAISS cache를 재사용했다.

### Task IDs

- MIMIC-IV: `54, 66, 83, 84, 87, 92, 94, 112`
- eICU: `16, 46, 66, 71, 79, 100, 114, 131`

모든 모델·arm·schema에서 같은 16개 logical tasks를 사용했다.

## 성능

각 칸은 성공 / 16이다.

| 모델 | Full Original | Full Star | SQL Available Original | SQL Available Star | SQL Unavailable Original | SQL Unavailable Star |
|---|---:|---:|---:|---:|---:|---:|
| 35B-A3B | 13/16 (81.25%) | 13/16 (81.25%) | 13/16 (81.25%) | 10/16 (62.50%) | 0/16 | 0/16 |
| 122B-A10B | 12/16 (75.00%) | 14/16 (87.50%) | 15/16 (93.75%) | 14/16 (87.50%) | 1/16 (6.25%) | 0/16 |
| 397B-A17B | 15/16 (93.75%) | 13/16 (81.25%) | 12/16 (75.00%) | 13/16 (81.25%) | 4/16 (25.00%) | 0/16 |
| 합계 | 40/48 (83.33%) | 40/48 (83.33%) | 40/48 (83.33%) | 37/48 (77.08%) | 5/48 (10.42%) | 0/48 |

전체 성공은 **162/288 (56.25%)**다.

### Full Tools 대 SQL-only Available

| 모델 | Schema | Full | SQL | 차이 | Full-only / SQL-only |
|---|---:|---:|---:|---:|---:|
| 35B-A3B | Original | 13 | 13 | 0 | 2 / 2 |
| 35B-A3B | Star | 13 | 10 | +3 | 4 / 1 |
| 122B-A10B | Original | 12 | 15 | -3 | 1 / 4 |
| 122B-A10B | Star | 14 | 14 | 0 | 0 / 0 |
| 397B-A17B | Original | 15 | 12 | +3 | 4 / 1 |
| 397B-A17B | Star | 13 | 13 | 0 | 2 / 2 |

Full Tools의 합산 성공은 80/96, SQL Available은 77/96이었다. Full은 35B Star와 397B Original에서 3건 높았지만, 122B Original에서는 3건 낮았다. 따라서 이 pilot은 Full Tools가 모든 모델·스키마에서 일관되게 우세하다고 말하지 않는다.

### Original 대 Star paired 결과

`Star rescue`는 Original 실패·Star 성공, `Star regression`은 Original 성공·Star 실패다.

| 모델 | Arm | 둘 다 성공 | Star rescue | Star regression | 둘 다 실패 |
|---|---|---:|---:|---:|---:|
| 35B-A3B | Full Available | 11 | 2 | 2 | 1 |
| 35B-A3B | SQL Available | 9 | 1 | 4 | 2 |
| 35B-A3B | SQL Unavailable | 0 | 0 | 0 | 16 |
| 122B-A10B | Full Available | 12 | 2 | 0 | 2 |
| 122B-A10B | SQL Available | 13 | 1 | 2 | 0 |
| 122B-A10B | SQL Unavailable | 0 | 0 | 1 | 15 |
| 397B-A17B | Full Available | 12 | 1 | 3 | 0 |
| 397B-A17B | SQL Available | 10 | 3 | 2 | 1 |
| 397B-A17B | SQL Unavailable | 0 | 0 | 4 | 12 |

Full에서는 Original과 Star가 각각 40/48로 동률이었다. SQL Available에서는 Original 40/48, Star 37/48이었다. 모델별 방향은 122B Full과 397B SQL Available에서 Star가 높고, 다른 일부 셀에서는 Original이 높아 하나의 방향으로 고정되지 않았다.

### SQL-only Metadata Availability

| 모델 | Schema | Available | Unavailable | 차이 | Available-only / Unavailable-only |
|---|---|---:|---:|---:|---:|
| 35B-A3B | Original | 13 | 0 | +13 | 13 / 0 |
| 35B-A3B | Star | 10 | 0 | +10 | 10 / 0 |
| 122B-A10B | Original | 15 | 1 | +14 | 14 / 0 |
| 122B-A10B | Star | 14 | 0 | +14 | 14 / 0 |
| 397B-A17B | Original | 12 | 4 | +8 | 9 / 1 |
| 397B-A17B | Star | 13 | 0 | +13 | 13 / 0 |

SQL Available은 **77/96 (80.21%)**, SQL Unavailable은 **5/96 (5.21%)**였다. Metadata와 schema guidance를 함께 차단했을 때의 성능 저하는 세 모델에서 반복됐다.

### 모델 크기

| Arm | 35B-A3B | 122B-A10B | 397B-A17B |
|---|---:|---:|---:|
| Full Available 전체 | 26/32 | 26/32 | 28/32 |
| SQL Available 전체 | 23/32 | 29/32 | 25/32 |
| SQL Unavailable 전체 | 0/32 | 1/32 | 4/32 |

큰 모델이 모든 조건에서 더 높은 성능을 보이지 않았다. 다만 익숙한 Original schema의 Unavailable 조건에서는 성공 수가 0 → 1 → 4로 증가했고, Star Unavailable은 세 모델 모두 0이었다.

## Star trajectory의 스키마 이름 사용

기존 deterministic `naming_audit` core와 supplementary metadata reviewer를 수정 없이 사용했다.

- Original에는 있고 Star에는 없는 이름과 Star에만 있는 이름을 테이블·컬럼별로 정확히 비교한다.
- 대소문자를 무시하되 underscore를 보존하고 의미적 유사성을 사용하지 않는다.
- SQL 물리 참조와 `column_search`·value-search의 명시적 table/column 인자를 포함한다.
- Alias, CTE, derived alias, 자연어, 임상 문자열 값과 `table_search` 입력은 제외한다.
- Parser failure와 unresolved lineage는 확정 이름 참조에 더하지 않는다.
- 실패 SQL과 reward 0 trajectory도 포함한다.

`Original table/column`의 분모는 해당 그룹의 확인된 primary 테이블/컬럼 참조다.

| 모델 | Arm | 관찰 대화 | Original table | Original column | Original 합계 | Star-only 합계 | Original 영향 대화 |
|---|---|---:|---:|---:|---:|---:|---:|
| 35B-A3B | Full Available | 16 | 0/232 | 0/1,155 | **0** | 1,371 | 0/16 |
| 35B-A3B | SQL Available | 16 | 1/242 | 6/1,162 | **7** | 1,288 | 4/16 |
| 35B-A3B | SQL Unavailable | 16 | 42/469 | 70/433 | **112** | 75 | 16/16 |
| 122B-A10B | Full Available | 16 | 0/281 | 2/1,081 | **2** | 1,324 | 1/16 |
| 122B-A10B | SQL Available | 16 | 1/206 | 1/984 | **2** | 1,160 | 2/16 |
| 122B-A10B | SQL Unavailable | 16 | 44/449 | 9/338 | **53** | 101 | 13/16 |
| 397B-A17B | Full Available | 16 | 0/271 | 0/1,283 | **0** | 1,507 | 0/16 |
| 397B-A17B | SQL Available | 16 | 6/226 | 17/1,195 | **23** | 1,301 | 7/16 |
| 397B-A17B | SQL Unavailable | 16 | 70/439 | 44/204 | **114** | 41 | 15/16 |

전체 144개 canonical Star trajectory의 대화를 모두 관찰했다.

- Tool calls: 2,597
- SQL calls: 2,361
- Primary table references: 2,815
- Primary column references: 7,835
- Original-only: 테이블 164 + 컬럼 149 = **313 occurrences**
- Original-only 영향: 237 calls / 58 trajectories
- Star-only: 테이블 1,432 + 컬럼 6,736 = **8,168 occurrences**
- Star-only 영향: 1,111 calls / 115 trajectories
- Parser failures: 4 calls
- Parser 또는 lineage unresolved: 12 calls

Full Tools의 Original-only 사용은 세 모델 합계 2회였다. SQL Available은 32회, SQL Unavailable은 279회였다. Full Tools에서는 schema search를 통해 Star 이름을 사용하면서 Original prior 이름이 거의 제거됐다.

Supplementary metadata audit에서는 Original-only table target **1회 / 1 call / 1 trajectory**를 확인했다. 이 값은 primary 물리 참조 표에 더하지 않았다. 270개 metadata-screened calls를 검토했고 473개 비식별자·임상값·패턴 evidence를 제외했다.

## Motivation 정합성

### Motivation 1

Metadata Available에서 Original/Star와 Full Tools/SQL-only 성능을 비교하고, Star trajectory의 Original-only/Star-only 이름 사용을 동일 analyzer로 측정했다.

Full 성능은 80/96, SQL Available은 77/96으로 차이가 작고 모델·스키마별 방향은 달랐다. 반면 Original-only 이름 사용은 Full 2회 대 SQL Available 32회로 감소했다. 즉 schema tools의 가장 일관된 효과는 이 pilot에서 성공률 상승 자체보다 Star schema에 맞춘 이름 사용이었다.

### Motivation 2

SQL-only에서 동일 task의 Available과 Unavailable을 비교했다. Available 77/96 대 Unavailable 5/96이었고, Star Unavailable은 0/48이었다. 동시에 Star의 Original-only 이름 사용은 Available 32회에서 Unavailable 279회로 증가했다.

### Motivation 3

Motivation 1 구성을 알려진 총/active parameter의 Qwen3.5 MoE 35B-A3B, 122B-A10B, 397B-A17B에 반복했다. Full 성능은 26 → 26 → 28, SQL Available은 23 → 29 → 25로 단조로운 size trend가 없었다. Original Unavailable의 0 → 1 → 4와 모델별 naming 차이는 model size와 schema prior의 상호작용을 Full80에서 더 확인할 가치가 있음을 보여준다.

## Runtime 호환성 수정과 복구

초기 launch에서 저장소의 legacy Qwen parser가 OpenRouter native `message.tool_calls`를 빈 `content` 파싱 결과로 덮어썼다. 그 결과 31개 scored trajectory가 tool call 없이 reward 0이 됐다.

최소 runtime 호환성 수정은 native tool call이 없을 때만 legacy text parser를 적용하도록 조건을 추가한 것이다. Prompt, tool set, scorer, metadata 조건과 모델 routing은 변경하지 않았다.

- 수정 전 회귀 테스트: 1 failed
- 수정 후: 1 passed
- 관련 runtime/wire/runner suite: 38 passed, 7 subtests passed
- 실제 benchmark-turn QA: native tool call 1개, action=`sql_execute`
- 새 source digest: `782d35661bf29b96dadd072ee2b40d80566089702b977722a4e1793222cc9825`

초기 31건은 최종 분석에서 전부 제외했고 fresh config-hashed roots에서 다시 실행했다.

35B Full은 `mimic_iv_star task 83`의 malformed tool-argument JSON으로 최초 31/32에서 종료됐다. 동일 config `--resume`로 복구했다. Resume가 incomplete 8-task job 전체를 다시 실행해 raw valid record 7개가 중복됐으므로, 최종 canonical cohort는 slot별 filename-timestamp 순서의 first valid record를 사용했다. 기존 7개를 유지하고 새 task 83만 채택했다.

## 비용과 시간

- OpenRouter baseline usage: $147.272021025
- Final usage: $167.450084895
- 실제 증가액: **$20.17806387**
- Guard: $28
- Guard 여유: **$7.82193613**
- Canonical saved cost: $14.79060487
- 최종 roots 전체 stored-attempt cost: $18.03869074
- 초기 무효 launch 중단 시점 증가액: $2.274955075
- Tavily: 538 → 538, **+0**

Stored cost는 LiteLLM이 checkpoint에 기록한 진단값이며 실제 OpenRouter key 차액을 청구액으로 사용한다.

| Stage | 시간 |
|---|---:|
| SQL 35B | 28.12분 |
| SQL 122B | 31.73분 |
| SQL 397B | 39.25분 |
| Full 35B, recovery 포함 | 20.77분 |
| Full 122B | 20.60분 |
| Full 397B | 26.71분 |

세 SQL config는 동시에 실행됐고 Full은 모델별 4-way wave를 순차 실행했다. Fresh relaunch 시작부터 최종 Full summary까지 약 1.88시간이었다.

## 보존과 검증

- 최종 roots 6개: 모두 complete
- Canonical coverage: **288/288**
- Missing/unexpected slots: 0/0
- 최종 summary의 checkpoint errors와 duplicate task IDs: 0
- Raw valid 295개 중 recovery duplicate 7개를 canonical selection에서 제외
- Reward-null: user_error 77 + other 2
- Agent timeout: 0
- AtlasCloud FP8 route와 no-fallback 정책: 모든 manifest에서 동일
- Canonical trajectory 중 native tool call이 없는 결과: 0
- Naming analyzer tests: **68 passed**
- Analyzer 11개 파일과 supplementary reviewer: 분석 전후 SHA-256 동일
- 최종 Qwen experiment process: 0

FAISS cache는 이전 검증 hash와 동일했다.

| Environment | Documents/vectors | Dimension | Hash 일치 |
|---|---:|---:|---:|
| MIMIC Original | 196,674 | 3,072 | yes |
| MIMIC Star | 196,674 | 3,072 | yes |
| eICU Original | 4,041 | 3,072 | yes |
| eICU Star | 4,041 | 3,072 | yes |

## Artifacts

- `preflight.json`
- `nativefix-preflight.json`
- `performance-analysis.json`
- `naming-analysis.json`
- `verification.json`

이 실험은 고정된 16-task pilot의 k=1 기술 통계다. p-value는 산출하지 않았으며, Full80 확장 여부를 판단하는 viability evidence로 사용한다.
