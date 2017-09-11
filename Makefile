ROOT ?= ${PWD}
ENV_DIR := $(shell pwd)/_env
PYTHON := ${ENV_DIR}/bin/python
PIP := ${ENV_DIR}/bin/pip
FLAKE8 := ${ENV_DIR}/bin/flake8

PYTHON_BIN := $(shell which python)

DEB_COMPONENT := crest
DEB_MAJOR_VERSION ?= 1.0${DEB_VERSION_QUALIFIER}
DEB_NAMES := crest crest-prov
DEB_NAMES += homer homer-node
DEB_NAMES += homestead-prov
DEB_NAMES += homer-cassandra homestead-prov-cassandra

MAX_LINE_LENGTH ?= 99

# As we plan to deploy on 64 bit systems, by default target 64 bit. Disable this to attempt to build on 32 bit
# Note we do not plan to support 32 bit going forward, so this may be removed in the future
X86_64_ONLY=1

.DEFAULT_GOAL = all

.PHONY: all
all: help

.PHONY: help
help:
	@cat docs/development.md

.PHONY: test
test: setup_crest.py setup_homer.py setup_homestead_prov.py env
	PYTHONPATH=src:common ${ENV_DIR}/bin/python setup_crest.py test -v
	PYTHONPATH=src:common ${ENV_DIR}/bin/python setup_homer.py test -v
	PYTHONPATH=src:common ${ENV_DIR}/bin/python setup_homestead_prov.py test -v

${FLAKE8}: env
	${PIP} install flake8

${ENV_DIR}/bin/coverage: env
	${ENV_DIR}/bin/pip install coverage

verify: ${FLAKE8}
	${FLAKE8} --select=E10,E11,E9,F src/

style: ${FLAKE8}
	${FLAKE8} --select=E,W,C,N --max-line-length=100 src/

explain-style: ${FLAKE8}
	${FLAKE8} --select=E,W,C,N --show-pep8 --first --max-line-length=100 src/

# TODO This repository doesn't have full code coverage - it should. Some files
# are temporarily excluded from coverage to make it easier to detect future
# regressions. We should fix up the coverage when we can
EXTRA_COVERAGE=src/metaswitch/crest/api/DeferTimeout.py,src/metaswitch/crest/api/__init__.py,src/metaswitch/crest/api/base.py,src/metaswitch/crest/api/lastvaluecache.py,src/metaswitch/crest/api/passthrough.py,src/metaswitch/crest/api/statistics.py,src/metaswitch/crest/api/utils.py,src/metaswitch/crest/main.py,src/metaswitch/crest/settings.py,src/metaswitch/crest/tools/bulk_autocomplete.py,src/metaswitch/crest/tools/bulk_create.py,src/metaswitch/crest/tools/utils.py,src/metaswitch/homer/__init__.py,src/metaswitch/homer/routes.py,src/metaswitch/homestead_prov/__init__.py,src/metaswitch/homestead_prov/auth_vectors.py,src/metaswitch/homestead_prov/cache/cache.py,src/metaswitch/homestead_prov/cache/db.py,src/metaswitch/homestead_prov/cassandra.py,src/metaswitch/homestead_prov/provisioning/handlers/irs.py,src/metaswitch/homestead_prov/provisioning/handlers/private.py,src/metaswitch/homestead_prov/provisioning/handlers/public.py,src/metaswitch/homestead_prov/provisioning/handlers/service_profile.py,src/metaswitch/homestead_prov/provisioning/models.py,src/metaswitch/homestead_prov/resultcodes.py

.PHONY: coverage
coverage: ${ENV_DIR}/bin/coverage setup_crest.py setup_homer.py setup_homestead_prov.py
	rm -rf htmlcov/
	${ENV_DIR}/bin/coverage erase
	${ENV_DIR}/bin/coverage run --append --source src --omit "**/test/**,$(EXTRA_COVERAGE)" setup_crest.py test
	${ENV_DIR}/bin/coverage run --append --source src --omit "**/test/**,$(EXTRA_COVERAGE)" setup_homer.py test
	${ENV_DIR}/bin/coverage run --append --source src --omit "**/test/**,$(EXTRA_COVERAGE)" setup_homestead_prov.py test
	${ENV_DIR}/bin/coverage report -m --fail-under 100
	${ENV_DIR}/bin/coverage html

.PHONY: env
env: ${ENV_DIR}/.wheels_installed

$(ENV_DIR)/bin/python: setup_crest.py setup_homer.py setup_homestead_prov.py common/setup.py
	# Set up a fresh virtual environment
	virtualenv --setuptools --python=$(PYTHON_BIN) $(ENV_DIR)
	$(ENV_DIR)/bin/easy_install -U "setuptools==24"
	$(ENV_DIR)/bin/easy_install distribute

INSTALLER := ${ENV_DIR}/bin/pip install --compile \
                                        --no-index \
                                        --upgrade \
                                        --force-reinstall

CREST_REQS := -r crest-requirements.txt -r common/requirements.txt

${ENV_DIR}/.wheels_installed : $(ENV_DIR)/bin/python common/requirements.txt crest-requirements.txt homer-requirements.txt homestead_prov-requirements.txt $(shell find src/metaswitch -type f -not -name "*.pyc") $(shell find common/metaswitch -type f -not -name "*.pyc")

	rm -rf .crest-wheelhouse .homer-wheelhouse .homestead_prov-wheelhouse

	# Get crest's dependencies
	cd common && REQUIREMENTS=../crest-requirements.txt WHEELHOUSE=../.crest-wheelhouse make build_common_wheel
	cd telephus && ${PIP} wheel -w ../.crest-wheelhouse \
								-r ../crest-requirements.txt \
								-r ../common/requirements.txt \
								.

	# Generate wheels for crest
	${PYTHON} setup_crest.py bdist_wheel -d .crest-wheelhouse
	${PIP} wheel -w .crest-wheelhouse \
					${CREST_REQS} \
					--find-links .crest-wheelhouse

	# Generate wheels for homer
	${PYTHON} setup_homer.py bdist_wheel -d .homer-wheelhouse
	${PIP} wheel -w .homer-wheelhouse \
					-r homer-requirements.txt \
					--find-links .homer wheelhouse \

	# Generate wheels for homestead_prov
	${PYTHON} setup_homestead_prov.py bdist_wheel -d .homestead_prov-wheelhouse
	${PIP} wheel -w .homestead_prov-wheelhouse \
					-r homestead_prov-requirements.txt \
					--find-links .homestead_prov-wheelhouse

	# Install the wheels
	${INSTALLER} --find-links .crest-wheelhouse crest
	${INSTALLER} --find-links .crest-wheelhouse --find-links .homer-wheelhouse homer
	${INSTALLER} --find-links .crest-wheelhouse --find-links .homestead_prov-wheelhouse homestead_prov

	# Touch the sentinel file
	touch $@

BANDIT_EXCLUDE_LIST = .eggs,_env,telephus,debian,common,build-crest,build-homer,build-homestead_prov,src/metaswitch/crest/test,src/metaswitch/homer/test
include build-infra/cw-deb.mk
include build-infra/python.mk
include mk/bulk-provision.mk

.PHONY: deb
deb: env bulk-prov deb-only

.PHONY: clean
clean: envclean bulk-prov_clean pyclean

.PHONY: pyclean
pyclean:
	-find src -name \*.pyc -exec rm {} \;
	-rm -rf src/*.egg-info
	-rm -f .coverage
	-rm -rf htmlcov/

.PHONY: envclean
envclean:
	-rm -rf .crest-wheelhouse .homer-wheelhouse .homestead_prov-wheelhouse build-crest build-homer build-homestead_prov ${ENV_DIR}
