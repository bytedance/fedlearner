package controller

import (
	"fmt"
	"strconv"
	"strings"

	v1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/labels"
	"k8s.io/klog"

	"github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/apis/fedlearner.k8s.io/v1alpha1"
)

// reconcileServices checks and updates services for each given TFReplicaSpec.
// It will requeue the flapp in case of an error while creating/deleting services.
func (am *appManager) reconcileService(app *v1alpha1.FLApp) error {
	services, err := am.getServicesForApp(app)
	if err != nil {
		return err
	}

	for rtype, spec := range app.Spec.FLReplicaSpecs {
		err = am.reconcileServicesWithType(app, services, rtype, spec)
		if err != nil {
			klog.Errorf("reconcileServices error: %v", err)
			return err
		}
	}
	return nil
}

func (am *appManager) reconcileServicesWithType(
	app *v1alpha1.FLApp,
	services []*v1.Service,
	rtype v1alpha1.FLReplicaType,
	spec v1alpha1.ReplicaSpec) error {

	// Convert TFReplicaType to lower string.
	rt := strings.ToLower(string(rtype))

	replicas := int(*spec.Replicas)
	// Get all services for the type rt.
	services, err := FilterServicesForReplicaType(services, rt)
	if err != nil {
		return err
	}

	serviceSlices := am.makeServiceSlicesByIndex(services, replicas)

	for index, serviceSlice := range serviceSlices {
		switch serviceCount := len(serviceSlice); serviceCount {
		case 0:
			// Need to create a new service
			klog.Infof("need to create new service for %s %d", rtype, index)
			if err = am.createNewService(app, rtype, spec, strconv.Itoa(index)); err != nil {
				return err
			}
		case 1:
			// Check the status of current service
			service := serviceSlice[0]
			updateAppLocalStatuses(app, rtype, service)
		default:
			// Kill unnecessary services
			for i := 1; i < serviceCount; i++ {
				service := serviceSlice[i]
				if err = am.serviceControl.DeleteService(service.Namespace, service.Name, app); err != nil {
					return err
				}
			}
		}
	}
	return nil
}

// getServicesForJob returns the set of services that this job should manage.
// It also reconciles ControllerRef by adopting/orphaning.
// Note that the returned services are pointers into the cache.
func (am *appManager) getServicesForApp(app *v1alpha1.FLApp) ([]*v1.Service, error) {
	// Create selector
	selector, err := metav1.LabelSelectorAsSelector(&metav1.LabelSelector{
		MatchLabels: GenLabels(app),
	})

	if err != nil {
		return nil, fmt.Errorf("couldn't convert App selector: %v", err)
	}
	// List all services to include those that don't match the selector anymore
	// but have a ControllerRef pointing to this controller.
	services, err := am.serviceLister.Services(app.GetNamespace()).List(labels.Everything())
	if err != nil {
		return nil, err
	}

	// If any adoptions are attempted, we should first recheck for deletion
	// with an uncached quorum read sometime after listing services (see #42639).
	canAdoptFunc := RecheckDeletionTimestamp(func() (metav1.Object, error) {
		fresh, err := am.crdClient.FedlearnerV1alpha1().FLApps(app.GetNamespace()).Get(app.GetName(), metav1.GetOptions{})
		if err != nil {
			return nil, err
		}
		if fresh.GetUID() != app.GetUID() {
			return nil, fmt.Errorf("original Job %v/%v is gone: got uid %v, wanted %v", app.GetNamespace(), app.GetName(), fresh.GetUID(), app.GetUID())
		}
		return fresh, nil
	})
	cm := NewServiceControllerRefManager(am.serviceControl, app, selector, am.GetAPIGroupVersionKind(), canAdoptFunc)
	return cm.ClaimServices(services)
}

// FilterServicesForReplicaType returns service belong to a replicaType.
func FilterServicesForReplicaType(services []*v1.Service, replicaType string) ([]*v1.Service, error) {
	var result []*v1.Service

	replicaSelector := &metav1.LabelSelector{
		MatchLabels: make(map[string]string),
	}

	replicaSelector.MatchLabels[flReplicaTypeLabel] = replicaType

	for _, service := range services {
		selector, err := metav1.LabelSelectorAsSelector(replicaSelector)
		if err != nil {
			return nil, err
		}
		if !selector.Matches(labels.Set(service.Labels)) {
			continue
		}
		result = append(result, service)
	}
	return result, nil
}

// createNewService creates a new service for the given index and type.
func (am *appManager) createNewService(app *v1alpha1.FLApp, rtype v1alpha1.FLReplicaType, spec v1alpha1.ReplicaSpec, index string) error {
	rt := strings.ToLower(string(rtype))
	controllerRef := am.GenOwnerReference(app)

	// Append tfReplicaTypeLabel and tfReplicaIndexLabel labels.
	labels := GenLabels(app)
	labels[flReplicaTypeLabel] = rt
	labels[flReplicaIndexLabel] = index

	port, err := GetPortFromApp(app, rtype)
	if err != nil {
		return err
	}

	service := &v1.Service{
		Spec: v1.ServiceSpec{
			ClusterIP: "None",
			Selector:  labels,
			Ports: []v1.ServicePort{
				{
					Name: v1alpha1.DefaultPortName,
					Port: port,
				},
			},
		},
	}

	service.Name = GenIndexName(app.Name, strings.ToLower(app.Spec.Role), rt, index)
	service.Labels = labels

	err = am.serviceControl.CreateServicesWithControllerRef(app.Namespace, service, app, controllerRef)
	if err != nil && errors.IsAlreadyExists(err) {
		return nil
	}
	return err
}

// makeServiceSlicesByIndex returns a slice, which element is the slice of service.
// Assume the return object is serviceSlices, then serviceSlices[i] is an
// array of pointers to services corresponding to Services for replica i.
func (am *appManager) makeServiceSlicesByIndex(services []*v1.Service, replicas int) [][]*v1.Service {
	serviceSlices := make([][]*v1.Service, replicas)
	for _, service := range services {
		if _, ok := service.Labels[flReplicaIndexLabel]; !ok {
			klog.Warning("The service do not have the index label.")
			continue
		}
		index, err := strconv.Atoi(service.Labels[flReplicaIndexLabel])
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
