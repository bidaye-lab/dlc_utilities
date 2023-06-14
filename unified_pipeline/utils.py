import yaml

def load_config(path: str):
    """Load config yml as dict.

    Parameters
    ----------
    path: str
        Path to config yml file

    Returns
    -------
    config: dict
        dictionary 
    """

    with open(path, 'r') as f:
        cfg = yaml.safe_load(f)


    return cfg