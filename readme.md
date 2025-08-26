# Universal Health Agent

A GitHub Pages site that aggregates **health & longevity evidence** (news, journals, preprints) and publishes a searchable UI with Topic / Discipline / Area filters. Also builds a **catalog** of Programs, Experts, and Institutions from permitted sources.

## Local Run
```bash
pip install -r requirements.txt
python app.py --query "longevity OR aging OR chronic disease treatment" --build-catalog
