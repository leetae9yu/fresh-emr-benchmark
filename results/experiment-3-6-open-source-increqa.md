# Experiments 3–6: 오픈소스 모델 IncreQA (2026-09-11 ~ 2026-09-15)

네 실험 모두 **IncreQA만** 실행했다(AdaptQA 없음). MIMIC-IV와 eICU 태스크는
IncreQA 안에서 합산해 보고하고, 데이터베이스는 태스크 식별용으로만 유지한다.
모든 조건은 Original/Star × Full Tools Available / sql execute only Available /
sql execute only Nonavailable, detailed feedback, **k=1**이다.

SR-1은 각 태스크·스키마에서 채택한 한 평가 결과(k=1)의 성공률이다.
사용자 오류로 거부된 시도는 제외하고 유효 실패와 점수화된 시간 초과는 0점으로 포함한다.
저장된 reward를 사용했으며 다시 채점하지 않았다.

[Original names in Star] 표는 **Star 스키마 대화만** 대상으로 한다.
Original에만 존재하는 테이블·컬럼의 SQL 내 물리 참조와 검색 도구의 명시적
인자를 세고, 반복 참조는 반복 집계한다. 분모는 Original 전용 + Star 전용 +
공통 + 미확인 이름의 물리 참조 합계다. 별칭·CTE·파생 이름·문자열·순수
메타데이터 탐색 대상은 주 참조 집계와 구분한다.

---

## Experiment 3: Ministral 3B/8B/14B (subset80)

80개 태스크(MIMIC-IV 40 + eICU 40) × 3 모델 × 2 스키마 × 3 조건 = **1,440 slots**
(기존 호환 SQL 파일럿 192개 재사용 + 신규 1,248개). 전부 완료, 341 성공.

### [SR-1]

#### IncreQA

| Model | DB | Tools | metadata | SR-1 |
| --- | --- | --- | --- | ---: |
| Ministral 3B | Original | Full Tools | Available | **31.25% (25/80)** |
| Ministral 3B | Star | Full Tools | Available | **27.50% (22/80)** |
| Ministral 3B | Original | sql execute only | Available | **8.75% (7/80)** |
| Ministral 3B | Star | sql execute only | Available | **15.00% (12/80)** |
| Ministral 3B | Original | sql execute only | Nonavailable | **0.00% (0/80)** |
| Ministral 3B | Star | sql execute only | Nonavailable | **0.00% (0/80)** |
| Ministral 8B | Original | Full Tools | Available | **40.00% (32/80)** |
| Ministral 8B | Star | Full Tools | Available | **53.75% (43/80)** |
| Ministral 8B | Original | sql execute only | Available | **26.25% (21/80)** |
| Ministral 8B | Star | sql execute only | Available | **33.75% (27/80)** |
| Ministral 8B | Original | sql execute only | Nonavailable | **0.00% (0/80)** |
| Ministral 8B | Star | sql execute only | Nonavailable | **0.00% (0/80)** |
| Ministral 14B | Original | Full Tools | Available | **52.50% (42/80)** |
| Ministral 14B | Star | Full Tools | Available | **55.00% (44/80)** |
| Ministral 14B | Original | sql execute only | Available | **40.00% (32/80)** |
| Ministral 14B | Star | sql execute only | Available | **42.50% (34/80)** |
| Ministral 14B | Original | sql execute only | Nonavailable | **0.00% (0/80)** |
| Ministral 14B | Star | sql execute only | Nonavailable | **0.00% (0/80)** |

→ 모델 크기가 커질수록 모든 조건에서 성능이 단조 증가한다(3B < 8B < 14B).

→ Full Tools가 SQL-only Available보다 모든 모델·스키마 셀에서 높다.

→ SQL-only Nonavailable은 세 모델 모두 **0/160**이다. Star뿐 아니라 Original에서도 0이다.

→ Original→Star 방향이 모델마다 다르다: 3B는 Full에서 소폭 하락, 8B·14B는 Star가 더 높다.

### [Original names in Star]

#### Full Tools

| Model | metadata | tool call 횟수 | Original 테이블 등장 | Original 컬럼 등장 | Original 이름을 사용한 대화 |
| --- | --- | ---: | ---: | ---: | ---: |
| Ministral 3B | Available | **1,191** | **0/2,044 (0.00%)** | **0/8,252 (0.00%)** | **0/80 (0.00%)** |
| Ministral 8B | Available | **960** | **1/1,269 (0.08%)** | **4/4,722 (0.08%)** | **3/80 (3.75%)** |
| Ministral 14B | Available | **757** | **2/1,103 (0.18%)** | **7/3,858 (0.18%)** | **6/80 (7.50%)** |

#### Tools in full tool condition

| 도구 | 3B | 8B | 14B |
| --- | ---: | ---: | ---: |
| sql_execute | 798 | 382 | 334 |
| table_search | 73 | 83 | 64 |
| column_search | 141 | 164 | 170 |
| value_substring_search | 139 | 278 | 173 |
| value_similarity_search | 37 | 52 | 15 |
| web_search | 2 | 1 | 1 |
| explanation | 1 | 0 | 0 |
| total | 1,191 | 960 | 757 |

#### SQL-only

| Model | metadata | SQL 실행 횟수 | Original 테이블 등장 | Original 컬럼 등장 | Original 이름을 사용한 대화 |
| --- | --- | ---: | ---: | ---: | ---: |
| Ministral 3B | Available | **1,514** | **65/2,135 (3.04%)** | **19/9,645 (0.20%)** | **41/80 (51.25%)** |
| Ministral 3B | Nonavailable | **1,605** | **158/1,438 (10.99%)** | **147/5,519 (2.66%)** | **36/80 (45.00%)** |
| Ministral 8B | Available | **1,063** | **114/1,982 (5.75%)** | **123/9,759 (1.26%)** | **49/80 (61.25%)** |
| Ministral 8B | Nonavailable | **1,660** | **98/1,293 (7.58%)** | **134/4,544 (2.95%)** | **49/80 (61.25%)** |
| Ministral 14B | Available | **999** | **145/1,790 (8.10%)** | **215/8,155 (2.64%)** | **61/80 (76.25%)** |
| Ministral 14B | Nonavailable | **1,613** | **206/1,927 (10.69%)** | **261/7,454 (3.50%)** | **55/80 (68.75%)** |

→ Full Tools에서는 Original 이름 사용이 거의 0이다(세 모델 합산 대화 9/240).

→ SQL-only에서는 모델이 클수록 Original 이름을 사용한 대화 비율이 높다
(Available 기준 51.25% → 61.25% → 76.25%). 성능이 높다고 Original 이름을 덜 쓰는 것은 아니다.

→ Nonavailable에서 SQL 호출 수가 늘고 Original 테이블 참조 비율이 상승한다.

→ 관측 불가한 빈 대화(점수 0 timeout 등)가 일부 있다: 3B 7개, 8B 2개, 14B 2개.
이 대화들은 이름 집계에서 관측되지 않았다.

실행 비용: OpenRouter 관측 차액 **$13.88** ($18 guard 이내). 실행 중 메모리 압박으로
Full Tools를 모델별 순차 실행으로 전환하고 FAISS 캐시를 별도 초기화했으나,
실험 요인(모델·스키마·도구·메타데이터)은 변경하지 않았다.

---

## Experiment 4: GPT-OSS 20B/120B (subset80)

80개 태스크 × 2 모델 × 2 스키마 × 3 조건 = **960 slots**. 전부 완료, 438 성공.
CoreWeave FP4 라우팅, 120B는 mandatory reasoning 모델이다.

### [SR-1]

#### IncreQA

| Model | DB | Tools | metadata | SR-1 |
| --- | --- | --- | --- | ---: |
| GPT-OSS 20B | Original | Full Tools | Available | **65.00% (52/80)** |
| GPT-OSS 20B | Star | Full Tools | Available | **75.00% (60/80)** |
| GPT-OSS 20B | Original | sql execute only | Available | **58.75% (47/80)** |
| GPT-OSS 20B | Star | sql execute only | Available | **72.50% (58/80)** |
| GPT-OSS 20B | Original | sql execute only | Nonavailable | **1.25% (1/80)** |
| GPT-OSS 20B | Star | sql execute only | Nonavailable | **0.00% (0/80)** |
| GPT-OSS 120B | Original | Full Tools | Available | **72.50% (58/80)** |
| GPT-OSS 120B | Star | Full Tools | Available | **65.00% (52/80)** |
| GPT-OSS 120B | Original | sql execute only | Available | **66.25% (53/80)** |
| GPT-OSS 120B | Star | sql execute only | Available | **65.00% (52/80)** |
| GPT-OSS 120B | Original | sql execute only | Nonavailable | **6.25% (5/80)** |
| GPT-OSS 120B | Star | sql execute only | Nonavailable | **0.00% (0/80)** |

→ 두 모델의 합산 성능은 거의 같다(Full 112/160 vs 110/160, SQL Available 105/160 vs 105/160).
크기 증가에 따른 성능 향상이 없다.

→ 다만 스키마 방향은 반대다: 20B는 Star가 높고, 120B는 Original이 높거나 같다.

→ Full Tools는 SQL-only Available보다 Original에서 두 모델 모두 5건 높았고,
Star에서는 20B가 2건 높고 120B는 동률이다. 도구 효과가 크지 않다.

→ SQL-only Nonavailable은 Star에서 0/160, Original에서 6/160이다.

### [Original names in Star]

#### Full Tools

| Model | metadata | tool call 횟수 | Original 테이블 등장 | Original 컬럼 등장 | Original 이름을 사용한 대화 |
| --- | --- | ---: | ---: | ---: | ---: |
| GPT-OSS 20B | Available | **694** | **0/895 (0.00%)** | **1/2,634 (0.04%)** | **1/80 (1.25%)** |
| GPT-OSS 120B | Available | **596** | **0/714 (0.00%)** | **0/2,139 (0.00%)** | **0/80 (0.00%)** |

#### Tools in full tool condition

| 도구 | 20B | 120B |
| --- | ---: | ---: |
| sql_execute | 306 | 258 |
| table_search | 77 | 77 |
| column_search | 159 | 146 |
| value_substring_search | 151 | 101 |
| value_similarity_search | 1 | 14 |
| total | 694 | 596 |

#### SQL-only

| Model | metadata | SQL 실행 횟수 | Original 테이블 등장 | Original 컬럼 등장 | Original 이름을 사용한 대화 |
| --- | --- | ---: | ---: | ---: | ---: |
| GPT-OSS 20B | Available | **762** | **24/796 (3.02%)** | **1/3,016 (0.03%)** | **22/80 (27.50%)** |
| GPT-OSS 20B | Nonavailable | **1,385** | **142/1,135 (12.51%)** | **52/1,145 (4.54%)** | **58/80 (72.50%)** |
| GPT-OSS 120B | Available | **507** | **12/473 (2.54%)** | **1/1,934 (0.05%)** | **10/80 (12.50%)** |
| GPT-OSS 120B | Nonavailable | **1,860** | **151/1,566 (9.64%)** | **76/759 (10.01%)** | **64/80 (80.00%)** |

→ Full Tools는 Original 이름 사용을 사실상 제거한다(두 모델 합산 대화 1/160).

→ SQL-only에서 Nonavailable로 바뀌면 SQL 호출 수와 Original 이름 사용이 모두 크게 늘어난다.
특히 120B는 Nonavailable에서 SQL 호출이 507 → 1,860으로 증가한다.

→ 120B는 mandatory reasoning 모델이라 SQL-only에서도 호출 패턴이 다르다.
Available에서 Original 이름 사용 대화가 20B(27.50%)보다 낮다(12.50%).

실행 비용: OpenRouter 관측 차액 **$7.51** ($18 guard 이내).

---

## Experiment 5: Qwen3.5 MoE 35B-A3B/122B-A10B/397B-A17B (pilot16)

16개 태스크(MIMIC-IV 8 + eICU 8) × 3 모델 × 2 스키마 × 3 조건 = **288 slots**.
전부 완료, 162 성공. MoE 모델이며 표기는 전체 파라미터-활성 파라미터다.

### [SR-1]

#### IncreQA

| Model | DB | Tools | metadata | SR-1 |
| --- | --- | --- | --- | ---: |
| Qwen3.5 35B-A3B | Original | Full Tools | Available | **81.25% (13/16)** |
| Qwen3.5 35B-A3B | Star | Full Tools | Available | **81.25% (13/16)** |
| Qwen3.5 35B-A3B | Original | sql execute only | Available | **81.25% (13/16)** |
| Qwen3.5 35B-A3B | Star | sql execute only | Available | **62.50% (10/16)** |
| Qwen3.5 35B-A3B | Original | sql execute only | Nonavailable | **0.00% (0/16)** |
| Qwen3.5 35B-A3B | Star | sql execute only | Nonavailable | **0.00% (0/16)** |
| Qwen3.5 122B-A10B | Original | Full Tools | Available | **75.00% (12/16)** |
| Qwen3.5 122B-A10B | Star | Full Tools | Available | **87.50% (14/16)** |
| Qwen3.5 122B-A10B | Original | sql execute only | Available | **93.75% (15/16)** |
| Qwen3.5 122B-A10B | Star | sql execute only | Available | **87.50% (14/16)** |
| Qwen3.5 122B-A10B | Original | sql execute only | Nonavailable | **6.25% (1/16)** |
| Qwen3.5 122B-A10B | Star | sql execute only | Nonavailable | **0.00% (0/16)** |
| Qwen3.5 397B-A17B | Original | Full Tools | Available | **93.75% (15/16)** |
| Qwen3.5 397B-A17B | Star | Full Tools | Available | **81.25% (13/16)** |
| Qwen3.5 397B-A17B | Original | sql execute only | Available | **75.00% (12/16)** |
| Qwen3.5 397B-A17B | Star | sql execute only | Available | **81.25% (13/16)** |
| Qwen3.5 397B-A17B | Original | sql execute only | Nonavailable | **25.00% (4/16)** |
| Qwen3.5 397B-A17B | Star | sql execute only | Nonavailable | **0.00% (0/16)** |

→ Full Tools와 SQL-only Available의 전체 차이는 3건(80/96 vs 77/96)뿐이다.
도구 효과는 모델·스키마에 따라 달랐고, 122B에서는 SQL-only가 Full보다 높다.

→ SQL-only Nonavailable의 성공 5건은 전부 Original에서 나왔고, Star Nonavailable은 0/48이다.

→ 크기에 따른 단조 증가는 없다(Full 총성공 26 → 26 → 28, SQL Available 23 → 29 → 25).

### [Original names in Star]

#### Full Tools

| Model | metadata | tool call 횟수 | Original 테이블 등장 | Original 컬럼 등장 | Original 이름을 사용한 대화 |
| --- | --- | ---: | ---: | ---: | ---: |
| Qwen3.5 35B-A3B | Available | **183** | **0/232 (0.00%)** | **0/1,155 (0.00%)** | **0/16 (0.00%)** |
| Qwen3.5 122B-A10B | Available | **203** | **0/281 (0.00%)** | **2/1,081 (0.19%)** | **1/16 (6.25%)** |
| Qwen3.5 397B-A17B | Available | **189** | **0/271 (0.00%)** | **0/1,283 (0.00%)** | **0/16 (0.00%)** |

#### SQL-only

| Model | metadata | SQL 실행 횟수 | Original 테이블 등장 | Original 컬럼 등장 | Original 이름을 사용한 대화 |
| --- | --- | ---: | ---: | ---: | ---: |
| Qwen3.5 35B-A3B | Available | **214** | **1/242 (0.41%)** | **6/1,162 (0.52%)** | **4/16 (25.00%)** |
| Qwen3.5 35B-A3B | Nonavailable | **468** | **42/469 (8.96%)** | **70/433 (16.17%)** | **16/16 (100.00%)** |
| Qwen3.5 122B-A10B | Available | **198** | **1/206 (0.49%)** | **1/984 (0.10%)** | **2/16 (12.50%)** |
| Qwen3.5 122B-A10B | Nonavailable | **470** | **44/449 (9.80%)** | **9/338 (2.66%)** | **13/16 (81.25%)** |
| Qwen3.5 397B-A17B | Available | **204** | **6/226 (2.65%)** | **17/1,195 (1.42%)** | **7/16 (43.75%)** |
| Qwen3.5 397B-A17B | Nonavailable | **468** | **70/439 (15.95%)** | **44/204 (21.57%)** | **15/16 (93.75%)** |

→ Full Tools의 Original 이름 사용은 Star trajectory 전체에서 2회뿐이다.

→ SQL-only에서 Nonavailable이 되면 SQL 호출이 약 2배로 늘고 Original 이름 사용이 폭증한다.
세 모델 모두 Nonavailable 대화의 81~100%에서 Original 이름이 등장한다.

→ 397B는 Nonavailable에서도 Original 스키마를 4/16 성공시켰지만,
Star에서는 Original 이름 탐색에 갇혀 0/16이다.

실행 비용: OpenRouter 관측 차액 **$20.18** ($28 guard 이내).

---

## Experiment 6: Qwen3 dense 8B/14B/32B (pilot16)

16개 태스크 × 3 모델 × 2 스키마 × 3 조건 = **288 slots**. 전부 완료, 78 성공.
provider/quantization을 고정하지 않고 OpenRouter 기본 라우팅을 사용했다.

### [SR-1]

#### IncreQA

| Model | DB | Tools | metadata | SR-1 |
| --- | --- | --- | --- | ---: |
| Qwen3 8B | Original | Full Tools | Available | **43.75% (7/16)** |
| Qwen3 8B | Star | Full Tools | Available | **68.75% (11/16)** |
| Qwen3 8B | Original | sql execute only | Available | **6.25% (1/16)** |
| Qwen3 8B | Star | sql execute only | Available | **12.50% (2/16)** |
| Qwen3 8B | Original | sql execute only | Nonavailable | **0.00% (0/16)** |
| Qwen3 8B | Star | sql execute only | Nonavailable | **0.00% (0/16)** |
| Qwen3 14B | Original | Full Tools | Available | **68.75% (11/16)** |
| Qwen3 14B | Star | Full Tools | Available | **75.00% (12/16)** |
| Qwen3 14B | Original | sql execute only | Available | **37.50% (6/16)** |
| Qwen3 14B | Star | sql execute only | Available | **12.50% (2/16)** |
| Qwen3 14B | Original | sql execute only | Nonavailable | **0.00% (0/16)** |
| Qwen3 14B | Star | sql execute only | Nonavailable | **0.00% (0/16)** |
| Qwen3 32B | Original | Full Tools | Available | **68.75% (11/16)** |
| Qwen3 32B | Star | Full Tools | Available | **56.25% (9/16)** |
| Qwen3 32B | Original | sql execute only | Available | **37.50% (6/16)** |
| Qwen3 32B | Star | sql execute only | Available | **0.00% (0/16)** |
| Qwen3 32B | Original | sql execute only | Nonavailable | **0.00% (0/16)** |
| Qwen3 32B | Star | sql execute only | Nonavailable | **0.00% (0/16)** |

→ Full Tools가 SQL-only Available보다 모든 모델·스키마에서 높다.
전체 61/96 vs 17/96으로 도구 효과가 이 패밀리에서 가장 크다.

→ SQL-only Nonavailable은 0/96이다.

→ 모델별 전체 성공은 8B 21/96, 14B 31/96, 32B 26/96으로 14B가 가장 높고
단조 증가가 없다.

→ SQL-only Available에서 14B와 32B는 Star가 Original보다 낮다(14B 2<6,
32B 0<6). 8B만 Star가 소폭 높다(2>1). 32B는 Star SQL Available이 0/16이다.

→ **32B SQL 조건에는 600초 Agent LLM timeout이 32건** 있었다(Available 18,
Unavailable 14). 전부 빈 응답으로 끝나 score 0이다. 32B의 SQL 성능과
아래 naming 관찰 범위를 해석할 때 함께 봐야 한다.

### [Original names in Star]

#### Full Tools

| Model | metadata | tool call 횟수 | Original 테이블 등장 | Original 컬럼 등장 | Original 이름을 사용한 대화 |
| --- | --- | ---: | ---: | ---: | ---: |
| Qwen3 8B | Available | **111** | **0/166 (0.00%)** | **0/544 (0.00%)** | **0/16 (0.00%)** |
| Qwen3 14B | Available | **142** | **0/182 (0.00%)** | **0/371 (0.00%)** | **0/16 (0.00%)** |
| Qwen3 32B | Available | **123** | **0/177 (0.00%)** | **0/521 (0.00%)** | **0/16 (0.00%)** |

#### SQL-only

| Model | metadata | SQL 실행 횟수 | Original 테이블 등장 | Original 컬럼 등장 | Original 이름을 사용한 대화 |
| --- | --- | ---: | ---: | ---: | ---: |
| Qwen3 8B | Available | **294** | **9/461 (1.95%)** | **2/1,291 (0.15%)** | **7/16 (43.75%)** |
| Qwen3 8B | Nonavailable | **267** | **28/330 (8.48%)** | **3/1,040 (0.29%)** | **10/16 (62.50%)** |
| Qwen3 14B | Available | **364** | **29/585 (4.96%)** | **43/2,438 (1.76%)** | **8/16 (50.00%)** |
| Qwen3 14B | Nonavailable | **437** | **22/698 (3.15%)** | **47/1,803 (2.61%)** | **10/16 (62.50%)** |
| Qwen3 32B | Available | **41** | **0/79 (0.00%)** | **0/258 (0.00%)** | **0/16 (0.00%)** |
| Qwen3 32B | Nonavailable | **202** | **13/268 (4.85%)** | **64/773 (8.28%)** | **7/16 (43.75%)** |

→ Full Tools에서는 세 모델 모두 Original 이름 사용이 0이다.

→ 32B SQL의 관측 대화는 Available 2/16, Nonavailable 10/16뿐이다
(나머지는 빈 timeout 대화). 32B 행의 낮은 Original 사용률은 관측 부족의
반영일 수 있어 다른 모델과 직접 비교하지 않는다.

→ 관측된 범위에서는 Nonavailable에서 Original 이름 사용 대화 비율이
Available보다 높다(8B 62.50% vs 43.75%, 14B 62.50% vs 50.00%).

실행 비용: OpenRouter 관측 차액 **$7.78** ($14 guard 이내).

---

## 표본과 실행 한계

- 네 실험 모두 **선택된 태스크의 k=1 기술적(descriptive) 결과**다.
  p-value나 전체 벤치마크 일반화 주장을 하지 않는다.
- subset80(Experiment 3·4)은 80태스크, pilot16(Experiment 5·6)은 16태스크다.
  pilot16의 셀당 분모 16은 subset80의 80보다 훨씬 작다.
- Ministral은 Mistral 공급자로 고정, GPT-OSS는 CoreWeave FP4, Qwen3 dense는
  OpenRouter 기본 라우팅을 사용했다. 정밀도·양자화는 패밀리마다 다르므로
  패밀리 간 절대 성능 비교는 하지 않는다.
- Full Tools Nonavailable 조건은 실행하지 않았다.
- 사용자 시뮬레이터는 Flash-Lite 계열이며, 동시성·타임아웃 같은 운영 설정은
  실험 요인이 아니라 실행 조건이다.

## 근거

- `results/ministral-incre-subset80-20260911/` — report.md, performance-analysis.json, naming-analysis.json, verification.json
- `results/gpt-oss-incre-subset80-20260913/` — report.md, performance-analysis.json, naming-analysis.json, verification.json
- `results/qwen35-moe-incre-pilot16-20260914/` — report.md, performance-analysis.json, naming-analysis.json, verification.json
- `results/qwen3-dense-incre-pilot16-20260915/` — report.md, performance-analysis.json, naming-analysis.json, verification.json
- 통합 회고: `results/motivation-retrospective-20260914/report.md`

위 자료의 확인된 점수와 집계를 발표용 형식으로 정리했으며 새 모델 호출은 하지 않았다.
