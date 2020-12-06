TF_PATH=../../thirdparty/tensorflow

.PHONY: test unit-test integration-test protobuf

lint:
	pylint --rcfile ../../ci/pylintrc fedlearner_webconsole

protobuf:
	python -m grpc_tools.protoc -I protocols -I$(TF_PATH) \
		--python_out=. \
		--grpc_python_out=. \
		protocols/fedlearner_webconsole/proto/*.proto

INTEGRATION_TEST_SCRIPTS := $(shell find test -type f -name "test_*.py")
INTEGRATION_TESTS := $(INTEGRATION_TEST_SCRIPTS:%.py=%.phony)

test/%.phony: test/%.py
	python $^

unit-test: protobuf
	python -m unittest discover -s fedlearner_webconsole -p '*_test.py'

integration-test: $(INTEGRATION_TESTS)

test: unit-test integration-test
