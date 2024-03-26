import tensorflow.compat.v1 as tf

def get_norm_pred(loss, var_list, gate_gradients):
    g = tf.gradients(loss, var_list, gate_gradients=gate_gradients)[0]
    norm_pred = tf.math.sigmoid(tf.norm(g, ord=2, axis=1))
    return norm_pred

def norm_attack_auc(loss, var_list, gate_gradients, y):
    norm_pred = get_norm_pred(loss, var_list, gate_gradients)
    norm_pred = tf.reshape(norm_pred, y.shape)
    _, norm_auc = tf.metrics.auc(y, norm_pred)
    return norm_auc
