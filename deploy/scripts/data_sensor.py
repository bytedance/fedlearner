import os
import sys
from time import sleep

import tensorflow as tf


def check_file_exist_infinity(input_file):
    while True:
        if tf.io.gfile.exists(input_file):
            break
        print('{} does not exist, sleep 10s...'.format(input_file))
        sleep(10)
    print('{} is ok'.format(input_file))


def main():
    input_dir = os.getenv('INPUT_PATH')
    check_success = int(os.getenv('CHECK_SUCCESS', '1'))
    if not input_dir:
        print("Input dir is not set")
        sys.exit(1)

    if check_success:
        input_dir = os.path.join(input_dir, '_SUCCESS')

    check_file_exist_infinity(input_dir)


if __name__ == "__main__":
    main()
