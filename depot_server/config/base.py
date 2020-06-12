import io
import os
from typing import Any, Dict, Union, Type, TypeVar

import oyaml as yaml
from pydantic import BaseModel

DEFAULT_PATH = os.environ.get('API_CONFIG_FILE', os.path.join(os.path.dirname(__file__), '..', 'config.yaml'))


def camelcase_to_underscore(camelcase: str) -> str:
    res = ''
    last_was_upper = True
    for i in range(len(camelcase)):
        if camelcase[i].isupper() and not last_was_upper:
            res += '_' + camelcase[i].lower()
        else:
            res += camelcase[i]
            last_was_upper = False
    return res


def config_to_underscore(cfg):
    if isinstance(cfg, dict):
        return {
            camelcase_to_underscore(key): config_to_underscore(value)
            for key, value in cfg.items()
        }
    return cfg


def _assign_key(cfg: Union[list, Dict[str, Any]], key: str, value: Any, self_path: str):
    found_key: Any = None
    found_key_underscore = None
    first_part = key.split('_', 1)[0]
    if isinstance(cfg, dict):
        for cfg_key in cfg.keys():
            if cfg_key.startswith(first_part):
                if key.startswith(cfg_key):
                    found_key = cfg_key
                    found_key_underscore = cfg_key
    elif isinstance(cfg, list):
        try:
            idx = int(first_part)
        except ValueError:
            pass
        else:
            if 0 <= idx < len(cfg):
                found_key = idx
                found_key_underscore = first_part
    else:
        raise ValueError("Invalid cfg")
    if found_key is None:
        raise ValueError("Cannot find {} in {}".format(key, self_path))
    if found_key_underscore == key:
        cfg[found_key] = value
    else:
        assert found_key_underscore is not None
        _assign_key(
            cfg[found_key],
            key[len(found_key_underscore)+1:],
            value,
            self_path + '_' + found_key_underscore
        )


TConfig = TypeVar('TConfig', bound=BaseModel)


def load_config(
        model_cls: Type[TConfig],
        config_file: str = DEFAULT_PATH,
        env_prefix: str = 'api_config_',
) -> TConfig:
    with open(config_file, 'r') as f:
        config = yaml.load(f, Loader=yaml.SafeLoader)
    # config = config_to_underscore(config)
    for env_key, env_val in os.environ.items():
        lower_key = env_key.lower()
        if lower_key.startswith(env_prefix):
            lower_key = lower_key[len(env_prefix):]

            _assign_key(
                config, lower_key, yaml.load(io.StringIO(env_val), Loader=yaml.SafeLoader), env_prefix[:-1]
            )
    return model_cls.validate(config)
