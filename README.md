# Bas Nijholt's Ph.D. thesis

See the compiled
* latest [dissertation](https://gitlab.kwant-project.org/qt/basnijholt/thesis-bas-nijholt/builds/artifacts/master/raw/dissertation.pdf?job=job)
* latest [propositions](https://gitlab.kwant-project.org/qt/basnijholt/thesis-bas-nijholt/builds/artifacts/master/file/propositions.pdf?job=job)


Automatic Docker builds [here](https://hub.docker.com/repository/docker/basnijholt/thesis).


## Instructions
Create (or update) `dissertation.bib` using
```bash
yaml2bib \
  --bib_fname "zigzag.bib" \
  --dois_yaml "zigzag.yaml" \
  --replacements_yaml "replacements.yaml" \
  --email "bas@nijho.lt" \
  --static_bib "not_on_crossref.bib"
```

Create `propositions.bib` using:
```bash
python create_propositions.py
```
