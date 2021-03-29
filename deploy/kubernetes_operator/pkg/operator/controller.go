/* Copyright 2020 The FedLearner Authors. All Rights Reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package operator

import (
	"fmt"
	"time"

	v1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/errors"
	utilruntime "k8s.io/apimachinery/pkg/util/runtime"
	"k8s.io/apimachinery/pkg/util/wait"
	"k8s.io/client-go/informers"
	clientset "k8s.io/client-go/kubernetes"
	"k8s.io/client-go/tools/cache"
	"k8s.io/client-go/tools/record"
	"k8s.io/client-go/util/workqueue"
	"k8s.io/klog"

	"github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/apis/fedlearner.k8s.io/v1alpha1"
	crdclientset "github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/client/clientset/versioned"
	crdinformers "github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/client/informers/externalversions"
	crdlisters "github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/client/listers/fedlearner.k8s.io/v1alpha1"
)

type FLController struct {
	jobQueue    workqueue.RateLimitingInterface
	cacheSynced cache.InformerSynced

	flAppLister crdlisters.FLAppLister

	syncHandler func(app *v1alpha1.FLApp, deleting bool) error
	podCache    *podCache
	stopCh      <-chan struct{}
}

func NewFLController(
	namespace string,
	recorder record.EventRecorder,
	resyncInterval int,
	ingressExtraHostSuffix string,
	ingressSecretName string,
	ingressEnableClientAuth bool,
	ingressClientAuthSecretName string,
	kubeClient clientset.Interface,
	crdClientset crdclientset.Interface,
	kubeSharedInformerFactory informers.SharedInformerFactory,
	crdSharedInformerFactory crdinformers.SharedInformerFactory,
	appEventHandler AppEventHandler,
	stopCh <-chan struct{},
) *FLController {
	podCache := newPodCache(time.Duration(5)*time.Minute, stopCh)
	go podCache.start(stopCh)

	appManager := NewAppManager(
		namespace,
		recorder,
		ingressExtraHostSuffix,
		ingressSecretName,
		ingressEnableClientAuth,
		ingressClientAuthSecretName,
		kubeClient,
		crdClientset,
		crdSharedInformerFactory.Fedlearner().V1alpha1().FLApps().Lister(),
		kubeSharedInformerFactory.Core().V1().ConfigMaps().Lister(),
		kubeSharedInformerFactory.Core().V1().Pods().Lister(),
		kubeSharedInformerFactory.Core().V1().Services().Lister(),
		kubeSharedInformerFactory.Networking().V1beta1().Ingresses().Lister(),
		kubeSharedInformerFactory.Core().V1().Secrets().Lister(),
		appEventHandler,
		podCache,
	)
	controller := &FLController{
		jobQueue: workqueue.NewNamedRateLimitingQueue(
			workqueue.NewItemExponentialFailureRateLimiter(5*time.Millisecond, time.Duration(resyncInterval)*time.Second),
			"fl-controller",
		),
		flAppLister: crdSharedInformerFactory.Fedlearner().V1alpha1().FLApps().Lister(),
		cacheSynced: func() bool {
			return crdSharedInformerFactory.Fedlearner().V1alpha1().FLApps().Informer().HasSynced() &&
				kubeSharedInformerFactory.Core().V1().ConfigMaps().Informer().HasSynced() &&
				kubeSharedInformerFactory.Core().V1().Pods().Informer().HasSynced() &&
				kubeSharedInformerFactory.Core().V1().Services().Informer().HasSynced() &&
				kubeSharedInformerFactory.Networking().V1beta1().Ingresses().Informer().HasSynced() &&
				kubeSharedInformerFactory.Core().V1().Secrets().Informer().HasSynced()
		},
		syncHandler: appManager.SyncApp,
		podCache:    podCache,
		stopCh:      stopCh,
	}

	kubeSharedInformerFactory.Core().V1().Pods().Informer().AddEventHandler(cache.FilteringResourceEventHandler{
		FilterFunc: func(obj interface{}) bool {
			validPodFunc := func(pod *v1.Pod) bool {
				if pod.Namespace != namespace {
					return false
				}
				if _, ok := pod.Labels[AppNameLabel]; !ok {
					// pod is not related to FLApp
					return false
				}
				return true
			}
			if cast, ok := obj.(*v1.Pod); ok {
				return validPodFunc(cast)
			}
			if tombstone, ok := obj.(cache.DeletedFinalStateUnknown); ok {
				if cast, ok := tombstone.Obj.(*v1.Pod); ok {
					return validPodFunc(cast)
				}
			}
			return false
		},
		Handler: cache.ResourceEventHandlerFuncs{
			AddFunc:    controller.onPodAdded,
			UpdateFunc: nil,
			DeleteFunc: nil,
		},
	})

	crdSharedInformerFactory.Fedlearner().V1alpha1().FLApps().Informer().AddEventHandler(
		cache.ResourceEventHandlerFuncs{
			AddFunc:    controller.onFLAppAdded,
			UpdateFunc: controller.onFLAppUpdated,
			DeleteFunc: controller.onFLAppDeleted,
		})
	return controller
}

func (c *FLController) onPodAdded(obj interface{}) {
	if pod, ok := obj.(*v1.Pod); ok {
		c.podCache.addPod(pod)
	}
}

func (c *FLController) onFLAppAdded(obj interface{}) {
	app := obj.(*v1alpha1.FLApp)
	c.enqueueApp(app)
}

func (c *FLController) onFLAppUpdated(oldObj, newObj interface{}) {
	_, ok := oldObj.(*v1alpha1.FLApp)
	if !ok {
		klog.Errorf("failed to convert oldObj to FLApp")
		return
	}
	app, ok := newObj.(*v1alpha1.FLApp)
	if !ok {
		klog.Errorf("failed to convert newObj to FLApp")
		return
	}
	c.enqueueApp(app)
}

func (c *FLController) onFLAppDeleted(obj interface{}) {
	var app *v1alpha1.FLApp
	switch obj.(type) {
	case *v1alpha1.FLApp:
		app = obj.(*v1alpha1.FLApp)
	case cache.DeletedFinalStateUnknown:
		deletedObj := obj.(cache.DeletedFinalStateUnknown).Obj
		app = deletedObj.(*v1alpha1.FLApp)
	}

	if app != nil {
		if err := c.syncHandler(app, true); err != nil {
			klog.Errorf("failed to delete app, name = %v, err = %v", app.Name, err)
		}
	}
}

func (c *FLController) enqueueApp(obj interface{}) {
	key, err := cache.DeletionHandlingMetaNamespaceKeyFunc(obj)
	if err != nil {
		klog.Errorf("failed to get key for %v: %v", obj, err)
		return
	}
	c.jobQueue.AddRateLimited(key)
}

func (c *FLController) Start(workers int) error {
	klog.Infof("controller start with %v workers", workers)
	if !cache.WaitForCacheSync(c.stopCh, c.cacheSynced) {
		return fmt.Errorf("timed out waiting for cache to sync")
	}

	for i := 0; i < workers; i++ {
		go wait.Until(c.runWorker, time.Second, c.stopCh)
	}
	return nil
}

func (c *FLController) runWorker() {
	defer utilruntime.HandleCrash()
	for c.processNextItem() {
	}
}

func (c *FLController) processNextItem() bool {
	key, shutdown := c.jobQueue.Get()

	if shutdown {
		return false
	}
	defer c.jobQueue.Done(key)

	err := c.syncFLApp(key.(string))
	if err == nil {
		c.jobQueue.Forget(key)
	} else {
		klog.Errorf("failed to sync FLApp %v, err = %v", key, err)
	}
	return true
}

func (c *FLController) syncFLApp(key string) error {
	namespace, name, err := cache.SplitMetaNamespaceKey(key)
	if err != nil {
		return fmt.Errorf("failed to get the namespace and name from key %s: %v", key, err)
	}
	app, err := c.flAppLister.FLApps(namespace).Get(name)
	if err != nil && !errors.IsNotFound(err) {
		return err
	}
	if app == nil {
		return nil
	}
	return c.syncHandler(app, false)
}

func (c *FLController) Stop() {
	klog.Info("stopping the fedlearner controller")
	c.jobQueue.ShutDown()
}
