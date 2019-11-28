"""Convert a yaml file to bib."""

import contextlib
import functools
import glob
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Tuple

import diskcache
import requests
import yaml
from crossref.restful import Etiquette, Works
from tqdm import tqdm

works = Works(etiquette=Etiquette("publist", contact_email="basnijholt@gmail.com"))


def get_pages(data, works=works):
    try:
        page = data["article-number"]
    except KeyError:
        if "page" in data:
            page = data["page"].split("-")[0]
        else:
            raise Exception("No page number found!")
    return page


def get_journal(data, works=works):
    return data["container-title"][0], data["short-container-title"][0]


def cached_crossref(doi: str) -> str:
    """Look up if this has previously been called."""
    with diskcache.Cache("crossref.pickle") as cache:
        info = cache.get(doi)
        if info is not None:
            return info
        info = works.doi(doi)
        cache[doi] = info
        return info


def replace_key(
    key: str, data, bib_entry: str, replacements: List[Tuple[str, str]]
) -> str:
    bib_type, *_ = bib_entry.split("{")
    _, *rest = bib_entry.split(",")
    bib_context = ",".join(rest)
    # Now only modify `bib_context` because we don't want to touch the key.

    # XXX: I am not sure whether these substitutions are needed.
    # the problem seemed to be the utf-8 `requests.get` encoding.
    to_replace = [("ö", r"\"{o}"), ("ü", r"\"{u}"), ("ë", r"\"{e}"), ("ï", r"\"{i}")]

    for old, new in to_replace:
        bib_context = bib_context.replace(old.upper(), new.upper())
        bib_context = bib_context.replace(old.lower(), new.lower())

    to_replace += replacements

    with contextlib.suppress(Exception):
        # Use the journal abbrv. from crossref, not used if hard coded.
        to_replace.append(get_journal(data))

    for old, new in to_replace:
        bib_context = bib_context.replace(old, new)

    result = bib_type + "{" + key + "," + bib_context

    if "pages = {" not in result:
        # Add the page number if it's missing
        with contextlib.suppress(Exception):
            pages = get_pages(data)
            lines = result.split("\n")
            lines.insert(2, f"\tpages = {{{pages}}},")
            result = "\n".join(lines)

    return result


def doi2bib(doi: str) -> str:
    """Return a bibTeX string of metadata for a given DOI."""
    print(f"Requesting {doi}")
    url = "http://dx.doi.org/" + doi
    headers = {"accept": "application/x-bibtex"}
    r = requests.get(url, headers=headers)
    r.encoding = "utf-8"
    return r.text


def cached_doi2bib(doi: str) -> str:
    """Look up if this has previously been called."""
    with diskcache.Cache("bibs.pickle") as cache:
        text = cache.get(doi)
        if text is not None:
            return text
        text = doi2bib(doi)
        if text is not "" and "<html>" not in text:
            print(f"Succesfully got '{doi}'")
            cache[doi] = text
        return text


def combine_yamls(pathname: str) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for fname in glob.glob(pathname):
        with open(fname) as f:
            for k, v in yaml.safe_load(f).items():
                # Check that there are no duplicate keys with different DOIs.
                if k in mapping:
                    if v.lower() != mapping[k].lower():
                        msg = f"{k} exists for multiple DOIs: {v} and {mapping[k]}."
                        raise KeyError(msg)
                else:
                    mapping[k] = v

    dois = dict(sorted(mapping.items()))
    return dois


def parse_yaml(pathname: str) -> Dict[str, str]:
    if os.path.isfile(pathname):
        return yaml.safe_load(pathname)
    else:
        return combine_yamls(pathname)


def parse_replacements_yaml(fname: Optional[str]) -> List[Tuple[str, str]]:
    if fname is None:
        return []

    with open(fname) as f:
        d = yaml.safe_load(f)
    all_replacements = []
    for replacements in d.values():
        for k, v in replacements.items():
            all_replacements.append((k, v))
    return all_replacements


def write_output(entries: List[str], bib_files: List[str], bib_fname: str) -> None:
    with open(bib_fname, "w") as outfile:
        outfile.write("@preamble{ {\\providecommand{\\BIBYu}{Yu} } }\n\n")
        for fname in bib_files:
            outfile.write(f"\n% Below is from `{fname}`.\n\n")
            with open(fname) as infile:
                outfile.write(infile.read())
        outfile.write("\n% Below is from all `yaml` files.\n\n")
        for e in entries:
            for line in e.split("\n"):
                # Remove the url line
                if "url = {" not in line:
                    outfile.write(f"{line}\n")
            outfile.write("\n")


def static_bib_entries(pathname: str) -> List[str]:
    if os.path.isfile(pathname):
        return [pathname]
    else:
        return glob.glob(pathname)


def get_bib_entries(dois, replacements: List[Tuple[str, str]]):
    return [
        replace_key(
            key,
            data=cached_crossref(doi),
            bib_entry=cached_doi2bib(doi),
            replacements=replacements,
        )
        for key, doi in tqdm(dois.items())
    ]


if __name__ == "__main__":
    dois = parse_yaml("*/*yaml")
    replacements = parse_replacements_yaml("replacements.yaml")
    entries = get_bib_entries(dois, replacements)
    bib_files = static_bib_entries("chapter_*/not_on_crossref.bib")
    write_output(entries, bib_files, bib_fname="dissertation.bib")
