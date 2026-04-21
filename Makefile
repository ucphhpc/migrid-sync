ifndef MIG_ENV
	MIG_ENV = 'local'
endif

ifndef PY
	PY = 3
endif

# TODO: enable on these dirs when ready, but just leave to dummy init for now
#LINT_ENFORCE_DIRS = ./bin ./mig/lib ./sbin ./tests
LINT_ENFORCE_DIRS = ./mig/__init__.py
LOCAL_PYTHON_BIN = './envhelp/lpython'

ifdef PYTHON_BIN
	LOCAL_PYTHON_BIN = $(PYTHON_BIN)
else
	PYTHON_BIN = './envhelp/python3'
endif

ifeq ($(ALLDEPS),1)
	REQS_PATH = ./recommended.txt
else
	REQS_PATH = ./requirements.txt
endif

info:
	@echo "Welcome to MiGrid"
	@echo
	@echo "The following should help you get started:"
	@echo
	@echo "'make test'      - run the test suite (default python 3)"
	@echo "'make test PYVER=X.Y' - run the test suite (python version X.Y)"
	@echo "'make unittest'  - execute tests locally for development"

.PHONY: fmt
fmt:
ifneq ($(MIG_ENV),'local')
	@echo "unavailable outside local development environment"
	@exit 1
endif
	@make format-python

# NOTE: black and isort use pyproject.toml to temporarily exclude a few paths
.PHONY: format-python
format-python:
	@$(LOCAL_PYTHON_BIN) -m black $(LINT_ENFORCE_DIRS)
	@$(LOCAL_PYTHON_BIN) -m isort $(LINT_ENFORCE_DIRS)

.PHONY: lint
lint:
ifneq ($(MIG_ENV),'local')
	@echo "unavailable outside local development environment"
	@exit 1
endif
	@make lint-python

# NOTE: black and isort use pyproject.toml to temporarily exclude a few paths
.PHONY: lint-python
lint-python:
	@$(LOCAL_PYTHON_BIN) -m black $(LINT_ENFORCE_DIRS) --check
	@$(LOCAL_PYTHON_BIN) -m isort $(LINT_ENFORCE_DIRS) --check-only

.PHONY: clean
clean:
	@rm -f ./envhelp/py3.imageid
	@rm -f ./envhelp/local.depends

.PHONY: distclean
distclean: clean
	@rm -rf ./envhelp/venv
	@rm -rf ./envhelp/output
	@rm -rf ./tests/__pycache__
	@rm -f ./tests/*.pyc

.PHONY: test
test: dependencies testconfig
	@$(PYTHON_BIN) -m unittest discover -s tests/

.PHONY: unittest
unittest: dependencies testconfig
	@$(LOCAL_PYTHON_BIN) -m unittest discover -s tests/

.PHONY: dependencies
dependencies: ./envhelp/venv/pyvenv.cfg ./envhelp/local.depends

.PHONY: testconfig
testconfig: ./envhelp/output/testconfs

./envhelp/output/testconfs:
	@./envhelp/makeconfig test --docker
	@./envhelp/makeconfig test

ifeq ($(MIG_ENV),'local')
./envhelp/local.depends: $(REQS_PATH) local-requirements.txt
else
./envhelp/local.depends: $(REQS_PATH)
endif
	@echo "installing dependencies from $(REQS_PATH)"
	@$(LOCAL_PYTHON_BIN) -m pip install -r $(REQS_PATH)
ifeq ($(MIG_ENV),'local')
	@echo ""
	@echo "installing development dependencies"
	@$(LOCAL_PYTHON_BIN) -m pip install -r local-requirements.txt
endif
	@touch ./envhelp/local.depends

./envhelp/venv/pyvenv.cfg:
	@echo "provisioning environment"
	@/usr/bin/env python3 -m venv ./envhelp/venv
	@rm -f ./envhelp/local.depends
	@echo "upgrading venv pip as required for some dependencies"
	@./envhelp/venv/bin/pip3 install --upgrade pip
