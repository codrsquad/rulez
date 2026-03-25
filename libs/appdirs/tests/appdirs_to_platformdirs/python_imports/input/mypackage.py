import appdirs
from appdirs import user_data_dir, user_cache_dir

DATA_DIR = user_data_dir('myapp', 'myorg')
CACHE_DIR = user_cache_dir('myapp')
