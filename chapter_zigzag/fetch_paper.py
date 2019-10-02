import os
import shutil

folder = "../../two_dim_majoranas/paper/"
for old, new in (
    ("zigzag.yaml", "zigzag.yaml"),
    ("zigzag.tex", "zigzag_full.tex"),
    ("not_on_crossref.bib", "not_on_crossref.bib"),
):
    shutil.copyfile(os.path.join(folder, old), new)

start = r"\section{Introduction}"
end = r"\end{document}"

to_replace = [
    (r"\citep", r"\cite"),
    (r"\comment", r"\co"),
    (r"\(", r"$"),
    (r"\)", r"$"),
    (r"\bibliographystyle{apsrev4-1}", r"\bibliographystyle{apsrev4-1}"),
    (r"\bibliography{zigzag}", r"\bibliography{zigzag}"),
    (r"\references{dissertation}", r"\references{dissertation}"),
    (r"{figures/", r"{chapter_zigzag/figures/"),
    (r"\onlinecite{", r"\cite{"),
    (r"\bibliography{zigzag}", ""),
    (r"\bibliographystyle{apsrev4-1}", ""),
    (r"\appendix", "\section{Appendix}")
]

with open("zigzag_full.tex") as f:
    add = False
    text = []
    for line in f.readlines():
        if add is False and start in line:
            add = True
        if add is True and end in line:
            add = False
        if add:
            for old, new in to_replace:
                line = line.replace(old, new)
            text.append(line)

text = "".join(text)

tex = (
    r"""\chapter{Enhanced proximity effect in zigzag-shaped Majorana Josephson junctions.}
\label{ch:zigzag}

%% Start the actual chapter on a new page.
\newpage
\noindent

"""
    + text
    + r"\references{dissertation}"
)

with open("zigzag.tex", "w") as f:
    f.writelines(tex)

old, new = (os.path.join(folder, "figures"), os.path.abspath("figures"))
os.system(f"rm -fr {new}; cp -r {old} {new}")
