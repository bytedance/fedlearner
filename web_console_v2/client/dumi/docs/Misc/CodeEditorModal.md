# CodeEditorModal

代码编辑器组件，具有文件目录树和代码编辑器和标签 Tab 的功能，支持同步/异步两种模式

导出多种类型组件

1. BaseCodeEditor, 核心代码
2. BaseCodeEditor.AlgorithmProject, 为了方便外部调用，封装了与 AlgorithmProject 相关的方法，只需要传 AlgorithmProject 的 id 即可，默认开启异步模式
3. BaseCodeEditor.Algorithm, 为了方便外部调用，封装了与 Algorithm 相关的方法，只需要传 Algorithm 的 id 即可，默认开启异步模式

4. CodeEditorModal，在 BaseCodeEditor 的基础上，用 Modal 包括起来，全屏显示
5. [CodeEditorModal.AlgorithmProject](#algorithmproject), 为了方便外部调用，封装了与 AlgorithmProject 相关的方法，只需要传 AlgorithmProject 的 id 即可，默认开启异步模式
6. [CodeEditorModal.Algorithm](#algorithm), 为了方便外部调用，封装了与 Algorithm 相关的方法，只需要传 Algorithm 的 id 即可，默认开启异步模式
7. [CodeEditorModal.AlgorithmProjectFormButton](#algorithmprojectformbutton)，在 CodeEditorModal.AlgorithmProject 的基础上，根据编辑算法页面的需要，封装了按钮组件，点击即可显示全屏幕的代码编辑器,只需要传 AlgorithmProject 的 id 即可，默认开启异步模式

在同步模式(isAsyncMode = false)下，数据从 `initialFileData` 中获取初始值，每次进行文件的操作时，`不会`调用接口，在点击右上角的`保存`按钮时，会把当前最新的 fileData 数据传递出去，给外部使用。点击`重置`按钮，会自动恢复成 `initialFileData` 的数据

在异步模式(isAsyncMode = true)下，每进行文件操作时，都会在内部`调用接口`来保存文件内容，包括新增文件，删除文件，重命名文件，编辑文件内容等

<API src="components/CodeEditorModal/index.tsx" exports='["default"]' hi></API>

## 基础用法

### 同步模式

```tsx
import React, { useState } from 'react';
import CodeEditorModal from 'components/CodeEditorModal';

const fileData = {
  'owner.py': '# coding: utf-8\n',
  'leader/main.py':
    "# coding: utf-8\nimport logging\nimport datetime\n\nimport tensorflow.compat.v1 as tf \nimport fedlearner.trainer as flt \nimport os\n\nfrom slot_2_bucket import slot_2_bucket\n\n_SLOT_2_IDX = {pair[0]: i for i, pair in enumerate(slot_2_bucket)}\n_SLOT_2_BUCKET = slot_2_bucket\nROLE = \"leader\"\n\nparser = flt.trainer_worker.create_argument_parser()\nparser.add_argument('--batch-size', type=int, default=256,\n                    help='Training batch size.')\nparser.add_argument('--clean-model', type=bool, default=True,\n                    help='clean checkpoint and saved_model')\nargs = parser.parse_args()\nargs.sparse_estimator = True\n\ndef apply_clean():\n  if args.worker_rank == 0 and args.clean_model and tf.io.gfile.exists(args.checkpoint_path):\n    tf.logging.info(\"--clean_model flag set. Removing existing checkpoint_path dir:\"\n                    \" {}\".format(args.checkpoint_path))\n    tf.io.gfile.rmtree(args.checkpoint_path)\n\n  if args.worker_rank == 0 and args.clean_model and args.export_path and tf.io.gfile.exists(args.export_path):\n    tf.logging.info(\"--clean_model flag set. Removing existing savedmodel dir:\"\n                    \" {}\".format(args.export_path))\n    tf.io.gfile.rmtree(args.export_path)\n\n\ndef input_fn(bridge, trainer_master=None):\n  dataset = flt.data.DataBlockLoader(\n        args.batch_size, ROLE, bridge, trainer_master).make_dataset()\n  \n  def parse_fn(example):\n    feature_map = {}\n    feature_map[\"example_id\"] = tf.FixedLenFeature([], tf.string)\n    feature_map['fids'] = tf.VarLenFeature(tf.int64)\n    # feature_map['y'] = tf.FixedLenFeature([], tf.int64)\n    features = tf.parse_example(example, features=feature_map)\n    # labels = {'y': features.pop('y')}\n    labels = {'y': tf.constant(0)}\n    return features, labels\n  dataset = dataset.map(map_func=parse_fn, num_parallel_calls=tf.data.experimental.AUTOTUNE)\n  dataset = dataset.prefetch(2)\n  return dataset\n  \n  # feature_map = {\"fids\": tf.VarLenFeature(tf.int64)}\n  # feature_map['example_id'] = tf.FixedLenFeature([], tf.string)\n  # record_batch = dataset.make_batch_iterator().get_next()\n  # features = tf.parse_example(record_batch, features=feature_map)\n  # return features, None\n\ndef raw_serving_input_receiver_fn():\n  feature_map = {\n    'fids_indices': tf.placeholder(dtype=tf.int64, shape=[None], name='fids_indices'),\n    'fids_values': tf.placeholder(dtype=tf.int64, shape=[None], name='fids_values'),\n    'fids_dense_shape': tf.placeholder(dtype=tf.int64, shape=[None], name='fids_dense_shape')\n  }\n  return tf.estimator.export.ServingInputReceiver(\n        feature_map, feature_map)\n\n\ndef model_fn(model, features, labels, mode):\n\n  def sum_pooling(embeddings, slots):\n    slot_embeddings = []\n    for slot in slots:\n      slot_embeddings.append(embeddings[_SLOT_2_IDX[slot]])\n    if len(slot_embeddings) == 1:\n      return slot_embeddings[0]\n    return tf.add_n(slot_embeddings)\n\n  global_step = tf.train.get_or_create_global_step()\n  num_slot, embed_size = len(_SLOT_2_BUCKET), 8\n  xavier_initializer = tf.glorot_normal_initializer()\n\n  flt.feature.FeatureSlot.set_default_bias_initializer(\n        tf.zeros_initializer())\n  flt.feature.FeatureSlot.set_default_vec_initializer(\n        tf.random_uniform_initializer(-0.0078125, 0.0078125))\n  flt.feature.FeatureSlot.set_default_bias_optimizer(\n        tf.train.FtrlOptimizer(learning_rate=0.01))\n  flt.feature.FeatureSlot.set_default_vec_optimizer(\n        tf.train.AdagradOptimizer(learning_rate=0.01))\n\n  # deal with input cols\n  categorical_embed = []\n  num_slot, embed_dim = len(_SLOT_2_BUCKET), 8\n\n  with tf.variable_scope(\"leader\"):\n    for slot, bucket_size in _SLOT_2_BUCKET:\n      fs = model.add_feature_slot(slot, bucket_size)\n      fc = model.add_feature_column(fs)\n      categorical_embed.append(fc.add_vector(embed_dim))\n\n\n  # concate all embeddings\n  slot_embeddings = categorical_embed\n  concat_embedding = tf.concat(slot_embeddings, axis=1)\n  output_size = len(slot_embeddings) * embed_dim\n\n  model.freeze_slots(features)\n\n  with tf.variable_scope(\"follower\"):\n    fc1_size, fc2_size, fc3_size = 16, 16, 16\n    w1 = tf.get_variable('w1', shape=[output_size, fc1_size], dtype=tf.float32,\n                        initializer=xavier_initializer)\n    b1 = tf.get_variable(\n        'b1', shape=[fc1_size], dtype=tf.float32, initializer=tf.zeros_initializer())\n    w2 = tf.get_variable('w2', shape=[fc1_size, fc2_size], dtype=tf.float32,\n                        initializer=xavier_initializer)\n    b2 = tf.get_variable(\n        'b2', shape=[fc2_size], dtype=tf.float32, initializer=tf.zeros_initializer())\n    w3 = tf.get_variable('w3', shape=[fc2_size, fc3_size], dtype=tf.float32,\n                        initializer=xavier_initializer)\n    b3 = tf.get_variable(\n        'b3', shape=[fc3_size], dtype=tf.float32, initializer=tf.zeros_initializer())\n\n  act1_l = tf.nn.relu(tf.nn.bias_add(tf.matmul(concat_embedding, w1), b1))\n  act1_l = tf.layers.batch_normalization(act1_l, training=True)\n  act2_l = tf.nn.relu(tf.nn.bias_add(tf.matmul(act1_l, w2), b2))\n  act2_l = tf.layers.batch_normalization(act2_l, training=True)\n  embedding = tf.nn.relu(tf.nn.bias_add(tf.matmul(act2_l, w3), b3))\n  embedding = tf.layers.batch_normalization(embedding, training=True)\n\n  if mode == tf.estimator.ModeKeys.TRAIN:\n    embedding_grad = model.send('embedding', embedding, require_grad=True)\n    optimizer = tf.train.GradientDescentOptimizer(0.01)\n    train_op = model.minimize(\n        optimizer, embedding, grad_loss=embedding_grad, global_step=global_step)\n    return model.make_spec(mode, loss=tf.math.reduce_mean(embedding), train_op=train_op)\n  elif mode == tf.estimator.ModeKeys.PREDICT:\n    return model.make_spec(mode, predictions={'embedding': embedding})\n\nif __name__ == '__main__':\n  logging.basicConfig(\n      level=logging.INFO,\n      format='%(asctime)-15s [%(filename)s:%(lineno)d] %(levelname)s %(message)s'\n  )\n  apply_clean()\n  flt.trainer_worker.train(\n      ROLE, args, input_fn,\n      model_fn, raw_serving_input_receiver_fn)\n",
  'leader/slot_2_bucket.py':
    '# coding: utf-8\nslot_2_bucket = [(0, 2),(1, 2),(2, 2),(3, 2),(4, 2),(5, 2),(6, 2),(7, 2),(8, 2),(9, 2),(10, 2),(11, 2),(12, 2),(13, 1341),(14, 535),(15, 74138),(16, 70862),(17, 279),(18, 17),(19, 11019),(20, 591),(21, 4),(22, 30227),(23, 4791),(24, 75100),(25, 3075),(26, 27),(27, 9226),(28, 79191),(29, 11),(30, 3990),(31, 1898),(32, 5),\n(33, 76976),(34, 18),(35, 16),(36, 36534),(37, 74),(38, 29059)]\n',
  'follower/main.py':
    "# coding: utf-8\n# encoding=utf8\nimport logging\n\nimport tensorflow.compat.v1 as tf\n\nimport fedlearner.trainer as flt\nimport os\n\nROLE = 'follower'\n\nparser = flt.trainer_worker.create_argument_parser()\nparser.add_argument('--batch-size', type=int, default=256,\n                    help='Training batch size.')\nparser.add_argument('--clean-model', type=bool, default=True,\n                    help='clean checkpoint and saved_model')\nargs = parser.parse_args()\n\ndef apply_clean():\n  if args.worker_rank == 0 and args.clean_model and tf.io.gfile.exists(args.checkpoint_path):\n    tf.logging.info(\"--clean_model flag set. Removing existing checkpoint_path dir:\"\n                    \" {}\".format(args.checkpoint_path))\n    tf.io.gfile.rmtree(args.checkpoint_path)\n\n  if args.worker_rank == 0 and args.clean_model and args.export_path and tf.io.gfile.exists(args.export_path):\n    tf.logging.info(\"--clean_model flag set. Removing existing savedmodel dir:\"\n                    \" {}\".format(args.export_path))\n    tf.io.gfile.rmtree(args.export_path)\n\ndef input_fn(bridge, trainer_master=None):\n  dataset = flt.data.DataBlockLoader(\n      args.batch_size, ROLE, bridge, trainer_master).make_dataset()\n  \n  def parse_fn(example):\n    feature_map = {}\n    feature_map['example_id'] = tf.FixedLenFeature([], tf.string)\n    # feature_map['y'] = tf.FixedLenFeature([], tf.int64)\n    features = tf.parse_example(example, features=feature_map)\n    labels = {'y': tf.constant(0, shape=[1])}\n    return features, labels\n  \n  dataset = dataset.map(map_func=parse_fn,\n    num_parallel_calls=tf.data.experimental.AUTOTUNE)\n  dataset = dataset.prefetch(2)\n  return dataset\n  \n\ndef raw_serving_input_receiver_fn():\n  features = {}\n  features['embedding'] = tf.placeholder(dtype=tf.float32, shape=[1, 16], name='embedding')\n  receiver_tensors = {\n    'embedding': features['embedding']\n  }\n  return tf.estimator.export.ServingInputReceiver(\n    features, receiver_tensors)\n\ndef model_fn(model, features, labels, mode):\n  global_step = tf.train.get_or_create_global_step()\n  xavier_initializer = tf.glorot_normal_initializer()\n\n  fc1_size = 16\n  with tf.variable_scope('follower'):\n    w1f = tf.get_variable('w1f', shape=[\n        fc1_size, 1], dtype=tf.float32, initializer=tf.random_uniform_initializer(-0.01, 0.01))\n    b1f = tf.get_variable(\n        'b1f', shape=[1], dtype=tf.float32, initializer=tf.zeros_initializer())\n  \n  if mode == tf.estimator.ModeKeys.TRAIN:\n    embedding = model.recv('embedding', tf.float32, require_grad=True)\n  else:\n    embedding = features['embedding']\n  \n  logits = tf.nn.bias_add(tf.matmul(embedding, w1f), b1f)\n\n  if mode == tf.estimator.ModeKeys.TRAIN:\n    y = tf.dtypes.cast(labels['y'], tf.float32)\n    loss = tf.nn.sigmoid_cross_entropy_with_logits(\n        labels=y, logits=logits)\n    loss = tf.math.reduce_mean(loss)\n\n    # cala auc\n    pred = tf.math.sigmoid(logits)\n    print('==============================================================')\n    print(tf.shape(y))\n    print(tf.shape(pred))\n    _, auc = tf.metrics.auc(labels=y, predictions=pred)\n\n    logging_hook = tf.train.LoggingTensorHook(\n        {\"loss\": loss, \"auc\": auc}, every_n_iter=10)\n\n    optimizer = tf.train.GradientDescentOptimizer(0.01)\n    train_op = model.minimize(optimizer, loss, global_step=global_step)\n    return model.make_spec(mode, loss=loss, train_op=train_op,\n                            training_hooks=[logging_hook])\n\n  if mode == tf.estimator.ModeKeys.PREDICT:\n    return model.make_spec(mode, predictions=logits)\n\nif __name__ == '__main__':\n    logging.basicConfig(\n        level=logging.INFO,\n        format='%(asctime)-15s [%(filename)s:%(lineno)d] %(levelname)s %(message)s'\n    )\n    apply_clean()\n    flt.trainer_worker.train(\n        ROLE, args, input_fn,\n        model_fn, raw_serving_input_receiver_fn)\n",
  'follower/slot_2_bucket.py':
    '# coding: utf-8\nslot_2_bucket = [(0, 2),(1, 2),(2, 2),(3, 2),(4, 2),(5, 2),(6, 2),(7, 2),(8, 2),(9, 2),(10, 2),(11, 2),(12, 2),(13, 1341),(14, 535),(15, 74138),(16, 70862),(17, 279),(18, 17),(19, 11019),(20, 591),(21, 4),(22, 30227),(23, 4791),(24, 75100),(25, 3075),(26, 27),(27, 9226),(28, 79191),(29, 11),(30, 3990),(31, 1898),(32, 5),\n(33, 76976),(34, 18),(35, 16),(36, 36534),(37, 74),(38, 29059)]\n',
};

export default () => {
  const [visible, setVisible] = useState(false);

  return (
    <>
      <button
        onClick={() => {
          setVisible(true);
        }}
      >
        Click me open code editor modal
      </button>
      <CodeEditorModal
        visible={visible}
        initialFileData={fileData}
        title="代码编辑器(同步模式)"
        onClose={() => {
          setVisible(false);
        }}
        onSave={(finalFiledata) => {
          console.log(finalFiledata);
        }}
      />
    </>
  );
};
```

### 异步模式

在异步模式(IsAsyncMode = true)下，需要提供以下 2 个函数，再内部自行调用接口，并转换格式

```
getFileTreeList?: () => Promise<any[]>;
getFile?: (filePath: string) => Promise<any>;
```

1. `getFileTreeList`，用于获取文件目录树的内容
2. `getFile`，用于获取文件的内容，他接收一个文件路径作为参数，例如 'leader/main.py'

`getFileTreeList` 返回 Promise，而且 ResolvedValue 为以下格式的数组

```tsx | pure
interface FileTreeNode {
  filename: string;
  path: string;
  /** File size */
  size: number;
  /** Last Time Modified */
  mtime: number;
  is_directory: boolean;
  files: FileTreeNode[];
}
```

`getFile` 返回 Promise，而且 ResolvedValue 为文件内容的字符串

为了方便调用，不用每次都输入`getFileTreeList`/`getFile`，封装了[AlgorithmProject](#algorithmproject)和[Algorithm](#algorithm) 2 个组件

```tsx
import React, { useState } from 'react';
import CodeEditorModal from 'components/CodeEditorModal';

import {
  fetchAlgorithmProjectFileTreeList,
  fetchAlgorithmProjectFileContentDetail,
} from 'services/algorithm';

export default () => {
  const [visible, setVisible] = useState(false);

  return (
    <>
      <button
        onClick={() => {
          setVisible(true);
        }}
      >
        Click me open code editor modal
      </button>
      <CodeEditorModal
        visible={visible}
        isAsyncMode={true}
        title="代码编辑器(异步模式)"
        id={3}
        onClose={() => {
          setVisible(false);
        }}
        getFileTreeList={() => fetchAlgorithmProjectFileTreeList(3).then((res) => res.data)}
        getFile={(filePath: string) =>
          fetchAlgorithmProjectFileContentDetail(3, {
            path: filePath,
          }).then((res) => res.data.content)
        }
      />
    </>
  );
};
```

## 子组件

### AlgorithmProject

为了方便外部调用，封装了与 AlgorithmProject 相关的方法，只需要传 AlgorithmProject 的 id 即可，默认开启异步模式

```tsx
import React, { useState } from 'react';
import CodeEditorModal from 'components/CodeEditorModal';

export default () => {
  const [visible, setVisible] = useState(false);

  return (
    <>
      <button
        onClick={() => {
          setVisible(true);
        }}
      >
        Click me open code editor modal
      </button>
      <CodeEditorModal.AlgorithmProject
        visible={visible}
        title="代码编辑器"
        id={3}
        onClose={() => {
          setVisible(false);
        }}
      />
    </>
  );
};
```

### Algorithm

为了方便外部调用，封装了与 Algorithm 相关的方法，只需要传 Algorithm 的 id 即可，默认开启异步模式

```tsx
import React, { useState } from 'react';
import CodeEditorModal from 'components/CodeEditorModal';

export default () => {
  const [visible, setVisible] = useState(false);

  return (
    <>
      <button
        onClick={() => {
          setVisible(true);
        }}
      >
        Click me open code editor modal
      </button>
      <CodeEditorModal.Algorithm
        visible={visible}
        id={3}
        onClose={() => {
          setVisible(false);
        }}
      />
    </>
  );
};
```

### AlgorithmProjectFormButton

在 CodeEditorModal.AlgorithmProject 的基础上，根据编辑算法页面的需要，封装了按钮组件，点击即可显示全屏幕的代码编辑器,只需要传 AlgorithmProject 的 id 即可，默认开启异步模式

可以额外设置设置 width 和 height

<API src="components/CodeEditorModal/index.tsx" exports='["AlgorithmProjectFormButton"]' hideTitle></API>

```tsx
import React from 'react';
import CodeEditorModal from 'components/CodeEditorModal';

export default () => {
  return (
    <>
      <CodeEditorModal.AlgorithmProjectFormButton id={3} title="代码编辑器" />
    </>
  );
};
```
