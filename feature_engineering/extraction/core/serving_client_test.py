from __future__ import print_function

import sys
import threading
import numpy
import tensorflow as tf
from tensorflow_serving.apis import predict_pb2, prediction_service_pb2_grpc
from serving_test.mnist_data import MnistData


class _ResultCounter(object):
    """Counter for the prediction results."""

    def __init__(self, num_tests, concurrency, batch_size):
        self._num_tests = num_tests
        self._concurrency = concurrency
        self._batch_size = batch_size
        self._error = 0
        self._done = 0
        self._active = 0
        self._condition = threading.Condition()

    def inc_error(self, num=1):
        with self._condition:
            self._error += num

    def inc_done(self):
        with self._condition:
            self._done += 1
            self._condition.notify()

    def dec_active(self):
        with self._condition:
            self._active -= 1
            self._condition.notify()

    def get_error_rate(self):
        with self._condition:
            while self._done != self._num_tests:
                self._condition.wait()
            return self._error / (float(self._num_tests) * self._batch_size)

    def throttle(self):
        with self._condition:
            while self._active == self._concurrency:
                self._condition.wait()
            self._active += 1


def _create_rpc_callback(label, result_counter):
    """Creates RPC callback function.

    Args:
      label: The correct label for the predicted example.
      result_counter: Counter for the prediction result.
    Returns:
      The callback function.
    """

    def _callback(result_future):
        """Callback function.

        Calculates the statistics for the prediction result.

        Args:
          result_future: Result future of the RPC.
        """
        exception = result_future.exception()
        if exception:
            result_counter.inc_error()
            print(exception)
        else:
            sys.stdout.write('.')
            sys.stdout.flush()
            response = numpy.array(
                result_future.result().outputs['scores'].float_val)
            prediction = numpy.argmax(response.reshape((16, -1)), axis=1)
            result_counter.inc_error(numpy.sum(prediction != label))
        result_counter.inc_done()
        result_counter.dec_active()

    return _callback


def do_inference(stub, concurrency, num_tests):
    test_data_set = MnistData()
    result_counter = _ResultCounter(num_tests, concurrency, batch_size=16)
    for _ in range(num_tests):
        request = predict_pb2.PredictRequest()
        request.model_spec.name = 'mnist'
        request.model_spec.signature_name = 'predict_images'
        image, label = test_data_set.test_batch()
        image = image.astype(numpy.float32, copy=False)
        request.inputs['images'].CopyFrom(
            tf.make_tensor_proto(image, shape=[16, image[0].size]))
        result_counter.throttle()
        result_future = stub.Predict.future(request, 5.0)  # 5 seconds
        result_future.add_done_callback(
            _create_rpc_callback(label, result_counter))
    return result_counter.get_error_rate()
