import tensorflow.compat.v1 as tf
from collections import deque


def oprange(inputs, outputs):
    inputs = inputs if inputs is not None else []
    outputs = outputs if outputs is not None else []
    input_name_set = set([i.op.name for i in inputs])
    que = deque(outputs)
    ops = []
    while len(que) > 0:
        o = que.popleft()
        ops.append(o)
        for i in o.op.inputs:
            if (i.op.name not in input_name_set):
                input_name_set.add(i.op.name)
                que.append(i.op.outputs[0]) 
        for op in o.op.control_inputs:
            if (op.name not in input_name_set):
                input_name_set.add(op.name)
                que.append(op.outputs[0]) 

    ops += inputs
    return ops
            
if __name__ == "__main__":
    a1 = tf.placeholder(tf.int32, name="a1")
    a2 = tf.placeholder(tf.int32, name="a2")
    a3 = tf.placeholder(tf.int32, name="a3")
    b1 = tf.add(a1, a2, name="b1")
    b2 = tf.add(a2, a3, name="b2")
    c1 = tf.add(b1, b2, name="c1")
    with tf.control_dependencies([c1]):
        e = tf.add_n([a1, b1], name="e")

    for n in oprange([b2], [e]):
        print(n)
