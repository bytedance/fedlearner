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
	"encoding/json"
	"fmt"
	"strconv"
	"strings"

	fedlearnerv2 "fedlearner.net/operator/api/v1alpha1"
)

const (
	ServiceFormat = "%s.%s.svc"
)

type ClusterSpec struct {
	Services map[fedlearnerv2.FedReplicaType][]string `json:"clusterSpec"`
}

func GenIndexName(appName string, rt string, index int) string {
	n := appName + "-" + rt + "-" + strconv.Itoa(index)
	return strings.Replace(n, "/", "-", -1)
}

func NewClusterSpec(namespace string, app *fedlearnerv2.FedApp) ClusterSpec {
	clusterSpec := ClusterSpec{
		Services: make(map[fedlearnerv2.FedReplicaType][]string),
	}
	for rtype, spec := range app.Spec.FedReplicaSpecs {
		rt := strings.ToLower(string(rtype))
		replicas := int(*spec.Replicas)
		port := spec.Port.ContainerPort

		for index := 0; index < replicas; index++ {
			serviceName := fmt.Sprintf(ServiceFormat, GenIndexName(app.Name, rt, index), namespace)
			clusterSpec.Services[rtype] = append(clusterSpec.Services[rtype], fmt.Sprintf("%s:%d", serviceName, port))
		}
	}
	return clusterSpec
}

func (cs ClusterSpec) Marshal() ([]byte, error) {
	return json.Marshal(cs)
}
