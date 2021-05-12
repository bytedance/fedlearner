export PYTHONPATH:=${PWD}:$(PYTHONPATH)

.PHONY: test unit-test protobuf

lint:
	pylint --rcfile ./ci/pylintrc --load-plugins pylint_quotes fedlearner_webconsole

protobuf:
	python -m grpc_tools.protoc -I protocols \
		--python_out=. \
		--grpc_python_out=. \
		--mypy_out=. \
		protocols/fedlearner_webconsole/proto/*.proto

UNIT_TEST_SCRIPTS := $(shell find test -type f -name "*_test.py")
UNIT_TESTS := $(UNIT_TEST_SCRIPTS:%.py=%.phony)

test/%.phony: test/%.py
	python $^

unit-test: protobuf $(UNIT_TESTS)

cli-test: 
	FLASK_APP=command:app flask routes

test: unit-test cli-test
	
clean:
	find ./ -type f \( -name "*.db" -o -name "*.log" \) -exec rm -f {} \;
