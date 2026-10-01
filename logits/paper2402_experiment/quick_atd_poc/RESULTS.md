# Original–Star DC/ATD 빠른 PoC (Qwen 2.5 1.5B)

**실행일:** 2026-10-01. **결론:** 이 모델/프롬프트에서는 두 지표가 모두 바닥에 가까워 스키마 암기 여부를 판별할 수 없다. Original 우세나 ATD 견고성을 보여줬다고 해석하지 않는다.

## 동일 모델의 가린 컬럼명 복원 (DC-accuracy)

기존 `paper2402_experiment/dataset.json`에서 원본·Star가 짝인 27개 테이블의 사전 고정 25% 컬럼 마스크 39쌍을 그대로 사용했다. 값/INSERT 없이 각 `CREATE TABLE`에서 한 이름을 가린 뒤, DDL 전체를 제시하고 `[MASK_n] =` 뒤에 정확한 이름을 생성하게 했다. 78개 결과 모두 확보했고 후처리에서 정확한 전체 식별자만 인정했다.

| 데이터베이스 | Original 정확 생성 | Star 정확 생성 |
|---|---:|---:|
| MIMIC-IV (16개 대응 테이블) | **1/24** | **0/24** |
| eICU (11개 대응 테이블) | **1/15** | **1/15** |
| 전체 (27개 대응 테이블) | **2/39** | **1/39** |

세 정답은 Original `d_icd_diagnoses.icd_code`, Original eICU `patient.gender`, Star eICU `vitalperiodic.temperature`다. 모델은 다른 항목에서 `subject_id`, `patientid` 같은 그럴듯하지만 틀린 이름을 자주 냈다. 이 정확 생성 결과로 Original에 특유한 스키마 암기를 주장할 수 없다.

## 동일 모델의 Full 대 ATD Text-to-SQL

기존 5문항 ATD 실행과 겹치지 않는 IncreQA 8문항(MIMIC-IV: 6, 9, 10, 46; eICU: 0, 8, 9, 42)을 먼저 고정했다. 각 문항의 Star 정답 SQL을 `convert_gold_sql`로 Original에 대응시켰고, 두 데이터베이스의 읽기 전용 실행 결과가 일치함을 확인했다. 정답 쿼리에 등장하는 물리 테이블의 값 없는 DDL만 제시했다. Full과 ATD의 유일한 입력 차이는 `FOREIGN KEY` 절 삭제(셀당 1–3개)다. 두 스키마 모두 같은 영어 과제 지시문을 받았다. Greedy SQL 한 개씩, 동일한 Qwen 체크포인트와 시스템 지시문, 최대 256토큰으로 8×2×2=32개 셀을 실행했다.

eICU 42번은 양쪽 DB의 정답 SQL 결과끼리는 일치하지만, 과제 파일의 저장된 `gold_answer`와 일치하지 않는다. 모델 출력 전에 로컬 검증에서 발견해 **주요 분석에서 문항 전체의 네 셀을 제외**했다. 남은 7개 문항의 실행 결과는 정답 SQL 결과와 정규화된 행 fingerprint로 비교했다. 아래의 `실행`은 SQL 문법/컬럼이 유효하다는 뜻이지 과제 정답이라는 뜻이 아니다.

| 스키마 | Full 정답 / 실행 | ATD 정답 / 실행 |
|---|---:|---:|
| Original | **0/7** / 6/7 | **0/7** / 3/7 |
| Star | **0/7** / 4/7 | **0/7** / 4/7 |

제외 문항까지 계산하면 Original Full 1/8, ATD 0/8; Star Full/ATD 모두 0/8이다. Original Full의 유일한 정답이 바로 주 분석에서 제외한 eICU 42번이다. **정답률에서 Full→ATD 하락은 양쪽 모두 0%p**인 바닥 효과이며, 논문의 “익숙한 스키마는 FK 삭제에도 견고하다”는 상호작용을 여기서 확인하지 못했다. 실행 가능성은 Original에서 6/7→3/7, Star에서 4/7→4/7이지만, 실행 가능성과 정답률은 다른 지표다. 원본 출력에는 잘못된 조인, 잘못된 리터럴·집계, 모호한 컬럼명, 없는 컬럼 등의 실패가 남아 있다.

## 해석 범위와 기존 실험과의 관계

- 이번 PoC의 **DC와 ATD는 모두 `Qwen/Qwen2.5-1.5B-Instruct`** 리비전 `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`에서 실행했다. T4에서 fp16으로 불러온 338개 파라미터 텐서와 생성 로짓의 유한성을 확인했다. OpenRouter는 호출하지 않았다.
- 이전 `paper2402_experiment/results.json`의 DC(7B Qwen MIMIC Original 테이블 평균 28.1%, Star 5.2%) 및 ATD 5문항은 **별개 모델·범위**다. 7B의 DC 신호와 이번 1.5B의 ATD 수치를 한 모델의 연쇄 증거로 합치면 안 된다. 7B를 새로 실행하려던 첫 Colab 세션은 가중치 다운로드 중 소실되어 결과 행이 0개였고, 이번 완료 결과에 포함되지 않는다.
- Spider–Termite 논문의 새로운 Termite에 대응하는 여기의 Star는 **같은 행을 이름만 바꾼 국소 반사실 DB**다. 과제/행의 차이는 줄지만 이름의 자연스러움과 컬럼 의미의 차이는 남는다. 새로운 샘플의 k=1 실행이며 테이블·문항 내 응답들은 독립 시행이 아니다.
- 이번 숫자로는 **Original의 정확한 스키마 암기**나 **암기가 Text-to-SQL 성능을 올렸다**는 주장을 할 수 없다. 반대로 능력 있는 모델에서 그러한 효과가 없다는 반증도 아니다. Full 자체가 바닥인 모델에서는 ATD의 추가 하락 여지가 없다.

## 보존 자료와 재계산

`jobs.json`은 32개 Full/ATD 입력, 짝지은 과제 ID, 스키마와 소스 해시, 정답 SQL 결과 fingerprint를 담는다. `dc_jobs.json`은 기존 78개 마스크 프롬프트의 생성 작업을 고정한다. `infer_qwen.jsonl`과 `infer_dc.jsonl`은 모델 원문 출력이며 각각 32행과 78행이다. `jobs_sha256.txt`와 `dc_jobs_sha256.txt`는 원격 실행 입력 다이제스트다. `model.json`과 `dc_model.json`은 실행별 동일 체크포인트 정보를 보존한다. `analysis.json`과 `dc_analysis.json`은 전 셀 판정 및 요약이다. DB 원본이나 환자 행은 이 디렉터리에 복사하지 않았다.

로컬 재검산:

```sh
../.venv/bin/python paper2402_experiment/quick_atd_poc.py check
../.venv/bin/python paper2402_experiment/quick_atd_poc.py analyze
../.venv/bin/python paper2402_experiment/quick_atd_poc.py analyze-dc
```

기존 DC/ATD 관련 테스트 15개가 통과했고, 새 코드의 Ruff 검사와 Python 컴파일이 통과했다. 의존성을 지정한 로컬 스크립트의 basedpyright 검사는 오류 0개·경고 40개이며, GPU 전용 스크립트는 로컬 환경에 Torch/Transformers가 없어 타입 검사 오류가 남는다. 이를 정적 검사 통과로 표시하지 않는다. 로컬 `quick_atd_poc.py check`는 eICU 42번의 별도 `ANNOTATED_ANSWER_MISMATCH`를 출력하면서 32개 입력의 원본·Star SQL 정합성과 고정 입력 일치를 검증한다. 새로운 모델 호출 없이 위 명령으로 요약을 다시 생성할 수 있다.
