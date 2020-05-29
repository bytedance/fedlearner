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

// Code generated by informer-gen. DO NOT EDIT.

package v1alpha2

import (
	time "time"

	fedlearnerk8siov1alpha2 "github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/apis/fedlearner.k8s.io/v1alpha2"
	versioned "github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/client/clientset/versioned"
	internalinterfaces "github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/client/informers/externalversions/internalinterfaces"
	v1alpha2 "github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/client/listers/fedlearner.k8s.io/v1alpha2"
	v1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	runtime "k8s.io/apimachinery/pkg/runtime"
	watch "k8s.io/apimachinery/pkg/watch"
	cache "k8s.io/client-go/tools/cache"
)

// TrainingSetInformer provides access to a shared informer and lister for
// TrainingSets.
type TrainingSetInformer interface {
	Informer() cache.SharedIndexInformer
	Lister() v1alpha2.TrainingSetLister
}

type trainingSetInformer struct {
	factory          internalinterfaces.SharedInformerFactory
	tweakListOptions internalinterfaces.TweakListOptionsFunc
	namespace        string
}

// NewTrainingSetInformer constructs a new informer for TrainingSet type.
// Always prefer using an informer factory to get a shared informer instead of getting an independent
// one. This reduces memory footprint and number of connections to the server.
func NewTrainingSetInformer(client versioned.Interface, namespace string, resyncPeriod time.Duration, indexers cache.Indexers) cache.SharedIndexInformer {
	return NewFilteredTrainingSetInformer(client, namespace, resyncPeriod, indexers, nil)
}

// NewFilteredTrainingSetInformer constructs a new informer for TrainingSet type.
// Always prefer using an informer factory to get a shared informer instead of getting an independent
// one. This reduces memory footprint and number of connections to the server.
func NewFilteredTrainingSetInformer(client versioned.Interface, namespace string, resyncPeriod time.Duration, indexers cache.Indexers, tweakListOptions internalinterfaces.TweakListOptionsFunc) cache.SharedIndexInformer {
	return cache.NewSharedIndexInformer(
		&cache.ListWatch{
			ListFunc: func(options v1.ListOptions) (runtime.Object, error) {
				if tweakListOptions != nil {
					tweakListOptions(&options)
				}
				return client.FedlearnerV1alpha2().TrainingSets(namespace).List(options)
			},
			WatchFunc: func(options v1.ListOptions) (watch.Interface, error) {
				if tweakListOptions != nil {
					tweakListOptions(&options)
				}
				return client.FedlearnerV1alpha2().TrainingSets(namespace).Watch(options)
			},
		},
		&fedlearnerk8siov1alpha2.TrainingSet{},
		resyncPeriod,
		indexers,
	)
}

func (f *trainingSetInformer) defaultInformer(client versioned.Interface, resyncPeriod time.Duration) cache.SharedIndexInformer {
	return NewFilteredTrainingSetInformer(client, f.namespace, resyncPeriod, cache.Indexers{cache.NamespaceIndex: cache.MetaNamespaceIndexFunc}, f.tweakListOptions)
}

func (f *trainingSetInformer) Informer() cache.SharedIndexInformer {
	return f.factory.InformerFor(&fedlearnerk8siov1alpha2.TrainingSet{}, f.defaultInformer)
}

func (f *trainingSetInformer) Lister() v1alpha2.TrainingSetLister {
	return v1alpha2.NewTrainingSetLister(f.Informer().GetIndexer())
}
