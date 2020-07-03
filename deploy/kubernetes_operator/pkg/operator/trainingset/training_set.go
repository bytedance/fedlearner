package trainingset

import (
	"context"
	"fmt"
	"time"

	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	utilruntime "k8s.io/apimachinery/pkg/util/runtime"
	"k8s.io/apimachinery/pkg/util/wait"
	"k8s.io/client-go/informers"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/kubernetes/scheme"
	typedcorev1 "k8s.io/client-go/kubernetes/typed/core/v1"
	corev1listers "k8s.io/client-go/listers/core/v1"
	"k8s.io/client-go/tools/cache"
	"k8s.io/client-go/tools/record"
	"k8s.io/client-go/util/workqueue"
	"k8s.io/klog"

	"github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/apis/fedlearner.k8s.io/v1alpha2"
	crdclientset "github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/client/clientset/versioned"
	crdinformers "github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/client/informers/externalversions"
	fllisters "github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/client/listers/fedlearner.k8s.io/v1alpha2"
	"github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/operator"
)

const controllerAgentName = "trainingset-controller"

const (
	// SuccessSynced is used as part of the Event 'reason' when a TrainingSet is synced
	SuccessSynced = "Synced"
	// ErrResourceExists is used as part of the Event 'reason' when a TrainingSet fails
	// to sync due to a Deployment of the same name already existing.
	ErrResourceExists = "ErrResourceExists"

	// MessageResourceExists is the message used for Events when a resource
	// fails to sync due to a Deployment already existing
	MessageResourceExists = "Resource %q already exists and is not managed by TrainingSet"
	// MessageResourceSynced is the message used for an Event fired when a TrainingSet
	// is synced successfully
	MessageResourceSynced = "TrainingSet synced successfully"
)

// Controller is the controller implementation for TrainingSet resources
type Controller struct {
	// kubeclientset is a standard kubernetes clientset
	kubeclientset kubernetes.Interface
	crdClient     crdclientset.Interface

	podControl     operator.PodControlInterface
	serviceControl operator.ServiceControlInterface

	trainingSetsLister fllisters.TrainingSetLister
	trainingSetsSynced cache.InformerSynced
	podsLister         corev1listers.PodLister
	podsSynced         cache.InformerSynced
	servicesLister     corev1listers.ServiceLister
	servicesSynced     cache.InformerSynced

	// workqueue is a rate limited work queue. This is used to queue work to be
	// processed instead of performing it as soon as a change happens. This
	// means we can ensure we only process a fixed amount of resources at a
	// time, and makes it easy to ensure we are never processing the same item
	// simultaneously in two different workers.
	workqueue workqueue.RateLimitingInterface
	// recorder is an event recorder for recording Event resources to the
	// Kubernetes API.
	recorder record.EventRecorder
}

// NewController returns a new sample controller
func NewController(
	kubeclientset kubernetes.Interface,
	crdClient crdclientset.Interface,
// trainingSetInformer flinformers.TrainingSetInformer,
	sharedInformerFactory informers.SharedInformerFactory,
	crdSharedInformerFactory crdinformers.SharedInformerFactory,
) *Controller {

	// Create event broadcaster
	// Add sample-controller types to the default Kubernetes Scheme so Events can be
	// logged for sample-controller types.
	utilruntime.Must(v1alpha2.AddToScheme(scheme.Scheme))
	klog.V(4).Info("Creating event broadcaster")
	eventBroadcaster := record.NewBroadcaster()
	eventBroadcaster.StartLogging(klog.Infof)
	eventBroadcaster.StartRecordingToSink(&typedcorev1.EventSinkImpl{Interface: kubeclientset.CoreV1().Events("")})
	recorder := eventBroadcaster.NewRecorder(scheme.Scheme, corev1.EventSource{Component: controllerAgentName})

	controller := &Controller{
		kubeclientset:      kubeclientset,
		crdClient:          crdClient,
		trainingSetsLister: crdSharedInformerFactory.Fedlearner().V1alpha2().TrainingSets().Lister(),
		trainingSetsSynced: crdSharedInformerFactory.Fedlearner().V1alpha2().TrainingSets().Informer().HasSynced,
		podsLister:         sharedInformerFactory.Core().V1().Pods().Lister(),
		podsSynced:         sharedInformerFactory.Core().V1().Pods().Informer().HasSynced,
		servicesLister:     sharedInformerFactory.Core().V1().Services().Lister(),
		servicesSynced:     sharedInformerFactory.Core().V1().Services().Informer().HasSynced,
		workqueue:          workqueue.NewNamedRateLimitingQueue(workqueue.DefaultControllerRateLimiter(), "TrainingSets"),
		recorder:           recorder,

		podControl: operator.RealPodControl{
			KubeClient: kubeclientset,
			Recorder:   recorder,
		},
		serviceControl: operator.RealServiceControl{
			KubeClient: kubeclientset,
			Recorder:   recorder,
		},
	}

	klog.Info("Setting up event handlers")

	crdSharedInformerFactory.Fedlearner().V1alpha2().TrainingSets().Informer().AddEventHandler(cache.ResourceEventHandlerFuncs{
		AddFunc: controller.enqueueTrainingSet,
		UpdateFunc: func(old, new interface{}) {
			controller.enqueueTrainingSet(new)
		},
	})

	sharedInformerFactory.Core().V1().Services().Informer().AddEventHandler(cache.ResourceEventHandlerFuncs{
		AddFunc: controller.handleObject,
		UpdateFunc: func(old, new interface{}) {
			controller.handleObject(new)
		},
		DeleteFunc: controller.handleObject,
	})

	sharedInformerFactory.Core().V1().Pods().Informer().AddEventHandler(cache.ResourceEventHandlerFuncs{
		AddFunc: controller.handleObject,
		UpdateFunc: func(old, new interface{}) {
			controller.handleObject(new)
		},
		DeleteFunc: controller.handleObject,
	})

	return controller
}

// Run will set up the event handlers for types we are interested in, as well
// as syncing informer caches and starting workers. It will block until stopCh
// is closed, at which point it will shutdown the workqueue and wait for
// workers to finish processing their current work items.
func (c *Controller) Run(threadiness int, stopCh <-chan struct{}) error {
	defer utilruntime.HandleCrash()
	defer c.workqueue.ShutDown()

	// Start the informer factories to begin populating the informer caches
	klog.Info("Starting TrainingSet controller")

	// Wait for the caches to be synced before starting workers
	klog.Info("Waiting for informer caches to sync")
	if ok := cache.WaitForCacheSync(
		stopCh,
		c.podsSynced,
		c.servicesSynced,
		c.trainingSetsSynced,
	); !ok {
		return fmt.Errorf("failed to wait for caches to sync")
	}

	klog.Info("Starting workers")
	// Launch two workers to process TrainingSet resources
	for i := 0; i < threadiness; i++ {
		go wait.Until(c.runWorker, time.Second, stopCh)
	}

	klog.Info("Started workers")
	<-stopCh
	klog.Info("Shutting down workers")

	return nil
}

// runWorker is a long-running function that will continually call the
// processNextWorkItem function in order to read and process a message on the
// workqueue.
func (c *Controller) runWorker() {
	for c.processNextWorkItem() {
	}
}

// processNextWorkItem will read a single work item off the workqueue and
// attempt to process it, by calling the syncHandler.
func (c *Controller) processNextWorkItem() bool {
	obj, shutdown := c.workqueue.Get()

	if shutdown {
		return false
	}

	// We wrap this block in a func so we can defer c.workqueue.Done.
	err := func(obj interface{}) error {
		// We call Done here so the workqueue knows we have finished
		// processing this item. We also must remember to call Forget if we
		// do not want this work item being re-queued. For example, we do
		// not call Forget if a transient error occurs, instead the item is
		// put back on the workqueue and attempted again after a back-off
		// period.
		defer c.workqueue.Done(obj)
		var key string
		var ok bool
		// We expect strings to come off the workqueue. These are of the
		// form namespace/name. We do this as the delayed nature of the
		// workqueue means the items in the informer cache may actually be
		// more up to date that when the item was initially put onto the
		// workqueue.
		if key, ok = obj.(string); !ok {
			// As the item in the workqueue is actually invalid, we call
			// Forget here else we'd go into a loop of attempting to
			// process a work item that is invalid.
			c.workqueue.Forget(obj)
			utilruntime.HandleError(fmt.Errorf("expected string in workqueue but got %#v", obj))
			return nil
		}
		// Run the syncHandler, passing it the namespace/name string of the
		// TrainingSet resource to be synced.
		if err := c.syncHandler(key); err != nil {
			// Put the item back on the workqueue to handle any transient errors.
			c.workqueue.AddRateLimited(key)
			return fmt.Errorf("error syncing '%s': %s, requeuing", key, err.Error())
		}
		// Finally, if no error occurs we Forget this item so it does not
		// get queued again until another change happens.
		c.workqueue.Forget(obj)
		klog.Infof("Successfully synced '%s'", key)
		return nil
	}(obj)

	if err != nil {
		utilruntime.HandleError(err)
		return true
	}

	return true
}

// syncHandler compares the actual state with the desired, and attempts to
// converge the two. It then updates the Status block of the TrainingSet resource
// with the current status of the resource.
func (c *Controller) syncHandler(key string) error {
	// Convert the namespace/name string into a distinct namespace and name
	namespace, name, err := cache.SplitMetaNamespaceKey(key)
	if err != nil {
		utilruntime.HandleError(fmt.Errorf("invalid resource key: %s", key))
		return nil
	}

	ts, err := c.trainingSetsLister.TrainingSets(namespace).Get(name)
	if err != nil {
		if errors.IsNotFound(err) {
			utilruntime.HandleError(fmt.Errorf("trainingset '%s' in work queue no longer exists", key))
			return nil
		}

		return err
	}

	tsCopy := ts.DeepCopy()
	scheme.Scheme.Default(tsCopy)

	// FIXME(draven): update trainingset status when failed

	ctx := context.Background()
	klog.Infof("Reconcile pods '%s/%s'", namespace, name)
	if err := c.reconcilePods(ctx, tsCopy); err != nil {
		return err
	}

	klog.Infof("Reconcile services '%s/%s'", namespace, name)
	if err := c.reconcileServices(ctx, tsCopy); err != nil {
		return err
	}

	c.recorder.Event(ts, corev1.EventTypeNormal, SuccessSynced, MessageResourceSynced)

	return c.updateStatus(ctx, tsCopy)
}

func (c *Controller) enqueueTrainingSet(obj interface{}) {
	var key string
	var err error
	if key, err = cache.MetaNamespaceKeyFunc(obj); err != nil {
		utilruntime.HandleError(err)
		return
	}
	c.workqueue.Add(key)
}

func (c *Controller) handleObject(obj interface{}) {
	var object metav1.Object
	var ok bool
	if object, ok = obj.(metav1.Object); !ok {
		tombstone, ok := obj.(cache.DeletedFinalStateUnknown)
		if !ok {
			utilruntime.HandleError(fmt.Errorf("error decoding object, invalid type"))
			return
		}
		object, ok = tombstone.Obj.(metav1.Object)
		if !ok {
			utilruntime.HandleError(fmt.Errorf("error decoding object tombstone, invalid type"))
			return
		}
		klog.V(4).Infof("Recovered deleted object '%s' from tombstone", object.GetName())
	}

	klog.V(4).Infof("Processing object: %s", object.GetName())
	if ownerRef := metav1.GetControllerOf(object); ownerRef != nil {
		// If this object is not owned by a TrainingSet, we should not do anything more
		// with it.
		if ownerRef.Kind != "TrainingSet" {
			return
		}

		ts, err := c.trainingSetsLister.TrainingSets(object.GetNamespace()).Get(ownerRef.Name)
		if err != nil {
			klog.V(4).Infof("ignoring orphaned object '%s' of TrainingSet '%s'", object.GetSelfLink(), ownerRef.Name)
			return
		}

		c.enqueueTrainingSet(ts)
		return
	}
}
