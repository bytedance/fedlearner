# Copyright 2020 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# coding: utf-8
# pylint: disable=protected-access

import time

from tensorflow.python.client import session
from tensorflow.python.framework.versions import VERSION
from tensorflow.python.platform import tf_logging as logging
from tensorflow.python.training import checkpoint_management, session_manager


assert VERSION.startswith("1.15."), "Monkey patch is only valid for TF 1.15."


def new_restore_checkpoint(self,
                           master,
                           saver=None,
                           checkpoint_dir=None,
                           checkpoint_filename_with_path=None,
                           wait_for_checkpoint=False,
                           max_wait_secs=7200,
                           config=None):
    """Creates a `Session`, and tries to restore a checkpoint if needed.

    Args:
        master: `String` representation of the TensorFlow master to use.
        saver: A `Saver` object used to restore a model.
        checkpoint_dir: Path to the checkpoint files. The latest checkpoint
            in the dir will be used to restore.
        checkpoint_filename_with_path: Full file name path to the checkpoint
            file.
        wait_for_checkpoint: Whether to wait for checkpoint to become
            available.
        max_wait_secs: Maximum time to wait for checkpoints to become
            available.
        config: Optional `ConfigProto` proto used to configure the session.

    Returns:
        A pair (sess, is_restored) where 'is_restored' is `True` if the
        session could be restored, `False` otherwise.

    Raises:
        ValueError: If both checkpoint_dir and checkpoint_filename_with_path
            are set.
    """
    self._target = master

    sess = session.Session(self._target, graph=self._graph, config=config)
    if checkpoint_dir and checkpoint_filename_with_path:
        raise ValueError("Can not provide both checkpoint_dir and "
                         "checkpoint_filename_with_path.")

    # If variables & resources in PS has beed initialized, do not recover.
    is_ready_for_local_init, _ = self._model_ready_for_local_init(sess)
    if is_ready_for_local_init:
        return sess, True

    # If either saver or checkpoint_* is not specified, cannot restore. Just
    # return.
    if not saver or not (checkpoint_dir or checkpoint_filename_with_path):
        return sess, False

    if checkpoint_filename_with_path:
        saver.restore(sess, checkpoint_filename_with_path)
        return sess, True

    # Waits up until max_wait_secs for checkpoint to become available.
    wait_time = 0
    ckpt = checkpoint_management.get_checkpoint_state(checkpoint_dir)
    while not ckpt or not ckpt.model_checkpoint_path:
        if wait_for_checkpoint and wait_time < max_wait_secs:
            logging.info("Waiting for checkpoint to be available.")
            time.sleep(self._recovery_wait_secs)
            wait_time += self._recovery_wait_secs
            ckpt = checkpoint_management.get_checkpoint_state(checkpoint_dir)
        else:
            return sess, False

    # Loads the checkpoint.
    saver.restore(sess, ckpt.model_checkpoint_path)
    saver.recover_last_checkpoints(ckpt.all_model_checkpoint_paths)
    return sess, True

session_manager.SessionManager._restore_checkpoint = new_restore_checkpoint
