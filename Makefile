.PHONY:	dist test validate format apidoc html doc browse publish_test

dist:
	rm -rf dist/*
	python -m build
	rm -rf src/encab.egg-info

test:
	python -m unittest discover -v -s tests/unit -p '*_test.py'

validate:
	mypy --config-file mypy.ini -p encab_gelf -p tests
	ruff check src/ tests/

audit:
	pip-audit -r requirements.txt

format:
	black src/encab_gelf/*.py src/encab_gelf/gelf/*.py tests/unit/*.py

publish_test: dist
	twine upload -r testpypi dist/*

publish: dist
	twine upload --repository pypi dist/*

tox:
	tox -p
