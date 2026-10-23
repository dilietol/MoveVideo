import os

# Maps an environment variable to the (section, key) of config.toml that it overrides.
# Secrets must be provided through the environment and must not be stored in config.toml.
ENV_OVERRIDES = {
    "QBITTORENT_USERNAME": ("QBittorent_Host", "username"),
    "QBITTORENT_PASSWORD": ("QBittorent_Host", "password"),
    "STASH_API_KEY": ("Stash_Host", "ApiKey"),
}


def apply_env_overrides(conf: dict) -> dict:
    """Override the values of the loaded configuration with the ones found in the environment.

    Only variables that are set and not empty are applied, so the value in config.toml
    is kept as a fallback. The same dictionary is returned for convenience.
    """
    for env_name, (section, key) in ENV_OVERRIDES.items():
        value = os.environ.get(env_name)
        if value:
            conf.setdefault(section, {})[key] = value
    return conf
