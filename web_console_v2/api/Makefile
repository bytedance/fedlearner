.PHONY: test unit-test

lint:
	pylint --rcfile ../../ci/pylintrc fedlearner_webconsole

UNIT_TEST_SCRIPTS := $(shell find test -type f -name "test_*.py")
UNIT_TESTS := $(UNIT_TEST_SCRIPTS:%.py=%.phony)

test/%.phony: test/%.py
	python $^

unit-test: $(UNIT_TESTS)

test: unit-test
