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
	"fmt"

	"github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/controller"
	"k8s.io/api/core/v1"
)

func getServiceDiscoveryKey(pod *v1.Pod) string {
	if pod == nil {
		return ""
	}
	key := getWorkerID(pod)
	if len(key) == 0 {
		key = pod.GetName()
	}
	return key
}

func getWorkerID(pod *v1.Pod) string {
	if pod == nil {
		return ""
	}
	for i := range pod.Spec.Containers {
		for j := range pod.Spec.Containers[i].Env {
			if pod.Spec.Containers[i].Env[j].Name != controller.WorkerEnvID {
				continue
			}
			return pod.Spec.Containers[i].Env[j].Value
		}
	}
	return ""
}

func getAddr(pod *v1.Pod) string {
	var ip string
	var port int32
	if pod.Spec.HostNetwork {
		ip = pod.Status.HostIP
	} else {
		ip = pod.Status.PodIP
	}
	if len(pod.Spec.Containers) > 0 && len(pod.Spec.Containers[0].Ports) > 0 {
		port = pod.Spec.Containers[0].Ports[0].ContainerPort
	}
	if port == 0 || len(ip) == 0 {
		return ""
	}
	return fmt.Sprintf("%s:%d", ip, port)
}

func isReady(pod *v1.Pod) bool {
	if pod.GetDeletionTimestamp() != nil {
		return false
	}
	for i := range pod.Status.ContainerStatuses {
		if !pod.Status.ContainerStatuses[i].Ready {
			return false
		}
	}
	for i := range pod.Status.Conditions {
		if pod.Status.Conditions[i].Type == v1.PodReady && pod.Status.Conditions[i].Status != v1.ConditionTrue {
			return false
		}
	}
	return true
}
