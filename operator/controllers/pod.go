/* Copyright 2023 The FedLearner Authors. All Rights Reserved.
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

package controllers

import (
	"context"
	"strconv"
	"strings"

	fedlearnerv2 "fedlearner.net/operator/api/v1alpha1"
	v1 "k8s.io/api/core/v1"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/log"
)

func (r *FedAppReconciler) CreatePod(ctx context.Context, app *fedlearnerv2.FedApp, spec *fedlearnerv2.ReplicaSpec, index int, rt string, podSliceHasFailed int) error {
	log := log.FromContext(ctx)
	podTemplate := spec.Template.DeepCopy()
	labels := GenLabels(app)
	labels[flReplicaTypeLabel] = rt
	labels[flReplicaIndexLabel] = strconv.Itoa(index)
	podTemplate.Name = GenIndexName(app.Name, rt, index) + "-retry-" + strconv.Itoa(podSliceHasFailed)
	podTemplate.Namespace = app.Namespace
	if podTemplate.Labels == nil {
		podTemplate.Labels = make(map[string]string)
	}
	for key, value := range labels {
		podTemplate.Labels[key] = value
	}
	// The controller will restart pod according to FedReplicaSpec
	podTemplate.Spec.RestartPolicy = v1.RestartPolicyNever

	clusterSpecValue, err := makeClusterSpec(app.Namespace, app)
	if err != nil {
		log.Error(err, "unable to make cluster spec")
		return err
	}
	for idx := range podTemplate.Spec.Containers {
		container := &podTemplate.Spec.Containers[idx]
		container.Env = ensureEnv(container.Env, v1.EnvVar{
			Name:  replicaIndex,
			Value: strconv.Itoa(index),
		})
		container.Env = ensureEnv(container.Env, v1.EnvVar{
			Name:  serviceID,
			Value: GenIndexName(app.Name, rt, index),
		})
		container.Env = ensureEnv(container.Env, v1.EnvVar{
			Name:  clusterSpec,
			Value: clusterSpecValue,
		})

		// If pod use host network, overwrite all port to 0 to support autoport.
		if podTemplate.Spec.HostNetwork {
			for i := range container.Ports {
				container.Ports[i].ContainerPort = 0
			}
		}

	}

	pod := &v1.Pod{
		ObjectMeta: podTemplate.ObjectMeta,
		Spec:       podTemplate.Spec,
	}
	if err := ctrl.SetControllerReference(app, pod, r.Scheme); err != nil {
		return err
	}
	log.Info("Create Pod", "Pod", pod.Name)
	if err = r.Create(ctx, pod); err != nil {
		return err
	}
	return nil
}

func ensureEnv(envVars []v1.EnvVar, item v1.EnvVar) []v1.EnvVar {
	for idx := range envVars {
		if envVars[idx].Name == item.Name {
			envVars[idx] = item
			return envVars
		}
	}
	envVars = append(envVars, item)
	return envVars
}

func GenLabels(app *fedlearnerv2.FedApp) map[string]string {
	return map[string]string{
		AppNameLabel: strings.Replace(app.Name, "/", "-", -1),
	}
}

func makeClusterSpec(namespace string, app *fedlearnerv2.FedApp) (string, error) {
	clusterSpec := NewClusterSpec(namespace, app)
	bytes, err := clusterSpec.Marshal()
	if err != nil {
		return "", err
	}
	return string(bytes), nil
}

func AllPodsFailed(podSlice []*v1.Pod) bool {
	for _, pod := range podSlice {
		// TODO: support restart policy
		if pod.Status.Phase != v1.PodFailed {
			return false
		}
	}
	return true
}
