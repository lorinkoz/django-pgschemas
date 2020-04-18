# Makefile for django-pgschemas

.PHONY: test
test:
	poetry run coverage run dpgs_sandbox/manage.py test tests
