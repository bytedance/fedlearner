import unittest
import random
import math
from datetime import datetime, timedelta
from fedlearner.common.common import time_diff

LEN_8_FORMAT = '%Y%m%d'
LEN_14_FORMAT = '%Y%m%d%H%M%S'


class TestTimeDiff(unittest.TestCase):
    def test_diff(self):
        now = datetime.now()
        year_diff = 365 * 24 * 60 * 60
        for trial in range(5):
            delta_secs = random.randint(0, 30 * year_diff)
            lhs8 = now.strftime(LEN_8_FORMAT)
            lhs8_dt = datetime.strptime(lhs8, LEN_8_FORMAT)

            lhs14 = now.strftime(LEN_14_FORMAT)
            lhs14_dt = datetime.strptime(lhs14, LEN_14_FORMAT)
            lhs_ts = now.timestamp()

            b4 = now - timedelta(seconds=delta_secs)
            rhs8 = b4.strftime(LEN_8_FORMAT)
            rhs8_dt = datetime.strptime(rhs8, LEN_8_FORMAT)

            rhs14 = b4.strftime(LEN_14_FORMAT)
            rhs14_dt = datetime.strptime(rhs14, LEN_14_FORMAT)
            rhs_ts = b4.timestamp()

            for lhs in ((lhs8, lhs8_dt), (lhs14, lhs14_dt), (lhs_ts, now)):
                for rhs in ((rhs8, rhs8_dt), (rhs14, rhs14_dt), (rhs_ts, b4)):
                    self.assertEqual(
                        math.isclose(time_diff(lhs[0], rhs[0]),
                                     (lhs[1] - rhs[1]).total_seconds()),
                        True
                    )


if __name__ == '__main__':
    unittest.main()
