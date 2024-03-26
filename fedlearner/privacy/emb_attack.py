import tensorflow.compat.v1 as tf

# Emb Attack见论文：https://arxiv.org/pdf/2203.01451.pdf

def get_emb_pred(emb):
    mean_emb = tf.reduce_mean(emb, axis=0)
    # 规范化处理emb
    mean_reduced_emb = emb - mean_emb
    # 对规范化矩阵做奇异值分解
    s, u, v = tf.linalg.svd(mean_reduced_emb)
    # 最大奇异值对应的右奇异向量与矩阵做内积
    top_singular_vector = tf.transpose(v)[0]
    pred = tf.linalg.matvec(mean_reduced_emb, top_singular_vector)
    # 内积之后的结果可以分为两个簇
    pred = tf.math.sigmoid(pred)
    return pred

def emb_attack_auc(emb, y):
    emb_pred = get_emb_pred(emb)
    emb_pred = tf.reshape(emb_pred, y.shape)
    # 计算emb attack auc
    _, emb_auc = tf.metrics.auc(y, emb_pred)
    return emb_auc
