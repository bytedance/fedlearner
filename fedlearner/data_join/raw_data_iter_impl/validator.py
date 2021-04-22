import datetime

from fedlearner.data_join.common import ALLOWED_FIELDS


class Validator(object):
    def __init__(self):
        """
        input data validator

        :required: [['default_value', 'type', 'must']]
        :optional: same with required
        """
        self._required_fields = set()
        self._optional_fields = set()
        self._checkers = {}
        for key, field in ALLOWED_FIELDS.items():
            if field.must:
                self._required_fields.add(key)
            else:
                self._optional_fields.add(key)
            self._checkers[key] = [TypeChecker([field.type])]

    def check(self, record, num_field=None):
        fields = set(record.keys())
        if num_field and len(record) != num_field:
            raise ValueError("There is some field missed, wanted {}, got {}"
                             "".format(num_field, len(record)))
        for field in self._required_fields:
            if field not in fields:
                raise ValueError("Fields {} is needed".format(field))
        for key, value in record.items():
            if key in self._checkers:
                for checker in self._checkers[key]:
                    status, msg = checker.check(value)
                    if not status:
                        raise ValueError(
                            "Field {} validation failed, reason: {}"
                                .format(key, msg))


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
        if not passed:
            for t in [int, float]:
                try:
                    if t in self._wanted_types:
                        value = t(value)
                        passed = True
                        break
                except Exception:  # pylint: disable=broad-except
                    pass

        if not passed:
            return False, "wanted type {}, but got {}".format(
                self._wanted_types, type(value))
        return True, ""
