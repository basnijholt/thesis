#!/usr/bin/env python3
import yaml
from jinja2 import Environment, FileSystemLoader


env = Environment(loader=FileSystemLoader(""))
template = env.get_template("propositions.jinja2")

with open("propositions.yaml") as f:
    propositions = yaml.safe_load(f)

result = template.render(propositions=propositions)

with open("propositions.tex", "w") as f:
    f.write(result)
