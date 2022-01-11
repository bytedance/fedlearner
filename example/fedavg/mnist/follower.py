import os
from .model import create_model, x_train, y_train, x_test, y_test
from fedlearner.fedavg import train_from_keras_model

fed_leader_address = os.getenv("FL_LEADER_ADDRESS", "0.0.0.0:6870")
fl_name="follower"
fl_cluster = {
   "leader":{"name":"leader", "address": fed_leader_address},
   "followers":[{"name":"follower"}]
}

model = create_model()
x = x_train[len(x_train)//2:]
y = y_train[len(y_train)//2:]
train_from_keras_model(model,
                       x,
                       y,
                       batch_size=30,
                       epochs=20,
                       fl_name=fl_name,
                       fl_cluster=fl_cluster,
                       steps_per_sync=10)

model.evaluate(x_test, y_test)