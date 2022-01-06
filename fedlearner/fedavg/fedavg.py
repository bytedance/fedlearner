import os
import tensorflow as tf
from .master import LeaderMaster, FollowerMaster
from fedlearner.cluster.cluster_spec import FedClusterSpec


class MasterControlKerasCallback(tf.keras.callbacks.Callback):
  def __init__(self, master):
    self._master = master
    super().__init__()

  def on_train_end(self, logs):
    self._master.on_train_end()

  def on_train_batch_begin(self, batch, logs=None):
    self._master.on_train_batch_begin()

  def on_train_batch_end(self, batch, logs=None):
    self._master.on_train_batch_end()

def train_from_keras_model(model,
                           x=None,
                           y=None,
                           batch_size=None,
                           epochs=1,
                           fed_name=None,
                           fed_cluster=None,
                           steps_per_sync=None):

  if not fed_name:
    fed_name = os.getenv("FL_FED_NAME")
  if not fed_cluster:
    fed_cluster = os.getenv("FL_FED_CLUSTER")
  if not steps_per_sync:
    steps_per_sync = int(os.getenv("FL_STPES_PER_SYNC"))

  fed_cluster_spec = FedClusterSpec(fed_cluster)
  if fed_cluster_spec.is_leader(fed_name):
    master_class = LeaderMaster
  elif fed_cluster_spec.is_follower(fed_name):
    master_class = FollowerMaster
  else:
    raise ValueError("unknow fed_name: {}".format(fed_name))

  master = master_class(model, fed_name, fed_cluster_spec, steps_per_sync)
  master.start()
  model.fit(x, y, batch_size=batch_size, epochs=epochs, callbacks=[MasterControlKerasCallback(master)])

  master.wait()
