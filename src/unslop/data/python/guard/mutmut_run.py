import json
import os
import sys

import mutmut.configuration as configuration

settings = json.loads(os.environ["UNSLOP_MUTMUT"])
configuration._config_reader = lambda: lambda key, default: settings.get(key, default)

from mutmut.__main__ import cli

sys.argv = ["mutmut", *sys.argv[1:]]
cli()
