import time
from typing import List, Optional, Dict, Any

from src.agents.base import Agent, AgentTimeoutError
from src.envs.base import Env
from src.types import AgentRunResult, EnvInfo, RewardInfo, AgentRunError
from src.utils import get_action, add_costs, request_deadline, remaining_timeout

TOOL_CALLING_INSTRUCTION = """Instruction:
- You are a DB agent that helps users by answering their questions in natural language based on information from a database.
- You are currently engaged in a conversation with a user who wants to retrieve some data or statistics from an EHR database.
- If the user's request is ambiguous or missing details (e.g., filtering criteria), ask clarifying questions to better understand the request.
- You have access to a set of tools to assist the user:
  - table_search: search for tables in the database
  - column_search: search for columns within a table
  - value_substring_search: search for values in a column by substring match
  - value_similarity_search: search for values in a column by semantic similarity (embedding-based)
  - sql_execute: run SQL queries on the database
  - web_search: retrieve external clinical knowledge not in the database
- Use table_search and column_search to explore the database schema.
- Use value_substring_search and value_similarity_search to explore stored values.
- Clinical concepts (e.g., diagnoses, procedures, medications, lab tests) in the database may not exactly match the user's words. Use the value search tools to find relevant entries. 
- To search for or verify clinical knowledge not in the database (e.g., a drug's mechanism of action), use web_search.
- Never invent or assume information that is not provided by the user or retrieved using the tools.
- Make only one tool call at a time. Do not send a user-facing response in the same turn as a tool call.
- After gathering all necessary information, use sql_execute to write and run a single valid SQL query that fully answers the user's latest request.
- When you write an SQL query, always execute it with sql_execute and return the results to the user along with your explanation."""

TOOL_SETS = ['table_search', 'column_search', 'sql_execute', 'value_substring_search', 'value_similarity_search', 'web_search']


def _instruction_for_tools(tool_names: set[str]) -> str:
    if tool_names == set(TOOL_SETS):
        return TOOL_CALLING_INSTRUCTION

    disabled_tool_names = set(TOOL_SETS) - tool_names
    has_value_search = bool(
        tool_names & {"value_substring_search", "value_similarity_search"}
    )
    retained_lines = []
    for line in TOOL_CALLING_INSTRUCTION.splitlines():
        mentions_disabled_tool = any(
            tool_name in line
            for tool_name in disabled_tool_names
        )
        directs_missing_value_search = (
            line.startswith("- Clinical concepts ")
            and not has_value_search
        )
        if not mentions_disabled_tool and not directs_missing_value_search:
            retained_lines.append(line)
    return "\n".join(retained_lines)


class ToolCallingAgent(Agent):
    def __init__(
        self,
        tools_info: List[Dict[str, Any]],
        rule: str,
        model: str,
        api_base: Optional[str] = None,
        temperature: float = 0.0,
        verbose: bool = False,
        reasoning_effort: Optional[str] = None,
        max_completion_tokens: Optional[int] = None,
    ):
        self.tools_info = [tool for tool in tools_info if tool['function']["name"] in TOOL_SETS]
        self.rule = rule
        self.model = model
        self.api_base = api_base
        self.temperature = temperature
        self.verbose = verbose
        self.reasoning_effort = reasoning_effort
        self.max_completion_tokens = max_completion_tokens
        tool_names = {
            tool["function"]["name"]
            for tool in self.tools_info
        }
        instruction = _instruction_for_tools(tool_names)
        self.instruction = instruction + '\n' + self.rule
    def run(
        self, env: Env, task_index: Optional[str] = None, max_num_steps: int = 30, agent_timeout: int = 600
    ) -> AgentRunResult:
        deadline = time.monotonic() + agent_timeout
        agent_cost = 0.0
        reward = 0.0
        env_info = EnvInfo(task=env.task, reward_info=RewardInfo())
        messages: List[Dict[str, Any]] = [{"role": "system", "content": self.instruction}]
        try:
            with request_deadline(deadline):
                remaining_timeout(deadline)
                env_reset_res = env.reset(task_index=task_index)
                env_info = env_reset_res.info
                messages.append({"role": "user", "content": env_reset_res.observation})
                if self.verbose:
                    print(f"[USER]: {env_reset_res.observation}")

                for step in range(1, max_num_steps + 1):
                    next_message, action, done, cost = get_action(
                        model=self.model, messages=messages, temperature=self.temperature,
                        api_base=self.api_base, tools=self.tools_info, deadline=deadline,
                        reasoning_effort=self.reasoning_effort,
                        max_completion_tokens=self.max_completion_tokens,
                    )
                    agent_cost = add_costs(agent_cost, cost)
                    if action.name != 'respond':
                        next_message["tool_calls"] = next_message["tool_calls"][:1]
                    # Record a completed model response even if the environment subsequently fails.
                    messages.append(next_message)
                    remaining_timeout(deadline)
                    if action.name == "sql_execute":
                        action.kwargs["timeout"] = remaining_timeout(
                            deadline, float(action.kwargs.get("timeout", 60))
                        )
                    env_response = env.step(action)
                    reward = env_response.reward
                    env_info = env_response.info
                    if action.name != 'respond':
                        tool_call = next_message["tool_calls"][0]
                        messages.append({"role": "tool", "tool_call_id": tool_call["id"],
                                         "name": tool_call["function"]["name"],
                                         "content": env_response.observation})
                    else:
                        messages.append({"role": "user", "content": env_response.observation})
                    if self.verbose:
                        print(f"[AGENT]: {next_message}")
                        print(f"[ENV]: {env_response.observation}")
                    remaining_timeout(deadline)
                    if done or env_response.done:
                        break
        except Exception as error:
            if isinstance(error, AgentRunError):
                agent_cost = add_costs(agent_cost, error.cost)
            error_type = AgentTimeoutError if isinstance(error, (AgentTimeoutError, TimeoutError)) else AgentRunError
            partial = AgentRunResult(reward=reward, messages=messages, agent_cost=agent_cost, info=env_info)
            raise error_type(str(error), result=partial) from error

        return AgentRunResult(reward=reward, messages=messages, agent_cost=agent_cost, info=env_info)
