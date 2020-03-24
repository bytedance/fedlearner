package controller

import (
	"fmt"
	"strings"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"

	"github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/apis/fedlearner.k8s.io/v1alpha1"
)

const (
	AppNameLabel = "app-name"
	RoleLabel    = "role"

	RoleLeader = "Leader"
)

func GenIndexName(appName, r, rt, index string) string {
	n := appName + "-" + r + "-" + rt + "-" + index
	return strings.Replace(n, "/", "-", -1)
}

func GenReplicaName(appName, r, rt string) string {
	n := appName + "-" + r + "-" + rt
	return strings.Replace(n, "/", "-", -1)
}

func GenName(appName, r string) string {
	n := appName + "-" + r
	return strings.Replace(n, "/", "-", -1)
}

func GenLabels(app *v1alpha1.FLApp) map[string]string {
	return map[string]string{
		AppNameLabel: strings.Replace(app.Name, "/", "-", -1),
		RoleLabel:    strings.ToLower(app.Spec.Role),
	}
}

func RecheckDeletionTimestamp(getObject func() (metav1.Object, error)) func() error {
	return func() error {
		obj, err := getObject()
		if err != nil {
			return fmt.Errorf("can't recheck DeletionTimestamp: %v", err)
		}
		if obj.GetDeletionTimestamp() != nil {
			return fmt.Errorf("%v/%v has just been deleted at %v", obj.GetNamespace(), obj.GetName(), obj.GetDeletionTimestamp())
		}
		return nil
	}
}

// GetPortFromApp gets the port of tensorflow container.
func GetPortFromApp(app *v1alpha1.FLApp, rtype v1alpha1.FLReplicaType) (int32, error) {
	containers := app.Spec.FLReplicaSpecs[rtype].Template.Spec.Containers
	for _, container := range containers {
		if container.Name == v1alpha1.DefaultContainerName {
			ports := container.Ports
			for _, port := range ports {
				if port.Name == v1alpha1.DefaultPortName {
					return port.ContainerPort, nil
				}
			}
		}
	}
	return -1, fmt.Errorf("port not found")
}

func IsLeader(role string) bool {
	return role == RoleLeader
}
