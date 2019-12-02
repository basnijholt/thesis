all: pdf

.ONESHELL:

.PHONY: force-build
force-build:

pdf: force-build
	pdflatex dissertation
	bibtex chapter_introduction/introduction
	bibtex chapter_adaptive/adaptive
	bibtex chapter_orbitalfield/orbitalfield
	bibtex chapter_supercurrent/supercurrent
	bibtex chapter_spinorbit/spinorbit
	bibtex chapter_zigzag/zigzag
	bibtex chapter_weakantilocalization/weakantilocalization
	bibtex chapter_shortjunction/shortjunction
	pdflatex dissertation
	pdflatex dissertation

propositions: force-build
	pdflatex propositions

introduction: force-build
	pdflatex dissertation
	bibtex chapter_introduction/introduction
	pdflatex dissertation
	pdflatex dissertation

adaptive: force-build
	pdflatex dissertation
	bibtex chapter_adaptive/adaptive
	pdflatex dissertation
	pdflatex dissertation

orbitalfield: force-build
	pdflatex dissertation
	bibtex chapter_orbitalfield/orbitalfield
	pdflatex dissertation
	pdflatex dissertation

supercurrent: force-build
	pdflatex dissertation
	bibtex chapter_supercurrent/supercurrent
	pdflatex dissertation
	pdflatex dissertation

spinorbit: force-build
	pdflatex dissertation
	bibtex chapter_spinorbit/spinorbit
	pdflatex dissertation
	pdflatex dissertation

zigzag: force-build
	pdflatex dissertation
	bibtex chapter_zigzag/zigzag
	pdflatex dissertation
	pdflatex dissertation

weakantilocalization: force-build
	pdflatex dissertation
	bibtex chapter_weakantilocalization/weakantilocalization
	pdflatex dissertation
	pdflatex dissertation

shortjunction: force-build
	pdflatex dissertation
	bibtex chapter_shortjunction/shortjunction
	pdflatex dissertation
	pdflatex dissertation

clean:
	find . -name "*.aux" -type f -delete
	find . -name "*.bbl" -type f -delete
	find . -name "*.blg" -type f -delete
	find . -name "*.log" -type f -delete
	find . -name "*.out" -type f -delete
	find . -name "*.toc" -type f -delete
	find . -name "*.gz" -type f -delete
