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
	fedlearnerv2 "fedlearner.net/operator/api/v1alpha1"
	v1 "k8s.io/api/core/v1"
)

func GetAllFailedPodsNames(tPods fedlearnerv2.TerminatedPods) []string {
	result := []string{}
	for _, podSet := range tPods.Failed {
		result = append(result, getPodNames(podSet)...)
	}
	return result
}

func getPodNames(set fedlearnerv2.PodSet) []string {
	result := []string{}
	for p := range set {
		result = append(result, p)
	}
	return result
}

func AllSliceCompletedOnce(tPods fedlearnerv2.TerminatedPods, replicas int) bool {
	for i := 0; i < replicas; i++ {
		if !IfSliceHasSucceeded(tPods, i) {
			return false
		}
	}
	return true
}

func IfSliceHasSucceeded(tPods fedlearnerv2.TerminatedPods, index int) bool {
	return len(tPods.Succeeded[index]) > 0
}

func SyncTerminatedPods(app *fedlearnerv2.FedApp, rtype fedlearnerv2.FedReplicaType, podSlices [][]*v1.Pod) {
	for index, podSlice := range podSlices {
		for _, pod := range podSlice {
			// TODO: support restart policy
			if pod.Status.Phase == v1.PodSucceeded {
				setAdd(app.Status.TerminatedPodsMap[rtype].Succeeded[index], pod.Name)
			}
			if pod.Status.Phase == v1.PodFailed {
				setAdd(app.Status.TerminatedPodsMap[rtype].Failed[index], pod.Name)
			}

		}
	}
}

func setAdd(set fedlearnerv2.PodSet, name string) {
	// TODO: remove finalizer when pod created with finalizer.
	set[name] = struct{}{}
}

func InitTerminatedPodsMap(app fedlearnerv2.FedApp) map[fedlearnerv2.FedReplicaType]*fedlearnerv2.TerminatedPods {
	terminatedPodsMap := fedlearnerv2.TerminatedPodsMap{}

	for rtype, spec := range app.Spec.FedReplicaSpecs {
		replicas := int(*spec.Replicas)
		succeeded := make([]fedlearnerv2.PodSet, replicas)
		failed := make([]fedlearnerv2.PodSet, replicas)
		for i := range succeeded {
			succeeded[i] = fedlearnerv2.PodSet{}
		}
		for i := range failed {
			failed[i] = fedlearnerv2.PodSet{}
		}
		terminatedPodsMap[rtype] = &fedlearnerv2.TerminatedPods{
			Succeeded: succeeded, Failed: failed,
		}
	}
	return terminatedPodsMap
}
