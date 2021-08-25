import logging
import os
import random
import re
import traceback

import tensorflow.compat.v1 as tf

from fedlearner.data_join.common import ALLOWED_FIELDS, \
    convert_tf_example_to_dict


class Validator(object):
    def __init__(self, sample_ratio=0):
        """
        input data validator

        :required: [['default_value', 'type', 'must']]
        :optional: same with required
        """
        self._sample_ratio = sample_ratio
        self._required_fields = set()
        self._optional_fields = set()
        self._checkers = {}
        for key, field in ALLOWED_FIELDS.items():
            if field.must:
                self._required_fields.add(key)
            else:
                self._optional_fields.add(key)
            self._checkers[key] = [TypeChecker([field.type])]

    def _check(self, record):
        fields = set(record.keys())
        for field in self._required_fields:
            if field not in fields:
                logging.error("Fields %s is needed", field)
                return False
        for key, value in record.items():
            if key in self._checkers:
                for checker in self._checkers[key]:
                    status, msg = checker.check(value)
                    if not status:
                        logging.info(
                            "Field %s validation failed, reason: %s", key, msg)
                        return False
        return True

    def check_tfrecord(self, raw_data):
        if random.random() < self._sample_ratio:
            try:
                example = tf.train.Example()
                example.ParseFromString(raw_data)
                org_dict = \
                    convert_tf_example_to_dict(example)
                example_dict = {}
                for key, val in org_dict.items():
                    example_dict[key] = val[0] if len(val) == 1 else val
                if not self._check(example_dict):
                    return False
            except Exception as e:  # pylint: disable=broad-except
                logging.error(
                    "Failed parse tf.Example from record %s, reason %s",
                    raw_data, e)
                return False
        return True

    @staticmethod
    def check_csv_header(headers):
        for header in headers:
            if not re.match("^[A-Za-z0-9_-]*$", header):
                logging.fatal("Illegal character in %s (csv header)",
                              header)
                traceback.print_stack()
                os._exit(-1)  # pylint: disable=protected-access

    def check_csv_record(self, record, num_field=None):
        if random.random() < self._sample_ratio:
            if num_field and len(record) != num_field:
                logging.error("There is some field missed, wanted %d, got %d",
                              num_field, len(record))
                return False
            if not self._check(record):
                return False
        return True


class Checker(object):
    def check(self, value):
        raise NotImplementedError


class TypeChecker(Checker):
    def __init__(self, wanted_types):
        self._wanted_types = []
        for t in wanted_types:
            if t == int:
                self._wanted_types.append(int)
            elif t == float:
                self._wanted_types.append(int)  # backward compatibility
                self._wanted_types.append(float)
            elif t in (str, bytes):
                self._wanted_types.append(str)
                self._wanted_types.append(bytes)

        self._wanted_types = tuple(self._wanted_types)

    def check(self, value):
        passed = isinstance(value, self._wanted_types)
        if not passed and isinstance(value, (str, bytes)):
            for t in self._wanted_types:
                if t not in [int, float]:
                    continue
                try:
                    value = t(value)
                    passed = True
                    break
                except Exception:  # pylint: disable=broad-except
                    pass

        if not passed:
            return False, "wanted type {}, but got {}".format(
                self._wanted_types, type(value))
        return True, ""
