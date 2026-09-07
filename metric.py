import os
import json
import sys
from collections import Counter, defaultdict
from argparse import ArgumentParser, Namespace
from typing import List, Dict, Any
from math import comb
from src.types import EnvRunResult


def load_result_file(file_path: str) -> List[EnvRunResult]:
    """Load results from a JSON file."""
    with open(file_path, 'r') as f:
        data = [json.loads(line) for line in f if line.strip()]
    latest = {result["sample_id"]: EnvRunResult(**result) for result in data}
    return list(latest.values())


def calculate_metrics(
    results: List[EnvRunResult],
    num_trials: int = 5,
    expected_tasks: set[tuple[str, str, str]] | None = None,
) -> Dict[str, Any]:
    """Calculate success rate and pass@k metrics."""

    attempts = list({result.sample_id: result for result in results}.values())
    observed_tasks = {(r.db_id, r.task_type, r.task_id) for r in attempts}
    tasks = observed_tasks if expected_tasks is None else expected_tasks
    if num_trials < 1 or not tasks:
        message = "Evaluation requires positive trials and a nonempty task cohort."
        raise ValueError(message)
    if observed_tasks - tasks:
        message = f"Unexpected tasks in results: {sorted(observed_tasks - tasks)}"
        raise ValueError(message)

    valid_results = [r for r in attempts if r.reward is not None]
    total_counts = dict.fromkeys(tasks, 0)
    success_counts = dict.fromkeys(tasks, 0)
    trial_slots: dict[tuple[str, str, str], set[int | None]] = {
        task: set() for task in tasks
    }
    for r in valid_results:
        key = (r.db_id, r.task_type, r.task_id)
        trial_id = getattr(r, "trial_id", None)
        if trial_id is not None and trial_id in trial_slots[key]:
            message = f"Duplicate valid trial slot: {key}, trial_id={trial_id}"
            raise ValueError(message)
        trial_slots[key].add(trial_id)
        total_counts[key] += 1
        if r.reward == 1:
            success_counts[key] += 1
    if any(None in slots and len(slots) > 1 for slots in trial_slots.values()):
        message = "Indexed and legacy unindexed trials cannot be pooled for one task."
        raise ValueError(message)

    invalid_tasks = [(key, count) for key, count in total_counts.items() if count != num_trials]
    if invalid_tasks:
        message = f"Expected {num_trials} valid trials per task; incomplete or duplicate counts: {sorted(invalid_tasks)}"
        raise ValueError(message)
    
    # Calculate basic metrics
    total_trajectories = len(valid_results)
    total_tasks = len(success_counts)
    rewards = [r.reward for r in valid_results if r.reward is not None]
    avg_reward = round(sum(rewards) / total_trajectories * 100, 1)
    
    # Calculate pass@k metrics
    denom_cache = {k: comb(num_trials, k) for k in range(1, num_trials + 1)}
    
    pass_at_k = {}
    pass_hat_k = {}
    
    for k in range(1, num_trials + 1):
        denom = denom_cache[k]
        
        # pass@k: probability that at least one of k samples passes
        no_succ = sum(
            comb(num_trials - s, k) / denom 
            for s in success_counts.values()
        ) / total_tasks
        pass_at_k[k] = round((1 - no_succ) * 100, 1)
        
        # pass^k: probability that all k samples pass
        all_succ = sum(
            comb(s, k) / denom 
            for s in success_counts.values()
        ) / total_tasks
        pass_hat_k[k] = round(all_succ * 100, 1)
    
    # Calculate cost statistics
    total_cost = sum(r.cost.total_cost for r in attempts if r.cost.total_cost is not None)
    agent_cost = sum(r.cost.agent_cost for r in attempts if r.cost.agent_cost is not None)
    user_cost = sum(r.cost.user_cost for r in attempts if r.cost.user_cost is not None)
    eval_cost = sum(r.cost.eval_cost for r in attempts if r.cost.eval_cost is not None)
    missing_total = sum(r.cost.total_cost is None for r in attempts)
    
    return {
        'total_trajectories': total_trajectories,
        'total_attempts': len(attempts),
        'invalid_attempts': len(attempts) - total_trajectories,
        'total_tasks': total_tasks,
        'avg_trials_per_task': round(total_trajectories / total_tasks, 2),
        'success_rate': avg_reward,
        'pass@k': pass_at_k,
        'pass^k': pass_hat_k,
        'gap': {k: round(pass_at_k[k] - pass_hat_k[k], 1) for k in pass_at_k.keys()},
        'costs': {
            'total': round(total_cost, 4),
            'agent': round(agent_cost, 4),
            'user': round(user_cost, 4),
            'eval': round(eval_cost, 4),
            'avg_per_trajectory': round(total_cost / total_trajectories, 4),
            'missing_total': missing_total,
            'complete': missing_total == 0,
            'missing_agent': sum(r.cost.agent_cost is None for r in attempts),
            'missing_user': sum(r.cost.user_cost is None for r in attempts),
            'missing_eval': sum(r.cost.eval_cost is None for r in attempts),
        }
    }


def calculate_metrics_by_env(results: List[EnvRunResult], num_trials: int = 5) -> Dict[str, Dict[str, Any]]:
    """Calculate metrics separately for each environment."""
    env_results = defaultdict(list)
    
    for r in results:
        env_results[r.db_id].append(r)
    
    metrics_by_env = {}
    for env_name, env_result_list in env_results.items():
        metrics_by_env[env_name] = calculate_metrics(env_result_list, num_trials)
    
    return metrics_by_env


def calculate_metrics_by_task_type(results: List[EnvRunResult], num_trials: int = 5) -> Dict[str, Dict[str, Any]]:
    """Calculate metrics separately for each task type."""
    task_type_results = defaultdict(list)
    
    for r in results:
        task_type_results[r.task_type].append(r)
    
    metrics_by_type = {}
    for task_type, type_result_list in task_type_results.items():
        metrics_by_type[task_type] = calculate_metrics(type_result_list, num_trials)
    
    return metrics_by_type


def print_metrics(metrics: Dict[str, Any], title: str = "Overall Metrics"):
    """Pretty print metrics."""
    print(f"\n{'='*60}")
    print(f"{title:^60}")
    print(f"{'='*60}")
    
    if 'error' in metrics:
        print(f"Error: {metrics['error']}")
        return
    
    print(f"\n📊 Basic Statistics:")
    print(f"  • Total Trajectories: {metrics['total_trajectories']}")
    print(f"  • Saved attempts (including invalid): {metrics['total_attempts']}")
    print(f"  • Total Tasks: {metrics['total_tasks']}")
    print(f"  • Avg Trials per Task: {metrics['avg_trials_per_task']}")
    print(f"  • Success Rate (SR): {metrics['success_rate']}%")
    
    print(f"\n🎯 Pass@k Metrics:")
    for k in sorted(metrics['pass@k'].keys()):
        print(f"  • Pass@{k}: {metrics['pass@k'][k]}%")
    
    print(f"\n✨ Pass^k Metrics (All k pass):")
    for k in sorted(metrics['pass^k'].keys()):
        print(f"  • Pass^{k}: {metrics['pass^k'][k]}%")
    
    print(f"\n📈 Gap (Pass@k - Pass^k):")
    for k in sorted(metrics['gap'].keys()):
        print(f"  • Gap-{k}: {metrics['gap'][k]}%")
    
    print(f"\n💰 Cost Statistics:")
    print(f"  • Recorded cost across all attempts: ${metrics['costs']['total']:.4f}")
    if not metrics['costs']['complete']:
        print(f"  • Incomplete cost: {metrics['costs']['missing_total']} attempts have unknown total cost.")
    print(f"  • Agent Cost: ${metrics['costs']['agent']:.4f}")
    print(f"  • User Cost: ${metrics['costs']['user']:.4f}")
    print(f"  • Eval Cost: ${metrics['costs']['eval']:.4f}")
    print(f"  • Avg Cost per Trajectory: ${metrics['costs']['avg_per_trajectory']:.4f}")
    print()


def main():
    parser = ArgumentParser(description="Analyze and report metrics from experiment results")
    parser.add_argument("result_file", type=str, help="Path to the result JSON file")
    parser.add_argument("--num_trials", type=int, default=5, help="Number of trials (k) used in the experiment")
    parser.add_argument("--by_env", action="store_true", help="Show metrics broken down by environment")
    parser.add_argument("--by_task_type", action="store_true", help="Show metrics broken down by task type")
    parser.add_argument("--expected_tasks", type=str, help="JSON file of expected [db_id, task_type, task_id] triples")
    
    args = parser.parse_args()
    
    # Check if file exists
    if not os.path.exists(args.result_file):
        print(f"Error: File '{args.result_file}' not found.")
        return 2
    
    # Load results
    print(f"Loading results from: {args.result_file}")
    results = load_result_file(args.result_file)
    print(f"Loaded {len(results)} results")
    
    # Calculate overall metrics
    expected_tasks = None
    if args.expected_tasks:
        from pydantic import TypeAdapter

        with open(args.expected_tasks, encoding="utf-8") as expected_file:
            expected_tasks = set(
                TypeAdapter(list[tuple[str, str, str]]).validate_json(expected_file.read())
            )
    overall_metrics = calculate_metrics(results, args.num_trials, expected_tasks)
    
    print_metrics(overall_metrics, "Overall Metrics")
    
    if args.by_env:
        env_metrics = calculate_metrics_by_env(results, args.num_trials)
        for env_name, metrics in env_metrics.items():
            print_metrics(metrics, f"Environment: {env_name}")
    
    if args.by_task_type:
        type_metrics = calculate_metrics_by_task_type(results, args.num_trials)
        for task_type, metrics in type_metrics.items():
            print_metrics(metrics, f"Task Type: {task_type}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

