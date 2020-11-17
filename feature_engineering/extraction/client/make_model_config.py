from tensorflow_serving.config import model_server_config_pb2 as cfg_pb
from google.protobuf import text_format

cfg1 = cfg_pb.ModelConfig()
cfg1.name = 'mnist'
cfg1.base_path = '/models/mnist'
cfg1.model_platform = 'tensorflow'
cfg1.version_labels['stable'] = 23
cfg1.version_labels['canary'] = 24
cfg1.model_version_policy.specific.versions[:] = [23, 24]
cfg2 = cfg_pb.ModelConfig()
cfg2.name = 'mnist2'
cfg2.base_path = '/models/mnist2'
cfg2.model_platform = 'tensorflow'
cfg2.model_version_policy.specific.versions[:] = [2, 3]
cfg_list = cfg_pb.ModelConfigList(config=[cfg1, cfg2])
model_server_cfg = cfg_pb.ModelServerConfig(model_config_list=cfg_list)
text = text_format.MessageToString(model_server_cfg)
with open('./config_pb.txt', 'w') as f:
    f.write(text)
