import tensorflow.compat.v1 as tf


def scale_transform(s_scalekey):
   """ 对密钥应用变换并计算缩放因子 """
   _, s_c = tf.shape(s_scalekey)[0], tf.shape(s_scalekey)[1]
   s_scale = tf.reduce_mean(s_scalekey, axis=0)
   s_scale = tf.reshape(s_scale, [1, s_c])
   return s_scale

def fedpass(hidden_feature, x, mean, scale):
   # hidden_feature: 中间层维度
   # x: 输入数据
   # mean, scale: 随机密钥的均值和方差

   # 定义层
   dense = tf.keras.layers.Dense(hidden_feature, use_bias=False, activation=None)
   encode = tf.keras.layers.Dense(hidden_feature // 4, use_bias=False, activation=None)
   decode = tf.keras.layers.Dense(hidden_feature, use_bias=False, activation=None)
   
   # 初始化随机变量
   newshape = tf.shape(x)
   skey = tf.random.normal(newshape, mean=mean, stddev=scale, dtype=x.dtype)
   bkey = tf.random.normal(newshape, mean=mean, stddev=scale, dtype=x.dtype)
   # 应用层和计算缩放因子
   s_scalekey = dense(skey)
   b_scalekey = dense(bkey)
   

   s_scale = scale_transform(s_scalekey)
   b_scale = scale_transform(b_scalekey)

   s_scale = tf.reshape(decode(tf.nn.leaky_relu(encode(s_scale))), [1, hidden_feature])
   b_scale = tf.reshape(decode(tf.nn.leaky_relu(encode(b_scale))), [1, hidden_feature])
   x = dense(x)
   x = tf.tanh(s_scale) * x + tf.tanh(b_scale)
   return x