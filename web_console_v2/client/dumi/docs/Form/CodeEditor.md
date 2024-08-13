# CodeEditor

代码编辑器

基于 [monaco-react](https://github.com/suren-atoyan/monaco-react) 封装，增加了`grey`主题色，更改了部分样式

<API src="components/CodeEditor/index.tsx"></API>

也支持传入 [monaco-react](https://github.com/suren-atoyan/monaco-react) 原有的 props

## 常规用法

```tsx
/**
 * compact: true
 */
import React from 'react';
import CodeEditor from 'components/CodeEditor';

const pyText =
  "# coding: utf-8\nimport logging\nimport datetime\n\nimport tensorflow.compat.v1 as tf \nimport fedlearner.trainer as flt \nimport os\n\nfrom slot_2_bucket import slot_2_bucket\n\n_SLOT_2_IDX = {pair[0]: i for i, pair in enumerate(slot_2_bucket)}\n_SLOT_2_BUCKET = slot_2_bucket\nROLE = \"leader\"\n\nparser = flt.trainer_worker.create_argument_parser()\nparser.add_argument('--batch-size', type=int, default=256,\n                    help='Training batch size.')\nparser.add_argument('--clean-model', type=bool, default=True,\n                    help='clean checkpoint and saved_model')\nargs = parser.parse_args()\nargs.sparse_estimator = True\n\ndef apply_clean():\n  if args.worker_rank == 0 and args.clean_model and tf.io.gfile.exists(args.checkpoint_path):\n    tf.logging.info(\"--clean_model flag set. Removing existing checkpoint_path dir:\"\n                    \" {}\".format(args.checkpoint_path))\n    tf.io.gfile.rmtree(args.checkpoint_path)\n\n  if args.worker_rank == 0 and args.clean_model and args.export_path and tf.io.gfile.exists(args.export_path):\n    tf.logging.info(\"--clean_model flag set. Removing existing savedmodel dir:\"\n                    \" {}\".format(args.export_path))\n    tf.io.gfile.rmtree(args.export_path)\n\n\ndef input_fn(bridge, trainer_master=None):\n  dataset = flt.data.DataBlockLoader(\n        args.batch_size, ROLE, bridge, trainer_master).make_dataset()\n  \n  def parse_fn(example):\n    feature_map = {}\n    feature_map[\"example_id\"] = tf.FixedLenFeature([], tf.string)\n    feature_map['fids'] = tf.VarLenFeature(tf.int64)\n    # feature_map['y'] = tf.FixedLenFeature([], tf.int64)\n    features = tf.parse_example(example, features=feature_map)\n    # labels = {'y': features.pop('y')}\n    labels = {'y': tf.constant(0)}\n    return features, labels\n  dataset = dataset.map(map_func=parse_fn, num_parallel_calls=tf.data.experimental.AUTOTUNE)\n  dataset = dataset.prefetch(2)\n  return dataset\n  \n  # feature_map = {\"fids\": tf.VarLenFeature(tf.int64)}\n  # feature_map['example_id'] = tf.FixedLenFeature([], tf.string)\n  # record_batch = dataset.make_batch_iterator().get_next()\n  # features = tf.parse_example(record_batch, features=feature_map)\n  # return features, None\n\ndef raw_serving_input_receiver_fn():\n  feature_map = {\n    'fids_indices': tf.placeholder(dtype=tf.int64, shape=[None], name='fids_indices'),\n    'fids_values': tf.placeholder(dtype=tf.int64, shape=[None], name='fids_values'),\n    'fids_dense_shape': tf.placeholder(dtype=tf.int64, shape=[None], name='fids_dense_shape')\n  }\n  return tf.estimator.export.ServingInputReceiver(\n        feature_map, feature_map)\n\n\ndef model_fn(model, features, labels, mode):\n\n  def sum_pooling(embeddings, slots):\n    slot_embeddings = []\n    for slot in slots:\n      slot_embeddings.append(embeddings[_SLOT_2_IDX[slot]])\n    if len(slot_embeddings) == 1:\n      return slot_embeddings[0]\n    return tf.add_n(slot_embeddings)\n\n  global_step = tf.train.get_or_create_global_step()\n  num_slot, embed_size = len(_SLOT_2_BUCKET), 8\n  xavier_initializer = tf.glorot_normal_initializer()\n\n  flt.feature.FeatureSlot.set_default_bias_initializer(\n        tf.zeros_initializer())\n  flt.feature.FeatureSlot.set_default_vec_initializer(\n        tf.random_uniform_initializer(-0.0078125, 0.0078125))\n  flt.feature.FeatureSlot.set_default_bias_optimizer(\n        tf.train.FtrlOptimizer(learning_rate=0.01))\n  flt.feature.FeatureSlot.set_default_vec_optimizer(\n        tf.train.AdagradOptimizer(learning_rate=0.01))\n\n  # deal with input cols\n  categorical_embed = []\n  num_slot, embed_dim = len(_SLOT_2_BUCKET), 8\n\n  with tf.variable_scope(\"leader\"):\n    for slot, bucket_size in _SLOT_2_BUCKET:\n      fs = model.add_feature_slot(slot, bucket_size)\n      fc = model.add_feature_column(fs)\n      categorical_embed.append(fc.add_vector(embed_dim))\n\n\n  # concate all embeddings\n  slot_embeddings = categorical_embed\n  concat_embedding = tf.concat(slot_embeddings, axis=1)\n  output_size = len(slot_embeddings) * embed_dim\n\n  model.freeze_slots(features)\n\n  with tf.variable_scope(\"follower\"):\n    fc1_size, fc2_size, fc3_size = 16, 16, 16\n    w1 = tf.get_variable('w1', shape=[output_size, fc1_size], dtype=tf.float32,\n                        initializer=xavier_initializer)\n    b1 = tf.get_variable(\n        'b1', shape=[fc1_size], dtype=tf.float32, initializer=tf.zeros_initializer())\n    w2 = tf.get_variable('w2', shape=[fc1_size, fc2_size], dtype=tf.float32,\n                        initializer=xavier_initializer)\n    b2 = tf.get_variable(\n        'b2', shape=[fc2_size], dtype=tf.float32, initializer=tf.zeros_initializer())\n    w3 = tf.get_variable('w3', shape=[fc2_size, fc3_size], dtype=tf.float32,\n                        initializer=xavier_initializer)\n    b3 = tf.get_variable(\n        'b3', shape=[fc3_size], dtype=tf.float32, initializer=tf.zeros_initializer())\n\n  act1_l = tf.nn.relu(tf.nn.bias_add(tf.matmul(concat_embedding, w1), b1))\n  act1_l = tf.layers.batch_normalization(act1_l, training=True)\n  act2_l = tf.nn.relu(tf.nn.bias_add(tf.matmul(act1_l, w2), b2))\n  act2_l = tf.layers.batch_normalization(act2_l, training=True)\n  embedding = tf.nn.relu(tf.nn.bias_add(tf.matmul(act2_l, w3), b3))\n  embedding = tf.layers.batch_normalization(embedding, training=True)\n\n  if mode == tf.estimator.ModeKeys.TRAIN:\n    embedding_grad = model.send('embedding', embedding, require_grad=True)\n    optimizer = tf.train.GradientDescentOptimizer(0.01)\n    train_op = model.minimize(\n        optimizer, embedding, grad_loss=embedding_grad, global_step=global_step)\n    return model.make_spec(mode, loss=tf.math.reduce_mean(embedding), train_op=train_op)\n  elif mode == tf.estimator.ModeKeys.PREDICT:\n    return model.make_spec(mode, predictions={'embedding': embedding})\n\nif __name__ == '__main__':\n  logging.basicConfig(\n      level=logging.INFO,\n      format='%(asctime)-15s [%(filename)s:%(lineno)d] %(levelname)s %(message)s'\n  )\n  apply_clean()\n  flt.trainer_worker.train(\n      ROLE, args, input_fn,\n      model_fn, raw_serving_input_receiver_fn)\n";

export default () => {
  return (
    <>
      <CodeEditor
        value={pyText}
        language="python"
        height="800px"
        onChange={(val) => {
          console.log(val);
        }}
      />
    </>
  );
};
```

## IsReadOnly

isReadOnly = true

```tsx
/**
 * compact: true
 */
import React from 'react';
import CodeEditor from 'components/CodeEditor';

const pyText =
  "# coding: utf-8\nimport logging\nimport datetime\n\nimport tensorflow.compat.v1 as tf \nimport fedlearner.trainer as flt \nimport os\n\nfrom slot_2_bucket import slot_2_bucket\n\n_SLOT_2_IDX = {pair[0]: i for i, pair in enumerate(slot_2_bucket)}\n_SLOT_2_BUCKET = slot_2_bucket\nROLE = \"leader\"\n\nparser = flt.trainer_worker.create_argument_parser()\nparser.add_argument('--batch-size', type=int, default=256,\n                    help='Training batch size.')\nparser.add_argument('--clean-model', type=bool, default=True,\n                    help='clean checkpoint and saved_model')\nargs = parser.parse_args()\nargs.sparse_estimator = True\n\ndef apply_clean():\n  if args.worker_rank == 0 and args.clean_model and tf.io.gfile.exists(args.checkpoint_path):\n    tf.logging.info(\"--clean_model flag set. Removing existing checkpoint_path dir:\"\n                    \" {}\".format(args.checkpoint_path))\n    tf.io.gfile.rmtree(args.checkpoint_path)\n\n  if args.worker_rank == 0 and args.clean_model and args.export_path and tf.io.gfile.exists(args.export_path):\n    tf.logging.info(\"--clean_model flag set. Removing existing savedmodel dir:\"\n                    \" {}\".format(args.export_path))\n    tf.io.gfile.rmtree(args.export_path)\n\n\ndef input_fn(bridge, trainer_master=None):\n  dataset = flt.data.DataBlockLoader(\n        args.batch_size, ROLE, bridge, trainer_master).make_dataset()\n  \n  def parse_fn(example):\n    feature_map = {}\n    feature_map[\"example_id\"] = tf.FixedLenFeature([], tf.string)\n    feature_map['fids'] = tf.VarLenFeature(tf.int64)\n    # feature_map['y'] = tf.FixedLenFeature([], tf.int64)\n    features = tf.parse_example(example, features=feature_map)\n    # labels = {'y': features.pop('y')}\n    labels = {'y': tf.constant(0)}\n    return features, labels\n  dataset = dataset.map(map_func=parse_fn, num_parallel_calls=tf.data.experimental.AUTOTUNE)\n  dataset = dataset.prefetch(2)\n  return dataset\n  \n  # feature_map = {\"fids\": tf.VarLenFeature(tf.int64)}\n  # feature_map['example_id'] = tf.FixedLenFeature([], tf.string)\n  # record_batch = dataset.make_batch_iterator().get_next()\n  # features = tf.parse_example(record_batch, features=feature_map)\n  # return features, None\n\ndef raw_serving_input_receiver_fn():\n  feature_map = {\n    'fids_indices': tf.placeholder(dtype=tf.int64, shape=[None], name='fids_indices'),\n    'fids_values': tf.placeholder(dtype=tf.int64, shape=[None], name='fids_values'),\n    'fids_dense_shape': tf.placeholder(dtype=tf.int64, shape=[None], name='fids_dense_shape')\n  }\n  return tf.estimator.export.ServingInputReceiver(\n        feature_map, feature_map)\n\n\ndef model_fn(model, features, labels, mode):\n\n  def sum_pooling(embeddings, slots):\n    slot_embeddings = []\n    for slot in slots:\n      slot_embeddings.append(embeddings[_SLOT_2_IDX[slot]])\n    if len(slot_embeddings) == 1:\n      return slot_embeddings[0]\n    return tf.add_n(slot_embeddings)\n\n  global_step = tf.train.get_or_create_global_step()\n  num_slot, embed_size = len(_SLOT_2_BUCKET), 8\n  xavier_initializer = tf.glorot_normal_initializer()\n\n  flt.feature.FeatureSlot.set_default_bias_initializer(\n        tf.zeros_initializer())\n  flt.feature.FeatureSlot.set_default_vec_initializer(\n        tf.random_uniform_initializer(-0.0078125, 0.0078125))\n  flt.feature.FeatureSlot.set_default_bias_optimizer(\n        tf.train.FtrlOptimizer(learning_rate=0.01))\n  flt.feature.FeatureSlot.set_default_vec_optimizer(\n        tf.train.AdagradOptimizer(learning_rate=0.01))\n\n  # deal with input cols\n  categorical_embed = []\n  num_slot, embed_dim = len(_SLOT_2_BUCKET), 8\n\n  with tf.variable_scope(\"leader\"):\n    for slot, bucket_size in _SLOT_2_BUCKET:\n      fs = model.add_feature_slot(slot, bucket_size)\n      fc = model.add_feature_column(fs)\n      categorical_embed.append(fc.add_vector(embed_dim))\n\n\n  # concate all embeddings\n  slot_embeddings = categorical_embed\n  concat_embedding = tf.concat(slot_embeddings, axis=1)\n  output_size = len(slot_embeddings) * embed_dim\n\n  model.freeze_slots(features)\n\n  with tf.variable_scope(\"follower\"):\n    fc1_size, fc2_size, fc3_size = 16, 16, 16\n    w1 = tf.get_variable('w1', shape=[output_size, fc1_size], dtype=tf.float32,\n                        initializer=xavier_initializer)\n    b1 = tf.get_variable(\n        'b1', shape=[fc1_size], dtype=tf.float32, initializer=tf.zeros_initializer())\n    w2 = tf.get_variable('w2', shape=[fc1_size, fc2_size], dtype=tf.float32,\n                        initializer=xavier_initializer)\n    b2 = tf.get_variable(\n        'b2', shape=[fc2_size], dtype=tf.float32, initializer=tf.zeros_initializer())\n    w3 = tf.get_variable('w3', shape=[fc2_size, fc3_size], dtype=tf.float32,\n                        initializer=xavier_initializer)\n    b3 = tf.get_variable(\n        'b3', shape=[fc3_size], dtype=tf.float32, initializer=tf.zeros_initializer())\n\n  act1_l = tf.nn.relu(tf.nn.bias_add(tf.matmul(concat_embedding, w1), b1))\n  act1_l = tf.layers.batch_normalization(act1_l, training=True)\n  act2_l = tf.nn.relu(tf.nn.bias_add(tf.matmul(act1_l, w2), b2))\n  act2_l = tf.layers.batch_normalization(act2_l, training=True)\n  embedding = tf.nn.relu(tf.nn.bias_add(tf.matmul(act2_l, w3), b3))\n  embedding = tf.layers.batch_normalization(embedding, training=True)\n\n  if mode == tf.estimator.ModeKeys.TRAIN:\n    embedding_grad = model.send('embedding', embedding, require_grad=True)\n    optimizer = tf.train.GradientDescentOptimizer(0.01)\n    train_op = model.minimize(\n        optimizer, embedding, grad_loss=embedding_grad, global_step=global_step)\n    return model.make_spec(mode, loss=tf.math.reduce_mean(embedding), train_op=train_op)\n  elif mode == tf.estimator.ModeKeys.PREDICT:\n    return model.make_spec(mode, predictions={'embedding': embedding})\n\nif __name__ == '__main__':\n  logging.basicConfig(\n      level=logging.INFO,\n      format='%(asctime)-15s [%(filename)s:%(lineno)d] %(levelname)s %(message)s'\n  )\n  apply_clean()\n  flt.trainer_worker.train(\n      ROLE, args, input_fn,\n      model_fn, raw_serving_input_receiver_fn)\n";

export default () => {
  return (
    <>
      <CodeEditor
        value={pyText}
        language="python"
        height="800px"
        onChange={(val) => {
          console.log(val);
        }}
        isReadOnly={true}
      />
    </>
  );
};
```

## Theme

theme = grey

```tsx
/**
 * iframe: true
 * compact: true
 */
import React from 'react';
import CodeEditor from 'components/CodeEditor';

const pyText =
  "# coding: utf-8\nimport logging\nimport datetime\n\nimport tensorflow.compat.v1 as tf \nimport fedlearner.trainer as flt \nimport os\n\nfrom slot_2_bucket import slot_2_bucket\n\n_SLOT_2_IDX = {pair[0]: i for i, pair in enumerate(slot_2_bucket)}\n_SLOT_2_BUCKET = slot_2_bucket\nROLE = \"leader\"\n\nparser = flt.trainer_worker.create_argument_parser()\nparser.add_argument('--batch-size', type=int, default=256,\n                    help='Training batch size.')\nparser.add_argument('--clean-model', type=bool, default=True,\n                    help='clean checkpoint and saved_model')\nargs = parser.parse_args()\nargs.sparse_estimator = True\n\ndef apply_clean():\n  if args.worker_rank == 0 and args.clean_model and tf.io.gfile.exists(args.checkpoint_path):\n    tf.logging.info(\"--clean_model flag set. Removing existing checkpoint_path dir:\"\n                    \" {}\".format(args.checkpoint_path))\n    tf.io.gfile.rmtree(args.checkpoint_path)\n\n  if args.worker_rank == 0 and args.clean_model and args.export_path and tf.io.gfile.exists(args.export_path):\n    tf.logging.info(\"--clean_model flag set. Removing existing savedmodel dir:\"\n                    \" {}\".format(args.export_path))\n    tf.io.gfile.rmtree(args.export_path)\n\n\ndef input_fn(bridge, trainer_master=None):\n  dataset = flt.data.DataBlockLoader(\n        args.batch_size, ROLE, bridge, trainer_master).make_dataset()\n  \n  def parse_fn(example):\n    feature_map = {}\n    feature_map[\"example_id\"] = tf.FixedLenFeature([], tf.string)\n    feature_map['fids'] = tf.VarLenFeature(tf.int64)\n    # feature_map['y'] = tf.FixedLenFeature([], tf.int64)\n    features = tf.parse_example(example, features=feature_map)\n    # labels = {'y': features.pop('y')}\n    labels = {'y': tf.constant(0)}\n    return features, labels\n  dataset = dataset.map(map_func=parse_fn, num_parallel_calls=tf.data.experimental.AUTOTUNE)\n  dataset = dataset.prefetch(2)\n  return dataset\n  \n  # feature_map = {\"fids\": tf.VarLenFeature(tf.int64)}\n  # feature_map['example_id'] = tf.FixedLenFeature([], tf.string)\n  # record_batch = dataset.make_batch_iterator().get_next()\n  # features = tf.parse_example(record_batch, features=feature_map)\n  # return features, None\n\ndef raw_serving_input_receiver_fn():\n  feature_map = {\n    'fids_indices': tf.placeholder(dtype=tf.int64, shape=[None], name='fids_indices'),\n    'fids_values': tf.placeholder(dtype=tf.int64, shape=[None], name='fids_values'),\n    'fids_dense_shape': tf.placeholder(dtype=tf.int64, shape=[None], name='fids_dense_shape')\n  }\n  return tf.estimator.export.ServingInputReceiver(\n        feature_map, feature_map)\n\n\ndef model_fn(model, features, labels, mode):\n\n  def sum_pooling(embeddings, slots):\n    slot_embeddings = []\n    for slot in slots:\n      slot_embeddings.append(embeddings[_SLOT_2_IDX[slot]])\n    if len(slot_embeddings) == 1:\n      return slot_embeddings[0]\n    return tf.add_n(slot_embeddings)\n\n  global_step = tf.train.get_or_create_global_step()\n  num_slot, embed_size = len(_SLOT_2_BUCKET), 8\n  xavier_initializer = tf.glorot_normal_initializer()\n\n  flt.feature.FeatureSlot.set_default_bias_initializer(\n        tf.zeros_initializer())\n  flt.feature.FeatureSlot.set_default_vec_initializer(\n        tf.random_uniform_initializer(-0.0078125, 0.0078125))\n  flt.feature.FeatureSlot.set_default_bias_optimizer(\n        tf.train.FtrlOptimizer(learning_rate=0.01))\n  flt.feature.FeatureSlot.set_default_vec_optimizer(\n        tf.train.AdagradOptimizer(learning_rate=0.01))\n\n  # deal with input cols\n  categorical_embed = []\n  num_slot, embed_dim = len(_SLOT_2_BUCKET), 8\n\n  with tf.variable_scope(\"leader\"):\n    for slot, bucket_size in _SLOT_2_BUCKET:\n      fs = model.add_feature_slot(slot, bucket_size)\n      fc = model.add_feature_column(fs)\n      categorical_embed.append(fc.add_vector(embed_dim))\n\n\n  # concate all embeddings\n  slot_embeddings = categorical_embed\n  concat_embedding = tf.concat(slot_embeddings, axis=1)\n  output_size = len(slot_embeddings) * embed_dim\n\n  model.freeze_slots(features)\n\n  with tf.variable_scope(\"follower\"):\n    fc1_size, fc2_size, fc3_size = 16, 16, 16\n    w1 = tf.get_variable('w1', shape=[output_size, fc1_size], dtype=tf.float32,\n                        initializer=xavier_initializer)\n    b1 = tf.get_variable(\n        'b1', shape=[fc1_size], dtype=tf.float32, initializer=tf.zeros_initializer())\n    w2 = tf.get_variable('w2', shape=[fc1_size, fc2_size], dtype=tf.float32,\n                        initializer=xavier_initializer)\n    b2 = tf.get_variable(\n        'b2', shape=[fc2_size], dtype=tf.float32, initializer=tf.zeros_initializer())\n    w3 = tf.get_variable('w3', shape=[fc2_size, fc3_size], dtype=tf.float32,\n                        initializer=xavier_initializer)\n    b3 = tf.get_variable(\n        'b3', shape=[fc3_size], dtype=tf.float32, initializer=tf.zeros_initializer())\n\n  act1_l = tf.nn.relu(tf.nn.bias_add(tf.matmul(concat_embedding, w1), b1))\n  act1_l = tf.layers.batch_normalization(act1_l, training=True)\n  act2_l = tf.nn.relu(tf.nn.bias_add(tf.matmul(act1_l, w2), b2))\n  act2_l = tf.layers.batch_normalization(act2_l, training=True)\n  embedding = tf.nn.relu(tf.nn.bias_add(tf.matmul(act2_l, w3), b3))\n  embedding = tf.layers.batch_normalization(embedding, training=True)\n\n  if mode == tf.estimator.ModeKeys.TRAIN:\n    embedding_grad = model.send('embedding', embedding, require_grad=True)\n    optimizer = tf.train.GradientDescentOptimizer(0.01)\n    train_op = model.minimize(\n        optimizer, embedding, grad_loss=embedding_grad, global_step=global_step)\n    return model.make_spec(mode, loss=tf.math.reduce_mean(embedding), train_op=train_op)\n  elif mode == tf.estimator.ModeKeys.PREDICT:\n    return model.make_spec(mode, predictions={'embedding': embedding})\n\nif __name__ == '__main__':\n  logging.basicConfig(\n      level=logging.INFO,\n      format='%(asctime)-15s [%(filename)s:%(lineno)d] %(levelname)s %(message)s'\n  )\n  apply_clean()\n  flt.trainer_worker.train(\n      ROLE, args, input_fn,\n      model_fn, raw_serving_input_receiver_fn)\n";

export default () => {
  return (
    <>
      <CodeEditor
        value={pyText}
        language="python"
        height="800px"
        onChange={(val) => {
          console.log(val);
        }}
        theme="grey"
      />
    </>
  );
};
```
