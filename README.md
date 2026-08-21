# EHR-ChatQA

A benchmark for evaluating database agents through multi-turn EHR (Electronic Health Record) database conversations with simulated users.

Paper: [From Conversation to Query Execution: Benchmarking User and Tool Interactions for EHR Database Agents](https://openreview.net/forum?id=hLweUPBz7k) (ICLR 2026)

## Setup

Python >= 3.10

```bash
pip install -r requirements.txt
```

Create `.env` in the project root:
```bash
OPENAI_API_KEY=...       # FAISS embeddings + OpenAI models
GOOGLE_API_KEY=...       # Gemini models
TAVILY_API_KEY=...       # web_search tool
OPENROUTER_API_KEY=...   # (optional) OpenRouter
```

## Data

Four environments are available:
- **MIMIC-IV Original** — original table and column identifiers
- **MIMIC-IV Star** — 145 incre + 40 adapt tasks
- **eICU Original** — original table and column identifiers
- **eICU Star** — 141 incre + 40 adapt tasks

### Database Files

Download the SQLite databases ([mimic_iv_star](https://drive.google.com/file/d/1FU66Em_VNYWWGLDbrMuKLdAsORZVR0d3/view?usp=sharing), [eicu_star](https://drive.google.com/file/d/1_fsa36CeryFZqLDNXBMs11Zvaa8IgKbm/view?usp=sharing)):
```bash
pip install gdown
bash download_db.sh
```

Place the corresponding original-schema databases at:

```text
data/mimic_iv.sqlite
data/eicu.sqlite
```

Original environments derive their GT SQL in memory from the canonical Star
task files using the inverse rename map from the paper. The conversion is
SQL-AST and source-table aware; neither database is modified.

SQL schema files are included in the repo:
```
src/envs/{env_name}/{env_name}.sql
```

### Evaluation Tasks

Each environment provides two evaluation files (JSONL format, one JSON object per line):
```
src/envs/{env_name}/eval_incre.jsonl    # Incremental query tasks
src/envs/{env_name}/eval_adapt.jsonl    # Adaptive query tasks
```

### FAISS Index

The `value_similarity_search` tool uses a FAISS vector index for semantic matching. On first run, the index is built using `text-embedding-3-large` and cached at:
```
src/envs/{env_name}/faiss_index_{env_name}-text-embedding-3-large/
```

## Usage

Run a single task:
```bash
python run.py \
    --env mimic_iv_star \
    --task_type incre \
    --model gemini/gemini-2.5-flash \
    --agent_strategy tool-calling \
    --num_trials 1 \
    --task_ids 0
```

Full benchmark run:
```bash
python run.py \
    --env all \
    --task_type all \
    --model gemini/gemini-2.5-flash \
    --agent_strategy tool-calling \
    --num_trials 5 \
    --max_concurrency 16
```

Models can be specified as `gemini/gemini-2.5-flash` (Google), `gpt-4o` / `o4-mini` (OpenAI), `openrouter/google/gemini-2.5-flash` (OpenRouter), or `Qwen/Qwen3-32B` with `--api_base` (self-hosted).

### Tool-Control Experiments

The default settings preserve the paper environment: all six tools are exposed,
database-specific SQL guidance is included, SQLite metadata is available, and
SQL errors are returned in detail.

For the schema-prior experiment, expose only `sql_execute` and hide
database-specific schema guidance:

```bash
python run.py \
    --env mimic_iv_star \
    --task_type incre \
    --model gemini/gemini-2.5-flash \
    --agent_strategy tool-calling \
    --tool_mode sql_only \
    --schema_guidance hidden \
    --metadata_access blocked \
    --failure_feedback binary \
    --num_trials 1 \
    --task_ids 0
```

The experiment controls are independent:

| Argument | Values | Behavior |
|----------|--------|----------|
| `--tool_mode` | `full`, `sql_only` | Expose the paper's six tools or only `sql_execute` |
| `--metadata_access` | `allowed`, `blocked` | Allow or deny SQLite catalogs, PRAGMAs, and table-valued PRAGMAs |
| `--failure_feedback` | `detailed`, `binary` | Return SQLite errors or the stable token `FAILED` |
| `--schema_guidance` | `benchmark`, `hidden` | Include or omit database-specific SQL rules containing schema identifiers |

Successful SQL queries return their result in both failure-feedback modes.
`sql_only` skips FAISS initialization, so Gemini-only runs require only:

```env
GOOGLE_API_KEY=...
```

`OPENAI_API_KEY` and `TAVILY_API_KEY` remain necessary only when the
corresponding embedding and web-search tools are enabled in `full` mode.
Checkpoint names include every non-default experiment control to prevent
results from different cells being resumed or aggregated together.

Run both original-schema databases for one condition with:

```bash
python run.py \
    --env all_original \
    --task_type incre \
    --model gemini/gemini-2.5-flash-lite \
    --agent_strategy tool-calling \
    --user_model gemini/gemini-2.5-flash-lite \
    --tool_mode sql_only \
    --schema_guidance hidden \
    --metadata_access allowed \
    --failure_feedback detailed \
    --num_trials 1
```

`--env all` intentionally retains the paper default and runs only the two
Star environments. Original environments require `--schema_guidance hidden`;
there is no translated benchmark guidance that could leak original schema
identifiers.

The paper default still records `gemini/gemini-2.0-flash` as the simulator
model for reproducibility, but Google has retired that endpoint. Current runs
must pass a replacement explicitly, such as
`--user_model gemini/gemini-2.5-flash-lite`.

### Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--env` | `all` | `mimic_iv`, `mimic_iv_star`, `eicu`, `eicu_star`, `all`, `all_original` |
| `--task_type` | `all` | `incre`, `adapt`, `all` |
| `--model` | (required) | Agent model |
| `--agent_strategy` | (required) | `tool-calling` |
| `--temperature` | `0.0` | Agent sampling temperature |
| `--user_model` | `gemini/gemini-2.0-flash` | User simulator model |
| `--user_temperature` | `1.0` | User sampling temperature |
| `--user_strategy` | `nested-reflection` | `human`, `nested-reflection` |
| `--validation_model` | `gemini/gemini-2.5-flash` | Post-hoc validator model |
| `--num_trials` | `5` | Number of trials (k) |
| `--max_concurrency` | `1` | Parallel workers |
| `--max_retry` | `10` | Max retries on user error |
| `--timeout` | `600` | Per-task timeout (seconds) |
| `--max_agent_turns` | `30` | Max agent turns per conversation |
| `--task_ids` | `None` | Specific task IDs (space-separated) |
| `--api_base` | `None` | API base URL for self-hosted models |
| `--verbose` | `false` | Print conversations during execution |
| `--tool_mode` | `full` | Tool exposure: `full` or `sql_only` |
| `--metadata_access` | `allowed` | SQLite metadata policy: `allowed` or `blocked` |
| `--failure_feedback` | `detailed` | SQL failure response: `detailed` or `binary` |
| `--schema_guidance` | `benchmark` | Database-specific prompt guidance: `benchmark` or `hidden` |

## Evaluation

**IncreQA**: Agent's SQL result set is compared against the gold answer (exact set match).
**AdaptQA**: Agent's natural-language answer (`<answer>` tags) is compared via fuzzy string matching.

| Metric | Description |
|--------|-------------|
| SR-k | Success rate across k trials |
| Pass@k | Probability of at least 1 success in k trials |
| Pass^k | Probability of all k trials succeeding |
| Gap-k | Pass@k − Pass^k (inconsistency) |

```bash
python metric.py <result_file>
python metric.py <result_file> --by_env
python metric.py <result_file> --by_task_type
```

## Results

Results are saved to `results/` in JSONL format and checkpointed during execution. Re-running with the same configuration resumes from where it left off.

## Citation

```bibtex
@inproceedings{
lee2026from,
title={From Conversation to Query Execution: Benchmarking User and Tool Interactions for {EHR} Database Agents},
author={Gyubok Lee and Woosog Chay and Heeyoung Kwak and Yeong Hwa Kim and Haanju Yoo and Oksoon Jeong and Meong Hi Son and Edward Choi},
booktitle={The Fourteenth International Conference on Learning Representations},
year={2026},
url={https://openreview.net/forum?id=hLweUPBz7k}
}
```
