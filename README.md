# Bas Nijholt's Ph.D. thesis

See the compiled
* latest [dissertation](https://gitlab.kwant-project.org/qt/basnijholt/thesis-bas-nijholt/builds/artifacts/master/raw/dissertation.pdf?job=job)
* latest [propositions](https://gitlab.kwant-project.org/qt/basnijholt/thesis-bas-nijholt/builds/artifacts/master/file/propositions.pdf?job=job)


Automatic Docker builds [here](https://hub.docker.com/repository/docker/basnijholt/thesis).


## Instructions
Create (or update) `dissertation.bib` using
```bash
yaml2bib \
  --bib_fname "dissertation.bib" \
  --dois_yaml "*/*.yaml" \
  --replacements_yaml "replacements.yaml" \
  --static_bib "chapter_*/not_on_crossref.bib" \
  --email "bas@nijho.lt"
```

Create `propositions.bib` using:
```bash
python create_propositions.py
```
