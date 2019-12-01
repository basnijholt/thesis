import sys

import yaml

fname = sys.argv[1]
with open(fname) as f:
    d = yaml.safe_load(f)

with open(fname, "w") as f:
    yaml.dump(d, f, sort_keys=True)
