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

package servicediscovery

import (
	"context"
	"fmt"
	"strings"
	"sync"
	"time"

	etcdclient "github.com/coreos/etcd/clientv3"
	"k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/labels"
	utilruntime "k8s.io/apimachinery/pkg/util/runtime"
	"k8s.io/apimachinery/pkg/util/wait"
	"k8s.io/client-go/informers"
	clientset "k8s.io/client-go/kubernetes"
	"k8s.io/client-go/kubernetes/scheme"
	typedcorev1 "k8s.io/client-go/kubernetes/typed/core/v1"
	listerscorev1 "k8s.io/client-go/listers/core/v1"
	"k8s.io/client-go/tools/cache"
	"k8s.io/client-go/tools/record"
	"k8s.io/client-go/util/workqueue"
	"k8s.io/klog"
)

const SDPrefix = "/service_discovery/"

type SDController struct {
	namespace    string
	podQueue     workqueue.RateLimitingInterface
	podLister    listerscorev1.PodLister
	cacheSynced  cache.InformerSynced
	recorder     record.EventRecorder
	kv           etcdclient.KV
	stopCh       <-chan struct{}
	routineMutex *sync.RWMutex
	podRoutine   map[string]string
}

func NewSDController(
	namespace string,
	kubeClient clientset.Interface,
	kubeSharedInformerFactory informers.SharedInformerFactory,
	etcdClient *etcdclient.Client,
	stopCh <-chan struct{},
) *SDController {

	eventBroadcaster := record.NewBroadcaster()
	eventBroadcaster.StartLogging(klog.Infof)
	eventBroadcaster.StartRecordingToSink(&typedcorev1.EventSinkImpl{
		Interface: kubeClient.CoreV1().Events(""),
	})
	recorder := eventBroadcaster.NewRecorder(scheme.Scheme, v1.EventSource{Component: "sd-controller"})
	controller := &SDController{
		namespace: namespace,
		podQueue: workqueue.NewNamedRateLimitingQueue(
			workqueue.DefaultControllerRateLimiter(),
			"sd-controller",
		),
		cacheSynced: func() bool {
			return kubeSharedInformerFactory.Core().V1().Pods().Informer().HasSynced()
		},
		recorder:     recorder,
		podLister:    kubeSharedInformerFactory.Core().V1().Pods().Lister(),
		stopCh:       stopCh,
		kv:           etcdclient.NewKV(etcdClient),
		routineMutex: &sync.RWMutex{},
		podRoutine:   make(map[string]string),
	}
	kubeSharedInformerFactory.Core().V1().Pods().Informer().AddEventHandler(
		cache.FilteringResourceEventHandler{
			FilterFunc: func(obj interface{}) bool {
				var pod *v1.Pod
				switch obj.(type) {
				case *v1.Pod:
					pod = obj.(*v1.Pod)
				case cache.DeletedFinalStateUnknown:
					deletedObj := obj.(cache.DeletedFinalStateUnknown).Obj
					pod = deletedObj.(*v1.Pod)
				}
				if pod != nil {
					return pod.Namespace == namespace
				}
				return false
			},
			Handler: cache.ResourceEventHandlerFuncs{
				AddFunc:    controller.addPod,
				UpdateFunc: controller.updatePod,
				DeleteFunc: controller.deletePod,
			},
		},
	)
	return controller
}

func (c *SDController) addPod(obj interface{}) {
	pod := obj.(*v1.Pod)
	c.enqueuePod(pod)
}

func (c *SDController) updatePod(oldObj, newObj interface{}) {
	newPod, ok := newObj.(*v1.Pod)
	if !ok {
		klog.Errorf("failed to convert newObj to Pod")
		return
	}
	c.enqueuePod(newPod)
}

func (c *SDController) deletePod(obj interface{}) {
	var pod *v1.Pod
	switch obj.(type) {
	case *v1.Pod:
		pod = obj.(*v1.Pod)
	case cache.DeletedFinalStateUnknown:
		deletedObj := obj.(cache.DeletedFinalStateUnknown).Obj
		pod = deletedObj.(*v1.Pod)
	}
	if pod != nil {
		c.enqueuePod(pod)
	}
}

func (c *SDController) enqueuePod(obj interface{}) {
	key, err := cache.DeletionHandlingMetaNamespaceKeyFunc(obj)
	if err != nil {
		klog.Errorf("failed to get key for %v: %v", obj, err)
		return
	}
	c.podQueue.AddRateLimited(key)
}

func (c *SDController) runWorker() {
	defer utilruntime.HandleCrash()
	for c.processNextItem() {
	}
}

func (c *SDController) processNextItem() bool {
	key, shutdown := c.podQueue.Get()

	if shutdown {
		return false
	}
	defer c.podQueue.Done(key)

	err := c.syncHandler(key.(string))
	if err == nil {
		c.podQueue.Forget(key)
	} else {
		klog.Errorf("SDController: service discovery handle %s failed: %v", key, err)
	}
	return true
}

func (c *SDController) Start(workers int) error {
	klog.Infof("controller start with %v workers", workers)
	if !cache.WaitForCacheSync(c.stopCh, c.cacheSynced) {
		return fmt.Errorf("timed out waiting for cache to sync")
	}

	err := c.SyncAllPod()
	if err != nil {
		klog.Fatalf("SDController: Init sync service discovery failed: %v", err)
	}
	klog.Info("Service discovery records synced.")
	for i := 0; i < workers; i++ {
		go wait.Until(c.runWorker, time.Second, c.stopCh)
	}
	return nil
}

func (c *SDController) syncHandler(key string) error {
	namespace, name, err := cache.SplitMetaNamespaceKey(key)
	if err != nil {
		return fmt.Errorf("failed to get the namespace and name from key %s: %v", key, err)
	}
	pod, err := c.podLister.Pods(namespace).Get(name)
	if err != nil {
		if errors.IsNotFound(err) {
			return nil
		}
		return err
	}

	return c.syncPod(pod)
}

// Stop stops the controller.
func (c *SDController) Stop() {
	klog.Info("stopping the sd controller")
	c.podQueue.ShutDown()
}

func (c *SDController) SyncAllPod() error {
	currentState, err := c.retrieveRecords()
	if err != nil {
		return err
	}

	c.routineMutex.Lock()
	c.podRoutine = currentState
	c.routineMutex.Unlock()

	desireState := c.buildDesireState()

	for sdKey := range currentState {
		if _, ok := desireState[sdKey]; !ok {
			err = c.deregister(sdKey)
			if err != nil {
				klog.Fatalf("SDController: Init sync service discovery deregister failed: %v", err)
			}
		}
	}
	for sdKey, sdVal := range desireState {
		if val, ok := currentState[sdKey]; !ok || (ok && val != sdVal) {
			err = c.register(sdKey, desireState[sdKey])
			if err != nil {
				klog.Fatalf("SDController: Init sync service discovery register failed: %v", err)
			}
		}
	}
	return nil
}

func (c *SDController) buildDesireState() map[string]string {
	desireState := make(map[string]string)
	podList, err := c.podLister.Pods(c.namespace).List(labels.Everything())
	if err != nil {
		klog.Fatalf("List desire pod state failed: %v", err)
	}

	for _, pod := range podList {
		sdKey := getServiceDiscoveryKey(pod)
		addr := getAddr(pod)
		if len(sdKey) > 0 && len(addr) > 0 && isReady(pod) {
			desireState[sdKey] = addr
		}
	}
	return desireState
}

func (c *SDController) deregister(key string) error {
	context, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	c.routineMutex.Lock()
	delete(c.podRoutine, key)
	c.routineMutex.Unlock()

	_, err := c.kv.Delete(context, SDPrefix+key)
	if err != nil {
		return err
	}
	klog.Infof("Deregister key: %s\n", SDPrefix+key)
	return nil
}

func (c *SDController) register(key, addr string) error {
	context, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	c.routineMutex.Lock()
	c.podRoutine[key] = addr
	c.routineMutex.Unlock()

	_, err := c.kv.Put(context, SDPrefix+key, addr)
	if err != nil {
		return err
	}
	klog.Infof("Register key: %s, value: %s\n", SDPrefix+key, addr)
	return nil
}

func (c *SDController) retrieveRecords() (map[string]string, error) {
	context, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	rangeResp, err := c.kv.Get(context, SDPrefix, etcdclient.WithPrefix())
	if err != nil {
		return nil, err
	}
	ret := make(map[string]string)
	for _, kv := range rangeResp.Kvs {
		sdKey := strings.Split(string(kv.Key), "/")[2]
		ret[sdKey] = string(kv.Value)
	}
	return ret, nil
}

func (c *SDController) syncPod(pod *v1.Pod) error {
	sdKey := getServiceDiscoveryKey(pod)
	addr := getAddr(pod)
	if len(sdKey) == 0 || len(addr) == 0 {
		return nil
	}
	c.routineMutex.RLock()
	val, ok := c.podRoutine[sdKey]
	c.routineMutex.RUnlock()
	podReady := isReady(pod)

	if podReady {
		if !ok || (ok && val != addr) {
			return c.register(sdKey, addr)
		}
	} else {
		if ok && val == addr {
			return c.deregister(sdKey)
		}
	}
	return nil
}
