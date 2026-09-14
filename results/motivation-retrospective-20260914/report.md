# EHR-ChatQA Motivation 실험 종합 보고서

기준일: 2026-09-14

분석 범위: 지금까지 완료한 Motivation 관련 실험을 재실행하거나 재채점하지 않고, 검증된 report·JSON·checkpoint 근거를 종합했다.

## 한 줄 결론

**현재 실험들은 사용자의 Motivation 1–3과 약 9/10 수준으로 잘 align된다.**

가장 강한 결과는 Metadata Available/Unavailable 차이이고, 다음으로 강한 결과는 Full Tools가 Star에서 Original 이름 의존을 거의 제거한다는 점이다. 반면 “Star는 항상 어렵다” 또는 “모델이 클수록 Original prior가 강하다”는 단일 방향 가설은 지지되지 않는다.

이는 motivation과의 불일치가 아니다. Motivation 1–3은 비교 질문이며, 특정 방향을 반드시 확인해야 하는 가설이 아니다.

## Authoritative Motivation 정의

### Motivation 1

Metadata Available에서:

- Original 대 Star
- Full Tools 대 SQL-only
- 성능
- Star trajectory에서 Original-only 대 Star-only table/column identifier 사용

을 함께 비교한다.

### Motivation 2

Motivation 1의 SQL-only 조건에서 Metadata Available 대 Unavailable을 비교한다.

여기서 Metadata는 하나의 결합 treatment다.

```text
Available   = metadata allowed + benchmark schema guidance
Unavailable = metadata blocked + identifier-free guidance
```

### Motivation 3

Motivation 1의 구성을 파라미터 수가 알려진 여러 모델 크기에 반복한다. 크기가 커질수록 반드시 특정 방향으로 변해야 한다고 가정하지 않는다.

## 완료 실험 지도

### Primary complete cohorts

| Family | Models | Tasks | k | Canonical slots | M1 | M2 | M3 |
|---|---|---:|---:|---:|---:|---:|---:|
| Ministral | 3B, 8B, 14B | 80 | 1 | 1,440 | 완료 | 완료 | 3 sizes |
| GPT-OSS | 20B, 120B | 동일 80 | 1 | 960 | 완료 | 완료 | 2 sizes |
| Qwen3.5 MoE | 35B-A3B, 122B-A10B, 397B-A17B | 16 | 1 | 288 | 완료 | 완료 | 3 sizes |
| **합계** | **8 model sizes** |  |  | **2,688** |  |  |  |

Ministral과 GPT-OSS는 동일한 80-task subset을 사용했다. Qwen의 16 tasks는 이 subset에 포함된 초기 pilot tasks지만, Qwen과 80-task family의 성공률을 그대로 순위화하지 않는다.

### Main-backbone 및 historical supporting cohorts

| Cohort | 직접 제공하는 근거 | 제한 |
|---|---|---|
| Gemini 2.5 Flash-Lite official-user Full IncreQA 572/572 | M1 Full 성능·naming | SQL control은 다른 실행 이력 |
| Gemini 3.8 Flash official-user SQL A/B 128/128 | M2와 M1 SQL 부분 | Full Tools 없음 |
| Flash-Lite legacy SQL-only IncreQA 1,144/1,144 | Historical M1 SQL·M2 | 혼합 first-valid 선택과 runtime parity 한계 |
| Gemini 3.8 initial Incre/Adapt pilot 48/48 | 작은 M2 replication | 이후 Incre A/B가 대체 |
| Gemma 4 26B-A4B pilot 24/24 | 작은 SQL-only M2 support | 단일 모델·6 tasks |

### Headline에서 제외한 것

- subset80에 재사용된 이전 Ministral pilot을 별도 replication으로 중복 계산하지 않는다.
- 공식-user rerun으로 대체된 이전 Gemini 3.8 expanded A/B를 추가 replication으로 세지 않는다.
- 혼합 simulator/source의 이전 Flash-Lite Full 결과는 최신 official-user 결과와 합산하지 않는다.
- Gemini CDEF 43/256은 중단됐으므로 완료된 Full control이 아니다.
- SQL_VALUE/value-similarity 실험은 six-tool Full Tools가 아니므로 현재 M1 arm으로 대체하지 않는다.
- Reasoning variants, provider smokes, canceled partials는 compatibility evidence이지 headline performance cohort가 아니다.

## Primary 전체 성능

| Family | Full Available | SQL Available | SQL Unavailable | 전체 |
|---|---:|---:|---:|---:|
| Ministral | 208/480 (43.33%) | 133/480 (27.71%) | 0/480 | 341/1,440 |
| GPT-OSS | 222/320 (69.38%) | 210/320 (65.63%) | 6/320 (1.88%) | 438/960 |
| Qwen pilot | 80/96 (83.33%) | 77/96 (80.21%) | 5/96 (5.21%) | 162/288 |
| **기술적 합계** | **510/896 (56.92%)** | **420/896 (46.88%)** | **11/896 (1.23%)** | **941/2,688** |

마지막 합계는 서로 다른 모델·task 범위를 합친 기술적 총계이며 family 순위나 모집단 성능 추정치가 아니다.

## Motivation 1 평가

### 1. 성능 측면

Full Tools와 SQL Available의 16개 model×schema 셀:

- Full이 높음: **11**
- 동률: **4**
- Full이 낮음: **1**

Family별 차이:

- Ministral: Full 208/480 대 SQL 133/480, **+75**
- GPT-OSS: 222/320 대 210/320, **+12**
- Qwen: 80/96 대 77/96, **+3**

Ministral에서는 모든 셀에서 Full이 높았다. GPT-OSS에서는 효과가 작고 120B Star가 동률이었다. Qwen에서는 122B Original이 Full 12/16 대 SQL 15/16으로 역전됐다.

따라서 **Full Tools의 평균적 도움은 관찰되지만 모든 모델·스키마에 대한 보편 법칙은 아니다.**

### 2. Original 대 Star

Star가 항상 어렵다는 패턴도 없다.

- Ministral은 8B·14B의 Full/SQL Available에서 Star가 높았다.
- GPT-OSS 20B는 Star가 높고 120B는 Original이 높거나 같았다.
- Qwen은 모델·arm에 따라 동률 또는 방향이 바뀌었다.
- Flash-Lite official-user Full은 Original 136/286, Star 147/286으로 Star가 높았다.

즉 schema renaming 자체의 효과는 model×tool 상호작용으로 보는 것이 정확하다.

### 3. Naming 측면

Primary 세 family의 Star trajectory에서:

| Arm | Original-only occurrences | Original 영향 대화 | Star-only occurrences |
|---|---:|---:|---:|
| Full Available | **17** | **11/439 (2.51%)** | 30,190 |
| SQL Available | **751** | **196/439 (44.65%)** | 33,867 |
| SQL Unavailable | **1,704** | **306/441 (69.39%)** | 3,975 |

Full 대 SQL Available의 Original-only 이름:

- Ministral: 14 대 681
- GPT-OSS: 1 대 38
- Qwen: 2 대 32

8개 모델 중 7개에서 Full이 더 낮고 Qwen 122B만 2 대 2로 동률이었다.

**Motivation 1에서 가장 일관된 결과는 성공률 상승보다 naming adaptation이다.** Full Tools가 있으면 모델은 Star 이름을 찾아 사용하고 Original schema 이름 재사용을 거의 제거한다.

### Motivation 1 verdict

**A- / 잘 align됨.**

비교 설계와 identifier 측정은 완성됐다. Full의 성능 효과는 조건부지만, schema tools가 Star naming adaptation을 돕는 행동 근거는 여러 family에서 반복됐다.

## Motivation 2 평가

Primary SQL-only 결과:

- Available: **420/896**
- Unavailable: **11/896**
- 16/16 model×schema cells에서 Available이 높음
- Unavailable 성공 11건은 전부 Original
- Star Unavailable: **0/448**

Naming도 같은 방향이다.

- Available Original-only: 751회, 영향 대화 196/439
- Unavailable Original-only: 1,704회, 영향 대화 306/441

Gemini 3.8 Flash의 main-backbone A/B에서도:

| Condition | Original | Star |
|---|---:|---:|
| Available | 26/32 | 25/32 |
| Unavailable | 23/32 | **0/32** |

Star의 Original-name 영향 대화는 Available 1/32에서 Unavailable 32/32로 바뀌었다.

Flash-Lite의 historical SQL-only full-task 결과도 Available 97/572 대 Unavailable 6/572였다.

이 결과는 “catalog access만의 효과”가 아니라 사용자가 정의한 결합 Metadata treatment의 효과다. 즉 메타데이터 접근과 identifier-bearing guidance가 함께 제공되거나 함께 차단된다.

### Motivation 2 verdict

**A / 현재 가장 강한 motivation evidence.**

모델·provider·family가 달라도 Star Unavailable collapse가 반복되고, 동시에 Original-name 재사용이 증가한다.

## Motivation 3 평가

### Ministral

| Arm | 3B | 8B | 14B |
|---|---:|---:|---:|
| Full Available | 47/160 | 75/160 | 86/160 |
| SQL Available | 19/160 | 48/160 | 66/160 |
| SQL Available Original-only names | 84 | 237 | 360 |

성능과 SQL Available의 Original-name 사용이 함께 단조 증가했다.

### GPT-OSS

| Arm | 20B | 120B |
|---|---:|---:|
| Full Available | 112/160 | 110/160 |
| SQL Available | 105/160 | 105/160 |
| SQL Available Original-only names | 25 | 13 |

큰 모델의 일관된 성능 향상이나 더 강한 Original-name 사용이 나타나지 않았다.

### Qwen3.5 MoE

| Arm | 35B-A3B | 122B-A10B | 397B-A17B |
|---|---:|---:|---:|
| Full Available | 26/32 | 26/32 | 28/32 |
| SQL Available | 23/32 | 29/32 | 25/32 |
| SQL Available Original-only names | 7 | 2 | 23 |

Qwen도 단조로운 크기 효과가 없다.

### Motivation 3 verdict

**B+ / descriptive coverage는 충분하지만 size-only 인과 주장은 아직 어려움.**

세 family, 8개 size point에서 M1을 반복했다는 점은 강하다. 하지만:

- GPT-OSS는 2개 size point뿐이다.
- Qwen 397B는 expert 수와 routing 설정도 달라진다.
- Family별 provider와 precision이 다르다.
- Qwen만 16-task pilot이다.
- 모든 primary cohort가 k=1이다.

따라서 지원되는 결론은 **“size effect는 보편적이지 않고 family·architecture·tool 조건에 의존한다”**이다.

## 현재 논문에서 가장 안전한 이야기

1. **Schema information이 없으면 renamed Star에서 문제 해결이 거의 붕괴한다.**
2. **Full Tools는 Star에서 Original identifier 의존을 크게 줄이고 현재 schema에 맞춘 탐색을 돕는다.**
3. **이 behavioral adaptation이 항상 같은 크기의 성공률 향상으로 이어지지는 않는다.**
4. **모델 크기의 영향은 family마다 다르므로 단일 scaling law보다 model×schema×tool 상호작용으로 설명해야 한다.**

이 framing은 지금까지의 모든 primary 결과와 충돌하지 않는다.

## 남은 핵심 gap

우선순위순으로:

1. **Gemini 3.8 Flash Full Tools Available**
   - 현재 main backbone은 SQL A/B만 완료됐다.
   - 같은 32-task subset에서 Full Original/Star를 돌리면 main-backbone M1이 완성된다.
2. **Qwen3.5 MoE subset80 확장**
   - Ministral/GPT-OSS와 동일 80 tasks로 맞춰 cross-family 비교를 강화한다.
3. **k>1 또는 제한된 repeated-trial replication**
   - 현재 k=1에서 보이는 task-level 변동성을 측정한다.
4. 필요할 때만 Metadata treatment와 Full Tools bundle을 세분화한다.
   - Catalog access와 guidance를 분리하거나 individual tool ablation을 추가하는 것은 현재 M1–M3의 필수 조건은 아니다.

AdaptQA는 사용자의 현재 authoritative M1–M3 정의를 충족하기 위한 필수 gap이 아니다.

## 최종 평가

| 항목 | 평가 |
|---|---|
| 실험 설계 정합성 | **A, 약 9/10** |
| Motivation 1 | **A-** |
| Motivation 2 | **A** |
| Motivation 3 | **B+** |
| Descriptive paper evidence | **높음** |
| Size-only/causal/population-level evidence | **중간** |

현재 결과는 motivation을 억지로 맞춘 것이 아니라, motivation이 묻는 질문에 실제로 답하고 있다. 특히 Motivation 2와 naming adaptation은 매우 강하고, M1 성능과 M3 size trend가 혼합적이라는 사실도 중요한 연구 결과다.

## 근거

Primary artifacts:

- `results/ministral-incre-subset80-20260911/report.md`
- `results/ministral-incre-subset80-20260911/performance-analysis.json`
- `results/ministral-incre-subset80-20260911/naming-analysis.json`
- `results/gpt-oss-incre-subset80-20260913/report.md`
- `results/gpt-oss-incre-subset80-20260913/performance-analysis.json`
- `results/gpt-oss-incre-subset80-20260913/naming-analysis.json`
- `results/qwen35-moe-incre-pilot16-20260914/report.md`
- `results/qwen35-moe-incre-pilot16-20260914/performance-analysis.json`
- `results/qwen35-moe-incre-pilot16-20260914/naming-analysis.json`

Historical branch artifacts:

- `analysis/schema-name-audit:results/gemini25fl-incre-full-official-rerun-report.md`
- `analysis/schema-name-audit:results/gemini38-incre-ab-official-rerun-report.md`
- `analysis/schema-name-audit:results/motivation_experiment_report.md`

Machine-readable synthesis:

- `results/motivation-retrospective-20260914/evidence.json`
