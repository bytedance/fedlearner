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

package v1alpha2

import (
	v1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/util/sets"
)

const (
	DefaultContainerName = "tensorflow"
	DefaultPortName      = "flapp-port"
)

// TrainingSetType can be one of: "Master", "Worker", or "PS".
type TrainingSetType string

const (
	// TrainingSetTypePS is the type for parameter servers of distributed TensorFlow.
	TrainingSetTypePS TrainingSetType = "PS"
	// TrainingSetTypeMaster is the type for master worker of distributed TensorFlow.
	TrainingSetTypeMaster TrainingSetType = "Master"
	// TrainingSetTypeChief is the type for chief worker of distributed TensorFlow.
	TrainingSetTypeChief TrainingSetType = "Chief"
	// TrainingSetTypeWorker is the type for workers of distributed TensorFlow.
	TrainingSetTypeWorker TrainingSetType = "Worker"
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
	RestartPolicyExitCode RestartPolicy = "ExitCode"
)

// +genclient
// +k8s:deepcopy-gen:interfaces=k8s.io/apimachinery/pkg/runtime.Object
// +resource:path=trainingset
// +kubebuilder:subresource:status

// TrainingSet represents a set of pods with consistent identities.
type TrainingSet struct {
	metav1.TypeMeta `json:",inline"`
	// +optional
	metav1.ObjectMeta `json:"metadata,omitempty"`

	// Spec defines the desired identities of pods in this set.
	// +optional
	Spec TrainingSetSpec `json:"spec,omitempty"`

	// Status is the current status of Pods in this TrainingSet. This data
	// may be out of date by some window of time.
	// +optional
	Status TrainingSetStatus `json:"status,omitempty"`
}

// TrainingSetSpec is the specification of a TrainingSet.
type TrainingSetSpec struct {
	// replicas is the desired number of replicas of the given Template.
	// These are replicas in the sense that they are instantiations of the
	// same Template, but individual replicas also have a consistent identity.
	// If unspecified, defaults to 1.
	// +optional
	Replicas *int32 `json:"replicas,omitempty"`

	// selector is a label query over pods that should match the replica count.
	// It must match the pod template's labels.
	Selector *metav1.LabelSelector `json:"selector"`

	// template is the object that describes the pod that will be created if
	// insufficient replicas are detected. Each pod stamped out by the StatefulSet
	// will fulfill this Template, but have a unique identity from the rest
	// of the StatefulSet.
	Template v1.PodTemplateSpec `json:"template"`

	// Restart policy for all replicas within the app.
	// One of Always, OnFailure, Never and ExitCode.
	// Default to OnFailure.
	RestartPolicy RestartPolicy `json:"restartPolicy,omitempty"`

	// Type is the type of training set.
	Type TrainingSetType `json:"trainingSetType,omitempty"`

	// Pair, when set to true, controller will try to pair it with peer controller.
	// +optional
	// Defaults to false.
	Pair *bool `json:"pair,omitempty"`
}

// TrainingSetStatus represents the current state of a TrainingSet.
type TrainingSetStatus struct {
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

// +k8s:deepcopy-gen:interfaces=k8s.io/apimachinery/pkg/runtime.Object
// +resource:path=trainingsets

// TrainingSetList is a list of TrainingSet resources
type TrainingSetList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata"`

	Items []TrainingSet `json:"items"`
}
