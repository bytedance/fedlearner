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
	"k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/util/sets"
)

const (
	DefaultContainerName = "tensorflow"
	DefaultPortName      = "flapp-port"
)

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

// RestartPolicy describes how the replicas should be restarted.
// Only one of the following restart policies may be specified.
// If none of the following policies is specified, the default one
// is RestartPolicyOnFailure.
type RestartPolicy string

const (
	RestartPolicyAlways    RestartPolicy = "Always"
	RestartPolicyOnFailure RestartPolicy = "OnFailure"
	RestartPolicyNever     RestartPolicy = "Never"
	// RestartPolicyExitCode policy means that user should add exit code by themselves,
	// The controller will check these exit codes to
	// determine the behavior when an error occurs:
	// - 1-127: permanent error, do not restart.
	// - 128-255: retryable error, will restart the pod.
	// RestartPolicyExitCode RestartPolicy = "ExitCode"
)

// ReplicaSpec is a description of the replica
type ReplicaSpec struct {
	// Replicas is the desired number of replicas of the given template.
	// +optional
	// Defaults to 1.
	Replicas *int32 `json:"replicas,omitempty"`
	// Pair, when set to true, controller will try to pair it with peer controller.
	// +optional
	// Defaults to false.
	Pair *bool `json:"pair,omitempty"`
	// Template is the object that describes the pod that
	// will be created for this replica.
	Template v1.PodTemplateSpec `json:"template,omitempty"`
	// Restart policy for all replicas within the app.
	// One of Always, OnFailure, Never and ExitCode.
	// Default to OnFailure.
	RestartPolicy RestartPolicy `json:"restartPolicy,omitempty"`
}

// FLReplicaSpecs is the mapping from FLReplicaType to ReplicaSpec
type FLReplicaSpecs map[FLReplicaType]ReplicaSpec

// PeerSpec is a description of a involved controller in the app
type PeerSpec struct {
	// PeerURL is the url of the involved controller
	PeerURL string `json:"peerURL"`
	// Authority is the GRPC Authority in the request
	// +optional
	Authority string `json:"authority,omitempty"`
	// The extra GRPC header in the request
	// +optional
	ExtraHeaders map[string]string `json:"extraHeaders,omitempty"`
}

// PeerSpecs is the mapping from Role to PeerSpec
type PeerSpecs map[string]PeerSpec

// FLReplicaStatus is a description of pairing status
type ReplicaStatus struct {
	// Local is the set of ID allocated locally
	Local sets.String `json:"local"`

	// Remote is the set of ID allocated from the peer side
	Remote sets.String `json:"remote"`

	// Mapping is the mapping from a local ID to remote ID
	Mapping map[string]string `json:"mapping"`

	// The actively running pods.
	Active sets.String `json:"active"`

	// The pods which reached phase Succeeded.
	Succeeded sets.String `json:"succeeded"`

	// The pods which reached phase Failed.
	Failed sets.String `json:"failed"`
}

// FLReplicaStatus describe FLReplicaStatus for each FLReplicaType
type FLReplicaStatus map[FLReplicaType]ReplicaStatus

// FLState describes the current state of FLApp
type FLState string

const (
	FLStateNew          FLState = "FLStateNew"
	FLStateBootstrapped FLState = "FLStateBootstrapped"
	FLStateSyncSent     FLState = "FLStateSyncSent"
	FLStateRunning      FLState = "FLStateRunning"
	FLStateComplete     FLState = "FLStateComplete"
	FLStateFailing      FLState = "FLStateFailing"
	FLStateShutDown     FLState = "FLStateShutDown"
	FLStateFailed       FLState = "FLStateFailed"
)

// CleanPodPolicy describes how to deal with pods when the job is finished.
type CleanPodPolicy string

const (
	CleanPodPolicyAll  CleanPodPolicy = "All"
	CleanPodPolicyNone CleanPodPolicy = "None"
	// TODO: support lazily Ingress and ConfigMaps deletion
	// CleanPodPolicyRunning   CleanPodPolicy = "Running"
)

// +genclient
// +k8s:deepcopy-gen:interfaces=k8s.io/apimachinery/pkg/runtime.Object
// +resource:path=flapp
// +kubebuilder:subresource:status

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
	// Specifies the duration (in seconds) since startTime during which the job can remain active
	// before it is terminated. Must be a positive integer.
	// This setting applies only to pods where restartPolicy is OnFailure or Always.
	// +optional
	// Defaults to infinite
	ActiveDeadlineSeconds *int64 `json:"activeDeadlineSeconds,omitempty"`

	// Number of retries before marking this job as failed.
	// +optional
	// Defaults to 5.
	BackoffLimit *int32 `json:"backoffLimit,omitempty"`

	// Defines the policy for cleaning up pods after the FLApp completes.
	// +optional
	// Defaults to All.
	CleanPodPolicy *CleanPodPolicy `json:"cleanPodPolicy,omitempty"`

	// Defines the TTL for cleaning up finished FLApps (temporary
	// before kubernetes adds the cleanup controller).
	// It may take extra ReconcilePeriod seconds for the cleanup, since
	// reconcile gets called periodically.
	// +optional
	// Defaults to infinite.
	// TODO: CompletionTime is required for this field
	TTLSecondsAfterFinished *int32 `json:"ttlSecondsAfterFinished,omitempty"`

	// Defines replica spec for replica type
	FLReplicaSpecs FLReplicaSpecs `json:"flReplicaSpecs"`

	// Defines the role of FLApp
	// +kubebuilder:validation:Pattern=(^Leader$)|(^Follower\d*$)
	Role string `json:"role"`

	// Defines all the controllers involved in the app
	PeerSpecs PeerSpecs `json:"peerSpecs"`
}

// FLAppStatus is the status for a FLApp resource
type FLAppStatus struct {
	// FLState is the current state of the entire job
	// Defaults to New.
	AppState FLState `json:"appState"`
	// A map of FLReplicaType to FLReplicaStatus
	FLReplicaStatus FLReplicaStatus `json:"flReplicaStatus"`
}

// +k8s:deepcopy-gen:interfaces=k8s.io/apimachinery/pkg/runtime.Object
// +resource:path=flapps

// FLAppList is a list of FLApp resources
type FLAppList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata"`

	Items []FLApp `json:"items"`
}
