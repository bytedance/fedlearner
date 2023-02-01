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
	"strconv"
	"strings"

	fedlearnerv2 "fedlearner.net/operator/api/v1alpha1"
	v1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/labels"
	"k8s.io/apimachinery/pkg/util/intstr"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/log"
)

func (r *FedAppReconciler) syncServices(ctx context.Context, app *fedlearnerv2.FedApp) error {
	log := log.FromContext(ctx)
	var services v1.ServiceList
	if err := r.List(ctx, &services, client.InNamespace(app.Namespace), client.MatchingFields{ownerKey: app.Name}); err != nil {
		log.Error(err, "unable to list child Pods")
		return err
	}
	for rtype, spec := range app.Spec.FedReplicaSpecs {
		rt := strings.ToLower(string(rtype))
		replicas := int(*spec.Replicas)
		// Get all services for the type rt.
		typeServices, err := filterServicesForReplicaType(&services, rt)
		if err != nil {
			return err
		}
		serviceSlices := makeServiceSlicesByIndex(ctx, typeServices, replicas)
		for index, serviceSlice := range serviceSlices {
			if len(serviceSlice) == 0 {
				log.Info("need to create new service for", string(rtype), strconv.Itoa(index))
				if err = r.createNewService(ctx, app, rtype, spec, index); err != nil {
					return err
				}
			}
		}

	}
	return nil
}

// createNewService creates a new service for the given index and type.
func (r *FedAppReconciler) createNewService(ctx context.Context, app *fedlearnerv2.FedApp, rtype fedlearnerv2.FedReplicaType, spec fedlearnerv2.ReplicaSpec, index int) error {
	log := log.FromContext(ctx)
	rt := strings.ToLower(string(rtype))

	// Append tfReplicaTypeLabel and tfReplicaIndexLabel labels.
	labels := GenLabels(app)
	labels[flReplicaTypeLabel] = rt
	labels[flReplicaIndexLabel] = strconv.Itoa(index)
	ports := GetPortsFromFedReplicaSpecs(app.Spec.FedReplicaSpecs[rtype])
	var servicePorts []v1.ServicePort
	for _, port := range ports {
		servicePorts = append(servicePorts, v1.ServicePort{
			Name: port.Name,
			Port: port.ContainerPort,
			TargetPort: intstr.IntOrString{
				Type:   1, // means string
				StrVal: port.Name,
			},
		})
	}
	service := &v1.Service{
		Spec: v1.ServiceSpec{
			Selector: labels,
			Ports:    servicePorts,
		},
	}

	service.Name = GenIndexName(app.Name, rt, index)
	service.Namespace = app.Namespace
	service.Labels = labels
	if err := ctrl.SetControllerReference(app, service, r.Scheme); err != nil {
		return err
	}
	log.Info("Create Service", "Service", service.Name)
	err := r.Create(ctx, service)
	if err != nil && errors.IsAlreadyExists(err) {
		return nil
	}
	return err
}

// GetPortsFromApp gets the ports of all containers.
func GetPortsFromFedReplicaSpecs(replicaSpec fedlearnerv2.ReplicaSpec) []v1.ContainerPort {
	var ports []v1.ContainerPort
	containers := replicaSpec.Template.Spec.Containers
	for _, container := range containers {
		for _, port := range container.Ports {
			if PortNotInPortList(port, ports) {
				ports = append(ports, port)
			}
		}
	}
	if PortNotInPortList(*replicaSpec.Port, ports) {
		ports = append(ports, *replicaSpec.Port)
	}
	return ports
}

func PortNotInPortList(port v1.ContainerPort, ports []v1.ContainerPort) bool {
	for _, p := range ports {
		if p.Name == port.Name || p.ContainerPort == port.ContainerPort {
			return false
		}
	}
	return true
}

// filterServicesForReplicaType returns service belong to a replicaType.
func filterServicesForReplicaType(servicesList *v1.ServiceList, replicaType string) ([]*v1.Service, error) {
	var result []*v1.Service
	replicaSelector := &metav1.LabelSelector{
		MatchLabels: make(map[string]string),
	}

	replicaSelector.MatchLabels[flReplicaTypeLabel] = replicaType
	services := servicesList.Items
	for index := range services {
		selector, err := metav1.LabelSelectorAsSelector(replicaSelector)
		if err != nil {
			return nil, err
		}
		if !selector.Matches(labels.Set(services[index].Labels)) {
			continue
		}
		result = append(result, &services[index])
	}
	return result, nil
}

// makeServiceSlicesByIndex returns a slice, which element is the slice of service.
// Assume the return object is serviceSlices, then serviceSlices[i] is an
// array of pointers to services corresponding to Services for replica i.
func makeServiceSlicesByIndex(ctx context.Context, services []*v1.Service, replicas int) [][]*v1.Service {
	log := log.FromContext(ctx)
	serviceSlices := make([][]*v1.Service, replicas)
	for _, service := range services {
		if _, ok := service.Labels[flReplicaIndexLabel]; !ok {
			log.Info("The pod do not have the index label.")
			continue
		}
		index, err := strconv.Atoi(service.Labels[flReplicaIndexLabel])
		if err != nil {
			log.Error(err, "Error when strconv.Atoi.")
			continue
		}
		if index < 0 || index >= replicas {
			log.Info("The label index is not expected", "index", index, "replicas", replicas)
			continue
		} else {
			serviceSlices[index] = append(serviceSlices[index], service)
		}
	}
	return serviceSlices
}
