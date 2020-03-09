package controller

import (
	v1 "k8s.io/api/core/v1"
	apiequality "k8s.io/apimachinery/pkg/api/equality"

	"github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/apis/fedlearner.k8s.io/v1alpha1"
)

// NOTE: this func will overwrite the whole app status, may raise race condition
// if multiple clients concurrently updates status.
func (am *appManager) setStatus(app *v1alpha1.FLApp) error {
	_, err := am.appStatusUpdater.UpdateStatusWithRetry(app, func(mutatingApp *v1alpha1.FLApp) bool {
		if apiequality.Semantic.DeepEqual(app.Status, mutatingApp.Status) {
			return false
		}
		app.Status.DeepCopyInto(&mutatingApp.Status)
		return true
	})
	return err
}

// updateAppReplicaStatuses updates the AppReplicaStatuses according to the pod.
func updateAppReplicaStatuses(app *v1alpha1.FLApp, rtype v1alpha1.FLReplicaType, pod *v1.Pod) {
	status := app.Status.FLReplicaStatus[rtype]
	replicaStatus := status.DeepCopy()
	switch pod.Status.Phase {
	case v1.PodRunning:
		replicaStatus.Active.Insert(pod.Name)
	case v1.PodSucceeded:
		replicaStatus.Active.Delete(pod.Name)
		replicaStatus.Succeeded.Insert(pod.Name)
	case v1.PodFailed:
		replicaStatus.Active.Delete(pod.Name)
		replicaStatus.Failed.Insert(pod.Name)
	}
	app.Status.FLReplicaStatus[rtype] = *replicaStatus
}

func updateAppLocalStatuses(app *v1alpha1.FLApp, rtype v1alpha1.FLReplicaType, service *v1.Service) {
	name := service.Name
	status := app.Status.FLReplicaStatus[rtype]
	replicaStatus := status.DeepCopy()
	replicaStatus.Local.Insert(name)
	app.Status.FLReplicaStatus[rtype] = *replicaStatus
}
