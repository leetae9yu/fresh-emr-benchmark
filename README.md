# EHR-ChatQA

A benchmark for evaluating database agents through multi-turn EHR (Electronic Health Record) database conversations with simulated users.

Paper: [From Conversation to Query Execution: Benchmarking User and Tool Interactions for EHR Database Agents](https://openreview.net/forum?id=hLweUPBz7k) (ICLR 2026)

## Setup

Python >= 3.11

```bash
pip install -r requirements.txt
```

Create `.env` in the project root:
```bash
OPENROUTER_API_KEY=...   # OpenRouter LLMs + OpenRouter embeddings
OPENAI_API_KEY=...       # FAISS embeddings + OpenAI models
GEMINI_API_KEY=...       # Gemini models (GOOGLE_API_KEY is also accepted)
TAVILY_API_KEY=...       # web_search tool
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

### Config-driven experiments

Edit `experiments/motivation.toml` instead of maintaining shell commands.
`experiment_runner.py` is a standalone launcher; it invokes the selected
checkout's `run.py` in subprocesses rather than copying the agent or evaluator.

```bash
# Read and validate the config, source options and task IDs without API calls
# or output files.
.venv/bin/python experiment_runner.py experiments/motivation.toml --dry-run

# Execute the reviewed matrix.
.venv/bin/python experiment_runner.py experiments/motivation.toml

# Continue only the identical resolved configuration and source code.
.venv/bin/python experiment_runner.py experiments/motivation.toml --resume
```

The TOML config selects `envs`, `task_types`, `trials`, `[[models]]`,
`[[conditions]]`, `[user]`, `[validator]`, and `[defaults]`. Pilot task IDs
are specified separately under `[task_ids.<env>]`, for example:

```toml
[task_ids.mimic_iv]
incre = [20, 16, 125]
adapt = [0, 20, 35]

[task_ids.mimic_iv_star]
incre = [20, 16, 125]
adapt = [0, 20, 35]
```

Keep Original and Star task selections paired when testing renaming. Each
trial has its own job, checkpoint directory and manifest trial ID; it does
not select a trial by concurrent completion order. Set `parallel_cells`
conservatively: FAISS-backed MIMIC processes consume substantial memory.
Within each job, `[defaults].max_concurrency` controls task workers.
Omit all `task_ids` tables to run the full selected catalogs. A nonempty
selection must explicitly cover every selected environment and task type.
The shipped sample uses one task per environment/flow and one trial, producing
16 jobs; it is an execution smoke configuration, not a representative study.

`[defaults].timeout` bounds the agent conversation's LLM/user work and SQL
timeouts are clamped to its remaining time. Each model request has at most a
120-second budget and three application attempts; SDK retries are disabled.
Post-conversation validation has its own 120-second budget. Embedding and web
tools retain their own runtime behavior, so `[defaults].run_timeout` is the
hard wall-clock limit for the entire job process tree, including setup.
Timed-out agent trajectories retain completed messages and recorded costs.

The launcher writes a resolved `manifest.json`, per-job metadata, `logs/`,
`checkpoints/`, `status/`, and a final `summary.json` under the config-hashed
result directory. Exit code 0 requires both successful subprocesses and
complete expected task coverage; invalid or duplicate outcomes are reported.
The hash includes model/provider settings and source content, including local
code changes. Changing a condition or code creates a separate experiment.
Logs are not placed in checkpoint directories.

`[source].path` is relative to the TOML file; `[source].python` can select
the checkout's `.venv/bin/python`. Requested options are checked against
that checkout's CLI before execution, including reasoning controls. Older
engines without `--trial_id` use the job manifest and directory to identify
the trial. Credentials stay in environment variables or the existing `.env`,
not in TOML. `full` and `schema_removed` retain web search and require
`TAVILY_API_KEY`, in addition to the chosen model and embedding credentials.

The sample compares `full` with `schema_removed`. This removes the two
schema helper tools and identifier-bearing guidance, but explicitly leaves
SQLite catalog access allowed. It is not a catalog-blocked experiment.
Change `metadata_access` separately if that is the intended treatment.

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

### OpenRouter-Only Setup

Agent, user simulator, validator, and embedding requests can all use one
`OPENROUTER_API_KEY`. The paper defaults remain unchanged, so every model must
be selected explicitly for an OpenRouter-only run:

```bash
python run.py \
    --env all \
    --task_type incre \
    --model openrouter/google/gemini-2.5-flash \
    --user_model openrouter/google/gemini-2.5-flash-lite \
    --validation_model openrouter/google/gemini-2.5-flash \
    --embedding_model openrouter/openai/text-embedding-3-small \
    --agent_strategy tool-calling \
    --tool_mode sql_value \
    --metadata_access blocked \
    --failure_feedback binary \
    --schema_guidance identifier_free \
    --num_trials 1
```

`sql_only` does not issue embedding requests. `sql_value` and `full` build a
FAISS index on first use and cache it under the environment directory; later
runs reuse that index. Non-default embedding models are included in checkpoint
names. `web_search` is absent from both restricted modes. A `TAVILY_API_KEY` is
still required for the paper `full` mode because Tavily is an external search
service rather than an LLM or embedding provider.

### Tool-Control Experiments

The default settings preserve the paper environment: all six tools are exposed,
database-specific SQL guidance is included, SQLite metadata is available, and
SQL errors are returned in detail.

For a schema-prior experiment without external value grounding, expose only
`sql_execute`, block SQLite catalog access, and use the identifier-free
database guide:

```bash
python run.py \
    --env mimic_iv_star \
    --task_type incre \
    --model gemini/gemini-2.5-flash \
    --agent_strategy tool-calling \
    --tool_mode sql_only \
    --schema_guidance identifier_free \
    --metadata_access blocked \
    --failure_feedback binary \
    --num_trials 1 \
    --task_ids 0
```

The experiment controls are independent:

| Argument | Values | Behavior |
|----------|--------|----------|
| `--tool_mode` | `full`, `schema_removed`, `sql_only`, `sql_value` | All six tools; remove only table/column search; SQL only; or SQL plus similarity |
| `--metadata_access` | `allowed`, `blocked` | Allow or deny SQLite catalogs, PRAGMAs, and table-valued PRAGMAs |
| `--failure_feedback` | `detailed`, `binary` | Return SQLite errors or the stable token `FAILED` |
| `--schema_guidance` | `benchmark`, `identifier_free`, `hidden` | Use the original/equivalent DB guide, a guide with identifier-bearing rules removed, or no DB-specific guide |
| `--reward_scope` | `any`, `final` | Credit any matching candidate (default) or only the final SQL attempt / agent response |

`schema_removed` retains SQL, similarity, substring, and web search in all
four environments. Its similarity description omits supported schema
identifiers. The config launcher requires `identifier_free` or `hidden`
guidance for this condition. `full` retains the original benchmark guide
and tool descriptions by default.

Successful SQL queries return their result in both failure-feedback modes.
`sql_only` skips FAISS initialization, so Gemini-only runs require only:

```env
GEMINI_API_KEY=...
```

`OPENAI_API_KEY` and `TAVILY_API_KEY` remain necessary only when the
corresponding embedding and web-search tools are enabled in `full` mode.
`sql_value` initializes only the FAISS value index and therefore needs the
embedding provider key, but it does not expose table search, column search,
substring search, or web search. Its tool description omits the supported
table and column list so the ablation does not disclose schema identifiers.
Checkpoint names include every non-default experiment control to prevent
results from different cells being resumed or aggregated together.

### Sixteen-Cell Motivation Experiment

The motivation design crosses four binary factors:

```text
schema:             original / Star
schema information: available / unavailable
error feedback:     detailed / binary
value similarity:   off / on
```

Use the following paired settings for schema information:

| Condition | Metadata | Prompt guide |
|-----------|----------|--------------|
| Available | `allowed` | `benchmark` |
| Unavailable | `blocked` | `identifier_free` |

Use `--tool_mode sql_only` when value similarity is off and
`--tool_mode sql_value` when it is on. Both modes exclude web search and the
other paper tools. Select `mimic_iv`/`eicu` for original schemas and
`mimic_iv_star`/`eicu_star` for renamed schemas.

Example unavailable-information cell with value similarity enabled:

```bash
python run.py \
    --env mimic_iv_star \
    --task_type incre \
    --model gemini/gemini-2.5-flash-lite \
    --agent_strategy tool-calling \
    --user_model gemini/gemini-2.5-flash-lite \
    --tool_mode sql_value \
    --metadata_access blocked \
    --failure_feedback binary \
    --schema_guidance identifier_free \
    --num_trials 1
```

The checked-in Star `db_rules.txt` files remain unchanged for paper
reproduction. Equivalent original-schema guides live beside the original
environments. Modified ablation guides use the same generic filename under
`src/ablation_prompts/`; file paths are never included in the model request.

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
Star environments. Original environments support both an identifier-equivalent
`benchmark` guide and the same identifier-free ablation guide used for Star.

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
| `--embedding_model` | `text-embedding-3-large` | Embedding model used by `sql_value` and `full` |
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
| `--tool_mode` | `full` | Tool exposure: `full`, `schema_removed`, `sql_only`, or `sql_value` |
| `--metadata_access` | `allowed` | SQLite metadata policy: `allowed` or `blocked` |
| `--failure_feedback` | `detailed` | SQL failure response: `detailed` or `binary` |
| `--schema_guidance` | `benchmark` | Database-specific prompt guidance: `benchmark`, `identifier_free`, or `hidden` |
| `--reward_scope` | `any` | Historical any-hit scope or `final` candidate only |
| `--trial_id` | automatic | Explicit trial slot for a single-trial invocation |
| `--reasoning_effort` | provider default | Explicit action-model reasoning setting; provider support is required |
| `--max_completion_tokens` | provider default | Action-model output budget, including reasoning where applicable |

## Evaluation

**IncreQA**: Agent's SQL result set is compared against the gold answer (exact set match).
**AdaptQA**: Agent's tagged answer is compared with exact numeric values and
normalized benchmark text/list formatting.

SQL scoring uses the full successful result captured during the actual tool
execution, not a second unrestricted database execution. Policy-denied and
timed-out queries cannot receive credit. Numeric normalization accepts
equivalent forms such as `1` and `1.0`, but not `1` and `10`.
`reward_scope=any` retains the benchmark's historical candidate-selection
scope; it is not a guarantee of final-answer correctness. `final` evaluates
only the last SQL attempt for IncreQA or the last agent response for AdaptQA.
These correctness fixes change scoring relative to the original release;
existing result files and published scores are not rewritten.

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
# Detect tasks that never produced even an invalid row:
python metric.py <result_file> --num_trials 1 --expected_tasks expected_tasks.json
```

`expected_tasks.json` is a JSON array of `[db_id, task_type, task_id]` string
triples. Metrics reject incomplete observed cohorts, including tasks with
only invalid attempts; explicit expected tasks also detect wholly absent
tasks. Appended revisions of a sample are counted once. Recorded costs
include invalid attempts and report unknown totals, rather than treating
missing costs as complete zero charges. Historical files containing
incorrectly recorded zeros cannot be repaired from those fields alone.

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
