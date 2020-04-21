# Fedlearner Operator

## Installation

```
helm template ./deploy/charts/fedlearner --namespace leader | kubectl apply -f
helm template ./deploy/charts/fedlearner --namespace follower | kubectl apply -f
kubectl apply -f ./deploy/charts/manifests/
```
