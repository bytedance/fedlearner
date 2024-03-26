import tensorflow.compat.v1 as tf

# Norm Attack见论文：https://arxiv.org/pdf/2102.08504.pdf

def get_norm_pred(loss, var_list, gate_gradients):
    # 获取gradient
    g = tf.gradients(loss, var_list, gate_gradients=gate_gradients)[0]
    # 计算gradient二范数，label=0和label=1的gradient二范数会存在差异
    norm_pred = tf.math.sigmoid(tf.norm(g, ord=2, axis=1))
    return norm_pred

def norm_attack_auc(loss, var_list, gate_gradients, y):
    norm_pred = get_norm_pred(loss, var_list, gate_gradients)
    norm_pred = tf.reshape(norm_pred, y.shape)
    # 计算norm attack auc
    _, norm_auc = tf.metrics.auc(y, norm_pred)
    return norm_auc
