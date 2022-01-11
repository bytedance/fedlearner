

import json

from google.protobuf import json_format
from .cluster_pb2 import FLClusterDef


class FLClusterSpec():
  def __init__(self, cluster):
    if isinstance(cluster, FLClusterSpec):
      self._cluster_def = FLClusterDef()
      self._cluster_def.CopyFrom(cluster.as_cluster_def())
    elif isinstance(cluster, dict):
      self._cluster_def = json_format.Parse(json.dumps(cluster), FLClusterDef())
    elif isinstance(cluster, str):
      self._cluster_def = json_format.Parse(cluster, FLClusterDef()) 
    else:
      raise TypeError("'cluster' must be a FederatedClusterSpec, or dict, or a str of json")

    self._check_and_load() 

  def _check_and_load(self):
    if not self._cluster_def.leader:
      raise ValueError("leader not found")

    self._leader = self._cluster_def.leader
    if not self._leader.name:
      raise ValueError("leader name not found")
    if not self._leader.address:
      raise ValueError("leader address not found")

    self._follower_mapping = {}
    for f in self._cluster_def.followers:
      if not f.name:
        raise ValueError("follower name not found")
      if f.name == self._leader.name:
        raise ValueError("ambiguity follower and leader: {}".format(f.name))
      if f.name in self._follower_mapping:
        raise ValueError("duplicated follower: {}".format(f.name))
      self._follower_mapping[f.name] = f

  def as_cluster_def(self):
    return self._cluster_def

  def as_json(self):
    return json_format.MessageToJson(self._cluster_def)

  @property
  def leader(self):
    return self._leader

  @property
  def followers(self):
    return list(self._cluster_def.followers)

  def follower(self, name: str):
    return self._follower_mapping.get(name, None)

  def is_leader(self, name: str):
    return self._leader.name == name

  def is_follower(self, name: str):
    return name in self._follower_mapping