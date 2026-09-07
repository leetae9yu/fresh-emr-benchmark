import sys
sys.stdout.reconfigure(line_buffering=True)

import os
import uuid
from tqdm import tqdm
from argparse import ArgumentParser, Namespace
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from src.agents.base import AgentTimeoutError
import litellm
import traceback
litellm.suppress_debug_info = True
file_lock = threading.Lock()

import json

from src.envs import get_env
from src.agent_factory import get_agent
from src.experiment import (
    ExperimentConfig,
    FailureFeedback,
    MetadataAccess,
    SchemaGuidance,
    ToolMode,
    RewardScope,
)
from src.types import EnvRunResult, CostInfo, ValidationResult, AgentRunError, EnvInfo, RewardInfo
from src.utils import save_checkpoint, display_metrics, update_checkpoint, load_results, get_ckpt_name, add_costs, experiment_fingerprint
from validator import user_validator
from dotenv import load_dotenv


load_dotenv()


def _parse_validation_explanation(reason: str) -> str | None:
    try:
        parsed = json.loads(reason)
        return parsed.get('explanation', '')
    except (json.JSONDecodeError, KeyError):
        return reason


def parse_arguments() -> Namespace:
    parser = ArgumentParser()
    parser.add_argument("--env", type=str, default="all", choices=["mimic_iv", "mimic_iv_star", "eicu", "eicu_star", "all", "all_original"], help="Environment name for fetching user instructions")
    parser.add_argument("--task_type", type=str, default="all", choices=["incre", "adapt", "all"], help="Task type to use")
    parser.add_argument("--model", type=str, required=True, help="The agent model to use")
    parser.add_argument("--embedding_model", type=str, default="text-embedding-3-large", help="Embedding model for value similarity search")
    parser.add_argument("--api_base", type=str, default=None, help="The API base to use")
    parser.add_argument("--agent_strategy", type=str, required=True, choices=["tool-calling"], help="The agent strategy to use")
    parser.add_argument("--temperature", type=float, default=0.0, help="Sampling temperature for the action model")
    parser.add_argument("--user_model", type=str, default='gemini/gemini-2.0-flash', help="The user model to use")
    parser.add_argument("--user_temperature", type=float, default=1.0, help="Sampling temperature for the user model")
    parser.add_argument("--user_strategy", type=str, default='nested-reflection', choices=["human", "nested-reflection"], help="The user strategy to use")
    parser.add_argument("--result_dir", type=str, default="results", help="Directory to save the results")
    parser.add_argument("--num_trials", type=int, default=5, help="Number of trials (k) to run")
    parser.add_argument("--max_concurrency", type=int, default=1, help="Maximum concurrency level")
    parser.add_argument("--start_index", type=int, default=0, help="Start index for tasks")
    parser.add_argument("--end_index", type=int, default=-1, help="End index for tasks (-1 for all)")
    parser.add_argument("--task_ids", nargs='+', type=int, default=None, help="Specific task ids to run")
    parser.add_argument("--max_agent_turns", type=int, default=30, help="Maximum number of agent turns")
    parser.add_argument("--max_retry", type=int, default=10, help="Maximum number of simulation retries")
    parser.add_argument("--timeout", type=int, default=600, help="Timeout for each task in seconds")
    parser.add_argument("--validation_model", type=str, default='gemini/gemini-2.5-flash', help="The validation model to use")
    parser.add_argument("--verbose", action="store_true", help="Print user-agent conversations during execution")
    parser.add_argument("--validation_trials", type=int, default=1, help="Number of validation trials")
    parser.add_argument("--tool_mode", choices=[mode.value for mode in ToolMode], default=ToolMode.FULL.value, help="Tool exposure mode")
    parser.add_argument("--metadata_access", choices=[mode.value for mode in MetadataAccess], default=MetadataAccess.ALLOWED.value, help="SQLite metadata access policy")
    parser.add_argument("--failure_feedback", choices=[mode.value for mode in FailureFeedback], default=FailureFeedback.DETAILED.value, help="SQL failure response policy")
    parser.add_argument("--schema_guidance", choices=[mode.value for mode in SchemaGuidance], default=SchemaGuidance.BENCHMARK.value, help="Database-specific prompt guidance")
    parser.add_argument("--trial_id", type=int, default=None, help="Explicit trial slot (requires num_trials=1)")
    parser.add_argument("--reasoning_effort", choices=["none", "minimal", "low", "medium", "high", "default"], default=None)
    parser.add_argument("--max_completion_tokens", type=int, default=None)
    parser.add_argument("--reward_scope", choices=[scope.value for scope in RewardScope], default=RewardScope.ANY.value)
    config = parser.parse_args()
    try:
        _validate_runtime_config(config)
    except ValueError as error:
        parser.error(str(error))
    return config


def _validate_runtime_config(config: Namespace):
    for name in ("num_trials", "max_concurrency", "max_agent_turns", "max_retry", "timeout", "validation_trials"):
        if getattr(config, name) < 1:
            raise ValueError(f"{name} must be >= 1")
    trial_id = getattr(config, "trial_id", None)
    if trial_id is not None and (trial_id < 1 or config.num_trials != 1):
        raise ValueError("trial_id must be >= 1 and requires num_trials=1")
    max_tokens = getattr(config, "max_completion_tokens", None)
    if max_tokens is not None and max_tokens < 1:
        raise ValueError("max_completion_tokens must be >= 1")


def run(config: Namespace):

    if (
        not config.model.lower().startswith("openrouter/")
        and any(x in config.model.lower() for x in ("llama", "qwen", "gpt-oss"))
    ):
        assert config.api_base is not None, f"api_base is required for {config.model}"

    if config.task_type == "all":
        task_types_to_run = ["incre", "adapt"]
        print("Running all task types: incre, adapt")
    else:
        task_types_to_run = [config.task_type]

    for task_type in task_types_to_run:
        config.task_type = task_type
        print(f"\n{'='*60}")
        print(f"Running task type: {task_type}")
        print(f"{'='*60}")
        _run_single(config)


def _run_single(config: Namespace):
    _validate_runtime_config(config)
    experiment = ExperimentConfig(
        tool_mode=ToolMode(getattr(config, "tool_mode", "full")),
        metadata_access=MetadataAccess(getattr(config, "metadata_access", "allowed")),
        failure_feedback=FailureFeedback(getattr(config, "failure_feedback", "detailed")),
        schema_guidance=SchemaGuidance(getattr(config, "schema_guidance", "benchmark")),
        reward_scope=RewardScope(getattr(config, "reward_scope", "any")),
    )

    if config.env == "all":
        envs_to_run = ["mimic_iv_star", "eicu_star"]
        print("Running all environments: mimic_iv_star, eicu_star")
    elif config.env == "all_original":
        envs_to_run = ["mimic_iv", "eicu"]
        print("Running all original environments: mimic_iv, eicu")
    else:
        envs_to_run = [config.env]

    ckpt_name = get_ckpt_name(config)
    ckpt_path = os.path.join(config.result_dir, ckpt_name + '.jsonl')
    os.makedirs(config.result_dir, exist_ok=True)
    
    print(f"Loading user with strategy: {config.user_strategy}")
    print(
        "Experiment controls: "
        f"tools={experiment.tool_mode.value}, "
        f"metadata={experiment.metadata_access.value}, "
        f"failure_feedback={experiment.failure_feedback.value}, "
        f"schema_guidance={experiment.schema_guidance.value}"
    )
    
    # Initialize environments and agents for each env
    envs = {}
    agents = {}
    env_task_indices = {}
    
    for env_name in envs_to_run:
        envs[env_name] = get_env(
            env_name=env_name,
            task_type=config.task_type,
            user_strategy=config.user_strategy,
            user_model=config.user_model,
            user_temperature=config.user_temperature,
            embedding_model=getattr(config, "embedding_model", "text-embedding-3-large"),
            api_base=config.api_base,
            experiment=experiment,
        )
        agents[env_name] = get_agent(
            tools_info=envs[env_name].tools_info,
            model=config.model,
            api_base=config.api_base,
            temperature=config.temperature,
            agent_strategy=config.agent_strategy,
            rule=envs[env_name].rule,
            verbose=config.verbose,
            reasoning_effort=getattr(config, "reasoning_effort", None),
            max_completion_tokens=getattr(config, "max_completion_tokens", None),
        )
        
        # Determine task indices for this environment
        total_tasks = len(envs[env_name].tasks)
        end_index = total_tasks if config.end_index == -1 else min(config.end_index, total_tasks)
        idx = config.task_ids if config.task_ids else list(range(config.start_index, end_index))
        if len(idx) != len(set(idx)) or any(task_id < 0 or task_id >= total_tasks for task_id in idx):
            raise ValueError(f"Invalid or duplicate task indices for {env_name}: {idx}")
        env_task_indices[env_name] = idx
        
        task_info = f"{config.task_ids}" if config.task_ids else f"{config.start_index} to {end_index}"
        print(f"Running tasks for {env_name}: {task_info} (checkpoint path: {ckpt_path})")
    
    # Collect all task indices for loading results
    all_task_ids = []
    for indices in env_task_indices.values():
        all_task_ids.extend(indices)
    all_task_ids = sorted(set(all_task_ids))
    
    results = load_results(config, idx=[str(i) for i in all_task_ids])
    
    expected_tasks = {(env_name, config.task_type, str(task_id))
                      for env_name, indices in env_task_indices.items() for task_id in indices}
    if any(result.trial_id is None for result in results):
        raise ValueError("Checkpoint rows lack explicit trial_id; migrate trial slots before resuming")
    trial_id = getattr(config, "trial_id", None)
    trial_ids = [trial_id] if trial_id is not None else list(range(1, config.num_trials + 1))
    requested_slots = [(env_name, task_id, trial)
                       for env_name, indices in env_task_indices.items()
                       for task_id in indices for trial in trial_ids]
    completed_slots = [(result.db_id, int(result.task_id), result.trial_id)
                       for result in results if result.reward is not None]
    if len(completed_slots) != len(set(completed_slots)):
        raise ValueError("Checkpoint contains duplicate completed trial slots")
    if any(slot not in requested_slots for slot in completed_slots):
        raise ValueError("Checkpoint contains unrequested trial slots")
    idx_to_run = [slot for slot in requested_slots if slot not in set(completed_slots)]

    if not idx_to_run:
        print("No new tasks to run. All tasks have been loaded from checkpoint.")
        display_metrics(results, config.num_trials, expected_tasks=expected_tasks)
        return

    save_checkpoint(ckpt_path, results)
    identity = experiment_fingerprint(config)

    def _run(task_item) -> list[EnvRunResult]:
        current_env_name, task_idx, trial = task_item
        retry_reason = []
        attempts = []
        for retry in range(config.max_retry):
            isolated_env = None
            result = None
            try:
                isolated_env = get_env(
                    env_name=current_env_name, task_type=config.task_type,
                    user_strategy=config.user_strategy, user_model=config.user_model,
                    user_temperature=config.user_temperature,
                    embedding_model=getattr(config, "embedding_model", "text-embedding-3-large"),
                    api_base=config.api_base, task_index=str(task_idx),
                    retry_reason=retry_reason, experiment=experiment,
                )
                response = agents[current_env_name].run(
                    isolated_env, str(task_idx), config.max_agent_turns, config.timeout
                )
                user_cost = isolated_env.user.get_total_cost()
                result = EnvRunResult(
                    db_id=isolated_env.task.db_id, task_type=isolated_env.task.task_type,
                    task_id=isolated_env.task.task_id, sample_id=str(uuid.uuid4()),
                    trial_id=trial, experiment_id=identity,
                    reward=response.reward, info=response.info, messages=response.messages,
                    cost=CostInfo(agent_cost=response.agent_cost, user_cost=user_cost, eval_cost=0.0,
                                  total_cost=add_costs(response.agent_cost, user_cost)),
                    retry=retry, retry_reason=list(retry_reason),
                )
                try:
                    validation_result = user_validator(
                        messages=response.messages, env=isolated_env, model=config.validation_model,
                        api_base=config.api_base, n=config.validation_trials,
                        max_agent_turns=config.max_agent_turns,
                    )
                except Exception as error:
                    # The trajectory already exists; validator failures must never replace it.
                    validation_result = ValidationResult(decision="validator_error", reason=str(error), eval_cost=None)
                result.cost.eval_cost = validation_result.eval_cost
                result.cost.total_cost = add_costs(result.cost.agent_cost, user_cost, validation_result.eval_cost)
                result.validation = validation_result
                if validation_result.decision != "no_error":
                    result.reward = None
            except Exception as error:
                task = envs[current_env_name].tasks[task_idx]
                partial = error.result if isinstance(error, AgentRunError) else None
                user_cost = isolated_env.user.get_total_cost() if isolated_env is not None else None
                agent_cost = partial.agent_cost if partial is not None else None
                is_timeout = isinstance(error, AgentTimeoutError)
                validation_result = ValidationResult(decision="agent_timeout" if is_timeout else "runtime_error",
                                                     reason=str(error), eval_cost=0.0)
                result = EnvRunResult(
                    db_id=task.db_id, task_type=task.task_type, task_id=task.task_id,
                    sample_id=str(uuid.uuid4()), trial_id=trial, experiment_id=identity,
                    reward=0.0 if is_timeout else None,
                    info=partial.info if partial is not None else EnvInfo(task=task, reward_info=RewardInfo()),
                    messages=partial.messages if partial is not None else [],
                    cost=CostInfo(agent_cost=agent_cost, user_cost=user_cost, eval_cost=0.0,
                                  total_cost=add_costs(agent_cost, user_cost)),
                    validation=validation_result,
                    retry=retry, retry_reason=list(retry_reason),
                )
                print(traceback.format_exc())

            retry_user = validation_result.decision == "user_error"
            result.retry_exhausted = retry_user and retry + 1 == config.max_retry
            update_checkpoint(ckpt_path, result, file_lock)
            attempts.append(result)
            print(f"task={current_env_name}/{task_idx} trial={trial} retry={retry} "
                  f"reward={result.reward} validation={validation_result.decision}")
            if not retry_user:
                break
            if config.user_strategy == "nested-reflection":
                explanation = _parse_validation_explanation(validation_result.reason)
                if explanation:
                    retry_reason.append(explanation)
        return attempts

    max_workers = max(1, min(config.max_concurrency, len(idx_to_run)))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(_run, task_item) for task_item in idx_to_run]
        for future in tqdm(as_completed(futures), total=len(futures), desc="Running"):
            results.extend(future.result())

    display_metrics(results, config.num_trials, expected_tasks=expected_tasks)

if __name__ == "__main__":
    config = parse_arguments()
    run(config)
