# Makefile for django-pgschemas

.PHONY: test
test:
	poetry run dpgs_sandbox/manage.py test tests


.PHONY: testall
testall:
	poetry run dpgs_sandbox/manage.py test tests --noinput
	poetry run dpgs_sandbox/manage.py test tests --noinput --keepdb -r
	poetry run dpgs_sandbox/manage.py test tests --noinput --keepdb
	poetry run dpgs_sandbox/manage.py test tests --noinput -r

.PHONY: coverage
coverage:
	poetry run coverage run dpgs_sandbox/manage.py test tests

.PHONY: coverage-html
coverage-html:
	poetry run coverage run dpgs_sandbox/manage.py test tests && poetry run coverage html

.PHONY: reqs
reqs:
	poetry export --without-hashes --dev --format requirements.txt > requirements.txt

.PHONY: update-clone-schema
update-clone-schema:
	curl https://raw.githubusercontent.com/denishpatel/pg-clone-schema/master/clone_schema.sql -o django_pgschemas/clone_schema.sql
