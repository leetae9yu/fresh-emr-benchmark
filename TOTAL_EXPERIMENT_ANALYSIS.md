# Original/Star 스키마 실험: 연구 동기별 증거 정리

**정리 기준:** [연구 동기 문서](https://docs.google.com/document/d/1CFrobyyHeQVOqwRq_wPzxhzYHBP7Sdh0KZlBH2sL9zM/edit?usp=drivesdk)의 세 축(이름 변경, 스키마 정보 차단, 모델 역량). 2026-10-01 현재 로컬 보고서에 기록된 완료 실험만 다룬다. 새 실행이나 서로 다른 실험의 결과를 합친 효과 추정은 하지 않는다.

## 한눈에 보는 결론

| 문서의 주장 | 가장 직접적인 관찰 | 판단 |
|---|---|---|
| 1. Original을 Star로 이름 변경하면 기존 스키마 이름에 대한 prior 때문에 성능이 떨어진다 | Gemini 3.8 Flash SQL-only IncreQA에서 정보 제공 시 Original/Star **29/32 대 29/32**, 정보 차단 시 **21/32 대 0/32**. Star에서 Original 이름을 실행해 실패한 궤적도 관찰된다. | 이름 변경 자체의 보편적 페널티가 아니라, **이름을 발견할 수 없을 때 유용한 Original 스키마 지식이 Star로 이전되지 않는 현상**으로 좁히는 것이 정확하다. |
| 2. 스키마 정보가 unavailable해지면 이름 변경의 성능 하락이 커진다 | 같은 3.8 Flash의 Original−Star 차이는 정보 제공 시 **0%p**, 차단 시 **65.625%p**. 3.5 Flash의 12쌍 파일럿도 제공 시 Original 10/12, Star 11/12; 차단 시 7/12, 0/12. | 방향은 뚜렷하지만, 차단 조건은 **메타데이터 접근과 identifier-bearing 가이드를 동시에 바꾸므로** 메타데이터 단독 효과는 아니다. |
| 3. 모델이 클수록 prior bias가 커진다 | 3.8 Flash가 차단된 Original에서 성공한 반면 약한 모델은 바닥 효과를 보인다. Gemma 4 26B-A4B와 31B 파일럿은 모두 차단 조건 0/12, 전체 6/24. | **아직 검증되지 않음.** 모델 계열·훈련·인터페이스·능력이 섞이고 크기에 따른 단조 증가도 없다. |

## 비교 가능성을 위한 조건

핵심 3.8 Flash 실험은 MIMIC-IV/eICU 각 16개 IncreQA 과제를 Original/Star로 짝지어 4조건, 총 128개 유효 k=1 궤적을 평가했다. 에이전트 도구는 `sql_execute` 하나, 상세 SQL 오류는 유지했다. 제공 조건에는 카탈로그 접근과 식별자 포함 가이드가 있고 차단 조건에는 둘 다 없다. 일반 SQL을 통한 테이블 존재 여부 추측은 차단되지 않는다. 유효한 시뮬레이션을 얻기 위한 재시도가 있었으므로 비율은 **수용된 시뮬레이션 조건부** 결과다. [3.8 Flash 확대 파일럿](results/gemini38-sqlonly-incre-128-report.md)

이하 성공률은 IncreQA에서 SQL 결과를 판정하는 k=1 점수다. AdaptQA는 답변 태그 평가를 쓰므로 성공률을 같은 모수의 반복 측정처럼 합산하지 않는다. 툴 수, 모델, 과제 집합, 시뮬레이터 시점이 다른 실험 간 수치를 직접 인과 비교하지 않는다.

## 동기 1: 이름 변경과 Original 스키마 prior

**가장 선명한 대조:** 3.8 Flash는 정보 제공 시 Original과 Star에서 각각 29/32(90.625%)로 같았다. 정보 차단 시 Original 21/32(65.625%)를 유지했지만 Star는 0/32였다. MIMIC-IV는 차단 시 Original 14/16, Star 0/16; eICU는 7/16, 0/16이다. 성공률만으로 prior를 직접 측정했다고 할 수는 없으나, 동일 과제의 이름 변경·정보 제공 대조와 아래 SQL 궤적이 기제를 뒷받침한다. [3.8 Flash 확대 파일럿](results/gemini38-sqlonly-incre-128-report.md)

**행동 증거:** 이전 3.8 Flash 6과제 파일럿의 Star 차단 궤적 5/6에서 Original 식별자가 등장했고, `diagnoses_icd`, `prescriptions`, `procedures_icd` 등 정확한 기존 테이블명을 반복 시도했으나 해당 Star 쿼리는 실패했다. 제공 시에는 0/6이었다. 별도 Gemini 3.5 Flash 12과제 Star 파일럿에서도 정보 제공 11/12 성공·Original 이름 등장 0회였으나, 차단 0/12 성공·Original 식별자 등장 55회·스키마 오류 247회였다. 식별자 사용은 **공개 Original 스키마로의 회귀와 일치**하지만, 사전학습 기원만을 독립적으로 증명하지는 않는다. [스키마 prior/추론 궤적 분석](results/schema_prior_reasoning_trajectory_analysis.md), [동기 실험 보고서 §8.8](results/motivation_experiment_report.md)

**반대 방향의 결과도 보존:** Gemini 2.5 Flash-Lite의 전체 366과제 SQL-only 실험에서는 정보 제공 시 Original 57/366(15.57%), Star 41/366(11.20%)였으나 짝지은 Original–Star 차이의 exact McNemar p=0.0722였다. 차단 시 5/366 대 1/366은 둘 다 바닥에 가까웠다. 더 최근 **모든 6개 도구 제공** 2.5 Flash-Lite 전체 IncreQA에서는 정보 제공 조건에서 MIMIC Original 78/145 대 Star 91/145, eICU Original 69/141 대 Star 86/141로 **Star가 더 높았다**. 이는 SQL-only 차단 실험의 복제가 아니라 도구·실행 시점이 다른 조건이다. 완료된 full-tool AdaptQA도 Original 14/80 대 Star 17/80이다. 따라서 “Star는 언제나 어렵다”는 서술은 결과와 맞지 않는다. [동기 실험 보고서 §4.6](results/motivation_experiment_report.md), [full-tool IncreQA](results/gemini25fl-full-incre-eval-report.md), [AdaptQA 완료 복구 보고서](results/gemini25fl-full-adapt-simulator-repair-20260909-audit/report.md)

## 동기 2: 스키마 정보 차단과 이름 변경의 상호작용

| SQL-only 실험 | 정보 제공: Original / Star | 정보 차단: Original / Star | 차단 시의 핵심 차이 |
|---|---:|---:|---|
| Gemini 3.8 Flash, IncreQA 32과제 | 29/32 / 29/32 | 21/32 / 0/32 | Original−Star **65.625%p** |
| Gemini 3.5 Flash, IncreQA+AdaptQA 12과제 파일럿 | 10/12 / 11/12 | 7/12 / 0/12 | Original−Star **58.3%p**; 짝지은 차단 비교 p=0.0156 |
| Gemini 2.5 Flash-Lite, 366과제 | 57/366 / 41/366 | 5/366 / 1/366 | 두 차단 셀의 바닥 효과로 증폭 여부 판단 곤란 |

출처: [3.8 Flash 확대 파일럿](results/gemini38-sqlonly-incre-128-report.md), [동기 실험 보고서 §4.5–4.6](results/motivation_experiment_report.md). 3.5 Flash의 p값은 작은 파일럿의 **차단 조건 내 Original 대 Star** 비교에만 해당하며, 상호작용 전체에 대한 별도 검정이 아니다.

차단의 기제는 단순한 “질문 난이도” 이상이다. 전체 2.5 Flash-Lite Star 궤적에서 이름이 바뀐 Star 테이블을 사용하는 SQL의 비율은 정보 제공 **1,245/3,538(35.2%)**에서 차단 **91/2,947(3.1%)**로 낮아졌고, Original 이름 오류 뒤 Star로 회복한 궤적은 **48/135(35.6%)**에서 **1/95(1.1%)**로 낮아졌다. Original 테이블명 발생은 327회에서 419회로 늘었지만, Original 식별자 **전체** 발생은 1,669회에서 1,393회로 줄었다. 짧게 끝난 실패 궤적에서 컬럼 시도가 감소하기 때문이다. “차단하면 Original 이름 사용 전체가 증가한다”는 식의 단순화는 틀리다. [동기 실험 보고서 §8.2–8.5](results/motivation_experiment_report.md)

**식별 한계:** 두 조건은 카탈로그/PRAGMA 접근과 프롬프트의 스키마 가이드를 함께 바꾼다. SQL-only에서는 `table_search`/`column_search` 도구도 양쪽에 없으며, 차단해도 상세 `no such table`/`no such column` 오류와 일반 SQL 실행을 통해 제한적 존재 여부를 탐색할 수 있다. 따라서 실험 변수 이름은 **“스키마 정보 제공/차단”**, 더 엄밀히는 “카탈로그 차단 + 식별자 없는 가이드”이지 “메타데이터만 제거”나 “스키마 완전 비공개”가 아니다. [스키마 prior/추론 궤적 분석: 차단 조건](results/schema_prior_reasoning_trajectory_analysis.md), [동기 실험 보고서 §2](results/motivation_experiment_report.md)

문서의 “모든 tool available하게 할 경우?”에는 현재 **정보 제공 상태의 full-tool** 결과가 있다. 전체 2.5 Flash-Lite IncreQA 572/572 유효 결과에서 Original 147/286(51.4%), Star 177/286(61.9%)이고, 위의 SQL-only 실험과 반대 방향이다. 그러나 full-tool **차단 조건의 같은 과제 전체 매트릭스가 없으므로**, 모든 도구를 열었을 때 차단×이름 변경 상호작용이 유지되는지는 아직 답할 수 없다. [full-tool IncreQA](results/gemini25fl-full-incre-eval-report.md)

## 동기 3: 모델 역량/크기

가까운 자료는 [스키마 prior/추론 궤적 분석](results/schema_prior_reasoning_trajectory_analysis.md)의 6과제×4조건 파일럿이다. Gemini 3.8 Flash는 제공 8/12, 차단 2/12이고 두 차단 성공은 Original이다. Gemma 4 26B-A4B와 31B는 각각 전체 6/24, 차단 0/12였다. 더 강한 모델이 Original prior를 **활용할 수 있을 가능성**은 있지만, Gemma 간 크기 차이가 대응하는 효과 증가로 나타나지 않았고 Gemini와 Gemma는 같은 계열의 크기 조절군이 아니다. Gemini 3.5 Flash의 12과제 대비도 모델 크기 단독 개입이 아니다.

최근 Ministral3 3B/8B/14B IncreQA 파일럿은 모든 16쌍 과제에서 메타데이터 **제공**만 비교했다. Full-tool 성공은 각각 13/32, 17/32, 18/32; SQL-only는 6/32, 13/32, 16/32다. 규모와 성능의 기술적 비교에는 유용하지만 차단 셀이 없어 **크기에 따른 Original prior bias**를 검정하지 못한다. [Ministral3 파일럿](results/ministral3-incre-tools-pilot-20260909-audit/report.md)

모델 간 SQL 오류·원본 이름 빈도도 시뮬레이터가 제공한 이름과 구별해야 한다. 앞선 SQL-only 궤적 분석에서 가장 어려운 조건의 없는 테이블 이름 625/926(67.5%)은 대화상 **사용자 메시지에 먼저** 등장했다. 따라서 에이전트의 Original 이름 사용은 강한 행동 단서이지만 모든 이름 추측을 곧바로 모델의 내부 암기로 돌릴 수 없다. [SQL-only 궤적 분석 §4](results/increqa32_k3/sql_only_trajectory_analysis.md)

## 발표에 쓸 수 있는 범위와 보류할 주장

1. **제시 가능:** 동일 과제의 Original/Star를 짝지은 능력 있는 모델에서, 스키마 정보 제공 시 이름 변경 페널티가 없고 차단 시 Original 성공만 유지되는 사례가 재현된다. Star SQL의 실제 Original 이름·오류·회복률이 가능한 기제를 보여준다.
2. **제시 가능:** 모든 도구가 켜지고 스키마 정보가 제공되면 Star 성능이 Original보다 높을 수도 있다. “이름 변경 = 성능 하락”은 조건부 주장으로 써야 한다.
3. **보류:** 메타데이터 단독 효과, 모델 크기 증가의 인과 효과, SQL 궤적만으로 사전학습 기억의 출처 특정, 작은 파일럿의 일관된 효과 크기. 각기 별도 대조가 필요하다.
4. **정정 주의:** 과거 4모델 비용 파일럿의 원래 24건씩 성공률은 현재 확정 성적이 아니다. 2.5 Pro의 1건이 성공→실패로 수정되고 8건의 validator 결과가 격리되어 모델별 유효 분모가 달라졌다. 이 표를 능력 순위의 근거로 사용하지 않는다. [과거 실험 정정](docs/historical-corrections.md)

기존 결과가 답하지 못한 부분을 판별하려면 동일 과제·모델·도구 세트에서 식별자 가이드, 카탈로그 접근, 상세 오류를 각각 독립적으로 바꾸고, 같은 모델 계열의 규모를 짝지어 비교해야 한다. 현재 보고서는 **실행된 결과의 정리**이며 이 후속 설계를 실행한 것으로 표기하지 않는다.
