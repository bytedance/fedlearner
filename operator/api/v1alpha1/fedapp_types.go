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

package v1alpha1

import (
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// EDIT THIS FILE!  THIS IS SCAFFOLDING FOR YOU TO OWN!
// NOTE: json tags are required.  Any new fields you add must have json tags for the fields to be serialized.

// FedReplicaType can be any string.
type FedReplicaType string

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

// ReplicaSpec is a description of the replica
type ReplicaSpec struct {
	// Replicas is the desired number of replicas of the given template.
	// +kubebuilder:default=0
	// +kubebuilder:validation:Maximum=200
	// +kubebuilder:validation:Minimum=0
	Replicas *int64 `json:"replicas,omitempty"`

	// Template is the object that describes the pod that
	// will be created for this replica.
	Template corev1.PodTemplateSpec `json:"template,omitempty"`

	// Restart policy for all replicas within the app.
	// One of Always, OnFailure, Never and ExitCode.
	// +kubebuilder:default=OnFailure
	RestartPolicy RestartPolicy `json:"restartPolicy,omitempty"`

	// Optional number of retries before marking this job failed.
	// +kubebuilder:default=1
	// +kubebuilder:validation:Maximum=100
	// +kubebuilder:validation:Minimum=1
	BackoffLimit *int64 `json:"backoffLimit,omitempty"`

	// Whether all pods of this replica are suceeded is necessary for marking the falpp as complete.
	// +kubebuilder:default=true
	MustSuccess *bool `json:"mustSuccess,omitempty"`

	// +kubebuilder:default:={"containerPort": 50051, "name": "flapp-port", "protocol": "TCP"}
	Port *corev1.ContainerPort `json:"port,omitempty"`
}

// FedReplicaSpecs is the mapping from FedReplicaType to ReplicaSpec
type FedReplicaSpecs map[FedReplicaType]ReplicaSpec

// FedAppSpec defines the desired state of FedApp
type FedAppSpec struct {
	// INSERT ADDITIONAL SPEC FIELDS - desired state of cluster
	// Important: Run "make" to regenerate code after modifying this file
	// Defines replica spec for replica type
	FedReplicaSpecs FedReplicaSpecs `json:"fedReplicaSpecs"`

	// TTLSecondsAfterFinished is the TTL to clean up jobs.
	// It may take extra ReconcilePeriod seconds for the cleanup, since
	// reconcile gets called periodically.
	// Default to 86400(one day).
	// +kubebuilder:default=86400
	// +optional
	TTLSecondsAfterFinished *int64 `json:"ttlSecondsAfterFinished,omitempty"`

	// Specifies the duration in seconds relative to the startTime that the job may be active
	// before the system tries to terminate it; value must be positive integer.
	// +optional
	ActiveDeadlineSeconds *int64 `json:"activeDeadlineSeconds,omitempty"`
}

// FedAppStatus defines the observed state of FedApp
type FedAppStatus struct {
	// INSERT ADDITIONAL STATUS FIELD - define observed state of cluster
	// Important: Run "make" to regenerate code after modifying this file

	// +optional
	StartTime *metav1.Time `json:"startTime"`

	Conditions []FedAppCondition `json:"conditions,omitempty"`

	// Record pods name which have terminated, hack for too fast pod GC.
	// TODO: when pods gc collection is too fast that fedapp controller
	// dont have enough time to record them in TerminatedPodsMap field,
	// use finalizer to avoid it.
	// +optional
	TerminatedPodsMap TerminatedPodsMap `json:"terminatedPodsMap,omitempty"`
}
type empty struct{}
type PodSet map[string]empty
type TerminatedPodsMap map[FedReplicaType]*TerminatedPods

// TerminatedPods holds name of Pods that have terminated.
type TerminatedPods struct {
	// Succeeded holds name of succeeded Pods.
	// +optional
	Succeeded []PodSet `json:"succeeded,omitempty"`

	// Failed holds name of failed Pods.
	// +optional
	Failed []PodSet `json:"failed,omitempty"`
}

// FedAppConditionType is a valid value for FedAppCondition.Type
type FedAppConditionType string

// These are valid conditions of a job.
const (
	// FedAppComplete means the job has completed its execution.
	// true: completed, false: failed, unknown: running
	Succeeded FedAppConditionType = "succeeded"
)

// FedAppCondition describes current state of a job.
type FedAppCondition struct {
	// Type of job condition.
	Type FedAppConditionType `json:"type"`
	// Status of the condition, one of True, False, Unknown.
	Status corev1.ConditionStatus `json:"status"`

	// Last time the condition transit from one status to another.
	// +optional
	LastTransitionTime metav1.Time `json:"lastTransitionTime"`
	// (brief) reason for the condition's last transition.
	// +optional
	Reason string `json:"reason"`
	// Human readable message indicating details about last transition.
	// +optional
	Message string `json:"message"`
}

//+kubebuilder:object:root=true
//+kubebuilder:subresource:status

// FedApp is the Schema for the fedapps API
type FedApp struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata,omitempty"`

	Spec   FedAppSpec   `json:"spec,omitempty"`
	Status FedAppStatus `json:"status,omitempty"`
}

//+kubebuilder:object:root=true

// FedAppList contains a list of FedApp
type FedAppList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata,omitempty"`
	Items           []FedApp `json:"items"`
}

func init() {
	SchemeBuilder.Register(&FedApp{}, &FedAppList{})
}
