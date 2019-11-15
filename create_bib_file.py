import contextlib
import functools
import glob
import os
from concurrent.futures import ThreadPoolExecutor

import diskcache
import requests
import yaml
from crossref.restful import Etiquette, Works
from tqdm import tqdm

bibs = [f for f in glob.glob("*/*yaml") if "tmp.yaml" not in f]
bib_files = glob.glob("chapter_*/not_on_crossref.bib")
output = "dissertation.bib"

works = Works(etiquette=Etiquette("publist", contact_email="basnijholt@gmail.com"))

TO_REPLACE = [
    (r"a{\r}", r"\r{a}"),  # "Nyga{\r}rd" -> "Nyg\r{a}rd", bug in doi.org
    ("Josephson", "{J}osephson"),
    ("Majorana", "{M}ajorana"),
    ("Andreev", "{A}ndreev"),
    ("Kramers", "{K}ramers"),
    ("Kitaev", "{K}itaev"),
    (
        r"metastable0and$\uppi$states",
        r"metastable $0$ and $\pi$ states",
    ),  # fix for 10.1103/physrevb.63.214512
    (
        r"Land{\'{e}}{gFactors}",
        r"Land{\'{e}} {$g$} Factors",
    ),  # fix for PhysRevLett.96.026804
    (
        r"apx$\mathplus$ipysuperconductor",
        r"a $p_x + i p_y$ superconductor",
    ),  # fix for 10.1103/physrevb.73.220502
    (
        r"apx$\mathplus${ipySuperfluid}",
        r"$p_x + i p_y$ superfluid",
    ),  # fix for 10.1103/physrevlett.98.010506
]


JOURNALS = [
    ("Advanced Materials", "Adv. Mater."),
    ("Annals of Physics", "Ann. Phys."),
    ("Applied Physics Letters", "Appl. Phys. Lett."),
    ("JETP Lett", "JETP Lett."),
    ("Journal de Physique", "J. Phys."),
    ("Journal of Computational Physics", "J. Comput. Phys."),
    ("Journal of Experimental and Theoretical Physics", "J. Exp. Theor. Phys."),
    ("Journal of Low Temperature Physics", "J. Low Temp. Phys."),
    ("Journal of Physics A: Mathematical and Theoretical", "J. Phys. A: Math. Theor."),
    ("Journal of Physics: Condensed Matter", "J. Phys.: Condens. Matter"),
    ("Nano Letters", "Nano Lett."),
    ("Nature Communications", "Nat. Commun."),
    ("Nature Materials", "Nat. Mater."),
    ("Nature Nanotechnology", "Nat. Nanotechnol."),
    ("Nature Physics", "Nat. Phys."),
    ("New Journal of Physics", "New J. Phys."),
    ("Physical Review B", "Phys. Rev. B"),
    ("Physical Review Letters", "Phys. Rev. Lett."),
    ("Physical Review X", "Phys. Rev. X"),
    ("Physical Review", "Phys. Rev."),  # should be before the above subs
    ("Physics-Uspekhi", "Phys. Usp."),
    ("Reports on Progress in Physics", "Rep. Prog. Phys."),
    ("Review of Scientific Instruments", "Rev. Sci. Instrum."),
    ("Reviews of Modern Physics", "Rev. Mod. Phys."),
    ("Science Advances", "Sci. Adv."),
    ("Scientific Reports", "Sci. Rep."),
    ("Semiconductor Science and Technology", "Semicond. Sci. Technol."),
    ("Annual Review of Condensed Matter Physics", "Annu. Rev. Condens. Matter Phys."),
    ("{EPL} (Europhysics Letters)", "{EPL}"),
    ("Nature Reviews Materials", "Nat. Rev. Mater."),
    ("Physics Letters", "Phys. Lett."),
    ("The European Physical Journal B", "Eur. Phys. J. B"),
    ("{SIAM} Journal on Numerical Analysis", "{SIAM} J. Numer. Anal."),
    ("{AIP} Conference Proceedings", "{AIP} Conf. Proc."),
]


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


def cached_crossref(doi):
    """Look up if this has previously been called."""
    with diskcache.Cache("crossref.pickle") as cache:
        info = cache.get(doi)
        if info is not None:
            return info
        info = works.doi(doi)
        cache[doi] = info
        return info


def replace_key(key, data, bib_entry):
    bib_type, *_ = bib_entry.split("{")
    _, *rest = bib_entry.split(",")
    rest = ",".join(rest)
    # Now only modify `rest` because we don't want to touch the key.

    # XXX: I am not sure whether these substitutions are needed.
    # the problem seemed to be the utf-8 `requests.get` encoding.
    to_replace = [("ö", r"\"{o}"), ("ü", r"\"{u}"), ("ë", r"\"{e}"), ("ï", r"\"{i}")]

    for old, new in to_replace:
        rest = rest.replace(old.upper(), new.upper())
        rest = rest.replace(old.lower(), new.lower())

    to_replace += TO_REPLACE + JOURNALS  # hard coded abbrvs

    with contextlib.suppress(Exception):
        # Use the journal abbrv. from crossref, not used if hard coded.
        to_replace.append(get_journal(data))

    for old, new in to_replace:
        rest = rest.replace(old, new)

    result = bib_type + "{" + key + "," + rest

    if "pages = {" not in result:
        # Add the page number if it's missing
        with contextlib.suppress(Exception):
            pages = get_pages(data)
            lines = result.split("\n")
            lines.insert(2, f"\tpages = {{{pages}}},")
            result = "\n".join(lines)

    return result


def doi2bib(doi):
    """Return a bibTeX string of metadata for a given DOI."""
    print(f"Requesting {doi}")
    url = "http://dx.doi.org/" + doi
    headers = {"accept": "application/x-bibtex"}
    r = requests.get(url, headers=headers)
    r.encoding = "utf-8"
    return r.text


def cached_doi2bib(doi):
    """Look up if this has previously been called."""
    with diskcache.Cache("bibs.pickle") as cache:
        text = cache.get(doi)
        if text is not None:
            return text
        text = doi2bib(doi)
        if text is not "" and "<html>" not in text:
            print(f"Succesfully got {doi}!create_bib_file.py")
            cache[doi] = text
        return text


if __name__ == "__main__":
    print("Reading: ", bibs)

    mapping = {}
    for fname in bibs:
        with open(fname) as f:
            mapping = {**mapping, **yaml.safe_load(f)}
    dois = dict(sorted(mapping.items()))

    entries = [
        replace_key(key, data=cached_crossref(doi), bib_entry=cached_doi2bib(doi))
        for key, doi in tqdm(dois.items())
    ]

    with open(output, "w") as outfile:
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
