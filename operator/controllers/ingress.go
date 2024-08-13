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
	"strings"

	fedlearnerv2 "fedlearner.net/operator/api/v1alpha1"
	networking "k8s.io/api/networking/v1beta1"
	"k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/types"
	"k8s.io/apimachinery/pkg/util/intstr"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/log"
)

func (r *FedAppReconciler) syncIngress(ctx context.Context, app *fedlearnerv2.FedApp) error {
	log := log.FromContext(ctx)
	var ingress networking.Ingress
	err := r.Get(ctx, types.NamespacedName{Name: app.Name, Namespace: app.Namespace}, &ingress)
	if errors.IsNotFound(err) {
		ingressName := app.Name
		labels := GenLabels(app)
		annotations := map[string]string{
			//"kubernetes.io/ingress.class":                       ingressClassName,
			"nginx.ingress.kubernetes.io/backend-protocol":      "GRPC",
			"nginx.ingress.kubernetes.io/configuration-snippet": "grpc_next_upstream_tries 5;",
			"nginx.ingress.kubernetes.io/http2-insecure-port":   "true",
		}

		newIngress := &networking.Ingress{
			ObjectMeta: metav1.ObjectMeta{
				Name:        ingressName,
				Namespace:   app.Namespace,
				Labels:      labels,
				Annotations: annotations,
			},
			// Explicitly set IngressClassName to nil for k8s backward compatibility
			Spec: networking.IngressSpec{
				IngressClassName: nil,
			},
		}
		for rtype, spec := range app.Spec.FedReplicaSpecs {
			replicas := int(*spec.Replicas)
			rt := strings.ToLower(string(rtype))
			for index := 0; index < replicas; index++ {
				path := networking.HTTPIngressPath{
					Backend: networking.IngressBackend{
						ServiceName: GenIndexName(app.Name, rt, index),
						ServicePort: intstr.FromString(spec.Port.Name),
					},
				}
				host := GenIndexName(app.Name, rt, index) + IngressExtraHostSuffix
				rule := networking.IngressRule{
					Host: host,
					IngressRuleValue: networking.IngressRuleValue{
						HTTP: &networking.HTTPIngressRuleValue{
							Paths: []networking.HTTPIngressPath{path},
						},
					},
				}
				newIngress.Spec.Rules = append(newIngress.Spec.Rules, rule)
			}
		}
		if err := ctrl.SetControllerReference(app, newIngress, r.Scheme); err != nil {
			return err
		}
		log.Info("Create Ingress", "Ingress", newIngress.Name)
		err := r.Create(ctx, newIngress)
		if err != nil && errors.IsAlreadyExists(err) {
			return nil
		}
		return err
	}
	return err
}
