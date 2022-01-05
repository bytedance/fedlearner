import os
import time
import grpc
import collections
from . import fl_logging as logging

class LocalServicerContext(grpc.ServicerContext):
  def invocation_metadata(self):
    return ()

  def peer(self):
    return "local"

  def peer_identities(self):
    return None

  def peer_identity_key(self):
    return None

  def auth_context(self):
    return dict()

  def set_compression(self, compression):
    return grpc.Compression.NoCompression

  def send_initial_metadata(self, initial_metadata):
    pass

  def set_trailing_metadata(self, trailing_metadata):
    pass

  def abort(self, code, details):
    pass

  def abort_with_status(self, status):
    pass

  def set_code(self, code):
    pass

  def set_details(self, details):
    pass

  def disable_next_message_compression(self):
    pass

  def is_active(self):
    return True

  def time_remaining(self):
    return None

  def cancel(self):
    pass

  def add_callback(self, callback):
    pass


def call_with_retry(call, max_retry_times=None, retry_interval=1):
  retry_times = 0
  while True:
    try:
      retry_times += 1
      return call()
    except grpc.RpcError as e:
      if max_retry_times is None or retry_times < max_retry_times:
        logging.warning("grpc call error, status: %s"
                ", details: %s, wait %ds for retry",
                e.code(), e.details(), retry_interval)
        time.sleep(retry_interval)
      else:
        raise e


def remote_insecure_channel(address, options=None, compression=None):
  EGRESS_URL = os.getenv('EGRESS_URL', None)
  EGRESS_HOST = os.environ.get('EGRESS_HOST', None)
  EGRESS_DOMAIN = os.environ.get('EGRESS_DOMAIN', None)
  if not EGRESS_URL:
    return grpc.insecure_channel(address, options, compression)

  options = list(options) if options else list()
  default_authority = EGRESS_HOST or address
  options.append(('grpc.default_authority', default_authority))
  channel = grpc.insecure_channel(EGRESS_URL, options, compression)

  if EGRESS_DOMAIN:
    address = address + '.' + EGRESS_DOMAIN
    channel = grpc.intercept_channel(
        channel, add_metadata_interceptor({'x-host': address}))

  return channel


def add_metadata_interceptor(headers):
  if not isinstance(headers, dict):
    raise TypeError("headers must be a dict")
  headers = list(headers.items())

  def add_metadata_fn(client_call_details, request_iterator,
                  request_streaming, response_streaming):
      metadata = list(client_call_details.metadata or [])
      metadata.extend(headers)
      client_call_details = _ClientCallDetails(
          client_call_details.method,
          client_call_details.timeout,
          metadata,
          client_call_details.credentials)
      return client_call_details, request_iterator, None
  return _GenericClientInterceptor(add_metadata_fn)

class _ClientCallDetails(
        collections.namedtuple(
            '_ClientCallDetails',
            ('method', 'timeout', 'metadata', 'credentials')),
        grpc.ClientCallDetails):
    pass


class _GenericClientInterceptor(grpc.UnaryUnaryClientInterceptor,
                                grpc.UnaryStreamClientInterceptor,
                                grpc.StreamUnaryClientInterceptor,
                                grpc.StreamStreamClientInterceptor):
  def __init__(self, interceptor_function):
    self._fn = interceptor_function

  def intercept_unary_unary(self, continuation, client_call_details,
                            request):
    new_details, new_request_iterator, postprocess = self._fn(
        client_call_details, iter((request, )), False, False)
    response = continuation(new_details, next(new_request_iterator))
    return postprocess(response) if postprocess else response

  def intercept_unary_stream(self, continuation, client_call_details,
                             request):
    new_details, new_request_iterator, postprocess = self._fn(
        client_call_details, iter((request, )), False, True)
    response_it = continuation(new_details, next(new_request_iterator))
    return postprocess(response_it) if postprocess else response_it

  def intercept_stream_unary(self, continuation, client_call_details,
                             request_iterator):
    new_details, new_request_iterator, postprocess = self._fn(
        client_call_details, request_iterator, True, False)
    response = continuation(new_details, new_request_iterator)
    return postprocess(response) if postprocess else response

  def intercept_stream_stream(self, continuation, client_call_details,
                              request_iterator):
    new_details, new_request_iterator, postprocess = self._fn(
        client_call_details, request_iterator, True, True)
    response_it = continuation(new_details, new_request_iterator)
    return postprocess(response_it) if postprocess else response_it