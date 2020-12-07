TF_PATH=../../thirdparty/tensorflow

.PHONY: test unit-test protobuf

lint:
	pylint --rcfile ../../ci/pylintrc fedlearner_webconsole

protobuf:
	python -m grpc_tools.protoc -I protocols -I$(TF_PATH) \
		--python_out=. \
		--grpc_python_out=. \
		protocols/fedlearner_webconsole/proto/*.proto

UNIT_TEST_SCRIPTS := $(shell find test -type f -name "*_test.py")
UNIT_TESTS := $(UNIT_TEST_SCRIPTS:%.py=%.phony)

test/%.phony: test/%.py
	python $^

unit-test: $(UNIT_TESTS)

test: unit-test
