ifeq ($(PY),2)
	PYTHON_BIN = './envhelp/python2'
else
	PYTHON_BIN = './envhelp/venv/bin/python3'
endif

info:
	@echo "Welcome to MiGrid"
	@echo
	@echo "The following should help you get started:"
	@echo
	@echo "'make test'      - run the test suite"
	@echo "'make PY=2 test' - run the test suite (python 2)"

.PHONY: clean
clean:
	@rm -f ./envhelp/py2.imageid
	@rm -f ./envhelp/py3.depends

.PHONY: distclean
distclean: clean
	@rm -rf ./envhelp/venv
	@rm -rf ./tests/__pycache__

.PHONY: test
test: dependencies
	@$(PYTHON_BIN) -m unittest discover -s tests/

.PHONY: dependencies
dependencies: ./envhelp/venv/pyvenv.cfg ./envhelp/py3.depends

./envhelp/py3.depends: requirements.txt
	@rm -f ./envhelp/py3.depends
	@echo "installing dependencies"
	@./envhelp/venv/bin/pip3 install -r requirements.txt
	@touch ./envhelp/py3.depends

./envhelp/venv/pyvenv.cfg:
	@echo "provisioning environment"
	@/usr/bin/env python3 -m venv ./envhelp/venv
	@rm -f ./envhelp/py3.depends
