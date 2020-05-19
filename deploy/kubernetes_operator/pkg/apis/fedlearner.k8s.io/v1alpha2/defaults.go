/*
 * Copyright 2020 The FedLearner Authors. All Rights Reserved.
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

package v1alpha2

import (
	v1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/util/sets"
)

const (
	defaultNonPairReplica int32 = 0
	defaultPairReplica    int32 = 1
	defaultBackoffLimit   int32 = 5
	defaultPort           int32 = 8888
)

func SetDefaults_TrainingSet(ts *TrainingSet) {
	setDefaultSpec(ts)
	setDefaultStatus(ts)
}

func setDefaultSpec(ts *TrainingSet) {
	spec := ts.Spec

	if string(spec.RestartPolicy) == "" {
		spec.RestartPolicy = RestartPolicyOnFailure
	}

	if spec.Pair == nil {
		pair := false
		spec.Pair = &pair
	}

	if spec.Replicas == nil {
		replica := defaultNonPairReplica
		if *spec.Pair {
			replica = defaultPairReplica
		}
		spec.Replicas = &replica
	}

	setDefaultPort(&spec.Template.Spec)

	ts.Spec = spec
}

func setDefaultStatus(ts *TrainingSet) {
	ts.Status = TrainingSetStatus{
		Local:     sets.NewString(),
		Remote:    sets.NewString(),
		Mapping:   make(map[string]string),
		Active:    sets.NewString(),
		Succeeded: sets.NewString(),
		Failed:    sets.NewString(),
	}
}
func setDefaultPort(spec *v1.PodSpec) {
	index := 0
	for i, container := range spec.Containers {
		if container.Name == DefaultContainerName {
			index = i
			break
		}
	}

	hasFLAppPort := false
	for _, port := range spec.Containers[index].Ports {
		if port.Name == DefaultPortName {
			hasFLAppPort = true
			break
		}
	}
	if !hasFLAppPort {
		spec.Containers[index].Ports = append(spec.Containers[index].Ports, v1.ContainerPort{
			Name:          DefaultPortName,
			ContainerPort: defaultPort,
		})
	}
}
