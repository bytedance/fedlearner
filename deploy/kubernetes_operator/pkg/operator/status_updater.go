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
	"context"
	"fmt"

	"k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/klog"

	"github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/apis/fedlearner.k8s.io/v1alpha1"
	crdclientset "github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/client/clientset/versioned"
)

type StatusUpdater interface {
	// Update app state only in app's status
	UpdateAppStateWithRetry(ctx context.Context, app *v1alpha1.FLApp, state v1alpha1.FLState) error
	// Update any field in app's status
	UpdateStatusWithRetry(ctx context.Context, app *v1alpha1.FLApp, updateFunc func(*v1alpha1.FLApp) bool) (*v1alpha1.FLApp, error)
}

type appStatusUpdater struct {
	crdClient crdclientset.Interface
	namespace string
}

func NewAppStatusUpdater(crdClient crdclientset.Interface, namespace string) StatusUpdater {
	return &appStatusUpdater{
		crdClient: crdClient,
		namespace: namespace,
	}
}

func (updater *appStatusUpdater) UpdateAppStateWithRetry(ctx context.Context, app *v1alpha1.FLApp, state v1alpha1.FLState) error {
	updateFunc := func(flapp *v1alpha1.FLApp) bool {
		for rtype, _ := range flapp.Status.FLReplicaStatus {
			status := flapp.Status.FLReplicaStatus[rtype]
			replicaStatus := status.DeepCopy()

			pods := make([]string, 0)
			for pod := range replicaStatus.Active {
				pods = append(pods, pod)
			}

			for _, pod := range pods {
				switch state {
				case v1alpha1.FLStateComplete:
					replicaStatus.Active.Delete(pod)
					replicaStatus.Succeeded.Insert(pod)
				case v1alpha1.FLStateFailing:
					replicaStatus.Active.Delete(pod)
					replicaStatus.Failed.Insert(pod)
				}
			}
			flapp.Status.FLReplicaStatus[rtype] = *replicaStatus
		}


		if state == v1alpha1.FLStateComplete || state == v1alpha1.FLStateFailed {
			now := metav1.Now()
			flapp.Status.CompletionTime = &now
		} else {
			flapp.Status.CompletionTime = nil
		}

		if flapp.Status.AppState == state {
			return false
		}
		flapp.Status.AppState = state
		return true
	}
	_, err := updater.UpdateStatusWithRetry(ctx, app, updateFunc)
	return err
}

func (updater *appStatusUpdater) UpdateStatusWithRetry(
	ctx context.Context,
	app *v1alpha1.FLApp,
	updateFunc func(*v1alpha1.FLApp) bool,
) (*v1alpha1.FLApp, error) {
	refresh := false
	var err error
	freshApp := app.DeepCopy()

	for {
		if refresh {
			freshApp, err = updater.crdClient.FedlearnerV1alpha1().FLApps(updater.namespace).Get(ctx, app.Name, metav1.GetOptions{})
			if err != nil || freshApp == nil {
				return nil, fmt.Errorf("failed to get app %s: %v", freshApp.Name, err)
			}
		}

		if !updateFunc(freshApp) {
			if !refresh {
				refresh = true
				continue
			}
			return freshApp, nil
		}

		klog.Infof(
			"updating flapp %v status, namespace = %v, new state = %v",
			freshApp.Name,
			updater.namespace,
			freshApp.Status.AppState)
		_, err = updater.crdClient.FedlearnerV1alpha1().FLApps(updater.namespace).UpdateStatus(ctx, freshApp, metav1.UpdateOptions{})
		if err != nil && errors.IsConflict(err) {
			refresh = true
			continue
		}
		if err != nil {
			klog.Errorf("failed to update app %s: %v", freshApp.Name, err)
			return nil, err
		}
		return freshApp, nil
	}
}
