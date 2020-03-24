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

package controller

import (
	"encoding/json"
	"fmt"
	"strconv"
	"strings"

	"github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/apis/fedlearner.k8s.io/v1alpha1"
)

const (
	ServiceFormat = "%s.%s.svc.cluster.local"
)

type ClusterSpec struct {
	Services map[v1alpha1.FLReplicaType][]string `json:"clusterSpec"`
}

func NewClusterSpec(namespace string, app *v1alpha1.FLApp) ClusterSpec {
	clusterSpec := ClusterSpec{
		Services: make(map[v1alpha1.FLReplicaType][]string),
	}
	for rtype := range app.Spec.FLReplicaSpecs {
		rt := strings.ToLower(string(rtype))
		replicas := getReplicas(app, rtype)
		port, err := GetPortFromApp(app, rtype)
		if err != nil {
			port = v1alpha1.DefaultPort
		}
		for index := 0; index < replicas; index++ {
			serviceName := fmt.Sprintf(ServiceFormat, GenIndexName(app.Name, strings.ToLower(app.Spec.Role), rt, strconv.Itoa(index)), namespace)
			clusterSpec.Services[rtype] = append(clusterSpec.Services[rtype], fmt.Sprintf("%s:%d", serviceName, port))
		}
	}
	return clusterSpec
}

func (cs ClusterSpec) Marshal() ([]byte, error) {
	return json.Marshal(cs)
}
