import glob

bib_files = glob.glob("chapter_*/*bib")
with open("dissertation.bib", "w") as outfile:
    outfile.write("@preamble{ {\providecommand{\BIBYu}{Yu} } }\n")
    for fname in bib_files:
        with open(fname) as infile:
            outfile.write(infile.read())

