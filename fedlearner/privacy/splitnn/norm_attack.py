import tensorflow.compat.v1 as tf
from fedlearner.privacy.splitnn.marvell import KL_gradient_perturb

# Norm Attack见论文：https://arxiv.org/pdf/2102.08504.pdf

def get_norm_pred(loss, var_list, gate_gradients, marvell_protection, sumkl_threshold):
    # 获取gradient
    g = tf.gradients(loss, var_list, gate_gradients=gate_gradients)[0]
    if marvell_protection:
        g = KL_gradient_perturb(g, y, float(sumkl_threshold))
    # 计算gradient二范数，label=0和label=1的gradient二范数会存在差异
    norm_pred = tf.math.sigmoid(tf.norm(g, ord=2, axis=1))
    return norm_pred

def norm_attack_auc(loss, var_list, gate_gradients, y, marvell_protection, sumkl_threshold):
    norm_pred = get_norm_pred(loss, var_list, gate_gradients, marvell_protection, sumkl_threshold)
    norm_pred = tf.reshape(norm_pred, y.shape)
    sum_pred = tf.reduce_sum(norm_pred)
    norm_pred = norm_pred / sum_pred
    # 计算norm attack auc
    _, norm_auc = tf.metrics.auc(y, norm_pred)
    return norm_auc
