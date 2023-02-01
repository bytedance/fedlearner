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
	"time"

	fedlearnerv2 "fedlearner.net/operator/api/v1alpha1"
	. "github.com/onsi/ginkgo"
	. "github.com/onsi/gomega"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/types"
)

var _ = Describe("Fedapp controller", func() {

	// Define utility constants for object names and testing timeouts/durations and intervals.
	const (
		FedAppName      = "test-fedapp"
		FailedAppName   = "failed-test-fedapp"
		FedAppNamespace = "default"
		FedReplicaType  = "Worker"
		timeout         = time.Second * 10
		interval        = time.Millisecond * 250
	)
	var replicas int64 = 2
	Context("When updating FedApp Status", func() {
		It("Should FedApp created successfully", func() {
			By("By creating a new Fedapp")
			ctx := context.Background()
			fedapp := &fedlearnerv2.FedApp{
				TypeMeta: metav1.TypeMeta{
					APIVersion: "fedlearner.k8s.io/v1alpha1",
					Kind:       "FedApp",
				},
				ObjectMeta: metav1.ObjectMeta{
					Name:      FedAppName,
					Namespace: FedAppNamespace,
				},
				Spec: fedlearnerv2.FedAppSpec{
					FedReplicaSpecs: fedlearnerv2.FedReplicaSpecs{
						FedReplicaType: fedlearnerv2.ReplicaSpec{
							Replicas: &replicas,
							Template: corev1.PodTemplateSpec{
								Spec: corev1.PodSpec{
									Containers: []corev1.Container{
										{
											Name:  "test-container",
											Image: "test-image",
										},
									},
								},
							},
						},
					},
				},
			}
			Expect(k8sClient.Create(ctx, fedapp)).Should(Succeed())
			fedappLookupKey := types.NamespacedName{Name: FedAppName, Namespace: FedAppNamespace}
			createdFedApp := &fedlearnerv2.FedApp{}

			// We'll need to retry getting this newly created FedApp, given that creation may not immediately happen.
			Eventually(func() bool {
				err := k8sClient.Get(ctx, fedappLookupKey, createdFedApp)
				if err == nil && createdFedApp.Status.StartTime != nil {
					return true
				}
				return false
			}, timeout, interval).Should(BeTrue(), "should have startTime in the status")
			// Let's make sure our Schedule string value was properly converted/handled.
			Expect(createdFedApp.Spec.FedReplicaSpecs[FedReplicaType].Port.ContainerPort).Should(Equal(int32(50051)))
			By("By checking Pod Service and Ingress created succcessfully")
			var childPods corev1.PodList
			Eventually(func() (int, error) {
				err := k8sClient.List(ctx, &childPods)
				if err != nil {
					return -1, err
				}
				return len(childPods.Items), nil
			}, timeout, interval).Should(Equal(2), "should create pods")

		})
		It("Should FedApp create pod failed", func() {
			By("By creating a new Fedapp")
			ctx := context.Background()
			fedapp := &fedlearnerv2.FedApp{
				TypeMeta: metav1.TypeMeta{
					APIVersion: "fedlearner.k8s.io/v1alpha1",
					Kind:       "FedApp",
				},
				ObjectMeta: metav1.ObjectMeta{
					Name:      FailedAppName,
					Namespace: FedAppNamespace,
				},
				Spec: fedlearnerv2.FedAppSpec{
					FedReplicaSpecs: fedlearnerv2.FedReplicaSpecs{
						FedReplicaType: fedlearnerv2.ReplicaSpec{
							Replicas: &replicas,
							Template: corev1.PodTemplateSpec{
								Spec: corev1.PodSpec{
									Containers: []corev1.Container{
										{
											Name:  "test-container",
											Image: "  failed-image",
										},
									},
								},
							},
						},
					},
				},
			}
			Expect(k8sClient.Create(ctx, fedapp)).Should(Succeed())
			fedappLookupKey := types.NamespacedName{Name: FailedAppName, Namespace: FedAppNamespace}
			createdFedApp := &fedlearnerv2.FedApp{}

			// We'll need to retry getting this newly created FedApp, given that creation may not immediately happen.
			Eventually(func() bool {
				err := k8sClient.Get(ctx, fedappLookupKey, createdFedApp)
				if err == nil {
					conditions := createdFedApp.Status.Conditions
					for i := range conditions {
						if conditions[i].Type != fedlearnerv2.Succeeded {
							continue
						}
						if conditions[i].Status != corev1.ConditionFalse {
							break
						}
						if conditions[i].Reason == "CreatePodFailed" {
							return true
						}
					}
				}
				return false
			}, timeout, interval).Should(BeTrue(), "should be failed for create pod failed")
		})
	})

})
