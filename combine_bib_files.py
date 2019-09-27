import glob
import os

import requests
import yaml

def replace_key(key, bib_entry):
    start = "@article{"
    result = start + ",".join([key] + bib_entry[len(start) :].split(",")[1:])
    return result


def doi2bib(doi):
    """Return a bibTeX string of metadata for a given DOI."""
    url = "http://dx.doi.org/" + doi
    headers = {"accept": "application/x-bibtex"}
    r = requests.get(url, headers=headers)
    return r.text

bibs = [f for f in glob.glob("*/*yaml") if "tmp.yaml" not in f]
print(bibs)

mapping = {}
for fname in bibs:
    with open(fname) as f:
        mapping = {**mapping, **yaml.safe_load(f)}
mapping = dict(sorted(mapping.items()))


entries = [
    replace_key(key, doi2bib(d["doi"]))
    for key, d in mapping.items()
    if not d["by_hand"]
]


bib_files = glob.glob("chapter_*/not_on_crossref.bib")
with open("dissertation.bib", "w") as outfile:
    outfile.write("@preamble{ {\providecommand{\BIBYu}{Yu} } }\n\n")
    for fname in bib_files:
        outfile.write(f"\n% Below is from `{fname}` \n\n")
        with open(fname) as infile:
            outfile.write(infile.read())
    outfile.write("\n% Below is from all `yaml` files. \n\n")
    for e in entries:
        outfile.write(f"{e}\n\n")
