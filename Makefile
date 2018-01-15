ROOT ?= ${PWD}
ENV_DIR := $(shell pwd)/_env
PYTHON_BIN := $(shell which python)

DEB_COMPONENT := crest
DEB_MAJOR_VERSION ?= 1.0${DEB_VERSION_QUALIFIER}
DEB_NAMES := crest crest-prov
DEB_NAMES += homer homer-node
DEB_NAMES += homestead-prov
DEB_NAMES += homer-cassandra homestead-prov-cassandra


# As we plan to deploy on 64 bit systems, by default target 64 bit. Disable this to attempt to build on 32 bit
# Note we do not plan to support 32 bit going forward, so this may be removed in the future
X86_64_ONLY=1

.DEFAULT_GOAL = all

.PHONY: all
all: help
FLAKE8_INCLUDE_DIR = src/
BANDIT_EXCLUDE_LIST = .crest-wheelhouse,.homestead_prov-wheelhouse,.homer-wheelhouse,_env,telephus,debian,common,build-crest,build-homer,build-homestead_prov,src/metaswitch/crest/test,src/metaswitch/homer/test
COVERAGE_SRC_DIR = src
COVERAGE_SETUP_PY = setup_crest.py setup_homer.py setup_homestead_prov.py

# TODO This repository doesn't have full code coverage - it should. Some files
# are temporarily excluded from coverage to make it easier to detect future
# regressions. We should fix up the coverage when we can
COVERAGE_EXCL = "**/test/**,src/metaswitch/crest/api/DeferTimeout.py,src/metaswitch/crest/api/__init__.py,src/metaswitch/crest/api/base.py,src/metaswitch/crest/api/lastvaluecache.py,src/metaswitch/crest/api/passthrough.py,src/metaswitch/crest/api/statistics.py,src/metaswitch/crest/api/utils.py,src/metaswitch/crest/main.py,src/metaswitch/crest/settings.py,src/metaswitch/crest/tools/bulk_autocomplete.py,src/metaswitch/crest/tools/bulk_create.py,src/metaswitch/crest/tools/utils.py,src/metaswitch/homer/__init__.py,src/metaswitch/homer/routes.py,src/metaswitch/homestead_prov/__init__.py,src/metaswitch/homestead_prov/auth_vectors.py,src/metaswitch/homestead_prov/cache/cache.py,src/metaswitch/homestead_prov/cache/db.py,src/metaswitch/homestead_prov/cassandra.py,src/metaswitch/homestead_prov/provisioning/handlers/irs.py,src/metaswitch/homestead_prov/provisioning/handlers/private.py,src/metaswitch/homestead_prov/provisioning/handlers/public.py,src/metaswitch/homestead_prov/provisioning/handlers/service_profile.py,src/metaswitch/homestead_prov/provisioning/models.py,src/metaswitch/homestead_prov/resultcodes.py"

CLEAN_SRC_DIR = src

include build-infra/cw-deb.mk
include build-infra/python.mk
include mk/bulk-provision.mk

.PHONY: help
help:
	@cat docs/development.md


# Crest

# Add a target that builds the python-common wheel into the correct wheelhouse
crest_wheelhouse/.crest_build_common_wheel: $(shell find common/metaswitch -type f -not -name "*.pyc") crest_wheelhouse/.clean-wheels
	cd common && WHEELHOUSE=../crest_wheelhouse make build_common_wheel
	touch $@

# Add a target that builds the telephus wheel into the correct wheelhouse
crest_wheelhouse/.crest_build_telephus_wheel: $(shell find common/metaswitch -type f -not -name "*.pyc") crest_wheelhouse/.clean-wheels
	cd telephus && ${PYTHON} setup.py bdist_wheel -d ../crest_wheelhouse
	touch $@

# Add dependency to the install-wheels and wheelhouse-complete to ensure we've built
# python-common and telephus before we try to install them or consider the wheelhouse complete
${ENV_DIR}/.crest-install-wheels: crest_wheelhouse/.crest_build_common_wheel
crest_wheelhouse/.wheelhouse_complete: crest_wheelhouse/.crest_build_common_wheel

${ENV_DIR}/.crest-install-wheels: crest_wheelhouse/.crest_build_telephus_wheel
crest_wheelhouse/.wheelhouse_complete: crest_wheelhouse/.crest_build_telephus_wheel

# Set up the variables for crest
crest_SETUP = setup_crest.py
crest_REQUIREMENTS = crest-requirements.txt common/requirements.txt
crest_TEST_SETUP = setup_crest.py
crest_TEST_REQUIREMENTS = common/requirements-test.txt
crest_SOURCES = $(shell find src/metaswitch -type f -not -name "*.pyc") $(shell find common/metaswitch -type f -not -name "*.pyc")
crest_WHEELS = metaswitchcommon telephus

# Create targets using the common python_component macro
$(eval $(call python_component,crest))

# Homestead-Prov

# Set up the variables for homestead-prov
homestead_prov_SETUP = setup_homestead_prov.py
homestead_prov_REQUIREMENTS = homestead_prov-requirements.txt
homestead_prov_TEST_SETUP = setup_homestead_prov.py
homestead_prov_TEST_REQUIREMENTS = common/requirements-test.txt
homestead_prov_SOURCES = $(shell find src/metaswitch -type f -not -name "*.pyc")
homestead_prov_WHEELS = crest
homestead_prov_EXTRA_LINKS = crest_wheelhouse

# Force homestead-prov to depend on crest
${ENV_DIR}/.homestead_prov-install-wheels: ${ENV_DIR}/.crest-install-wheels
##${ENV_DIR}/.homestead_prov-install-wheels: ${ENV_DIR}/.crest-install-wheels

# Create targets using the common python_component macro
$(eval $(call python_component,homestead_prov))

# Homer

# Set up the variables for homer
homer_SETUP = setup_homer.py
homer_REQUIREMENTS = homer-requirements.txt
homer_TEST_SETUP = setup_homer.py
homer_TEST_REQUIREMENTS = common/requirements-test.txt
homer_SOURCES = $(shell find src/metaswitch -type f -not -name "*.pyc")
homer_WHEELS = crest
homer_EXTRA_LINKS = crest_wheelhouse

# Force homer to depend on crest
##${ENV_DIR}/.homer-install-wheels: ${ENV_DIR}/.crest-install-wheels
${ENV_DIR}/.homer-install-wheels: ${ENV_DIR}/.crest-install-wheels

# Create targets using the common python_component macro
$(eval $(call python_component,homer))

.PHONY: deb
deb: wheelhouses bulk-prov deb-only

.PHONY: clean
clean: envclean pyclean bulk-prov_clean

