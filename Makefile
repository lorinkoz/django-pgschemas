# Makefile

CLONESCHEMA_FILE := https://raw.githubusercontent.com/denishpatel/pg-clone-schema/master/clone_schema.sql

.PHONY: test
test:
	poetry run pytest sandbox/tests --reuse-db

.PHONY: coverage
coverage:
	poetry run pytest --cov="django_pgschemas" sandbox/tests --reuse-db
	poetry run coverage html


.PHONY: types
types:
	poetry run mypy .

.PHONY: down
down:
	docker compose down

.PHONY: up
up:
	docker compose up --wait
	poetry run sandbox/manage.py migrate

.PHONY: docs
docs:
	poetry run mkdocs serve -a localhost:9005

.PHONY: update-clone-schema
update-clone-schema:
	curl ${CLONESCHEMA_FILE} | python -m gzip - > django_pgschemas/clone_schema.gz
