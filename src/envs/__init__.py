import logging
from typing import Optional, List

from src.envs.base import Env
from src.experiment import DEFAULT_EXPERIMENT_CONFIG, ExperimentConfig


def get_env(
    env_name: str,
    user_strategy: str,
    task_type: str,
    user_model: str,
    user_temperature: float = 1.0,
    embedding_model: str = "text-embedding-3-large",
    api_base: Optional[str] = None,
    task_index: Optional[str] = None,
    retry_reason: Optional[List[str]] = None,
    experiment: ExperimentConfig = DEFAULT_EXPERIMENT_CONFIG,
) -> Env:
    if env_name == "mimic_iv_star":
        from src.envs.mimic_iv_star import MimicIVStarEnv
        return MimicIVStarEnv(
            user_strategy=user_strategy,
            user_model=user_model,
            user_temperature=user_temperature,
            embedding_model=embedding_model,
            task_type=task_type,
            task_index=task_index,
            api_base=api_base,
            retry_reason=retry_reason,
            experiment=experiment,
        )
    elif env_name == "mimic_iv":
        from src.envs.mimic_iv import MimicIVEnv
        return MimicIVEnv(
            user_strategy=user_strategy,
            user_model=user_model,
            user_temperature=user_temperature,
            embedding_model=embedding_model,
            task_type=task_type,
            task_index=task_index,
            api_base=api_base,
            retry_reason=retry_reason,
            experiment=experiment,
        )
    elif env_name == "eicu_star":
        from src.envs.eicu_star import eICUStarEnv
        return eICUStarEnv(
            user_strategy=user_strategy,
            user_model=user_model,
            user_temperature=user_temperature,
            embedding_model=embedding_model,
            task_type=task_type,
            task_index=task_index,
            api_base=api_base,
            retry_reason=retry_reason,
            experiment=experiment,
        )
    elif env_name == "eicu":
        from src.envs.eicu import eICUEnv
        return eICUEnv(
            user_strategy=user_strategy,
            user_model=user_model,
            user_temperature=user_temperature,
            embedding_model=embedding_model,
            task_type=task_type,
            task_index=task_index,
            api_base=api_base,
            retry_reason=retry_reason,
            experiment=experiment,
        )
    else:
        raise ValueError(f"Unknown environment: {env_name}")
