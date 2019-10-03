import os
import shutil

folder = "../../adaptive-paper/"
for old, new in (
    ("paper.yaml", "adaptive.yaml"),
    ("paper.tex", "adaptive_full.tex"),
    ("not_on_crossref.bib", "not_on_crossref.bib"),
):
    shutil.copyfile(os.path.join(folder, old), new)

start = r"\section{Introduction}"
end = r"\section*{Acknowledgements}"

to_replace = [
    (r"\citep", r"\cite"),
    (r"\(", r"$"),
    (r"\)", r"$"),
    (r"\includegraphics{figures/", r"\includegraphics{chapter_adaptive/figures/"),
    (r"\onlinecite{", r"\cite{"),
    (r"\paragraph", r"\co"),
]

with open("adaptive_full.tex") as f:
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
    r"""\chapter{Adaptive, tools for adaptive parallel sampling of mathematical functions}
\label{ch:adaptive}

%% Start the actual chapter on a new page.
\newpage
\noindent
"""
    + text
    + r"\references{dissertation}"
)

with open("adaptive.tex", "w") as f:
    f.writelines(tex)

old, new = (os.path.join(folder, "figures"), os.path.abspath("figures"))
os.system(f"rm -fr {new}; cp -r {old} {new}")
