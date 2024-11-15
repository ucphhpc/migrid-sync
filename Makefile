ifndef MIG_ENV
	MIG_ENV = 'local'
endif

ifndef PY
	PY = 3
endif

LOCAL_PYTHON_BIN = './envhelp/lpython'

ifdef PYTHON_BIN
	LOCAL_PYTHON_BIN = $(PYTHON_BIN)
else ifeq ($(PY),2)
	PYTHON_BIN = './envhelp/python2'
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
	@echo "'make PY=2 test' - run the test suite (default python 2)"
	@echo "'make unittest'  - execute tests locally for development"

.PHONY: fmt
fmt:
ifneq ($(MIG_ENV),'local')
	@echo "unavailable outside local development environment"
	@exit 1
endif
	$(LOCAL_PYTHON_BIN) -m autopep8 --ignore E402 -i

.PHONY: clean
clean:
	@rm -f ./envhelp/py2.imageid
	@rm -f ./envhelp/py3.imageid
	@rm -f ./envhelp/local.depends

.PHONY: distclean
distclean: clean
	@rm -rf ./envhelp/venv
	@rm -rf ./envhelp/output
	@rm -rf ./tests/__pycache__
	@rm -f ./tests/*.pyc

.PHONY: lint
lint:
# ifneq ($(PY),'XXX')
# 	@echo "linting is currently restricted to a lowest common denomiator of PY2"
# 	@exit 1
# endif
	@./envhelp/python2 -m flake8 . --exclude=tests,state,envhelp,fixture,output,unittest,grsfs-fuse,irclib.py,seafile-seahub_settings-template.py --count --select=E9,F63,F7,F82 --show-source --statistics

.PHONY: test
test: dependencies testconfig
	@$(PYTHON_BIN) -m unittest discover -s tests/

.PHONY: unittest
unittest: dependencies testconfig
	@$(LOCAL_PYTHON_BIN) -m unittest discover -s tests/

.PHONY: dependencies
ifeq ($(PY),2)
dependencies: ./envhelp/local.depends
else
dependencies: ./envhelp/venv/pyvenv.cfg ./envhelp/local.depends
endif

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
