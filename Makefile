# Makefile

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
	poetry run mkdocs build

.PHONY: update-clone-schema
update-clone-schema:
	curl https://raw.githubusercontent.com/denishpatel/pg-clone-schema/master/clone_schema.sql -o django_pgschemas/clone_schema.sql
