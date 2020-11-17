import grpc
import argparse
import numpy as np
import tensorflow as tf
from flask import Flask
from flask_restful import reqparse, abort, Api, Resource
from google.protobuf.json_format import MessageToJson
from tensorflow_serving.apis import prediction_service_pb2_grpc, model_service_pb2_grpc,\
    predict_pb2, get_model_status_pb2, get_model_metadata_pb2
# from core.build_session import build_session
from core.serving_client_test import do_inference
tf_const = tf.compat.v1.saved_model.signature_constants

app = Flask(__name__)
api = Api(app)


def dump_numpy_array():
    return np.random.random((1, 28, 28))


def _assign_version_to_request(req, version):
    if version is not None:
        if str(version).isdigit():
            req.model_spec.version.value = int(version)
        else:
            req.model_spec.version_label = str(version)
# Session should be pre-built by scripts and assigned here.
# sess = build_session()
#
#
# class SessResult(Resource):
#     def get(self):
#         run_args = result_parser.parse_args()
#         feature_name = run_args['feature_name']
#         persistent = run_args['persistent']
#         try:
#             result = sess.run(feature_name)
#         except Exception as e:
#             abort(404, message='Error/Exception encountered: {}'.format(repr(e)))
#             return
#         return result, 201
#
#
# api.add_resource(SessResult, '/session_result')


class MnistServingTest(Resource):
    def get(self):
        err_rate = do_inference(serving_stub, 1, 500)
        return err_rate, 201


api.add_resource(MnistServingTest, '/mnist-test')


class PredictionTest(Resource):
    def get(self, model_name, version=None):
        _request = predict_pb2.PredictRequest()
        _request.model_spec.name = str(model_name)
        _request.model_spec.signature_name = 'predict_images'
        _assign_version_to_request(_request, version)
        data = dump_numpy_array().astype(np.float32, copy=False).reshape(-1)
        send_data = tf.make_tensor_proto(data)
        _request.inputs['images'].CopyFrom(send_data)
        response = serving_stub.Predict(_request, 5)
        return MessageToJson(response), 201


api.add_resource(PredictionTest, '/predict/<string:model_name>', endpoint='test_predict_latest')
api.add_resource(PredictionTest, '/predict/<string:model_name>/<version>', endpoint='test_predict_specific')


class Extraction(Resource):
    def get(self, feature_to_extract, model_name, version=None, signature_name='predict'):
        _request = predict_pb2.PredictRequest()
        _request.model_spec.name = str(model_name)
        _request.model_spec.signature_name = signature_name
        _assign_version_to_request(_request, version)
        # random data here, should use feature_to_extract to determine what feature to be extracted and transmitted
        data = dump_numpy_array().astype(np.float32, copy=False).reshape(-1)
        send_data = tf.make_tensor_proto(data)
        _request.inputs['images'].CopyFrom(send_data)
        response = serving_stub.Predict(_request, 5)
        return MessageToJson(response), 201


api.add_resource(Extraction,
                 '/extraction/<feature_to_extract>/<string:model_name>',
                 endpoint='extraction_default')
api.add_resource(Extraction,
                 '/extraction/<feature_to_extract>/<string:model_name>/<version>',
                 endpoint='extraction_specific')
api.add_resource(Extraction,
                 '/extraction/<feature_to_extract>/<string:model_name>/<version>/<signature_name>',
                 endpoint='extraction_signature')


class ModelStatus(Resource):
    def get(self, model_name, version=None):
        _request = get_model_status_pb2.GetModelStatusRequest()
        _request.model_spec.name = str(model_name)
        _assign_version_to_request(_request, version)
        response = model_status_stub.GetModelStatus(_request)
        return MessageToJson(response), 201


api.add_resource(ModelStatus, '/model-status/<string:model_name>', endpoint='model_status_all')
api.add_resource(ModelStatus, '/model-status/<string:model_name>/<version>', endpoint='model_status_specific')


class ModelMeta(Resource):
    def get(self, model_name, version=None):
        _request = get_model_metadata_pb2.GetModelMetadataRequest()
        _request.model_spec.name = str(model_name)
        _assign_version_to_request(_request, version)
        _request.metadata_field.append('signature_def')
        response = serving_stub.GetModelMetadata(_request)
        return MessageToJson(response), 201


api.add_resource(ModelStatus, '/model-meta/<string:model_name>', endpoint='model_meta_latest')
api.add_resource(ModelStatus, '/model-meta/<string:model_name>/<version>', endpoint='model_meta_specific')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--serving_hostport',
                        type=str,
                        help='Host:port to serving_test server.')
    args = parser.parse_args()

    channel = grpc.insecure_channel(args.serving_hostport)
    serving_stub = prediction_service_pb2_grpc.PredictionServiceStub(channel)
    model_status_stub = model_service_pb2_grpc.ModelServiceStub(channel)
    app.run()
