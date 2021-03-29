/*
 * Copyright 2021 The FedLearner Authors. All Rights Reserved.
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
	"sync"
	"time"

	v1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/labels"
	"k8s.io/apimachinery/pkg/util/wait"
	"k8s.io/klog"

	"github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/apis/fedlearner.k8s.io/v1alpha1"
)

type item struct {
	pod       *v1.Pod
	timestamp time.Time
}

// data is the map from podName to *v1.Pod
type data map[string]item

type podCache struct {
	mutex      sync.RWMutex
	cache      map[v1.PodPhase]data
	expiration time.Duration
}

func newPodCache(expiration time.Duration, stopCh <-chan struct{}) *podCache {
	cache := &podCache{
		cache:      make(map[v1.PodPhase]data),
		expiration: expiration,
	}
	go cache.start(stopCh)
	return cache
}

func (p *podCache) start(stopCh <-chan struct{}) {
	go wait.Until(p.cleanExpiredPod, time.Second*30, stopCh)
}

func (p *podCache) cleanExpiredPod() {
	p.mutex.Lock()
	defer p.mutex.Unlock()

	for _, cacheData := range p.cache {
		for podName, podItem := range cacheData {
			if time.Since(podItem.timestamp) >= p.expiration {
				delete(cacheData, podName)
			}
		}
	}
}

func (p *podCache) getSucceededPod(app *v1alpha1.FLApp, rt, index string) (*v1.Pod, error) {
	p.mutex.RLock()
	defer p.mutex.RUnlock()

	podLabels := GenLabels(app)
	podLabels[flReplicaTypeLabel] = rt
	podLabels[flReplicaIndexLabel] = index
	selector, err := metav1.LabelSelectorAsSelector(&metav1.LabelSelector{
		MatchLabels: podLabels,
	})
	if err != nil {
		klog.Errorf("failed to build selector to select succeeded pod, err = %v", err)
		return nil, err
	}

	var ret []*v1.Pod
	for _, podItem := range p.cache[v1.PodSucceeded] {
		if selector.Matches(labels.Set(podItem.pod.Labels)) {
			ret = append(ret, podItem.pod)
		}
	}
	switch len(ret) {
	case 0:
		return nil, nil
	case 1:
		return ret[0], nil
	default:
		err := fmt.Errorf("more than 1 pod matches selector for flapp %v", app.Name)
		klog.Error(err)
		return nil, err
	}
}

func (p *podCache) addPod(pod *v1.Pod) {
	p.mutex.Lock()
	defer p.mutex.Unlock()

	if pod.Status.Phase != v1.PodSucceeded {
		// pod is not succeeded
		return
	}
	if _, ok := pod.Labels[AppNameLabel]; !ok {
		// pod is not related to FLApp
		return
	}

	if _, ok := p.cache[pod.Status.Phase]; !ok {
		p.cache[pod.Status.Phase] = make(data)
	}
	p.cache[pod.Status.Phase][pod.Name] = item{
		pod:       pod.DeepCopy(),
		timestamp: time.Now(),
	}
}
