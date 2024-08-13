# Copyright 2023 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from typing import Dict, Union
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.orm import Session
from fedlearner_webconsole.utils.flask_utils import get_current_user
from fedlearner_webconsole.utils.pp_yaml import compile_yaml_template,\
    add_username_in_label, GenerateDictService

CONFIG_MAP_TEMPLATE = """{
  "apiVersion": "v1",
  "kind": "ConfigMap",
  "metadata": {
    "name": self.name + "-config"
  },
  "data": {
    "config.pb": "model_config_list {\\n  config {\\n    name: '" + self.name + "'\\n    base_path: '" + model.base_path + "'\\n    model_platform: 'tensorflow'\\n  }\\n}\\n"
  }
}"""

DEPLOYMENT_TEMPLATE = """{
  "apiVersion": "apps/v1",
  "kind": "Deployment",
  "metadata": {
    "name": self.name,
    "labels": system.variables.labels,
    "annotations":  {
      "queue": "fedlearner",
      "schedulerName": "batch",
      "min-member": "1",
      "resource-cpu": str(self.resource.resource.cpu),
      "resource-mem": str(self.resource.resource.memory),
    },
  },
  "spec": {
    "selector": {
      "matchLabels": {
        "app": self.name
      }
    },
    "replicas": int(self.resource.replicas),
    "template": {
      "metadata": {
        "labels": {
          "app": self.name
        }
      },
      "spec": {
        "volumes": [
          {
            "name": self.name+ "-config",
            "configMap": {
              "name": self.name + "-config"
            }
          }
        ] + list(system.variables.volumes_list),
        "containers": [
          {
            "name": self.name,
            "image": system.variables.serving_image,
            "resources": {
              "limits": dict(self.resource.resource)
            },
            "args": [
              "--port=8500",
              "--rest_api_port=8501",
              "--model_config_file=/app/config/config.pb"
            ],
            "env": system.basic_envs_list,
            "ports": [
              {
                "containerPort": 8500,
                "name": "grpc",
              },
              {
                "containerPort": 8501,
                "name": "restful",
              }
            ],
            "volumeMounts": [
              {
                "name": self.name + "-config",
                "mountPath": "/app/config/"
              }
            ] + list(system.variables.volume_mounts_list)
          }
        ]
      }
    }
  }
}"""

SERVICE_TEMPLATE = """{
  "apiVersion": "v1",
  "kind": "Service",
  "metadata": {
    "name": self.name
  },
  "spec": {
    "selector": {
      "app": self.name
    },
    "ports": [
      {
        "port": 8501,
        "targetPort": "restful",
        "name": "restful",
      },
      {
        "port": 8500,
        "targetPort": "grpc",
        "name": "grpc",
      }
    ]
  }
}"""


def generate_self_dict(serving: Union[Dict, DeclarativeMeta]) -> Dict:
    if not isinstance(serving, dict):
        serving = serving.to_dict()
    return serving


def generate_model_dict(model: Union[Dict, DeclarativeMeta]) -> Dict:
    if not isinstance(model, dict):
        model = model.to_dict()
    return model


def generate_serving_yaml(serving: Dict[str, Union[Dict, DeclarativeMeta]], yaml_template: str,
                          session: Session) -> Dict:
    result_dict = compile_yaml_template(
        yaml_template,
        post_processors=[
            lambda loaded_json: add_username_in_label(loaded_json, getattr(get_current_user(), 'username', None))
        ],
        system=GenerateDictService(session).generate_system_dict(),
        model=generate_model_dict(serving['model']),
        self=generate_self_dict(serving['serving']))
    return result_dict
