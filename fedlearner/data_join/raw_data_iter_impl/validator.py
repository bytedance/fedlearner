import datetime
import re


class Validator(object):
    def __init__(self, required, optional=None):
        """
        input data validator

        :required: { "field": type(int), "field1": date_format(%Y%m%d)}
        :optional: same with required
        """
        if optional is None:
            optional = {}
        self._required_fields = set()
        self._optional_fields = set()
        self._checkers = {}
        for key, rule in required.items():
            self._required_fields.add(key)
            self._checkers[key] = CheckerManager.get_checker(rule)
        for key, rule in optional.items():
            self._optional_fields.add(key)
            self._checkers[key] = CheckerManager.get_checker(rule)

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
            if t == 'int':
                self._wanted_types.append(int)
            elif t == 'float':
                self._wanted_types.append(int)  # backward compatibility
                self._wanted_types.append(float)
            elif t == 'str':
                self._wanted_types.append(str)
                self._wanted_types.append(bytes)
        self._wanted_types = tuple(self._wanted_types)

    @staticmethod
    def re_pattern():
        return r'type\((.*?)\)'

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


class DateFormatChecker(Checker):
    def __init__(self, str_formats):
        self._format = str_formats[0]

    @staticmethod
    def re_pattern():
        return r'datetime\((.*?)\)'

    def check(self, value):
        try:
            datetime.datetime.strptime(value, self._format)
            return True, ""
        except Exception:  # pylint: disable=broad-except
            return False, "Incorrect date string format, " \
                          "should be {}, but got {}".format(self._format, value)


class CheckerManager(object):
    @staticmethod
    def get_checker(rule):
        patterns = {
            TypeChecker.re_pattern(): TypeChecker,
            DateFormatChecker.re_pattern(): DateFormatChecker
        }
        checkers = []
        for pattern, cls in patterns.items():
            res = re.findall(pattern, rule)
            if res:
                checkers.append(cls(res))
        return checkers
