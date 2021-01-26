package operator

import (
	"context"
	"fmt"
	"sync"

	log "github.com/sirupsen/logrus"
	v1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/api/meta"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/labels"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/types"
	clientset "k8s.io/client-go/kubernetes"
	"k8s.io/client-go/tools/record"
)

const (
	FailedCreateServiceReason     = "FailedCreateService"
	SuccessfulCreateServiceReason = "SuccessfulCreateService"
	FailedDeleteServiceReason     = "FailedDeleteService"
	SuccessfulDeleteServiceReason = "SuccessfulDeleteService"
)

// ServiceControlInterface is an interface that knows how to add or delete Services
// created as an interface to allow testing.
type ServiceControlInterface interface {
	// CreateServices creates new Services according to the spec.
	CreateServices(ctx context.Context, namespace string, service *v1.Service, object runtime.Object) error
	// CreateServicesWithControllerRef creates new services according to the spec, and sets object as the service's controller.
	CreateServicesWithControllerRef(ctx context.Context, namespace string, service *v1.Service, object runtime.Object, controllerRef *metav1.OwnerReference) error
	// PatchService patches the service.
	PatchService(ctx context.Context, namespace, name string, data []byte) error
	// DeleteService deletes the service identified by serviceID.
	DeleteService(ctx context.Context, namespace, serviceID string, object runtime.Object) error
}

func validateControllerRef(controllerRef *metav1.OwnerReference) error {
	if controllerRef == nil {
		return fmt.Errorf("controllerRef is nil")
	}
	if len(controllerRef.APIVersion) == 0 {
		return fmt.Errorf("controllerRef has empty APIVersion")
	}
	if len(controllerRef.Kind) == 0 {
		return fmt.Errorf("controllerRef has empty Kind")
	}
	if controllerRef.Controller == nil || !*controllerRef.Controller {
		return fmt.Errorf("controllerRef.Controller is not set to true")
	}
	if controllerRef.BlockOwnerDeletion == nil || !*controllerRef.BlockOwnerDeletion {
		return fmt.Errorf("controllerRef.BlockOwnerDeletion is not set")
	}
	return nil
}

// RealServiceControl is the default implementation of ServiceControlInterface.
type RealServiceControl struct {
	KubeClient clientset.Interface
	Recorder   record.EventRecorder
}

func (r RealServiceControl) PatchService(ctx context.Context, namespace, name string, data []byte) error {
	_, err := r.KubeClient.CoreV1().Services(namespace).Patch(ctx, name, types.StrategicMergePatchType, data, metav1.PatchOptions{})
	return err
}

func (r RealServiceControl) CreateServices(ctx context.Context, namespace string, service *v1.Service, object runtime.Object) error {
	return r.createServices(ctx, namespace, service, object, nil)
}

func (r RealServiceControl) CreateServicesWithControllerRef(ctx context.Context, namespace string, service *v1.Service, controllerObject runtime.Object, controllerRef *metav1.OwnerReference) error {
	if err := validateControllerRef(controllerRef); err != nil {
		return err
	}
	return r.createServices(ctx, namespace, service, controllerObject, controllerRef)
}

func (r RealServiceControl) createServices(ctx context.Context, namespace string, service *v1.Service, object runtime.Object, controllerRef *metav1.OwnerReference) error {
	if labels.Set(service.Labels).AsSelectorPreValidated().Empty() {
		return fmt.Errorf("unable to create Services, no labels")
	}
	serviceWithOwner, err := getServiceFromTemplate(service, object, controllerRef)
	if err != nil {
		r.Recorder.Eventf(object, v1.EventTypeWarning, FailedCreateServiceReason, "Error creating: %v", err)
		return fmt.Errorf("unable to create services: %v", err)
	}

	newService, err := r.KubeClient.CoreV1().Services(namespace).Create(ctx, serviceWithOwner, metav1.CreateOptions{})
	if err != nil {
		r.Recorder.Eventf(object, v1.EventTypeWarning, FailedCreateServiceReason, "Error creating: %v", err)
		return fmt.Errorf("unable to create services: %v", err)
	}

	accessor, err := meta.Accessor(object)
	if err != nil {
		log.Errorf("parentObject does not have ObjectMeta, %v", err)
		return nil
	}
	log.Infof("Controller %v created service %v", accessor.GetName(), newService.Name)
	r.Recorder.Eventf(object, v1.EventTypeNormal, SuccessfulCreateServiceReason, "Created service: %v", newService.Name)

	return nil
}

// DeleteService deletes the service identified by serviceID.
func (r RealServiceControl) DeleteService(ctx context.Context, namespace, serviceID string, object runtime.Object) error {
	accessor, err := meta.Accessor(object)
	if err != nil {
		return fmt.Errorf("object does not have ObjectMeta, %v", err)
	}
	service, err := r.KubeClient.CoreV1().Services(namespace).Get(ctx, serviceID, metav1.GetOptions{})
	if err != nil {
		if errors.IsNotFound(err) {
			return nil
		}
		return err
	}
	if service.DeletionTimestamp != nil {
		log.Infof("service %s/%s is terminating, skip deleting", service.Namespace, service.Name)
		return nil
	}
	log.Infof("Controller %v deleting service %v/%v", accessor.GetName(), namespace, serviceID)
	if err := r.KubeClient.CoreV1().Services(namespace).Delete(ctx, serviceID, metav1.DeleteOptions{}); err != nil {
		r.Recorder.Eventf(object, v1.EventTypeWarning, FailedDeleteServiceReason, "Error deleting: %v", err)
		return fmt.Errorf("unable to delete service: %v", err)
	}

	r.Recorder.Eventf(object, v1.EventTypeNormal, SuccessfulDeleteServiceReason, "Deleted service: %v", serviceID)

	return nil
}

type FakeServiceControl struct {
	sync.Mutex
	Templates         []v1.Service
	ControllerRefs    []metav1.OwnerReference
	DeleteServiceName []string
	Patches           [][]byte
	Err               error
	CreateLimit       int
	CreateCallCount   int
}

var _ ServiceControlInterface = &FakeServiceControl{}

func (f *FakeServiceControl) PatchService(ctx context.Context, namespace, name string, data []byte) error {
	f.Lock()
	defer f.Unlock()
	f.Patches = append(f.Patches, data)
	if f.Err != nil {
		return f.Err
	}
	return nil
}

func (f *FakeServiceControl) CreateServices(ctx context.Context, namespace string, service *v1.Service, object runtime.Object) error {
	f.Lock()
	defer f.Unlock()
	f.CreateCallCount++
	if f.CreateLimit != 0 && f.CreateCallCount > f.CreateLimit {
		return fmt.Errorf("not creating service, limit %d already reached (create call %d)", f.CreateLimit, f.CreateCallCount)
	}
	f.Templates = append(f.Templates, *service)
	if f.Err != nil {
		return f.Err
	}
	return nil
}

func (f *FakeServiceControl) CreateServicesWithControllerRef(ctx context.Context, namespace string, service *v1.Service, object runtime.Object, controllerRef *metav1.OwnerReference) error {
	f.Lock()
	defer f.Unlock()
	f.CreateCallCount++
	if f.CreateLimit != 0 && f.CreateCallCount > f.CreateLimit {
		return fmt.Errorf("not creating service, limit %d already reached (create call %d)", f.CreateLimit, f.CreateCallCount)
	}
	f.Templates = append(f.Templates, *service)
	f.ControllerRefs = append(f.ControllerRefs, *controllerRef)
	if f.Err != nil {
		return f.Err
	}
	return nil
}

func (f *FakeServiceControl) DeleteService(ctx context.Context, namespace string, serviceID string, object runtime.Object) error {
	f.Lock()
	defer f.Unlock()
	f.DeleteServiceName = append(f.DeleteServiceName, serviceID)
	if f.Err != nil {
		return f.Err
	}
	return nil
}

func (f *FakeServiceControl) Clear() {
	f.Lock()
	defer f.Unlock()
	f.DeleteServiceName = []string{}
	f.Templates = []v1.Service{}
	f.ControllerRefs = []metav1.OwnerReference{}
	f.Patches = [][]byte{}
	f.CreateLimit = 0
	f.CreateCallCount = 0
}

func getServiceFromTemplate(template *v1.Service, parentObject runtime.Object, controllerRef *metav1.OwnerReference) (*v1.Service, error) {
	service := template.DeepCopy()
	if controllerRef != nil {
		service.OwnerReferences = append(service.OwnerReferences, *controllerRef)
	}
	return service, nil
}
