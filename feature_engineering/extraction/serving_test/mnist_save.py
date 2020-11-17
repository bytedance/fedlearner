import os
import tensorflow
from serving_test.mnist_data import MnistData
from tensorflow.python.ops import lookup_ops

tf = tensorflow.compat.v1
sess = tf.InteractiveSession()
tf.compat.v1.disable_eager_execution()


def export_model(model_version, signature_def_map, main_op_def):
    export_path_base = './model/mnist2'
    export_path = os.path.join(tf.compat.as_bytes(export_path_base), tf.compat.as_bytes(str(model_version)))
    builder = tf.saved_model.builder.SavedModelBuilder(export_path)
    builder.add_meta_graph_and_variables(
        sess, [tf.saved_model.tag_constants.SERVING],
        signature_def_map=signature_def_map,
        main_op=tf.tables_initializer() if main_op_def else None,
        strip_default_attrs=True)
    builder.save()
    print('Done exporting for version {}.'.format(model_version))


def train_and_export():
    x = tf.placeholder(tf.float32, [None, 28, 28], name='x')
    y_ = tf.placeholder(tf.int32, [None], name='y_')
    x_ = tf.reshape(x, [-1, 28, 28, 1])

    conv1_w = tf.get_variable('conv1_w', shape=[5, 5, 1, 16], dtype=tf.float32)
    conv1_b = tf.get_variable('conv1_b', shape=[16], dtype=tf.float32)
    p1_x = tf.nn.max_pool(tf.nn.relu(tf.nn.conv2d(x_, conv1_w, padding='SAME') + conv1_b),
                          ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1], padding='VALID')  # 14, 14, 16

    conv2_w = tf.get_variable('conv2_w', shape=[5, 5, 16, 32], dtype=tf.float32)
    conv2_b = tf.get_variable('conv2_b', shape=[32], dtype=tf.float32)
    p2_x = tf.nn.max_pool(tf.nn.relu(tf.nn.conv2d(p1_x, conv2_w, padding='VALID') + conv2_b),
                          ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1], padding='VALID')  # 5, 5, 32

    conv3_w = tf.get_variable('conv3_w', shape=[5, 5, 32, 120], dtype=tf.float32)
    conv3_b = tf.get_variable('conv3_b', shape=[120], dtype=tf.float32)
    r3_x = tf.nn.relu(tf.nn.conv2d(p2_x, conv3_w, padding='VALID') + conv3_b)  # 1, 1, 120

    r3_x = tf.reshape(r3_x, [-1, 120])
    fc1_w = tf.get_variable('fc1_w', shape=[120, 84], dtype=tf.float32)
    fc1_b = tf.get_variable('fc1_b', shape=[84], dtype=tf.float32)
    fc1_x = tf.nn.relu(tf.matmul(r3_x, fc1_w) + fc1_b)  # 84

    fc2_w = tf.get_variable('fc2_w', shape=[84, 10], dtype=tf.float32)
    fc2_b = tf.get_variable('fc2_b', shape=[10], dtype=tf.float32)
    y = tf.matmul(fc1_x, fc2_w) + fc2_b  # 10
    y_soft = tf.nn.softmax(y)

    values, indices = tf.nn.top_k(y_soft, 10)
    table = lookup_ops.index_to_string_table_from_tensor(tf.constant([str(i) for i in range(10)]))
    prediction_classes = table.lookup(tf.dtypes.cast(indices, tf.int64))

    loss = tf.reduce_mean(tf.nn.sparse_softmax_cross_entropy_with_logits(logits=y, labels=y_))
    train_step = tf.train.GradientDescentOptimizer(0.001).minimize(loss)

    # Build the signature_def_map.
    classification_inputs = tf.saved_model.utils.build_tensor_info(x)
    classification_outputs_classes = tf.saved_model.utils.build_tensor_info(prediction_classes)
    classification_outputs_scores = tf.saved_model.utils.build_tensor_info(values)

    classification_signature = (
        tf.saved_model.signature_def_utils.build_signature_def(
            inputs={tf.saved_model.signature_constants.CLASSIFY_INPUTS: classification_inputs},
            outputs={tf.saved_model.signature_constants.CLASSIFY_OUTPUT_CLASSES: classification_outputs_classes,
                     tf.saved_model.signature_constants.CLASSIFY_OUTPUT_SCORES: classification_outputs_scores},
            method_name=tf.saved_model.signature_constants.CLASSIFY_METHOD_NAME))

    tensor_info_x = tf.saved_model.utils.build_tensor_info(x)
    tensor_info_y = tf.saved_model.utils.build_tensor_info(y_soft)

    prediction_signature = (
        tf.saved_model.signature_def_utils.build_signature_def(
            inputs={'images': tensor_info_x},
            outputs={'scores': tensor_info_y},
            method_name=tf.saved_model.signature_constants.PREDICT_METHOD_NAME
        )
    )

    signature_def_map = {
            'predict_images': prediction_signature,
            tf.saved_model.signature_constants.DEFAULT_SERVING_SIGNATURE_DEF_KEY: classification_signature,
    }

    sess.run(tf.global_variables_initializer())
    dataset = MnistData()
    main_op_def = True
    for version in range(0, 5):
        for i in range(200):
            batch = dataset.train_batch()
            _, loss_val = sess.run([train_step, loss], feed_dict={x: batch[0], y_: batch[1]})
        export_model(model_version=version, signature_def_map=signature_def_map, main_op_def=main_op_def)
        main_op_def = False


train_and_export()
