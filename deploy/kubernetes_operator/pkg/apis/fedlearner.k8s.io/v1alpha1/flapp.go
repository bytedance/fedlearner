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

package v1alpha1

import (
	appv1 "k8s.io/api/apps/v1"
	batchv1 "k8s.io/api/batch/v1"
	"k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/util/sets"
)

type FLRole string

const (
	Leader   FLRole = "Leader"
	Follower FLRole = "Follower"
)

type AppState string

const (
	AppNew          AppState = "New"
	AppPSStarted    AppState = "PSStarted"
	AppBootstrapped AppState = "Bootstrapped"
	AppSyncSent     AppState = "SyncSent"
	AppRunning      AppState = "Running"
	AppFailing      AppState = "Failing"
	AppShuttingDown AppState = "ShuttingDown"
	AppComplete     AppState = "Complete"
	AppFailed       AppState = "Failed"
)

// +genclient
// +k8s:deepcopy-gen:interfaces=k8s.io/apimachinery/pkg/runtime.Object

// FLApp is a specification for a FLApp resource
type FLApp struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata,omitempty"`

	// Spec is the spec for FLApp
	// +optional
	Spec FLAppSpec `json:"spec"`
	// Status is the status for FLApp
	// +optional
	Status FLAppStatus `json:"status"`
}

// FLAppSpec is the spec for a FLAppSpec resource
type FLAppSpec struct {
	AppID string `json:"appID"`

	PS             PSSpec                         `json:"ps"`
	Master         MasterSpec                     `json:"master"`
	Worker         WorkerSpec                     `json:"worker"`
	FLReplicaSpecs map[FLReplicaType]*ReplicaSpec `json:"flReplicaSpecs"`

	Role FLRole `json:"role"`
}

// ReplicaSpec is a description of the replica
type ReplicaSpec struct {
	// Replicas is the desired number of replicas of the given template.
	Replicas *int32 `json:"replicas,omitempty"`
	// Pair, when set to true, controller will try to pair it with peer controller.
	Pair bool `json:"pair,omitempty"`
	// Template is the object that describes the pod that
	// will be created for this replica.
	Template v1.PodTemplateSpec `json:"template,omitempty"`
}

type PSSpec struct {
	// Template is the PS template
	Template appv1.StatefulSetSpec `json:"template"`
}

type MasterSpec struct {
	// Template is the driver pod template
	Template appv1.StatefulSetSpec `json:"template"`
}

type WorkerSpec struct {
	// Template is the worker pod template
	Template batchv1.JobSpec `json:"template"`
}

// FLReplicaType can be one of: "Master", "Worker", or "PS".
type FLReplicaType string

const (
	// FLReplicaTypePS is the type for parameter servers of distributed TensorFlow.
	FLReplicaTypePS FLReplicaType = "PS"
	// FLReplicaTypeMaster is the type for master worker of distributed TensorFlow.
	FLReplicaTypeMaster FLReplicaType = "Master"
	// FLReplicaTypeWorker is the type for workers of distributed TensorFlow.
	FLReplicaTypeWorker FLReplicaType = "Worker"
)

type Pair struct {
	// Local is the current ID allocated locally
	Local sets.String
	// Remote is the ID allocated in the remote side
	Remote sets.String
	// Mapping is the map from a local ID to remote IDs
	Mapping map[string]string
}

// FLAppStatus is the status for a FLApp resource
type FLAppStatus struct {
	// AppState is the current state of the entire job
	AppState AppState `json:"appState"`
	// PSAddress is the PodIP:Port addresses of PS server
	PSAddress sets.String `json:"psAddress"`
	// A map of FLReplicaType to Pair Status
	PairStatus map[FLReplicaType]*Pair `json:"pairStatus"`
}

// +k8s:deepcopy-gen:interfaces=k8s.io/apimachinery/pkg/runtime.Object

// FLAppList is a list of FLApp resources
type FLAppList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata"`

	Items []FLApp `json:"items"`
}
