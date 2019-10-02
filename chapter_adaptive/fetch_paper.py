import os

import wget

url = "https://gitlab.kwant-project.org/qt/adaptive-paper/builds/artifacts/master/raw/paper.tex?job=make"
os.system(f"wget -O adaptive_full.tex  {url}")

with open("adaptive_full.tex") as f:
    add = False
    text = []
    for line in f.readlines():
        if add is False and r"\hypertarget{introduction}" in line:
            add = True
        if add is True and r"\section*{Acknowledgements}" in line:
            add = False
        if add:
            line = line.replace(r"\citep", r"\cite")
            line = line.replace(r"\(", r"$")
            line = line.replace(r"\)", r"$")
            line = line.replace(
                r"\includegraphics{figures/",
                r"\includegraphics{chapter_adaptive/figures/",
            )
            line = line.replace(r"\onlinecite{", r"\cite{")
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


os.system("rm -fr tmp* figures adaptive-paper-master-figures")
os.system(
    "wget -O tmp.zip https://gitlab.kwant-project.org/qt/adaptive-paper/-/archive/master/adaptive-paper-master.zip?path=figures"
)
os.system("unzip tmp.zip")
os.system("mv adaptive-paper-master-figures/figures .")
os.system("rm -fr adaptive-paper-master-figures")

fnames = {
    "paper.yaml": "adaptive.yaml",
    "paper.bib": "adaptive.bib",
    "not_on_crossref.bib": "not_on_crossref.bib",
}
for fname_old, fname_new in fnames.items():
    os.system(f"rm -fr {fname_old}")
    cmd = f"wget -O {fname_old} https://gitlab.kwant-project.org/qt/adaptive-paper/raw/master/{fname_old}?inline=false"
    print(cmd)
    os.system(cmd)
    os.rename(fname_old, fname_new)
