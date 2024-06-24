# Fedlearner标签保护参数说明

## embedding保护

--using_embedding_protection : bool型，是否开启embedding保护(discorloss)，True为开启

--discorloss_weight : float型，若开启embedding保护，设置embedding保护大小，值越大embedding保护效果越强，相应的对准确率影响越大，推荐设置设置范围在[0.001, 0.05]

样例：

```python
from fedlearner.privacy.splitnn.discorloss import DisCorLoss

if args.using_embedding_protection:

  discorloss = DisCorLoss().tf_distance_cor(act1_f, y, False)

  #act1_f为另一方的前传激活值，y为标签，False表示不输出debug信息

  discorloss = tf.math.reduce_mean(discorloss)

  loss += float(args.discorloss_weight) * discorloss

  #在原来的loss上添加discorloss
```

## gradient保护

--using_marvell_protection : bool型，是否开启gradient保护(Marvell)，True为开启

--sumkl_threshold : float型，若开启gradient保护，设置gradient保护大小，值越小保护效果越强，相应的对准确率影响越大，推荐设置范围在[0.1, 4.0]

样例：

train_op = model.minimize(optimizer, loss, global_step=global_step, \ 

                  marvell_protection=args.using_marvell_protection, \ 

                  marvell_threshold=float(args.sumkl_threshold), labels=y) 

// model.minimize中使用参数marvell_protection和marvell_threshold并传入labels

## fedpass保护

--using_fedpass: bool型，是否开启FedPass，True为开启

--fedpass_mean: fedpass的密钥的均值，默认值为50.0

--fedpass_scale: fedpass的密钥的方差，默认值为5.0

样例：dense_logits = fedpass(32, dense_activations， mean=float(args.fedpass_mean), scale=float(args.fedpass_scale))

## embedding攻击

--using_emb_attack : bool型，是否开启embedding攻击，True为开启

样例：

from fedlearner.privacy.splitnn.emb_attack import emb_attack_auc

if args.using_emb_attack:

  //传入另一方的前传激活值act1_f和标签y

  emb_auc = emb_attack_auc(act1_f, y)

## gradient攻击

--using_norm_attack : bool型，是否开启norm攻击，True为开启

样例：

from fedlearner.privacy.splitnn.norm_attack import norm_attack_auc

if args.using_norm_attack:

  //传入loss，另一方的前传激活值act1_f，model.minimize使用的参数gate_gradients以及标签y以及marvell参数

  norm_auc = norm_attack_auc(loss=loss, var_list=[act1_f], gate_gradients=tf.train.Optimizer.GATE_OP, y=y, marvell_protection=args.marvell_protection, sumkl_threshold=args.sumkl_threshold)
