export PYTHONPATH:=${PWD}:$(PYTHONPATH)

.PHONY: test unit-test-all unit-test protobuf

lint:
	pylint --rcfile ./ci/pylintrc --load-plugins pylint_quotes fedlearner_webconsole

protobuf:
	python -m grpc_tools.protoc -I protocols \
		--python_out=. \
		--grpc_python_out=. \
		--mypy_out=. \
		protocols/fedlearner_webconsole/proto/*.proto

UNIT_TEST_SCRIPTS := $(shell find test/ -type f -name "*_test.py")
UNIT_TEST_SCRIPTS_REGEX := $(shell find test/$(FOLDER) -type f -name "$(REG)*.py")
UNIT_TESTS := $(UNIT_TEST_SCRIPTS:%.py=%.phony)
UNIT_TESTS_REGEX := $(UNIT_TEST_SCRIPTS_REGEX:%.py=%.phony)

test/%.phony: test/%.py
	python $^

unit-test-all: protobuf $(UNIT_TESTS)

# run unit test with optional $FOLDER and $REG parameter to limit the number of
# running tests.
# Sample: make unit-test FOLDER="/fedlearner_webconsole/utils" REG="file*"
unit-test: protobuf $(UNIT_TESTS_REGEX)

cli-test:
   FLASK_APP=command:app flask routes

test: unit-test-all cli-test

clean:
	find ./ -type f \( -name "*.db" -o -name "*.log" \) -exec rm -f {} \;
