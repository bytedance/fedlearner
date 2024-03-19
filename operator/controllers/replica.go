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
	"k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/labels"
	"sigs.k8s.io/controller-runtime/pkg/log"
)

func (r *FedAppReconciler) SyncReplicas(ctx context.Context, app *fedlearnerv2.FedApp, rtype fedlearnerv2.FedReplicaType,
	childPods *v1.PodList, spec *fedlearnerv2.ReplicaSpec) (ReplicaResult, error) {
	log := log.FromContext(ctx)
	rt := strings.ToLower(string(rtype))
	pods, err := filterPodsForReplicaType(childPods, rt)
	if err != nil {
		log.Error(err, "filter pods error: %v")
		return ReplicaResult{}, err
	}
	replicas := int(*spec.Replicas)
	podSlices := make([][]*v1.Pod, replicas)
	for _, pod := range pods {
		val, ok := pod.Labels[flReplicaIndexLabel]
		if !ok {
			log.Info("The pod do not have the index label.")
			continue
		}
		index, err := strconv.Atoi(val)
		if err != nil {
			log.Error(err, "Error when strconv.Atoi.")
			continue
		}
		if index < 0 || index >= replicas {
			log.Info("The label index is not expected", "index", index)
		} else {
			podSlices[index] = append(podSlices[index], pod)
		}
	}
	SyncTerminatedPods(app, rtype, podSlices)
	// Fedapp old crd in some environment does not have terminatedPodsMap field.
	// Can't update status here, because terminatedPodsMap will be nil after fedapp updated.
	terminatedPods := *app.Status.TerminatedPodsMap[rtype]
	failedPodsNames := GetAllFailedPodsNames(terminatedPods)
	if len(failedPodsNames) >= int(*spec.BackoffLimit) {
		// TODO(xiangyuxuan.prs): remove failed pod name, and add pod details in fedapp status.
		app.Status.Conditions, _ = ensureConditionStatus(app.Status.Conditions, fedlearnerv2.Succeeded, v1.ConditionFalse, "BackoffLimitExceeded", "FedApp has reached the specified backoff limit: "+strings.Join(failedPodsNames, ", "))
		if err := r.Status().Update(ctx, app); err != nil {
			log.Error(err, "unable to update FedApp status BackoffLimitExceeded")
			return ReplicaResult{}, err
		}
		// Requeue to rlease the resource
		return ReplicaResult{isFailed: true}, nil
	}

	for index, podSlice := range podSlices {
		if IfSliceHasSucceeded(terminatedPods, index) {
			continue
		}
		needCreate := AllPodsFailed(podSlice)
		if !needCreate {
			continue
		}
		sliceHasFailedNum := len(terminatedPods.Failed[index])
		if err := r.CreatePod(ctx, app, spec, index, rt, sliceHasFailedNum); !errors.IsAlreadyExists(err) {
			if err == nil {
				return ReplicaResult{}, nil
			}
			log.Error(err, "create Pod failed")
			app.Status.Conditions, _ = ensureConditionStatus(app.Status.Conditions, fedlearnerv2.Succeeded, v1.ConditionFalse, "CreatePodFailed", err.Error())
			if err := r.Status().Update(ctx, app); err != nil {
				log.Error(err, "unable to update FedApp status CreatePodFailed")
				return ReplicaResult{}, err
			}
			return ReplicaResult{isFailed: true}, nil
		}

	}
	replicaCompleted := AllSliceCompletedOnce(terminatedPods, replicas)
	return ReplicaResult{isCompleted: !*spec.MustSuccess || replicaCompleted}, nil
}

// filterPodsForReplicaType returns pods belong to a replicaType.
func filterPodsForReplicaType(childPods *v1.PodList, replicaType string) ([]*v1.Pod, error) {
	var result []*v1.Pod

	replicaSelector := &metav1.LabelSelector{
		MatchLabels: make(map[string]string),
	}

	replicaSelector.MatchLabels[flReplicaTypeLabel] = replicaType

	selector, err := metav1.LabelSelectorAsSelector(replicaSelector)
	if err != nil {
		return nil, err
	}
	pods := childPods.Items
	for i := range pods {
		if !selector.Matches(labels.Set(pods[i].Labels)) {
			continue
		}
		result = append(result, &pods[i])
	}
	return result, nil
}
