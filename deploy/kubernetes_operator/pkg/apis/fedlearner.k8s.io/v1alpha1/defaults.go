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

package v1alpha1

import (
	v1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/util/sets"
)

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
			ContainerPort: DefaultPort,
		})
	}
}

func setDefaultAppSpec(app *FLApp) {
	if app.Spec.BackoffLimit == nil {
		backoffLimit := DefaultBackoffLimit
		app.Spec.BackoffLimit = &backoffLimit
	}

	if app.Spec.CleanPodPolicy == nil {
		all := CleanPodPolicyAll
		app.Spec.CleanPodPolicy = &all
	}
}

func setDefaultReplicaSpec(app *FLApp, rtype FLReplicaType) {
	spec := app.Spec.FLReplicaSpecs[rtype] // copy struct
	if spec.Pair == nil {
		pair := false
		spec.Pair = &pair
	}
	if spec.Replicas == nil {
		replica := DefaultNonPairReplica
		if *spec.Pair {
			replica = DefaultPairReplica
		}
		spec.Replicas = &replica
	}
	if string(spec.RestartPolicy) == "" {
		spec.RestartPolicy = RestartPolicyOnFailure
	}
	setDefaultPort(&spec.Template.Spec)
	app.Spec.FLReplicaSpecs[rtype] = spec
}

func SetDefaultStatus(app *FLApp) {
	if app.Status.FLReplicaStatus == nil {
		app.Status.FLReplicaStatus = make(FLReplicaStatus)
		for rtype := range app.Spec.FLReplicaSpecs {
			app.Status.FLReplicaStatus[rtype] = ReplicaStatus{
				Local:     sets.NewString(),
				Remote:    sets.NewString(),
				Mapping:   make(map[string]string),
				Active:    sets.NewString(),
				Succeeded: sets.NewString(),
				Failed:    sets.NewString(),
			}
		}
	}
	if app.Status.AppState == "" {
		app.Status.AppState = FLStateNew
	}
}

func SetDefaults_FLApp(app *FLApp) {
	setDefaultAppSpec(app)
	for rtype := range app.Spec.FLReplicaSpecs {
		setDefaultReplicaSpec(app, rtype)
	}
	SetDefaultStatus(app)
}
