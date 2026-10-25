import os

# Maps an environment variable to the (section, key) of config.toml that it overrides.
# Secrets must be provided through the environment and must not be stored in config.toml.
ENV_OVERRIDES = {
    "QBITTORENT_USERNAME": ("QBittorent_Host", "username", "admin"),
    "QBITTORENT_PASSWORD": ("QBittorent_Host", "password", None),
    "STASH_API_KEY": ("Stash_Host", "ApiKey", None),
}


def apply_env_overrides(conf: dict) -> dict:
    """Override the values of the loaded configuration with the ones found in the environment.

    Environment variables override config.toml values. If not set, defaults are applied.
    Returns the same dictionary for convenience.
    """
    for env_name, (section, key, default) in ENV_OVERRIDES.items():
        value = os.environ.get(env_name)
        if value:
            conf.setdefault(section, {})[key] = value
        elif default is not None:
            conf.setdefault(section, {})[key] = default
    return conf
