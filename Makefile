ENV_DIR := $(shell pwd)/_env
PYTHON_BIN := $(shell which python)

DEB_COMPONENT := homer
DEB_MAJOR_VERSION := 1.0
DEB_NAMES := homer homestead

# As we plan to deploy on 64 bit systems, by default target 64 bit. Disable this to attempt to build on 32 bit
# Note we do not plan to support 32 bit going forward, so this may be removed in the future
X86_64_ONLY=1

.DEFAULT_GOAL = all

.PHONY: all
all: help

.PHONY: help
help:
	@cat README.md

.PHONY: run
run: bin/python setup.py
	PYTHONPATH=src bash -c 'bin/python src/metaswitch/crest/main.py'

.PHONY: test
test: bin/python setup.py
	bin/python setup.py test

.PHONY: coverage
coverage: bin/coverage setup.py
	# Explictly force use of bin/python so we load the correct python modules
	rm -rf htmlcov/
	bin/python bin/coverage erase
	bin/python bin/coverage run --source src --omit "src/metaswitch/**/test/**"  setup.py test
	bin/python bin/coverage report -m
	bin/python bin/coverage html

.PHONY: env
env: bin/python

bin/python bin/coverage: bin/buildout buildout.cfg
ifeq ($(X86_64_ONLY),1)
	ARCHFLAGS="-arch x86_64" ./bin/buildout -N
else
	ARCHFLAGS="-arch i386 -arch x86_64" ./bin/buildout -N
endif
	${ENV_DIR}/bin/easy_install -zmaxd eggs/ zc.buildout

bin/buildout: $(ENV_DIR)/bin/python
	mkdir -p .buildout_downloads/dist
	cp thrift_download/thrift-0.8.0.tar.gz .buildout_downloads/dist/
	$(ENV_DIR)/bin/easy_install "setuptools>0.7"
	$(ENV_DIR)/bin/easy_install zc.buildout
	mkdir -p bin/
	ln -s $(ENV_DIR)/bin/buildout bin/

$(ENV_DIR)/bin/python:
	virtualenv --no-site-packages --setuptools --python=$(PYTHON_BIN) $(ENV_DIR)

include build-infra/cw-deb.mk

.PHONY: deb
deb: env deb-only

.PHONY: clean
clean: envclean pyclean

.PHONY: pyclean
pyclean:
	find src -name \*.pyc -exec rm -f {} \;
	rm -rf src/*.egg-info dist
	rm -f .coverage
	rm -rf htmlcov/

.PHONY: envclean
envclean:
	rm -rf bin eggs develop-eggs parts .installed.cfg bootstrap.py .downloads .buildout_downloads
	rm -rf distribute-*.tar.gz
	rm -rf $(ENV_DIR)

