#!/usr/bin/env python3
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

CROSSREF_DATABASE = "crossref.pickle"
DOI2BIB_DATABASE = "bibs.pickle"

works = Works(etiquette=Etiquette("publist", contact_email="basnijholt@gmail.com"))


def pages_from_crossref(data, works=works):
    try:
        page = data["article-number"]
    except KeyError:
        if "page" in data:
            page = data["page"].split("-")[0]
        else:
            raise Exception("No page number found!")
    return page


def journal_from_crossref(data, works=works):
    return data["container-title"][0], data["short-container-title"][0]


def cached_crossref(doi: str) -> str:
    """Look up if this has previously been called."""
    with diskcache.Cache(CROSSREF_DATABASE) as cache:
        info = cache.get(doi)
        if info is not None:
            return info
        info = works.doi(doi)
        cache[doi] = info
        return info


def replace_special_letters(x):
    # XXX: I am not sure whether these substitutions are needed.
    # the problem seemed to be the utf-8 `requests.get` encoding.
    to_replace = [("ö", r"\"{o}"), ("ü", r"\"{u}"), ("ë", r"\"{e}"), ("ï", r"\"{i}")]

    for old, new in to_replace:
        x = x.replace(old, new)
        x = x.replace(old.upper(), new.upper())

    return x


def replace_key(
    key: str, data, bib_entry: str, replacements: List[Tuple[str, str]]
) -> str:
    bib_type = bib_entry.split("{")[0]
    bib_context = bib_entry.split(",", maxsplit=1)[1]
    # Now only modify `bib_context` because we don't want to touch the key.

    bib_context = replace_special_letters(bib_context)

    to_replace = replacements.copy()

    with contextlib.suppress(Exception):
        # Use the journal abbrv. from crossref, not used if hard coded.
        to_replace.append(journal_from_crossref(data))

    for old, new in to_replace:
        bib_context = bib_context.replace(old, new)

    result = bib_type + "{" + key + "," + bib_context

    if "pages = {" not in result:
        # Add the page number if it's missing
        with contextlib.suppress(Exception):
            pages = pages_from_crossref(data)
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
    with diskcache.Cache(DOI2BIB_DATABASE) as cache:
        text = cache.get(doi)
        if text is not None:
            return text
        text = doi2bib(doi)
        if text != "" and "<html>" not in text:
            print(f"Succesfully got '{doi}' 🎉")
            cache[doi] = text
        else:
            print(f"Failed on '{doi}' 😢")
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


def parse_doi_yaml(fname: str) -> Dict[str, str]:
    if os.path.isfile(fname):
        with open(fname) as f:
            return yaml.safe_load(f)
    else:
        return combine_yamls(fname)


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
                # Remove the url line because LaTeX creates it from the DOI
                if "url = {" not in line:
                    outfile.write(f"{line}\n")
            outfile.write("\n")


def static_bib_entries(pathname: str) -> List[str]:
    if os.path.isfile(pathname):
        return [pathname]
    else:
        return glob.glob(pathname)


def get_bib_entries(dois: Dict[str, str], replacements: List[Tuple[str, str]]):
    return [
        replace_key(
            key,
            data=cached_crossref(doi),
            bib_entry=cached_doi2bib(doi),
            replacements=replacements,
        )
        for key, doi in tqdm(dois.items())
    ]


def main(bib_fname, dois_yaml, replacements_yaml, static_bib):
    dois = parse_doi_yaml(dois_yaml)
    replacements = parse_replacements_yaml(replacements_yaml)
    entries = get_bib_entries(dois, replacements)
    bib_files = static_bib_entries(static_bib)
    write_output(entries, bib_files, bib_fname)


if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser(description="Process some integers.")
    parser.add_argument(
        "--bib_fname",
        default="dissertation.bib",
        help="output file (default: 'dissertation.bib')",
    )
    parser.add_argument(
        "--dois_yaml",
        default="*/*.yaml",
        help="`key: doi` yaml, may contain wildcards (*) (default: '*/*.yaml')",
    )
    parser.add_argument(
        "--replacements_yaml",
        default="replacements.yaml",
        help="replacements to perform, might be None (default: 'replacements.yaml')",
    )
    parser.add_argument(
        "--static_bib",
        default="chapter_*/not_on_crossref.bib",
        help="static bib entries, may contain wildcards (*) (default: 'chapter_*/not_on_crossref.bib')",
    )

    args = parser.parse_args()

    main(
        bib_fname=args.bib_fname,
        dois_yaml=args.dois_yaml,
        replacements_yaml=args.replacements_yaml,
        static_bib=args.static_bib,
    )
