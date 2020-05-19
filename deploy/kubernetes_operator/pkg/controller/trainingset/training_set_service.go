package trainingset

import (
	"context"
	"fmt"
	"strconv"
	"strings"

	"github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/apis/fedlearner.k8s.io/v1alpha2"
	"github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/controller"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/labels"
	"k8s.io/klog"
)

func (c *Controller) reconcileServices(ctx context.Context, ts *v1alpha2.TrainingSet) error {
	services, err := c.getTrainingSetServices(ctx, ts)
	if err != nil {
		return err
	}

	replicas := int(*ts.Spec.Replicas)
	serviceSlices := c.makeServiceSlicesByIndex(services, replicas)
	if err := c.reconcileServiceSlices(ctx, ts, serviceSlices); err != nil {
		return err
	}

	return nil
}

func (c *Controller) reconcileServiceSlices(ctx context.Context, ts *v1alpha2.TrainingSet, serviceSlices [][]*corev1.Service) error {
	for index, serviceSlice := range serviceSlices {
		switch serviceCount := len(serviceSlice); serviceCount {
		case 0:
			// Need to create a new service
			klog.Infof("need to create new service for %s %d", ts.Name, index)
			if err := c.createService(ctx, ts, index); err != nil {
				return err
			}
		case 1:
			// Check the status of current service
			service := serviceSlice[0]
			updateTrainingSetLocalStatus(ts, service)
		default:
			// Kill unnecessary services
			for i := 1; i < serviceCount; i++ {
				service := serviceSlice[i]
				if err := c.serviceControl.DeleteService(ctx, service.Namespace, service.Name, ts); err != nil {
					return err
				}
			}
		}
	}

	return nil
}

func (c *Controller) createService(ctx context.Context, ts *v1alpha2.TrainingSet, idx int) error {
	boolPtr := func(b bool) *bool { return &b }
	controllerRef := &metav1.OwnerReference{
		APIVersion:         v1alpha2.SchemeGroupVersion.String(),
		Kind:               v1alpha2.Kind,
		Name:               ts.Name,
		UID:                ts.UID,
		BlockOwnerDeletion: boolPtr(true),
		Controller:         boolPtr(true),
	}

	port, err := getPortFromTrainingSet(ts)
	if err != nil {
		return err
	}

	service := &corev1.Service{
		Spec: corev1.ServiceSpec{
			ClusterIP: "None",
			Selector:  ts.Spec.Selector.MatchLabels,
			Ports: []corev1.ServicePort{
				{
					Name: v1alpha2.DefaultPortName,
					Port: port,
				},
			},
		},
	}

	service.Name = fmt.Sprintf("%s-%d", ts.Name, idx)
	service.Labels = ts.Spec.Selector.MatchLabels

	if service.Labels == nil {
		service.Labels = map[string]string{}
	}
	service.Labels[trainingSetIndexLabel] = fmt.Sprintf("%d", idx)
	service.Labels[trainingSetTypeLabel] = strings.ToLower(string(ts.Spec.Type))

	err = c.serviceControl.CreateServicesWithControllerRef(ctx, ts.Namespace, service, ts, controllerRef)
	if err != nil && errors.IsAlreadyExists(err) {
		return nil
	}

	return nil
}

func (c *Controller) getTrainingSetServices(ctx context.Context, ts *v1alpha2.TrainingSet) ([]*corev1.Service, error) {
	selector, err := metav1.LabelSelectorAsSelector(ts.Spec.Selector)
	if err != nil {
		return nil, err
	}

	services, err := c.servicesLister.Services(ts.Namespace).List(labels.Everything())
	if err != nil {
		return nil, err
	}

	cm := controller.NewServiceControllerRefManager(c.serviceControl, ts, selector, v1alpha2.SchemeGroupVersionKind, controller.RecheckDeletionTimestamp(func() (metav1.Object, error) {
		new, err := c.crdClient.FedlearnerV1alpha2().TrainingSets(ts.Namespace).Get(ts.Name, metav1.GetOptions{})
		if err != nil {
			return nil, err
		}

		if new.GetUID() != ts.GetUID() {
			return nil, fmt.Errorf("original %v/%v is gone: got uid %v, wanted %v", ts.Namespace, ts.Name, new.GetUID(), ts.GetUID())
		}

		return new, nil
	}))

	return cm.ClaimServices(ctx, services)
}

// makeServiceSlicesByIndex returns a slice, which element is the slice of service.
// Assume the return object is serviceSlices, then serviceSlices[i] is an
// array of pointers to services corresponding to Services for replica i.
func (c *Controller) makeServiceSlicesByIndex(services []*corev1.Service, replicas int) [][]*corev1.Service {
	serviceSlices := make([][]*corev1.Service, replicas)
	for _, service := range services {
		val, ok := service.Labels[trainingSetIndexLabel]
		if !ok {
			// compatible with previous v1alpha2's pod.
			val, ok = service.Labels[deprecatedFlReplicaIndexLabel]
			if !ok {
				klog.Warningln("The pod do not have the index label.")
				continue
			}
		}

		index, err := strconv.Atoi(val)
		if err != nil {
			klog.Warningf("Error when strconv.Atoi: %v", err)
			continue
		}
		if index < 0 || index >= replicas {
			klog.Warningf("The label index is not expected: %d", index)
		} else {
			serviceSlices[index] = append(serviceSlices[index], service)
		}
	}
	return serviceSlices
}

// getPortFromTrainingSet gets the port of tensorflow container.
func getPortFromTrainingSet(ts *v1alpha2.TrainingSet) (int32, error) {
	containers := ts.Spec.Template.Spec.Containers
	for _, container := range containers {
		if container.Name == v1alpha2.DefaultContainerName {
			ports := container.Ports
			for _, port := range ports {
				if port.Name == v1alpha2.DefaultPortName {
					return port.ContainerPort, nil
				}
			}
		}
	}
	return -1, fmt.Errorf("port not found")
}
