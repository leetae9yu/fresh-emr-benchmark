import re
import random
from decimal import Decimal
from src.envs.tools import Tool
from src.utils import process_result, process_answer
from typing import Dict, List, Type, Optional, TypeVar, assert_never

from src.experiment import DEFAULT_EXPERIMENT_CONFIG, ExperimentConfig, RewardScope
from src.envs.user import load_user
from src.types import (
    Action,
    Task,
    EnvInfo,
    EnvResponse,
    RewardInfo,
)

numeric_to_words = {'two hundred and forty-seven': '247', 'two hundred forty-seven': '247',
                    'six hundred and fifty-nine': '659', 'six hundred fifty-nine': '659',
                    'thirty five': '35', 'thirty-five': '35',
                    'forty-eight': '48', 'forty eight': '48',
                    'thirty-seven': '37', 'thirty seven': '37',
                    'twenty-eight': '28', 'twenty eight': '28',
                    'seventy-two': '72', 'seventy two': '72',
                    'eleven': '11', 'thirty': '30',
                    'three': '3', 'four': '4', 'five': '5', 'six': '6',
                    'seven': '7', 'eight': '8', 'nine': '9', 'ten': '10',
                    'fourteen': '14', 'sixteen': '16', 'nineteen': '19',
                    'zero': '0', 'two': '2', 'one': '1'}

_RewardCandidate = TypeVar('_RewardCandidate')
_NUMBER = re.compile(r'(?<![\w.+-])[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?(?![\w.])')


def _answer_matches(gold_answer: list[str], answer: str) -> bool:
    """Match numeric values exactly without losing benchmark text/list support."""
    remaining = numeric_to_words.get(answer.lower(), answer.lower())
    for gold in sorted(gold_answer, key=len, reverse=True):
        if _NUMBER.fullmatch(gold):
            number = next((match for match in _NUMBER.finditer(remaining)
                           if Decimal(match.group()) == Decimal(gold)), None)
            if number is None:
                return False
            remaining = remaining[:number.start()] + ' ' + remaining[number.end():]
        else:
            if gold not in remaining:
                return False
            remaining = remaining.replace(gold, ' ', 1)
    return not re.sub(r'\b(?:and|days?)\b|[,;%]', '', remaining).strip(' .\n\t\r')


class Env(object):
    def __init__(
        self,
        tools: List[Type[Tool]],
        tasks: List[Task],
        user_strategy: str,
        user_model: str,
        user_temperature: float,
        db_path: str,
        task_type: str,
        api_base: Optional[str] = None,
        task_index: Optional[str] = None,
        rule: Optional[str] = "",
        retry_reason: Optional[List[str]] = None,
        experiment: ExperimentConfig = DEFAULT_EXPERIMENT_CONFIG,
    ) -> None:
        super().__init__()
        if retry_reason is None:
            retry_reason = []
        self.tools_map: Dict[str, Type[Tool]] = {
            tool.get_info()["function"]["name"]: tool for tool in tools
        }
        self.tools_info = [tool.get_info() for tool in tools]
        self.rule = rule
        self.user = load_user(
            user_strategy=user_strategy, model=user_model, temperature=user_temperature, api_base=api_base, retry_reason=retry_reason
        )
        self.actions: List[Action] = []
        self._sql_observations: list[tuple[str, str, str | None]] = []
        self.experiment = experiment
        self.db_path = db_path
        self.task_type = task_type
        self.tasks = tasks
        if tasks is not None:
            if task_index is not None:
                self.task_index = int(task_index)
            else:
                self.task_index = random.randint(0, len(tasks)-1)
            self.task = self.tasks[self.task_index]

    def reset(self, task_index: Optional[str] = None) -> EnvResponse:
        if task_index is not None:
            self.task_index = int(task_index)
        else:
            self.task_index = random.randint(0, len(self.tasks)-1)
        self.task = self.tasks[self.task_index]
        self.actions = []
        self._sql_observations = []
        initial_observation = self.user.reset(self.task)
        return EnvResponse(
            observation=initial_observation,
            reward=0.0,
            done=False,
            info=EnvInfo(task=self.task, reward_info=RewardInfo())
        )

    def step(self, action: Action) -> EnvResponse:
        self.actions.append(action)

        info = EnvInfo(task=self.task, reward_info=RewardInfo())
        reward = 0.0
        done = False
        sql_result: str | None = None
        if action.name == 'respond':
            observation = self.user.step(action.kwargs["content"])
            if observation:
                done = "###END###" in observation
            else:
                observation = ""
        elif action.name in self.tools_map:
            try:
                observation = self.tools_map[action.name].invoke(**action.kwargs)
                if action.name == 'sql_execute':
                    sql_result = getattr(self.tools_map[action.name], 'last_result', None)
            except Exception as e:
                observation = f"Error: {e}"
        else:
            observation = f"Unknown action {action.name}"
        if action.name == 'sql_execute':
            self._sql_observations.append((str(action.kwargs.get('query', '')).strip(), observation, sql_result))
        if done:
            if self.task_type == 'incre':
                reward_info = self.calculate_reward_sql()
            elif self.task_type == 'adapt':
                reward_info = self.calculate_reward_ans()
            else:
                raise NotImplementedError("Task type must be either 'incre' or 'adapt'")
            reward = reward_info.reward
            info.reward_info = reward_info
        return EnvResponse(
            observation=observation, 
            reward=reward,
            done=done,
            info=info)

    def _reward_candidates(self, candidates: list[_RewardCandidate]) -> list[_RewardCandidate]:
        match self.experiment.reward_scope:
            case RewardScope.ANY:
                return candidates
            case RewardScope.FINAL:
                return candidates[-1:]
            case unreachable:
                assert_never(unreachable)

    def calculate_reward_sql(self) -> RewardInfo:

        reward = 0.0
        gold_answer = process_result(self.task.gold_answer)
        pred_sql = []
        pred_answer = []
        for sql, observation, full_result in self._reward_candidates(self._sql_observations):
            if full_result is None:
                pred_sql.append(sql)
                pred_answer.append(observation)
                continue
            # Normalize all live rows before the benchmark's sorting/100-row cap.
            rows = process_result(full_result)
            if isinstance(rows, str):
                pred_sql.append(sql)
                pred_answer.append(observation)
                continue
            for column in zip(*rows):
                pred_sql.append(sql)
                pred_answer.append(column)
                if {value for value in column if value != 'None'} == {row[0] for row in gold_answer}:
                    reward = 1.0
                    break
            if reward == 1.0:
                break

        reward_info = RewardInfo(reward=reward, info={'pred_sql': pred_sql, 'pred_answer': pred_answer})
        return reward_info

    def calculate_reward_ans(self) -> RewardInfo:

        reward = 0.0
        gold_answer = [str(process_answer(ans[0])) for ans in process_result(self.task.gold_answer)]
        gold_answer = [numeric_to_words.get(gold_ans, gold_ans) for gold_ans in gold_answer]
        pred_response = []
        pred_answer = []
        response_actions = [action.kwargs["content"] for action in self.actions if action.name == 'respond' and 'content' in action.kwargs and action.kwargs['content'] is not None]
        if len(response_actions) > 0:
            for response in self._reward_candidates(response_actions):
                pred_response.append(response)
                pattern = r'(?:<answer>|```answer|```\s*\n)(.*?)(?:</answer>|```)'
                match = re.search(pattern, response, re.DOTALL)
                if match:
                    pred_ans = match.group(1).strip()
                    pred_answer.append(pred_ans)
                    reward = float(_answer_matches(gold_answer, pred_ans))

                else:
                    pred_answer.append('N/A')
                if reward == 1.0:
                    break
                
        reward_info = RewardInfo(reward=reward, info={'pred_response': pred_response, 'pred_answer': pred_answer})
        return reward_info
