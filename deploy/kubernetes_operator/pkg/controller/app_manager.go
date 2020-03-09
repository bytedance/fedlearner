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

package controller

import (
	"fmt"
	"strconv"
	"strings"
	"time"

	v1 "k8s.io/api/core/v1"
	networking "k8s.io/api/networking/v1beta1"
	apiequality "k8s.io/apimachinery/pkg/api/equality"
	"k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime/schema"
	"k8s.io/apimachinery/pkg/util/intstr"
	clientset "k8s.io/client-go/kubernetes"
	listerscorev1 "k8s.io/client-go/listers/core/v1"
	listersnetworking "k8s.io/client-go/listers/networking/v1beta1"
	"k8s.io/client-go/tools/record"
	"k8s.io/klog"

	"github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/apis/fedlearner.k8s.io/v1alpha1"
	crdclientset "github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/client/clientset/versioned"
	"github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/client/clientset/versioned/scheme"
	crdlisters "github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/client/listers/fedlearner.k8s.io/v1alpha1"
)

const (
	flReplicaTypeLabel  = "fl-replica-type"
	flReplicaIndexLabel = "fl-replica-index"
)

type AppManager interface {
	SyncApp(app *v1alpha1.FLApp, deleting bool) error
}

type appManager struct {
	namespace string

	kubeClient clientset.Interface
	crdClient  crdclientset.Interface

	appLister       crdlisters.FLAppLister
	configMapLister listerscorev1.ConfigMapLister
	podLister       listerscorev1.PodLister
	serviceLister   listerscorev1.ServiceLister
	ingressLister   listersnetworking.IngressLister

	appStatusUpdater StatusUpdater
	appEventHandler  AppEventHandler

	podControl     PodControlInterface
	serviceControl ServiceControlInterface

	recorder record.EventRecorder
}

var (
	_ AppManager = &appManager{}
)

func NewAppManager(
	namespace string,
	recorder record.EventRecorder,
	kubeClient clientset.Interface,
	crdClient crdclientset.Interface,
	appLister crdlisters.FLAppLister,
	configMapLister listerscorev1.ConfigMapLister,
	podLister listerscorev1.PodLister,
	serviceLister listerscorev1.ServiceLister,
	ingressLister listersnetworking.IngressLister,
	appEventHandler AppEventHandler,
) AppManager {
	manager := &appManager{
		namespace: namespace,

		kubeClient: kubeClient,
		crdClient:  crdClient,

		appLister:       appLister,
		configMapLister: configMapLister,
		podLister:       podLister,
		serviceLister:   serviceLister,
		ingressLister:   ingressLister,

		appStatusUpdater: NewAppStatusUpdater(crdClient, namespace),
		appEventHandler:  appEventHandler,

		podControl: RealPodControl{
			KubeClient: kubeClient,
			Recorder:   recorder,
		},
		serviceControl: RealServiceControl{
			KubeClient: kubeClient,
			Recorder:   recorder,
		},

		recorder: recorder,
	}
	return manager
}

func (am *appManager) GenOwnerReference(obj metav1.Object) *metav1.OwnerReference {
	boolPtr := func(b bool) *bool { return &b }
	controllerRef := &metav1.OwnerReference{
		APIVersion:         am.GetAPIGroupVersion().String(),
		Kind:               am.GetAPIGroupVersionKind().Kind,
		Name:               obj.GetName(),
		UID:                obj.GetUID(),
		BlockOwnerDeletion: boolPtr(true),
		Controller:         boolPtr(true),
	}

	return controllerRef
}

func (am *appManager) GetAPIGroupVersionKind() schema.GroupVersionKind {
	return v1alpha1.SchemeGroupVersionKind
}

func (am *appManager) GetAPIGroupVersion() schema.GroupVersion {
	return v1alpha1.SchemeGroupVersion
}

func (am *appManager) SyncApp(app *v1alpha1.FLApp, deleting bool) error {
	appCopy := app.DeepCopy()
	name := appCopy.Name

	scheme.Scheme.Default(appCopy)
	if deleting {
		klog.Infof("deleting application %v, shut it down", name)
		return am.deleteApp(appCopy)
	}

	appState := appCopy.Status.AppState
	if appState == v1alpha1.FLStateNew || appState == v1alpha1.FLStateBootstrapped || appState == v1alpha1.FLStateSyncSent || appState == v1alpha1.FLStateRunning {
		now := time.Now()
		timeout := am.isAppTimeOut(appCopy, now)
		if am.isAppFailing(appCopy) || timeout {
			if timeout {
				klog.Errorf("app is failing because timed out, name = %v, creationTimestamp = %v, activeDeadlineSeconds = %v, now is %v", name, appCopy.GetCreationTimestamp(), *appCopy.Spec.ActiveDeadlineSeconds, now)
			}
			return am.appStatusUpdater.UpdateAppStateWithRetry(appCopy, v1alpha1.FLStateFailing)
		}
	}

	switch appState {
	case v1alpha1.FLStateNew:
		return am.syncNewApp(appCopy)
	case v1alpha1.FLStateBootstrapped:
		return am.syncBootstrappedApp(appCopy)
	case v1alpha1.FLStateSyncSent:
		return am.syncSyncSentApp(appCopy)
	case v1alpha1.FLStateRunning:
		return am.syncRunningApp(appCopy)
	case v1alpha1.FLStateFailing:
		return am.syncFailingApp(appCopy)
	case v1alpha1.FLStateShutDown:
		return am.syncShuttingDownApp(appCopy)
	case v1alpha1.FLStateComplete, v1alpha1.FLStateFailed:
		klog.Infof("ignore app %v as its state is %v", name, appState)
	}
	return nil
}

func (am *appManager) deleteApp(app *v1alpha1.FLApp) error {
	name := app.Name
	appState := app.Status.AppState
	if appState == "" {
		appState = v1alpha1.FLStateNew
	}
	switch appState {
	case v1alpha1.FLStateNew, v1alpha1.FLStateBootstrapped, v1alpha1.FLStateSyncSent, v1alpha1.FLStateRunning:
		klog.Infof("shutting down peer as app is deleted, name = %v", name)
		if err := am.appEventHandler.Shutdown(app); err != nil {
			klog.Errorf("failed to shutdown peer when app is deleted, name = %v, err = %v", name, err)
		}
	}
	if err := am.freeResource(app); err != nil {
		klog.Errorf("failed to free resources when app is deleted, name = %v, err = %v", name, err)
	}
	return nil
}

func (am *appManager) syncNewApp(app *v1alpha1.FLApp) error {
	name := app.Name
	klog.Infof("sync new app, name = %v", name)
	if am.isAppBootstrapped(app) {
		return am.appStatusUpdater.UpdateAppStateWithRetry(app, v1alpha1.FLStateBootstrapped)
	}
	return am.reconcileFLApp(app)
}

func (am *appManager) reconcileFLApp(app *v1alpha1.FLApp) error {
	name := app.Name
	if err := am.reconcileConfigMaps(app); err != nil {
		klog.Errorf("failed to reconcile configMap for app, name = %v, err = %v", name, err)
		return err
	}
	if err := am.reconcilePods(app); err != nil {
		klog.Errorf("failed to reconcile pod for app, name = %v, err = %v", name, err)
		return err
	}
	if err := am.reconcileService(app); err != nil {
		klog.Errorf("failed to reconcile service for app, name = %v, err = %v", name, err)
		return err
	}
	if err := am.reconcileIngress(app); err != nil {
		klog.Errorf("failed to reconcile ingress for app, name = %v, err = %v", name, err)
		return err
	}
	return am.setStatus(app)
}

func (am *appManager) isAppBootstrapped(app *v1alpha1.FLApp) bool {
	for rtype := range app.Spec.FLReplicaSpecs {
		rt := strings.ToLower(string(rtype))
		if needPair(app, rtype) {
			name := GenName(app.Name, rt)
			configMap, err := am.configMapLister.ConfigMaps(am.namespace).Get(name)
			// ConfigMap not ready
			if err != nil || configMap == nil {
				return false
			}
		}
		// Pod not ready
		if app.Status.FLReplicaStatus[rtype].Active.Len() != getReplicas(app, rtype) {
			return false
		}
		// Service not ready
		if app.Status.FLReplicaStatus[rtype].Local.Len() != getReplicas(app, rtype) {
			return false
		}
	}
	ingress, err := am.ingressLister.Ingresses(am.namespace).Get(app.Name)
	// Ingress not ready
	if err != nil || ingress == nil {
		return false
	}
	return true
}

func (am *appManager) reconcileConfigMaps(app *v1alpha1.FLApp) error {
	for rtype := range app.Spec.FLReplicaSpecs {
		if needPair(app, rtype) {
			if err := am.createOrUpdateConfigMap(app, rtype, nil); err != nil {
				return err
			}
		}
	}
	return nil
}

func (am *appManager) reconcileIngress(app *v1alpha1.FLApp) error {
	name := app.Name
	needIngress := false
	for rtype := range app.Spec.FLReplicaSpecs {
		if needPair(app, rtype) {
			needIngress = true
			break
		}
	}
	if !needIngress {
		ingress, err := am.ingressLister.Ingresses(am.namespace).Get(name)
		if err != nil {
			return err
		}
		if ingress != nil {
			return am.kubeClient.NetworkingV1beta1().Ingresses(am.namespace).Delete(name, &metav1.DeleteOptions{})
		}
	}
	return am.createIngress(app)
}

func (am *appManager) createIngress(app *v1alpha1.FLApp) error {
	name := app.Name
	ownerReference := am.GenOwnerReference(app)
	labels := GenLabels(name)
	// TODO: support more kinds of ingress
	annotations := map[string]string{
		"kubernetes.io/ingress.class":                       "nginx",
		"nginx.ingress.kubernetes.io/backend-protocol":      "GRPC",
		"nginx.ingress.kubernetes.io/configuration-snippet": "grpc_next_upstream_tries 5 ;",
	}
	ingress, err := am.ingressLister.Ingresses(am.namespace).Get(name)
	if err != nil && !errors.IsNotFound(err) {
		return err
	}
	if ingress == nil {
		newIngress := &networking.Ingress{
			ObjectMeta: metav1.ObjectMeta{
				Name:            name,
				Labels:          labels,
				Annotations:     annotations,
				OwnerReferences: []metav1.OwnerReference{*ownerReference},
			},
		}
		for rtype := range app.Spec.FLReplicaSpecs {
			if needPair(app, rtype) {
				replicas := getReplicas(app, rtype)
				rt := strings.ToLower(string(rtype))
				for index := 0; index < replicas; index++ {
					path := networking.HTTPIngressPath{
						Backend: networking.IngressBackend{
							ServiceName: GenIndexName(name, rt, strconv.Itoa(index)),
							ServicePort: intstr.FromString(v1alpha1.DefaultPortName),
						},
					}
					rule := networking.IngressRule{
						Host: GenIndexName(app.Name, rt, strconv.Itoa(index)),
						IngressRuleValue: networking.IngressRuleValue{
							HTTP: &networking.HTTPIngressRuleValue{
								Paths: []networking.HTTPIngressPath{path},
							},
						},
					}
					newIngress.Spec.Rules = append(newIngress.Spec.Rules, rule)
				}
			}
		}
		_, err := am.kubeClient.NetworkingV1beta1().Ingresses(am.namespace).Create(newIngress)
		return err
	}
	return nil
}

// if data is not nil, update configMap Data to data
func (am *appManager) createOrUpdateConfigMap(app *v1alpha1.FLApp, rtype v1alpha1.FLReplicaType, data map[string]string) error {
	namespace := am.namespace
	rt := strings.ToLower(string(rtype))
	name := GenName(app.Name, rt)
	ownerReference := am.GenOwnerReference(app)

	labels := GenLabels(app.Name)
	labels[flReplicaTypeLabel] = rt

	configMap, err := am.configMapLister.ConfigMaps(am.namespace).Get(name)
	if err != nil && !errors.IsNotFound(err) {
		return err
	}

	createConfigMap := configMap == nil
	newConfigMap := &v1.ConfigMap{
		ObjectMeta: metav1.ObjectMeta{
			Name:            name,
			Labels:          labels,
			OwnerReferences: []metav1.OwnerReference{*ownerReference},
		},
	}
	if data != nil {
		newConfigMap.Data = data
	} else if configMap != nil {
		newConfigMap.Data = configMap.Data
	}
	if createConfigMap {
		_, err := am.kubeClient.CoreV1().ConfigMaps(namespace).Create(newConfigMap)
		return err
	} else {
		_, err := am.kubeClient.CoreV1().ConfigMaps(namespace).Update(newConfigMap)
		return err
	}
}

func (am *appManager) syncBootstrappedApp(app *v1alpha1.FLApp) error {
	name := app.Name
	klog.Infof("sync bootstrapped app, name = %v", name)

	if IsLeader(app.Spec.Role) {
		return am.syncLeaderApp(app)
	}
	return am.syncFollowerApp(app)
}

func (am *appManager) syncLeaderApp(app *v1alpha1.FLApp) error {
	name := app.Name
	klog.Infof("sync bootstrapped leader app, name = %v", name)
	if am.replicaPaired(app) && am.configMapUpdated(app) {
		return am.appStatusUpdater.UpdateAppStateWithRetry(app, v1alpha1.FLStateRunning)
	}

	for rtype := range app.Spec.FLReplicaSpecs {
		if needPair(app, rtype) {
			if app.Status.FLReplicaStatus[rtype].Remote.Len() != getReplicas(app, rtype) {
				err := fmt.Errorf("still waiting for follower, name = %v, rtype = %v", name, rtype)
				klog.Info(err)
				return err
			}
		}
	}

	for rtype := range app.Spec.FLReplicaSpecs {
		if needPair(app, rtype) {
			local := app.Status.FLReplicaStatus[rtype].Local.List()
			remote := app.Status.FLReplicaStatus[rtype].Remote.List()
			mapping := make(map[string]string)
			for idx := 0; idx < len(local); idx++ {
				mapping[local[idx]] = remote[idx]
			}
			// Update configMap and then update mapping status
			if err := am.createOrUpdateConfigMap(app, rtype, mapping); err != nil {
				return err
			}
			status := app.Status.FLReplicaStatus[rtype]
			replicaStatus := status.DeepCopy()
			replicaStatus.Mapping = mapping
			app.Status.FLReplicaStatus[rtype] = *replicaStatus
		}
	}
	if err := am.appEventHandler.Pair(app); err != nil {
		klog.Errorf("failed to call Pair handler, name = %v, err = %v", name, err)
		return err
	}
	return am.setStatus(app)
}

func (am *appManager) syncFollowerApp(app *v1alpha1.FLApp) error {
	name := app.Name
	klog.Infof("sync bootstrapped follower app, name = %v", name)

	if err := am.appEventHandler.Register(app); err != nil {
		klog.Errorf("failed to call Register, name = %v, err = %v", name, err)
		return err
	}
	return am.appStatusUpdater.UpdateAppStateWithRetry(app, v1alpha1.FLStateSyncSent)
}

func (am *appManager) syncSyncSentApp(app *v1alpha1.FLApp) error {
	name := app.Name
	klog.Infof("sync sync-sent app, name = %v", name)
	configMapUpdated := am.configMapUpdated(app)
	if am.replicaPaired(app) && am.configMapUpdated(app) {
		return am.appStatusUpdater.UpdateAppStateWithRetry(app, v1alpha1.FLStateRunning)
	}
	klog.Infof("still waiting for leader, name = %v", name)
	if !configMapUpdated {
		for rtype := range app.Spec.FLReplicaSpecs {
			if needPair(app, rtype) {
				if err := am.createOrUpdateConfigMap(app, rtype, app.Status.FLReplicaStatus[rtype].Mapping); err != nil {
					return err
				}
			}
		}
	}
	return nil
}

func (am *appManager) replicaPaired(app *v1alpha1.FLApp) bool {
	for rtype := range app.Spec.FLReplicaSpecs {
		if needPair(app, rtype) {
			if app.Status.FLReplicaStatus[rtype].Local.Len() != getReplicas(app, rtype) {
				return false
			}
			if app.Status.FLReplicaStatus[rtype].Remote.Len() != getReplicas(app, rtype) {
				return false
			}
			if len(app.Status.FLReplicaStatus[rtype].Mapping) != getReplicas(app, rtype) {
				return false
			}
		}
	}
	return true
}

func (am *appManager) configMapUpdated(app *v1alpha1.FLApp) bool {
	for rtype := range app.Spec.FLReplicaSpecs {
		if needPair(app, rtype) {
			rt := strings.ToLower(string(rtype))
			configMapName := GenName(app.Name, rt)

			configMap, err := am.configMapLister.ConfigMaps(am.namespace).Get(configMapName)
			if err != nil || configMap == nil {
				return false
			}
			return apiequality.Semantic.DeepEqual(configMap.Data, app.Status.FLReplicaStatus[rtype].Mapping)
		}
	}
	return true
}

func (am *appManager) syncRunningApp(app *v1alpha1.FLApp) error {
	name := app.Name
	klog.Infof("sync running app, name = %v", name)
	if am.isAppFinished(app) {
		if err := am.appEventHandler.Finish(app); err != nil {
			klog.Errorf("failed to call Finished handler, name = %v, err = %v", name, err)
			return err
		}
		if err := am.freeResource(app); err != nil {
			klog.Errorf("failed to free resource when app is finished, name = %v, err = %v", name, err)
			return err
		}
		return am.appStatusUpdater.UpdateAppStateWithRetry(app, v1alpha1.FLStateComplete)
	}
	klog.Infof("app still running, name = %v", name)
	return am.reconcileFLApp(app)
}

func (am *appManager) isAppFinished(app *v1alpha1.FLApp) bool {
	rtypeWorker := v1alpha1.FLReplicaTypeWorker
	return app.Status.FLReplicaStatus[rtypeWorker].Succeeded.Len() == getReplicas(app, rtypeWorker)
}

func (am *appManager) isAppFailing(app *v1alpha1.FLApp) bool {
	rtypePS := v1alpha1.FLReplicaTypePS
	// PS can not tolerate failure
	if app.Status.FLReplicaStatus[rtypePS].Failed.Len() > 0 {
		return true
	}
	prevReplicasFailedNum := 0
	for _, status := range app.Status.FLReplicaStatus {
		prevReplicasFailedNum += status.Failed.Len()
	}
	return prevReplicasFailedNum > int(*app.Spec.BackoffLimit)
}

func (am *appManager) isAppTimeOut(app *v1alpha1.FLApp, now time.Time) bool {
	if app.Spec.ActiveDeadlineSeconds == nil {
		return false
	}
	return app.GetCreationTimestamp().Add(time.Duration(*app.Spec.ActiveDeadlineSeconds)).After(now)
}

func (am *appManager) syncFailingApp(app *v1alpha1.FLApp) error {
	name := app.Name
	klog.Infof("sync failing app, name = %v", name)
	if err := am.appEventHandler.Shutdown(app); err != nil {
		klog.Errorf("failed to call FLStateFailed handler, name = %v, err = %v", name, err)
		return err
	}
	return am.appStatusUpdater.UpdateAppStateWithRetry(app, v1alpha1.FLStateShutDown)
}

func (am *appManager) syncShuttingDownApp(app *v1alpha1.FLApp) error {
	name := app.Name
	klog.Infof("sync shutting-down app, name = %v", name)
	if err := am.freeResource(app); err != nil {
		return err
	}
	return am.appStatusUpdater.UpdateAppStateWithRetry(app, v1alpha1.FLStateFailed)
}

func (am *appManager) freeResource(app *v1alpha1.FLApp) error {
	name := app.Name
	deletePropagationBackground := metav1.DeletePropagationBackground
	pods, err := am.getPodsForApp(app)
	if err != nil {
		return err
	}
	selector, err := metav1.LabelSelectorAsSelector(&metav1.LabelSelector{
		MatchLabels: GenLabels(app.GetName()),
	})
	if err != nil {
		return err
	}

	if *app.Spec.CleanPodPolicy == v1alpha1.CleanPodPolicyNone {
		klog.Infof("CleanPodPolicy = %v, nothing will be deleted for app, name = %v", v1alpha1.CleanPodPolicyNone, name)
		return nil
	}

	for _, pod := range pods {
		rt := pod.Labels[flReplicaTypeLabel]
		index := pod.Labels[flReplicaIndexLabel]
		if err := am.podControl.DeletePod(pod.Namespace, pod.Name, app); err != nil && !errors.IsNotFound(err) {
			return err
		}
		if err := am.serviceControl.DeleteService(pod.Namespace, GenIndexName(app.Name, rt, index), app); err != nil && !errors.IsNotFound(err) {
			return err
		}
	}
	if err := am.kubeClient.CoreV1().ConfigMaps(am.namespace).DeleteCollection(&metav1.DeleteOptions{
		PropagationPolicy: &deletePropagationBackground,
	}, metav1.ListOptions{
		LabelSelector: selector.String(),
	}); err != nil && !errors.IsNotFound(err) {
		return err
	}
	if err := am.kubeClient.NetworkingV1beta1().Ingresses(am.namespace).Delete(app.Name, &metav1.DeleteOptions{
		PropagationPolicy: &deletePropagationBackground,
	}); err != nil && !errors.IsNotFound(err) {
		return err
	}
	return nil
}

func getReplicas(app *v1alpha1.FLApp, rtype v1alpha1.FLReplicaType) int {
	return int(*app.Spec.FLReplicaSpecs[rtype].Replicas)
}

func needPair(app *v1alpha1.FLApp, rtype v1alpha1.FLReplicaType) bool {
	return app.Spec.FLReplicaSpecs[rtype].Pair != nil && *app.Spec.FLReplicaSpecs[rtype].Pair == true
}
