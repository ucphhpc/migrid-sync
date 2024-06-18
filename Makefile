ifndef MIG_ENV
	MIG_ENV = 'local'
endif
ifeq ($(PY),2)
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
	@echo "'make test'      - run the test suite"
	@echo "'make PY=2 test' - run the test suite (python 2)"

.PHONY: fmt
fmt:
ifneq ($(MIG_ENV),'local')
	@echo "unavailable outside local development environment"
	@exit 1
endif
	$(PYTHON_BIN) -m autopep8 --ignore E402 -i

.PHONY: clean
clean:
	@rm -f ./envhelp/py2.imageid
	@rm -f ./envhelp/py3.depends

.PHONY: distclean
distclean: clean
	@rm -rf ./envhelp/venv
	@rm -rf ./tests/__pycache__
	@rm -f ./tests/*.pyc

.PHONY: test
test: dependencies
	@$(PYTHON_BIN) -m unittest discover -s tests/

.PHONY: dependencies
dependencies: ./envhelp/venv/pyvenv.cfg ./envhelp/py3.depends

ifeq ($(MIG_ENV),'local')
./envhelp/py3.depends: $(REQS_PATH) local-requirements.txt
else
./envhelp/py3.depends: $(REQS_PATH)
endif
	@rm -f ./envhelp/py3.depends
	@echo "installing dependencies from $(REQS_PATH)"
	@./envhelp/venv/bin/pip3 install -r $(REQS_PATH)
ifeq ($(MIG_ENV),'local')
	@echo ""
	@echo "installing development dependencies"
	@./envhelp/venv/bin/pip3 install -r local-requirements.txt
endif
	@touch ./envhelp/py3.depends

./envhelp/venv/pyvenv.cfg:
	@echo "provisioning environment"
	@/usr/bin/env python3 -m venv ./envhelp/venv
	@rm -f ./envhelp/py3.depends
