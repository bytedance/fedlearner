export PYTHONPATH:=${PWD}:$(PYTHONPATH)

.PHONY: test unit-test protobuf

lint:
	pylint --rcfile ../../ci/pylintrc fedlearner_webconsole

protobuf:
	python -m grpc_tools.protoc -I protocols \
		--python_out=. \
		--grpc_python_out=. \
		protocols/fedlearner_webconsole/proto/*.proto

UNIT_TEST_SCRIPTS := $(shell find test -type f -name "*_test.py")
UNIT_TESTS := $(UNIT_TEST_SCRIPTS:%.py=%.phony)

test/%.phony: test/%.py
	python $^

unit-test: protobuf $(UNIT_TESTS)

test: unit-test
