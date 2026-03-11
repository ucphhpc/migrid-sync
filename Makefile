ifndef MIG_ENV
	MIG_ENV = 'local'
endif

ifndef PY
	PY = 3
endif

FORMAT_ENFORCE_DIRS = ./bin ./mig/lib ./sbin ./tests
FORMAT_EXCLUDE_REGEX = '.git|tests/data/|tests/fixture/|bin/checkconf.py|bin/createresource.py|bin/notifypassword.py|sbin/grid\_ftps.py|sbin/grid\_openid.py|sbin/grid\_sftp.py|sbin/grid\_webdavs.py'
FORMAT_LINE_LENGTH = 80
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
	@echo "'make PYVER=X.Y' - run the test suite (python version X.Y)"
	@echo "'make unittest'  - execute tests locally for development"

.PHONY: fmt
fmt:
ifneq ($(MIG_ENV),'local')
	@echo "unavailable outside local development environment"
	@exit 1
endif
	@make format-python

.PHONY:format-python
format-python:
	@$(LOCAL_PYTHON_BIN) -m black $(FORMAT_ENFORCE_DIRS) \
			--line-length=$(FORMAT_LINE_LENGTH) \
			--exclude=$(FORMAT_EXCLUDE_REGEX)
	@$(LOCAL_PYTHON_BIN) -m isort $(FORMAT_ENFORCE_DIRS) \
			--profile=black \
			--line-length=$(FORMAT_LINE_LENGTH)

.PHONY: lint
lint:
ifneq ($(MIG_ENV),'local')
	@echo "unavailable outside local development environment"
	@exit 1
endif
	@make lint-python

.PHONY: lint-python
lint-python:
	@$(LOCAL_PYTHON_BIN) -m black $(FORMAT_ENFORCE_DIRS) \
			--check \
			--line-length=$(FORMAT_LINE_LENGTH) \
			--exclude $(FORMAT_EXCLUDE_REGEX)
	@$(LOCAL_PYTHON_BIN) -m isort $(FORMAT_ENFORCE_DIRS) \
			--check-only \
			--profile=black \
			--line-length=$(FORMAT_LINE_LENGTH) \
			--skip-glob=$(FORMAT_EXCLUDE_GLOB)

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
