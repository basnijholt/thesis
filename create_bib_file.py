import functools
import glob
import os
from concurrent.futures import ThreadPoolExecutor

import requests
import yaml


def replace_key(key, bib_entry):
    start = "@article{"
    result = start + ",".join([key] + bib_entry[len(start) :].split(",")[1:])

    # XXX: I am not sure whether these substitutions are needed.
    # the problem seemed to be the utf-8 `requests.get` encoding.
    to_replace = [("ö", r"\"{o}"), ("ü", r"\"{u}"), ("ë", r"\"{e}"), ("ï", r"\"{i}") ]
    for old, new in to_replace:
        result = result.replace(old.upper(), new.upper())
        result = result.replace(old.lower(), new.lower())

    print(result, "\n")
    return result


@functools.lru_cache()
def doi2bib(doi):
    """Return a bibTeX string of metadata for a given DOI."""
    url = "http://dx.doi.org/" + doi
    headers = {"accept": "application/x-bibtex"}
    r = requests.get(url, headers=headers)
    r.encoding = "utf-8"
    return r.text


bibs = [f for f in glob.glob("*/*yaml") if "tmp.yaml" not in f]
print("Reading: ", bibs)

mapping = {}
for fname in bibs:
    with open(fname) as f:
        mapping = {**mapping, **yaml.safe_load(f)}
mapping = dict(sorted(mapping.items()))


dois = {key: d["doi"] for key, d in mapping.items() if not d["by_hand"]}
with ThreadPoolExecutor() as ex:
    futs = ex.map(doi2bib, dois.values())
    bibs = list(futs)


entries = [replace_key(key, bib) for key, bib in zip(dois.keys(), bibs)]


bib_files = glob.glob("chapter_*/not_on_crossref.bib")
with open("dissertation.bib", "w") as outfile:
    outfile.write("@preamble{ {\\providecommand{\\BIBYu}{Yu} } }\n\n")
    for fname in bib_files:
        outfile.write(f"\n% Below is from `{fname}`.\n\n")
        with open(fname) as infile:
            outfile.write(infile.read())
    outfile.write("\n% Below is from all `yaml` files.\n\n")
    for e in entries:
        outfile.write(f"{e}\n\n")
