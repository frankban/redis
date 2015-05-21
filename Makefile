# Copyright 2015 Canonical Ltd.
# Licensed under the GPLv3, see copyright file for details.

export JUJU_TEST_CHARM=redis
export JUJU_REPOSITORY=

# Override those values to run functional tests with a different environment
# or Juju series.
SERIES=trusty
JUJU_ENV=local

# Define system Debian dependencies: run "make sysdeps" to install them.
# Please keep them in alphabetical order.
SYSDEPS = charm-tools juju-core juju-local python-dev python-pip \
	python-virtualenv rsync

PYTHON = python
VENV = .venv
VENV_ACTIVATE = $(VENV)/bin/activate
NOSE = $(VENV)/bin/nosetests
PIP = $(VENV)/bin/pip
FTESTS=$(shell find -L tests -type f -executable | sort)

.DEFAULT_GOAL := setup

.PHONY: help
help:
	@echo -e 'Redis charm - list of make targets:\n'
	@echo 'make - Set up the development and testing environment.'
	@echo 'make test - Run tests (including unit and functional tests).'
	@echo 'make lint - Run linter and pep8.'
	@echo 'make check - Run all the tests and lint.'
	@echo 'make unittest - Run unit tests.'
	@echo 'make ftest - Run functional tests.'
	@echo 'make clean - Get rid of bytecode files and virtual envs.'
	@echo 'make deploy - Deploy the local copy of the charm.'

.PHONY: setup
setup: $(VENV_ACTIVATE)

.PHONY: sysdeps
sysdeps:
	sudo apt-get install --yes $(SYSDEPS)

$(VENV_ACTIVATE): test-requirements.pip
	virtualenv --distribute -p $(PYTHON) $(VENV)
	$(PIP) install -r test-requirements.pip || \
		(touch test-requirements.pip; exit 1)
	@touch $(VENV_ACTIVATE)

.PHONY: clean
clean:
	-$(RM) -rfv $(VENV) .coverage
	find . -name '*.pyc' -delete

.PHONY: check
check: lint test
	juju charm proof

.PHONY: lint
lint: setup
	@$(VENV)/bin/flake8 --show-source --exclude=$(VENV) \
		--filename *.py,install,generic-hook \
		hooks/ tests/ unit_tests/

.PHONY: deploy
deploy:
	@# The use of readlink below is required for OS X.
	@$(eval export JUJU_REPOSITORY:=$(shell mktemp -d `readlink -f /tmp`/temp.XXXX))
	@echo "JUJU_REPOSITORY is $(JUJU_REPOSITORY)"
	@# Setting up the Juju repository.
	@mkdir $(JUJU_REPOSITORY)/${SERIES}
	@rsync -a . $(JUJU_REPOSITORY)/${SERIES}/$(JUJU_TEST_CHARM) \
		--exclude .git --exclude .bzr --exclude tests --exclude unit_tests
	@# Deploying the charm.
	juju deploy local:${SERIES}/$(JUJU_TEST_CHARM) $(JUJU_SERVICE_NAME)

.PHONY: test
test: unittest ftest

.PHONY: ftest
ftest:
	juju bootstrap -e $(JUJU_ENV) --upload-tools
	@# Setting the path is required because internally amulet calls
	@# juju-deployer using subprocess.
	PATH="$(VENV)/bin:$(PATH)" $(NOSE) --verbosity 2 -s $(FTESTS)
	juju destroy-environment $(JUJU_ENV) -y

.PHONY: unittest
unittest: setup
	$(NOSE) --verbosity 2 -s -w unit_tests \
		--with-coverage --cover-package hooks --cover-erase
