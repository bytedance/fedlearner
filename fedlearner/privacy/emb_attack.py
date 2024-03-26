import tensorflow.compat.v1 as tf

def get_emb_pred(emb):
    mean_emb = tf.reduce_mean(emb, axis=0)
    mean_reduced_emb = emb - mean_emb
    s, u, v = tf.linalg.svd(mean_reduced_emb)
    top_singular_vector = tf.transpose(v)[0]
    pred = tf.linalg.matvec(mean_reduced_emb, top_singular_vector)
    pred = tf.math.sigmoid(pred)
    return pred

def emb_attack_auc(emb, y):
    emb_pred = get_emb_pred(emb)
    emb_pred = tf.reshape(emb_pred, y.shape)
    _, emb_auc = tf.metrics.auc(y, emb_pred)
    return emb_auc
