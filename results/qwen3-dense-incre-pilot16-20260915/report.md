# Qwen3 Dense IncreQA 16-task Pilot 결과

실행 상태: **완료 및 검증 통과**

분석 단위: MIMIC-IV 8문제와 eICU 8문제를 IncreQA 안에서 합산

실험 규모: Qwen3 dense 3개 모델 × 16 tasks × Original/Star × 3 arms × k=1 = **288 canonical slots**

## 결론

- 여섯 config가 모두 완료됐고 **288/288 canonical scored slots**를 확인했다.
- 전체 성공은 **78/288 (27.08%)**였다.
- Full Tools Available은 **61/96 (63.54%)**, SQL-only Available은 **17/96 (17.71%)**, SQL-only Unavailable은 **0/96**이었다.
- Full Tools는 Original에서 SQL Available보다 16건, Star에서 28건 더 성공했다.
- 모델별 전체 성공은 8B **21/96**, 14B **31/96**, 32B **26/96**이었다. 14B가 가장 높았으며 크기에 따른 단조 증가 패턴은 없었다.
- Star trajectory의 primary Original-only 이름 사용은 Full Tools에서 세 모델 모두 **0회**, SQL Available에서 **83회**, SQL Unavailable에서 **177회**였다.
- 32B SQL 조건에는 600초 Agent LLM timeout이 32건 발생했다. 이 결과들은 논문 설정에 따라 score 0으로 유지했으며, 32B의 SQL 성능과 naming 관찰 범위를 해석할 때 함께 봐야 한다.
- OpenRouter 실제 사용 증가액은 **$7.776360469**로 $14 guard보다 **$6.223639531** 낮았다.

## 실험 설정

### 모델

| 모델 | OpenRouter model ID |
| --- | --- |
| Qwen3 8B | `openrouter/qwen/qwen3-8b` |
| Qwen3 14B | `openrouter/qwen/qwen3-14b` |
| Qwen3 32B | `openrouter/qwen/qwen3-32b` |

세 모델 모두 Qwen3 dense 계열이다. Provider와 quantization은 별도로 고정하지 않고 OpenRouter 기본 라우팅을 사용했다.

### 공통 조건

- Agent temperature: 0
- Agent reasoning override: 없음
- User: OpenRouter Gemini 2.5 Flash-Lite, temperature 1, `nested-reflection`
- Validator: OpenRouter Gemini 2.5 Flash, n=1
- Embedding: OpenRouter `text-embedding-3-large`
- k=1, detailed feedback
- 최대 30 agent turns
- simulation retry 최대 10회
- task timeout 600초
- Metadata Available: `metadata_access=allowed` + benchmark schema guidance
- Metadata Unavailable: `metadata_access=blocked` + identifier-free schema guidance
- Source digest: `782d35661bf29b96dadd072ee2b40d80566089702b977722a4e1793222cc9825`

### Arms

1. Full Tools + Metadata Available
2. SQL-only + Metadata Available
3. SQL-only + Metadata Unavailable

Full Tools는 `table_search`, `column_search`, `sql_execute`, `value_substring_search`, `value_similarity_search`, `web_search`를 노출했다.

### Task IDs

- MIMIC-IV: `54, 66, 83, 84, 87, 92, 94, 112`
- eICU: `16, 46, 66, 71, 79, 100, 114, 131`

모든 모델·arm·schema에서 같은 16개 logical tasks를 사용했다.

## Canonical cohort

Full 8B와 Full 14B에서 SQLite 실행이 설정된 timeout 이후에도 `sqlite3_step` 안에 남는 현상이 발생했다. 해당 model run만 종료하고 동일 config와 result root에 `--resume`을 사용했다.

Resume가 미완료 job을 다시 실행하면서 scored record 25건이 중복 저장됐다.

- 8B Full duplicate: 1건
- 14B Full duplicate: 24건

최종 분석은 모델·arm·schema·database·task ID별로 checkpoint 파일명 timestamp가 가장 이른 scored record를 선택했다. 따라서 원래 유효 결과를 유지하고 resume에서 새로 채워진 missing slot만 추가했다.

| 항목 | 수 |
| --- | ---: |
| Raw attempts | 435 |
| User-error attempts | 122 |
| Raw scored records | 313 |
| Recovery duplicates 제외 | 25 |
| Canonical scored slots | 288 |
| Canonical 성공 | 78 |
| Canonical 실패 | 210 |
| Missing / unexpected slots | 0 / 0 |

## 성능

각 칸은 성공 / 16이다.

| 모델 | Full Original | Full Star | SQL Available Original | SQL Available Star | SQL Unavailable Original | SQL Unavailable Star |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 8B | 7/16 | 11/16 | 1/16 | 2/16 | 0/16 | 0/16 |
| 14B | 11/16 | 12/16 | 6/16 | 2/16 | 0/16 | 0/16 |
| 32B | 11/16 | 9/16 | 6/16 | 0/16 | 0/16 | 0/16 |
| 합계 | 29/48 | 32/48 | 13/48 | 4/48 | 0/48 | 0/48 |

### 모델별 합계

| 모델 | Full Available | SQL Available | SQL Unavailable | 전체 |
| --- | ---: | ---: | ---: | ---: |
| 8B | 18/32 | 3/32 | 0/32 | 21/96 |
| 14B | 23/32 | 8/32 | 0/32 | 31/96 |
| 32B | 20/32 | 6/32 | 0/32 | 26/96 |

14B가 세 arm 합계에서 가장 높았다. Full은 18 → 23 → 20, SQL Available은 3 → 8 → 6으로 두 조건 모두 14B에서 정점을 보였다.

## Motivation 1: Original/Star × Full/SQL

Metadata Available에서 Full Tools와 SQL-only를 비교했다.

| Schema | Full | SQL Available | 차이 |
| --- | ---: | ---: | ---: |
| Original | 29/48 (60.42%) | 13/48 (27.08%) | +16 |
| Star | 32/48 (66.67%) | 4/48 (8.33%) | +28 |

Paired 결과:

| Schema | 둘 다 성공 | Full-only | SQL-only | 둘 다 실패 |
| --- | ---: | ---: | ---: | ---: |
| Original | 11 | 18 | 2 | 17 |
| Star | 4 | 28 | 0 | 16 |

Full Tools의 이점은 Star에서 더 컸다. Original/Star 자체 비교에서는 Full이 Original 29/48 대 Star 32/48로 비슷했지만, SQL Available은 Original 13/48 대 Star 4/48이었다.

### Original/Star paired 결과

`Star rescue`는 Original 실패·Star 성공, `Star regression`은 Original 성공·Star 실패다.

| 모델 | Arm | 둘 다 성공 | Star rescue | Star regression | 둘 다 실패 |
| --- | --- | ---: | ---: | ---: | ---: |
| 8B | Full Available | 5 | 6 | 2 | 3 |
| 8B | SQL Available | 0 | 2 | 1 | 13 |
| 8B | SQL Unavailable | 0 | 0 | 0 | 16 |
| 14B | Full Available | 10 | 2 | 1 | 3 |
| 14B | SQL Available | 2 | 0 | 4 | 10 |
| 14B | SQL Unavailable | 0 | 0 | 0 | 16 |
| 32B | Full Available | 7 | 2 | 4 | 3 |
| 32B | SQL Available | 0 | 0 | 6 | 10 |
| 32B | SQL Unavailable | 0 | 0 | 0 | 16 |

## Motivation 2: SQL-only Metadata Availability

| 조건 | 성공 |
| --- | ---: |
| SQL Available | 17/96 (17.71%) |
| SQL Unavailable | 0/96 |

동일 태스크 paired 비교에서 Available-only 성공은 17건, Unavailable-only 성공은 0건이었다.

모델별 Available-only 수:

| 모델 | Original | Star |
| --- | ---: | ---: |
| 8B | 1 | 2 |
| 14B | 6 | 2 |
| 32B | 6 | 0 |

## Motivation 3: Qwen3 dense 크기 비교

Qwen3 8B·14B·32B의 전체 성공은 21 → 31 → 26이었다. 이번 pilot에서는 크기가 커질수록 모든 조건의 성공률이 단조롭게 증가하지 않았다.

- Full Available: 8B 18/32, 14B 23/32, 32B 20/32
- SQL Available: 8B 3/32, 14B 8/32, 32B 6/32
- SQL Unavailable: 세 모델 모두 0/32

32B SQL에는 32건의 Agent LLM timeout이 집중됐다. 따라서 14B 대 32B의 SQL 차이는 task-solving 결과뿐 아니라 현재 OpenRouter 기본 라우팅에서 관찰된 inference-time behavior도 포함한다. Full에서는 세 모델 모두 Agent LLM timeout이 없었다.

## Star trajectory의 schema 이름 사용

기존 deterministic `naming_audit`를 수정 없이 사용했다.

- Original에는 있고 Star에는 없는 이름과 Star에만 있는 이름을 테이블·컬럼별로 정확히 비교한다.
- SQL physical reference와 `column_search`, value-search의 명시적 table/column 인자를 포함한다.
- Alias, CTE, derived alias, 자연어, 임상 문자열 값과 `table_search` 입력은 제외한다.
- Parser failure와 unresolved lineage는 확정 이름 참조로 올리지 않는다.
- 성공과 실패 trajectory를 모두 포함한다.
- Empty timeout trajectory는 관찰된 0회가 아니라 **미관찰**로 구분한다.

| 모델 | Arm | Scored | 관찰 transcript | Original-only table | Original-only column | Original 합계 | Star-only 합계 | Original 영향 trajectory |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 8B | Full Available | 16 | 16 | 0 | 0 | 0 | 686 | 0 |
| 8B | SQL Available | 16 | 16 | 9 | 2 | 11 | 1,099 | 7 |
| 8B | SQL Unavailable | 16 | 16 | 28 | 3 | 31 | 175 | 10 |
| 14B | Full Available | 16 | 16 | 0 | 0 | 0 | 523 | 0 |
| 14B | SQL Available | 16 | 16 | 29 | 43 | 72 | 1,265 | 8 |
| 14B | SQL Unavailable | 16 | 16 | 22 | 47 | 69 | 390 | 10 |
| 32B | Full Available | 16 | 16 | 0 | 0 | 0 | 666 | 0 |
| 32B | SQL Available | 16 | 2 | 0 | 0 | 0 | 204 | 0 |
| 32B | SQL Unavailable | 16 | 10 | 13 | 64 | 77 | 95 | 7 |

전체 144개 canonical Star trajectory 중 124개 transcript를 관찰했다. 20개는 Agent LLM timeout으로 대화가 비어 있었다.

Primary totals:

- Tool calls: 1,981
- SQL calls: 1,781
- Primary table references: 2,946
- Primary column references: 9,039
- Original-only: table 101 + column 159 = **260 occurrences**
- Star-only: table 1,178 + column 3,925 = **5,103 occurrences**
- Parse failure calls: 1
- Unresolved calls: 19

Arm별 Original-only 합계:

| Arm | Original-only occurrences | 영향 trajectory |
| --- | ---: | ---: |
| Full Available | 0 | 0 |
| SQL Available | 83 | 15 |
| SQL Unavailable | 177 | 27 |

Full Tools에서는 관찰된 48개 Star transcript 모두에서 Original-only 이름이 0회였다. Schema search를 사용할 수 있을 때 세 모델 모두 Star 이름에 맞춰 SQL과 search arguments를 구성했다.

Supplementary metadata audit는 SQL catalog/PRAGMA에 직접 적힌 target을 primary와 별도로 검토했다. Original-only table target은 1회·1 trajectory였으며 primary 합계에는 더하지 않았다.

## Timeout 및 실행 복구

### Agent LLM timeout

| 모델·arm | 건수 |
| --- | ---: |
| 14B SQL Available | 1 |
| 32B SQL Available | 18 |
| 32B SQL Unavailable | 14 |
| 합계 | 33 |

33건은 모두 빈 message trajectory로 score 0이 저장됐다. Log의 `Agent LLM cumulative time exceeded 600s` 이벤트와 정확히 일치한다. Non-timeout canonical trajectory에서 native tool-call parser 손실은 발견되지 않았다.

### SQLite execution stall

8B Full과 14B Full의 eICU worker가 `sqlite3_step`에서 설정 timeout 이후에도 종료되지 않는 현상이 각각 한 번 발생했다.

- Prompt, model, tools, scoring, timeout 설정은 변경하지 않았다.
- 해당 model run만 종료했다.
- 기존 결과를 보존했다.
- 동일 config와 result root에 `--resume`를 사용했다.
- 최종 canonical cohort에서 원래 scored record를 우선하고 recovery duplicate를 제외했다.

## Tool 사용

Canonical 288 trajectory에 저장된 tool call:

| Tool | Calls |
| --- | ---: |
| `sql_execute` | 3,421 |
| `column_search` | 189 |
| `table_search` | 71 |
| `value_substring_search` | 72 |
| `value_similarity_search` | 48 |
| `web_search` | 0 |

## 비용과 시간

- OpenRouter baseline usage: $167.450339730
- OpenRouter final usage: $175.226700199
- 실제 증가액: **$7.776360469**
- Guard: $14
- Guard 여유: **$6.223639531**
- Canonical saved cost 진단값: $7.744678620
- 모든 saved attempts의 LiteLLM 추정 합계: $10.858860830
- 실행 시간: 약 **215.15분**

최종 OpenRouter usage는 2026-09-15 12:08:14 UTC와 12:11:43 UTC에 동일했다. 실제 비용은 account usage delta를 사용한다. Saved cost는 provider 라우팅별 실제 청구액과 다를 수 있고 resume duplicate를 포함하므로 진단값으로만 유지한다.

## 보존과 검증

- Final roots: 6
- Complete summaries: 6
- Summary completed slots: 288
- Missing / unexpected slots: 0 / 0
- Summary errors와 duplicate task IDs: 0
- 실행 종료 후 Qwen experiment process: 0
- Naming analyzer tests: **68 passed**
- Analyzer 11개 파일: 분석 전후 SHA-256 동일
- Naming core/supplementary unexpected exception: 0 / 0
- Task instruction·gold-answer pairing mismatch: 0
- 기존 FAISS index 네 개: 이전 검증 SHA-256와 모두 일치

## 해석 범위

이 결과는 고정된 16-task, k=1 pilot의 기술 통계다. p-value를 계산하지 않았고 task별 반복 신뢰도나 전체 IncreQA 모집단 효과를 추정하지 않는다.

Provider와 quantization은 고정하지 않았으므로 모델 크기와 serving behavior를 분리한 인과적 size-only 결과로 해석하지 않는다. 다만 동일 Qwen3 dense 계열에서 같은 태스크·schema·arm을 paired 비교했다는 점에서 다음 확대실험의 정보가치와 실행 가능성을 판단하는 pilot으로 사용한다.

## Artifacts

- `baseline.json`
- `performance-analysis.json`
- `naming-analysis.json`
- `verification.json`
- `report.md`
