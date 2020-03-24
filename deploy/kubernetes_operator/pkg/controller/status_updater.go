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

package controller

import (
	"fmt"

	"k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/klog"

	"github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/apis/fedlearner.k8s.io/v1alpha1"
	crdclientset "github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/client/clientset/versioned"
)

type StatusUpdater interface {
	// Update app state only in app's status
	UpdateAppStateWithRetry(app *v1alpha1.FLApp, state v1alpha1.FLState) error
	// Update any field in app's status
	UpdateStatusWithRetry(app *v1alpha1.FLApp, updateFunc func(*v1alpha1.FLApp) bool) (*v1alpha1.FLApp, error)
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

func (updater *appStatusUpdater) UpdateAppStateWithRetry(app *v1alpha1.FLApp, state v1alpha1.FLState) error {
	updateFunc := func(flapp *v1alpha1.FLApp) bool {
		if flapp.Status.AppState == state {
			return false
		}
		flapp.Status.AppState = state
		return true
	}
	_, err := updater.UpdateStatusWithRetry(app, updateFunc)
	return err
}

func (updater *appStatusUpdater) UpdateStatusWithRetry(
	app *v1alpha1.FLApp,
	updateFunc func(*v1alpha1.FLApp) bool,
) (*v1alpha1.FLApp, error) {
	refresh := false
	var err error
	freshApp := app.DeepCopy()

	for {
		if refresh {
			freshApp, err = updater.crdClient.FedlearnerV1alpha1().FLApps(updater.namespace).Get(app.Name, metav1.GetOptions{})
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
		_, err = updater.crdClient.FedlearnerV1alpha1().FLApps(updater.namespace).UpdateStatus(freshApp)
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
