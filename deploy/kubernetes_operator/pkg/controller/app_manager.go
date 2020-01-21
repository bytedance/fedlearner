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
	"reflect"
	"strings"
	"time"

	appsv1 "k8s.io/api/apps/v1"
	batchv1 "k8s.io/api/batch/v1"
	v1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/labels"
	"k8s.io/apimachinery/pkg/util/rand"
	"k8s.io/apimachinery/pkg/util/sets"
	"k8s.io/apimachinery/pkg/util/uuid"
	"k8s.io/apimachinery/pkg/util/wait"
	clientset "k8s.io/client-go/kubernetes"
	listersappv1 "k8s.io/client-go/listers/apps/v1"
	listersbatchv1 "k8s.io/client-go/listers/batch/v1"
	listerscorev1 "k8s.io/client-go/listers/core/v1"
	"k8s.io/klog"

	"github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/apis/fedlearner.k8s.io/v1alpha1"
	crdclientset "github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/client/clientset/versioned"
	crdlisters "github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/client/listers/fedlearner.k8s.io/v1alpha1"
	"github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/util"
)

const (
	LabelKeyWorkerID = "workerID"
	LabelKeyMaster   = "master"
	LabelKeyPS       = "PS"

	WorkerPairVolumeName = "worker-pair"
	WorkerPairMountPath  = "/etc/worker"
	MasterPairVolumeName = "master-pair"
	MasterPairMountPath  = "/etc/worker"

	WorkerEnvID             = "WORKER_ID"
	WorkerEnvPSHosts        = "PS_HOSTS"
	WorkerEnvMasterPodNames = "MASTER_POD_NAMES"

	HousekeepingPeriod   = time.Duration(30) * time.Second
	CondemnedJobDeadline = time.Duration(1) * time.Minute
)

type AppManager interface {
	SyncApp(app *v1alpha1.FLApp, deleting bool) error
}

type appManager struct {
	namespace            string
	assignWorkerPort     bool
	workerPortLowerBound int
	workerPortUpperBound int

	kubeClient clientset.Interface
	crdClient  crdclientset.Interface

	appLister         crdlisters.FLAppLister
	statefulsetLister listersappv1.StatefulSetLister
	jobLister         listersbatchv1.JobLister
	configMapLister   listerscorev1.ConfigMapLister
	podLister         listerscorev1.PodLister

	appFailingCache *util.ExpirationCache

	appStatusUpdater util.StatusUpdater
	appEventHandler  AppEventHandler
}

var (
	_ AppManager = &appManager{}
)

func NewAppManager(
	namespace string,
	assignWorkerPort bool,
	workerPortLowerBound int,
	workerPortUpperBound int,
	kubeClient clientset.Interface,
	crdClient crdclientset.Interface,
	appLister crdlisters.FLAppLister,
	statefulsetLister listersappv1.StatefulSetLister,
	jobLister listersbatchv1.JobLister,
	configMapLister listerscorev1.ConfigMapLister,
	podLister listerscorev1.PodLister,
	appEventHandler AppEventHandler,
	stopCh <-chan struct{},
) AppManager {
	manager := &appManager{
		namespace:            namespace,
		assignWorkerPort:     assignWorkerPort,
		workerPortLowerBound: workerPortLowerBound,
		workerPortUpperBound: workerPortUpperBound,

		kubeClient: kubeClient,
		crdClient:  crdClient,

		appLister:         appLister,
		statefulsetLister: statefulsetLister,
		jobLister:         jobLister,
		configMapLister:   configMapLister,
		podLister:         podLister,

		appFailingCache: util.NewExpirationCache(),

		appStatusUpdater: util.NewappStatusUpdater(crdClient, namespace),
		appEventHandler:  appEventHandler,
	}
	go wait.Until(manager.housekeeping, HousekeepingPeriod, stopCh)
	return manager
}

func (tm *appManager) housekeeping() {
	apps, err := tm.appLister.FLApps(tm.namespace).List(labels.Everything())
	if err != nil {
		return
	}

	for _, app := range apps {
		appID := app.Spec.AppID
		if app.Status.AppState == v1alpha1.AppComplete && !tm.isResourceFreed(app) {
			if err := tm.freeResource(app); err != nil {
				klog.Errorf("failed to free resource for app, appID = %v, err = %v", appID, err)
			}
		}
		_, condemnedJobs, _, _, err := tm.getCurrentJobs(app, tm.namespace)
		if err != nil {
			klog.Errorf("failed to get jobs for app when housekeeping, appID = %v, err = %v", appID, err)
			continue
		}
		if err := tm.cleanCondemnedJobs(app, condemnedJobs); err != nil {
			klog.Errorf("failed to clean condemned jobs, appID = %v, err = %v", appID, err)
		}
	}
}

func (tm *appManager) cleanCondemnedJobs(
	app *v1alpha1.FLApp,
	condemnedJobs []*batchv1.Job,
) error {
	appID := app.Spec.AppID
	for _, job := range condemnedJobs {
		jobName := job.Name
		createdAt := job.GetCreationTimestamp().Time
		if time.Now().Sub(createdAt) >= CondemnedJobDeadline {
			klog.Errorf("removing condemn job %v for application %v", jobName, appID)
			policy := metav1.DeletePropagationBackground
			if err := tm.kubeClient.BatchV1().Jobs(tm.namespace).Delete(jobName, &metav1.DeleteOptions{PropagationPolicy: &policy}); err != nil {
				if errors.IsNotFound(err) {
					klog.Infof("application %v job %v is already deleted", appID, jobName)
					continue
				}
				klog.Errorf("failed to clean condemned job %v, err = %v", jobName, err)
			}
		}
	}
	return nil
}

func (tm *appManager) SyncApp(app *v1alpha1.FLApp, deleting bool) error {
	appCopy := app.DeepCopy()
	appID := appCopy.Spec.AppID

	if deleting {
		klog.Infof("deleting application %v, shut it down", appID)
		return tm.deleteApp(appCopy)
	}

	appState := appCopy.Status.AppState
	if appState == "" {
		if _, err := tm.appStatusUpdater.UpdateAppStatusWithRetry(appCopy, func(mutatingApp *v1alpha1.FLApp) bool {
			if mutatingApp.Status.PairStatus != nil {
				return false
			}
			mutatingApp.Status.AppState = v1alpha1.AppNew
			mutatingApp.Status.PairStatus = make(map[v1alpha1.FLReplicaType]*v1alpha1.Pair)
			for rtype, spec := range mutatingApp.Spec.FLReplicaSpecs {
				if spec != nil && spec.Pair {
					mutatingApp.Status.PairStatus[rtype] = &v1alpha1.Pair{}
				}
			}
			return true
		}); err != nil {
			klog.Errorf("failed to init app, appID = %v", appID)
		}
	}

	if appState == v1alpha1.AppBootstrapped || appState == v1alpha1.AppSyncSent || appState == v1alpha1.AppRunning {
		if tm.isAppFailing(app) {
			return tm.appStatusUpdater.UpdateAppStateWithRetry(app, v1alpha1.AppFailing)
		}
	} else {
		tm.appFailingCache.Delete(appID)
	}

	switch appState {
	case v1alpha1.AppNew:
		return tm.syncNewApp(appCopy)
	case v1alpha1.AppPSStarted:
		return tm.syncPSStartedApp(appCopy)
	case v1alpha1.AppBootstrapped:
		return tm.syncBootstrappedApp(appCopy)
	case v1alpha1.AppSyncSent:
		return tm.syncSyncSentApp(appCopy)
	case v1alpha1.AppRunning:
		return tm.syncRunningApp(appCopy)
	case v1alpha1.AppFailing:
		return tm.syncFailingApp(appCopy)
	case v1alpha1.AppShuttingDown:
		return tm.syncShuttingDownApp(appCopy)
	case v1alpha1.AppComplete, v1alpha1.AppFailed:
		klog.Infof("ignore app %v as its state is %v", appID, appState)
	}
	return nil
}

func (tm *appManager) deleteApp(app *v1alpha1.FLApp) error {
	appID := app.Spec.AppID
	appState := app.Status.AppState
	if appState == "" {
		appState = v1alpha1.AppNew
	}
	switch appState {
	case v1alpha1.AppNew, v1alpha1.AppPSStarted, v1alpha1.AppBootstrapped, v1alpha1.AppSyncSent, v1alpha1.AppRunning:
		klog.Infof("shutting down peer as app is deleted, appID = %v", appID)
		if err := tm.appEventHandler.OnFailedHandler(app); err != nil {
			klog.Errorf("failed to shutdown peer when app is deleted, appID = %v, err = %v", appID, err)
		}
	}
	if err := tm.freeResource(app); err != nil {
		klog.Errorf("failed to free resources when app is deleted, appID = %v, err = %v", appID, err)
	}
	return nil
}

func (tm *appManager) syncNewApp(app *v1alpha1.FLApp) error {
	appID := app.Spec.AppID
	klog.Infof("sync new app, appID = %v", appID)
	if tm.psStarted(app) {
		return tm.appStatusUpdater.UpdateAppStateWithRetry(app, v1alpha1.AppPSStarted)
	}
	klog.Infof("creating PS stateful_set, appID = %v", appID)
	return tm.startPS(app)
}

func (tm *appManager) psStarted(app *v1alpha1.FLApp) bool {
	desiredReplica := int(*getReplicas(app, v1alpha1.FLReplicaTypePS))
	labelSet := util.GetLabelSetWithappID(app)
	labelSet[LabelKeyPS] = "true"
	if app.Status.PSAddress.Len() != desiredReplica {
		return false
	}
	address := tm.getPodAddress(labelSet.AsSelector())
	if address.Len() != desiredReplica {
		return false
	}
	if len(address) == 0 {
		return app.Status.PSAddress.Len() == 0
	}
	return reflect.DeepEqual(address, app.Status.PSAddress)
}

func (tm *appManager) getPodAddress(labelSelector labels.Selector) sets.String {
	address := sets.NewString()
	pods, err := tm.podLister.Pods(tm.namespace).List(labelSelector)
	if err != nil {
		return sets.NewString()
	}
	// pods must be running
	for _, pod := range pods {
		podCopy := *pod
		if podCopy.Status.Phase != v1.PodRunning {
			return sets.NewString()
		}
		// container status unknown
		if len(podCopy.Status.ContainerStatuses) == 0 {
			return sets.NewString()
		}
		// container restarted
		containerStatus := podCopy.Status.ContainerStatuses[0]
		if containerStatus.RestartCount > 0 {
			return sets.NewString()
		}
		// container without ports
		container := podCopy.Spec.Containers[0]
		if len(container.Ports) == 0 {
			return sets.NewString()
		}
		port := fmt.Sprintf("%d", container.Ports[0].ContainerPort)
		address.Insert(strings.Join([]string{podCopy.Status.PodIP, port}, ":"))
	}
	return address
}

func (tm *appManager) startPS(app *v1alpha1.FLApp) error {
	appID := app.Spec.AppID
	desiredReplica := int(*getReplicas(app, v1alpha1.FLReplicaTypePS))

	statefulSetSpec := app.Spec.PS.Template
	labelSet := util.GetLabelSetWithappID(app)
	labelSet[LabelKeyPS] = "true"
	statefulSetSpec.Selector = metav1.SetAsLabelSelector(labelSet)
	statefulSetSpec.Template.Labels = labelSet
	statefulSetSpec.Replicas = getReplicas(app, v1alpha1.FLReplicaTypePS)
	statefulset := &appsv1.StatefulSet{
		ObjectMeta: metav1.ObjectMeta{
			Name: psName(appID),
		},
		Spec: statefulSetSpec,
	}

	_, err := tm.kubeClient.AppsV1().StatefulSets(tm.namespace).Create(statefulset)
	if err != nil && !errors.IsAlreadyExists(err) {
		return err
	}
	if len(app.Status.PSAddress) != desiredReplica {
		if address := tm.getPodAddress(labelSet.AsSelector()); address.Len() == desiredReplica {
			_, err := tm.appStatusUpdater.UpdateAppStatusWithRetry(app, func(mutatingApp *v1alpha1.FLApp) bool {
				if reflect.DeepEqual(mutatingApp.Status.PSAddress, address) {
					return false
				}
				mutatingApp.Status.PSAddress = address
				return true
			})
			return err
		}
	}
	return nil
}

func (tm *appManager) syncPSStartedApp(app *v1alpha1.FLApp) error {
	appID := app.Spec.AppID
	klog.Infof("sync PS started app, appID = %v", appID)

	if tm.isAppBootstrapped(app) {
		return tm.appStatusUpdater.UpdateAppStateWithRetry(app, v1alpha1.AppBootstrapped)
	}

	if err := tm.startMaster(app); err != nil {
		klog.Errorf("failed to start master, appID = %v", appID)
		return err
	}
	activeJobs, _, phantomJobs, allJobs, err := tm.getCurrentJobs(app, tm.namespace)
	if err != nil {
		klog.Errorf("failed to get current jobs after PS started, appID = %v", appID)
		return err
	}
	if err := tm.startNewJobs(app, activeJobs, phantomJobs, allJobs); err != nil {
		klog.Errorf("failed to start new jobs after PS started, appID = %v", appID)
		return err
	}
	return nil
}

func (tm *appManager) isAppBootstrapped(app *v1alpha1.FLApp) bool {
	appID := app.Spec.AppID
	masterDesiredReplica := *getReplicas(app, v1alpha1.FLReplicaTypeMaster)
	workerDesiredReplica := int(*getReplicas(app, v1alpha1.FLReplicaTypeWorker))

	master, err := tm.statefulsetLister.StatefulSets(tm.namespace).Get(masterName(appID))
	if err != nil || master == nil {
		return false
	}
	if master.Status.ReadyReplicas != masterDesiredReplica {
		return false
	}
	if configMap, err := tm.configMapLister.ConfigMaps(tm.namespace).Get(masterConfigMapName(appID)); err != nil || configMap == nil {
		return false
	}
	if configMap, err := tm.configMapLister.ConfigMaps(tm.namespace).Get(workerConfigMapName(appID)); err != nil || configMap == nil {
		return false
	}
	if activeJobs, _, _, _, err := tm.getCurrentJobs(app, tm.namespace); err != nil || len(activeJobs) != workerDesiredReplica {
		return false
	}
	return true
}

func (tm *appManager) startMaster(app *v1alpha1.FLApp) error {
	appID := app.Spec.AppID

	configMap := &v1.ConfigMap{
		ObjectMeta: metav1.ObjectMeta{
			Name: workerConfigMapName(appID),
		},
	}
	if _, err := tm.kubeClient.CoreV1().ConfigMaps(tm.namespace).Create(configMap); err != nil && !errors.IsAlreadyExists(err) {
		return err
	}
	configMap = &v1.ConfigMap{
		ObjectMeta: metav1.ObjectMeta{
			Name: masterConfigMapName(appID),
		},
	}
	if _, err := tm.kubeClient.CoreV1().ConfigMaps(tm.namespace).Create(configMap); err != nil && !errors.IsAlreadyExists(err) {
		return err
	}

	statefulsetSpec := app.Spec.Master.Template
	labelSelector := util.GetLabelSetWithappID(app)
	labelSelector[LabelKeyMaster] = "true"
	statefulsetSpec.Selector = metav1.SetAsLabelSelector(labelSelector)
	statefulsetSpec.Template.Labels = labelSelector
	statefulsetSpec.Replicas = getReplicas(app, v1alpha1.FLReplicaTypeMaster)

	for idx := range statefulsetSpec.Template.Spec.Containers {
		container := &statefulsetSpec.Template.Spec.Containers[idx]
		container.VolumeMounts = appendVolumeMountIfAbsent(container.VolumeMounts, v1.VolumeMount{
			Name:      MasterPairVolumeName,
			ReadOnly:  true,
			MountPath: MasterPairMountPath,
		})
	}
	statefulsetSpec.Template.Spec.Volumes = append(statefulsetSpec.Template.Spec.Volumes, v1.Volume{
		Name: MasterPairVolumeName,
		VolumeSource: v1.VolumeSource{
			ConfigMap: &v1.ConfigMapVolumeSource{
				LocalObjectReference: v1.LocalObjectReference{
					Name: masterConfigMapName(appID),
				},
			},
		},
	})

	statefulset := &appsv1.StatefulSet{
		ObjectMeta: metav1.ObjectMeta{
			Name: masterName(appID),
		},
		Spec: statefulsetSpec,
	}
	if _, err := tm.kubeClient.AppsV1().StatefulSets(tm.namespace).Create(statefulset); err != nil && !errors.IsAlreadyExists(err) {
		return err
	}

	masterPodNames := tm.getPodNames(labelSelector.AsSelector())
	desiredReplicas := int(*getReplicas(app, v1alpha1.FLReplicaTypeMaster))
	if masterPodNames.Len() == desiredReplicas {
		_, err := tm.appStatusUpdater.UpdateAppStatusWithRetry(app, func(mutatingApp *v1alpha1.FLApp) bool {
			if mutatingApp.Status.PairStatus[v1alpha1.FLReplicaTypeMaster].Local.Len() == desiredReplicas {
				return false
			}
			if mutatingApp.Status.PairStatus[v1alpha1.FLReplicaTypeMaster].Local == nil {
				mutatingApp.Status.PairStatus[v1alpha1.FLReplicaTypeMaster].Local = sets.NewString()
			}
			mutatingApp.Status.PairStatus[v1alpha1.FLReplicaTypeMaster].Local = masterPodNames
			return true
		})
		return err
	}
	return nil
}

// activeJobs contain bootstrapped jobs that are either running or waiting for peers,
// condemnedJobs are failed jobs
// phantomJobs are unrecognized job keys in app status
func (tm *appManager) getCurrentJobs(app *v1alpha1.FLApp, namespace string) ([]*batchv1.Job, []*batchv1.Job, []string, []*batchv1.Job, error) {
	allJobs, err := tm.jobLister.Jobs(namespace).List(util.GetLabelSetWithappID(app).AsSelector())
	if err != nil {
		return nil, nil, nil, nil, err
	}

	var activeJobs, condemnedJobs []*batchv1.Job
	var phantomJobs []string
	for _, job := range allJobs {
		if _, ok := app.Status.PairStatus[v1alpha1.FLReplicaTypeWorker].Local[job.Name]; ok {
			activeJobs = append(activeJobs, job)
		} else {
			condemnedJobs = append(condemnedJobs, job)
		}
	}
	for jobName := range app.Status.PairStatus[v1alpha1.FLReplicaTypeWorker].Local {
		exist := false
		for _, job := range allJobs {
			if jobName == job.Name {
				exist = true
				break
			}
		}
		if !exist {
			phantomJobs = append(phantomJobs, jobName)
		}
	}
	return activeJobs, condemnedJobs, phantomJobs, allJobs, nil
}

func (tm *appManager) startNewJobs(
	app *v1alpha1.FLApp,
	activeJobs []*batchv1.Job,
	phantomJobs []string,
	allJobs []*batchv1.Job,
) error {
	var err error
	appID := app.Spec.AppID
	masterReplica := int(*getReplicas(app, v1alpha1.FLReplicaTypeMaster))
	workerReplica := int(*getReplicas(app, v1alpha1.FLReplicaTypeWorker))
	currentWorkerReplica := app.Status.PairStatus[v1alpha1.FLReplicaTypeWorker].Local.Len()
	labelSet := util.GetLabelSetWithappID(app)
	labelSet[LabelKeyMaster] = "true"

	podNames := tm.getPodNames(labelSet.AsSelector())
	if podNames.Len() != masterReplica {
		err := fmt.Errorf("master is not ready for application %v, podNames = %v", appID, podNames)
		klog.Error(err)
		return err
	}

	// recreate jobs if not already exists
	for _, jobName := range phantomJobs {
		klog.Infof("recreating phantom job %v for application %v", jobName, appID)
		if err = tm.createJob(app, jobName, podNames); err != nil {
			err = fmt.Errorf("failed to recreate phantom job %v, err = %v", jobName, err)
			klog.Error(err)
			return err
		}
	}
	for idx := 0; idx < workerReplica-currentWorkerReplica; idx++ {
		jobName := fmt.Sprintf("job-%v-%v", currentWorkerReplica+idx, string(uuid.NewUUID()))
		klog.Infof("updating desired job %v for application %v", jobName, appID)
		app, err = tm.appStatusUpdater.UpdateAppStatusWithRetry(app, func(mutatingApp *v1alpha1.FLApp) bool {
			if mutatingApp.Status.PairStatus[v1alpha1.FLReplicaTypeWorker].Local != nil && mutatingApp.Status.PairStatus[v1alpha1.FLReplicaTypeWorker].Local.Has(jobName) {
				return false
			}
			if mutatingApp.Status.PairStatus[v1alpha1.FLReplicaTypeWorker].Local == nil {
				mutatingApp.Status.PairStatus[v1alpha1.FLReplicaTypeWorker].Local = sets.NewString()
			}
			mutatingApp.Status.PairStatus[v1alpha1.FLReplicaTypeWorker].Local.Insert(jobName)
			return true
		})
		if err != nil {
			klog.Errorf(
				"failed to update app status for job %v, appID = %v, err = %v",
				jobName,
				appID,
				err,
			)
			return err
		}
		klog.Infof("creating desired job %v for application %v", jobName, appID)
		if err = tm.createJob(app, jobName, podNames); err != nil {
			klog.Errorf("failed to create new job %v, err = %v", jobName, err)
			return err
		}
	}
	return nil
}

func (tm *appManager) getPodNames(labelSelector labels.Selector) sets.String {
	names := sets.NewString()
	pods, err := tm.podLister.Pods(tm.namespace).List(labelSelector)
	if err != nil {
		return sets.NewString()
	}
	// pods must be running
	for _, pod := range pods {
		podCopy := *pod
		if podCopy.Status.Phase != v1.PodRunning {
			return sets.NewString()
		}
		// containers not started
		if len(podCopy.Status.ContainerStatuses) == 0 {
			return sets.NewString()
		}
		names.Insert(podCopy.Name)
	}
	return names
}

func (tm *appManager) createJob(app *v1alpha1.FLApp, jobName string, names sets.String) error {
	appID := app.Spec.AppID
	var limit int32 = 1
	manualSelector := true
	jobSpec := app.Spec.Worker.Template
	jobSpec.Parallelism = &limit
	jobSpec.Completions = &limit
	jobSpec.ManualSelector = &manualSelector
	set := util.GetLabelSetWithappID(app)
	set[LabelKeyWorkerID] = jobName
	jobSpec.Selector = metav1.SetAsLabelSelector(set)
	jobSpec.Template.Spec.RestartPolicy = v1.RestartPolicyOnFailure
	jobSpec.Template.Labels = set

	for idx := range jobSpec.Template.Spec.Containers {
		container := &jobSpec.Template.Spec.Containers[idx]
		container.Env = ensureEnv(container.Env, v1.EnvVar{
			Name:  WorkerEnvID,
			Value: jobName,
		})
		container.Env = ensureEnv(container.Env, v1.EnvVar{
			Name:  WorkerEnvPSHosts,
			Value: strings.Join(app.Status.PSAddress.List(), ","),
		})
		container.Env = ensureEnv(container.Env, v1.EnvVar{
			Name:  WorkerEnvMasterPodNames,
			Value: strings.Join(names.List(), ","),
		})
		if tm.assignWorkerPort && len(container.Ports) > 0 {
			for idx2 := range container.Ports {
				port := int32(rand.IntnRange(tm.workerPortLowerBound, tm.workerPortUpperBound+1))
				container.Ports[idx2].ContainerPort = port
				container.Env = ensureEnv(container.Env, v1.EnvVar{
					Name:  strings.ToUpper(container.Ports[idx2].Name),
					Value: fmt.Sprintf("%d", port),
				})
			}
		}

		container.VolumeMounts = appendVolumeMountIfAbsent(container.VolumeMounts, v1.VolumeMount{
			Name:      WorkerPairVolumeName,
			ReadOnly:  true,
			MountPath: WorkerPairMountPath,
		})
	}
	jobSpec.Template.Spec.Volumes = append(jobSpec.Template.Spec.Volumes, v1.Volume{
		Name: WorkerPairVolumeName,
		VolumeSource: v1.VolumeSource{
			ConfigMap: &v1.ConfigMapVolumeSource{
				LocalObjectReference: v1.LocalObjectReference{
					Name: workerConfigMapName(appID),
				},
			},
		},
	})

	job := &batchv1.Job{
		ObjectMeta: metav1.ObjectMeta{
			Name:   jobName,
			Labels: util.GetLabelSetWithappID(app),
		},
		Spec: jobSpec,
	}
	if _, err := tm.kubeClient.BatchV1().Jobs(tm.namespace).Create(job); err != nil && !errors.IsAlreadyExists(err) {
		return err
	}
	return nil
}

func ensureEnv(envVars []v1.EnvVar, item v1.EnvVar) []v1.EnvVar {
	for idx := range envVars {
		if envVars[idx].Name == item.Name {
			envVars[idx].Value = item.Value
			return envVars
		}
	}
	envVars = append(envVars, item)
	return envVars
}

func appendVolumeMountIfAbsent(volumeMounts []v1.VolumeMount, item v1.VolumeMount) []v1.VolumeMount {
	for _, volumeMount := range volumeMounts {
		if volumeMount.Name == item.Name {
			return volumeMounts
		}
	}
	volumeMounts = append(volumeMounts, item)
	return volumeMounts
}

func (tm *appManager) syncBootstrappedApp(app *v1alpha1.FLApp) error {
	appID := app.Spec.AppID
	klog.Infof("sync bootstrapped app, appID = %v", appID)

	switch app.Spec.Role {
	case v1alpha1.Leader:
		return tm.syncLeaderApp(app)
	case v1alpha1.Follower:
		return tm.syncFollowerApp(app)
	}
	return nil
}

func (tm *appManager) syncLeaderApp(app *v1alpha1.FLApp) error {
	appID := app.Spec.AppID
	klog.Infof("sync bootstrapped leader app, appID = %v", appID)

	if err := tm.appEventHandler.OnBootstrappedHandler(app); err != nil {
		klog.Errorf("failed to call Bootstrapped handler, appID = %v, err = %v", appID, err)
		return err
	}
	return tm.appStatusUpdater.UpdateAppStateWithRetry(app, v1alpha1.AppSyncSent)
}

func (tm *appManager) syncFollowerApp(app *v1alpha1.FLApp) error {
	appID := app.Spec.AppID
	klog.Infof("sync bootstrapped follower app, appID = %v", appID)

	if tm.workerPaired(app) && tm.masterPaired(app) && tm.configMapUpdated(app) {
		return tm.appStatusUpdater.UpdateAppStateWithRetry(app, v1alpha1.AppRunning)
	}

	workers := app.Status.PairStatus[v1alpha1.FLReplicaTypeWorker].Local.List()
	peerWorkers := app.Status.PairStatus[v1alpha1.FLReplicaTypeWorker].Remote.List()
	desiredReplica := int(*getReplicas(app, v1alpha1.FLReplicaTypeWorker))

	if len(peerWorkers) != desiredReplica || len(workers) != desiredReplica {
		return fmt.Errorf("still waiting for leader workers, appID = %v", appID)
	}
	workerMapping := make(map[string]string)
	for idx := 0; idx < len(workers); idx++ {
		workerMapping[workers[idx]] = peerWorkers[idx]
	}

	configMap := &v1.ConfigMap{
		ObjectMeta: metav1.ObjectMeta{
			Name: workerConfigMapName(appID),
		},
		Data: workerMapping,
	}
	if _, err := tm.kubeClient.CoreV1().ConfigMaps(tm.namespace).Update(configMap); err != nil {
		return err
	}

	masters := app.Status.PairStatus[v1alpha1.FLReplicaTypeMaster].Local.List()
	peerMasters := app.Status.PairStatus[v1alpha1.FLReplicaTypeMaster].Remote.List()
	desiredReplica = int(*getReplicas(app, v1alpha1.FLReplicaTypeMaster))

	if len(peerMasters) != desiredReplica || len(masters) != desiredReplica {
		return fmt.Errorf("still waiting for leader masters, appID = %v", appID)
	}
	masterMapping := make(map[string]string)
	for idx := 0; idx < len(masters); idx++ {
		masterMapping[masters[idx]] = peerMasters[idx]
	}

	configMap = &v1.ConfigMap{
		ObjectMeta: metav1.ObjectMeta{
			Name: masterConfigMapName(appID),
		},
		Data: masterMapping,
	}
	if _, err := tm.kubeClient.CoreV1().ConfigMaps(tm.namespace).Update(configMap); err != nil {
		return err
	}

	appCopy := app.DeepCopy()
	appCopy.Status.PairStatus[v1alpha1.FLReplicaTypeWorker].Mapping = workerMapping
	appCopy.Status.PairStatus[v1alpha1.FLReplicaTypeMaster].Mapping = masterMapping
	if err := tm.appEventHandler.SyncWorkers(appCopy); err != nil {
		klog.Errorf("failed to call SyncWorker handler, appID = %v, err = %v", appID, err)
		return err
	}

	_, err := tm.appStatusUpdater.UpdateAppStatusWithRetry(app, func(mutatingApp *v1alpha1.FLApp) bool {
		if len(mutatingApp.Status.PairStatus[v1alpha1.FLReplicaTypeWorker].Mapping) == int(*getReplicas(mutatingApp, v1alpha1.FLReplicaTypeWorker)) &&
			len(mutatingApp.Status.PairStatus[v1alpha1.FLReplicaTypeMaster].Mapping) == int(*getReplicas(mutatingApp, v1alpha1.FLReplicaTypeMaster)) {
			return false
		}
		mutatingApp.Status.PairStatus[v1alpha1.FLReplicaTypeWorker].Mapping = workerMapping
		mutatingApp.Status.PairStatus[v1alpha1.FLReplicaTypeMaster].Mapping = masterMapping
		return true
	})
	return err
}

func (tm *appManager) syncSyncSentApp(app *v1alpha1.FLApp) error {
	appID := app.Spec.AppID
	klog.Infof("sync sync-sent app, appID = %v", appID)
	configMapUpdated := tm.configMapUpdated(app)
	if tm.workerPaired(app) && tm.masterPaired(app) && configMapUpdated {
		return tm.appStatusUpdater.UpdateAppStateWithRetry(app, v1alpha1.AppRunning)
	}

	if !configMapUpdated {
		workerPair := app.Status.PairStatus[v1alpha1.FLReplicaTypeWorker].Mapping
		mapping := make(map[string]string)
		for worker, peerWorker := range workerPair {
			mapping[worker] = peerWorker
		}
		configMap := &v1.ConfigMap{
			ObjectMeta: metav1.ObjectMeta{
				Name: workerConfigMapName(appID),
			},
			Data: mapping,
		}
		if _, err := tm.kubeClient.CoreV1().ConfigMaps(tm.namespace).Update(configMap); err != nil {
			return err
		}
		masterPair := app.Status.PairStatus[v1alpha1.FLReplicaTypeMaster].Mapping
		mapping = make(map[string]string)
		for master, peerMaster := range masterPair {
			mapping[master] = peerMaster
		}
		configMap = &v1.ConfigMap{
			ObjectMeta: metav1.ObjectMeta{
				Name: masterConfigMapName(appID),
			},
			Data: mapping,
		}
		if _, err := tm.kubeClient.CoreV1().ConfigMaps(tm.namespace).Update(configMap); err != nil {
			return err
		}
	}
	klog.Infof("still waiting for follower, appID = %v", appID)
	return nil
}

func (tm *appManager) workerPaired(app *v1alpha1.FLApp) bool {
	desiredReplica := int(*getReplicas(app, v1alpha1.FLReplicaTypeWorker))
	// TODO: check detailed worker matching
	return app.Status.PairStatus[v1alpha1.FLReplicaTypeWorker].Remote.Len() == desiredReplica &&
		app.Status.PairStatus[v1alpha1.FLReplicaTypeWorker].Local.Len() == desiredReplica &&
		len(app.Status.PairStatus[v1alpha1.FLReplicaTypeWorker].Mapping) == desiredReplica
}

func (tm *appManager) masterPaired(app *v1alpha1.FLApp) bool {
	desiredReplica := int(*getReplicas(app, v1alpha1.FLReplicaTypeMaster))
	return app.Status.PairStatus[v1alpha1.FLReplicaTypeMaster].Remote.Len() == desiredReplica &&
		app.Status.PairStatus[v1alpha1.FLReplicaTypeMaster].Local.Len() == desiredReplica &&
		len(app.Status.PairStatus[v1alpha1.FLReplicaTypeMaster].Mapping) == desiredReplica
}

func (tm *appManager) configMapUpdated(app *v1alpha1.FLApp) bool {
	configMapName := app.Spec.AppID
	configMap, err := tm.configMapLister.ConfigMaps(tm.namespace).Get(workerConfigMapName(configMapName))
	if err != nil || configMap == nil {
		return false
	}
	if configMap.Data == nil {
		return len(app.Status.PairStatus[v1alpha1.FLReplicaTypeWorker].Mapping) == 0
	}
	if !reflect.DeepEqual(configMap.Data, app.Status.PairStatus[v1alpha1.FLReplicaTypeWorker].Mapping) {
		return false
	}
	configMap, err = tm.configMapLister.ConfigMaps(tm.namespace).Get(masterConfigMapName(configMapName))
	if err != nil || configMap == nil {
		return false
	}
	if configMap.Data == nil {
		return len(app.Status.PairStatus[v1alpha1.FLReplicaTypeMaster].Mapping) == 0
	}
	return reflect.DeepEqual(configMap.Data, app.Status.PairStatus[v1alpha1.FLReplicaTypeMaster].Mapping)
}

func (tm *appManager) syncRunningApp(app *v1alpha1.FLApp) error {
	appID := app.Spec.AppID
	klog.Infof("sync running app, appID = %v", appID)
	if tm.isAppFinished(app) {
		if err := tm.appEventHandler.OnFinishedHandler(app); err != nil {
			klog.Errorf("failed to call Finished handler, appID = %v, err = %v", appID, err)
			return err
		}
		return tm.appStatusUpdater.UpdateAppStateWithRetry(app, v1alpha1.AppComplete)
	}
	klog.Infof("app still running, appID = %v", appID)
	return nil
}

func (tm *appManager) isAppFinished(app *v1alpha1.FLApp) bool {
	desiredReplica := int(*getReplicas(app, v1alpha1.FLReplicaTypeWorker))
	activeJobs, _, _, _, err := tm.getCurrentJobs(app, tm.namespace)
	if err != nil || desiredReplica != len(activeJobs) {
		return false
	}
	for _, job := range activeJobs {
		completed := false
		for _, condition := range job.Status.Conditions {
			if condition.Status == v1.ConditionTrue && condition.Type == batchv1.JobComplete {
				completed = true
			}
		}
		if !completed {
			return false
		}
	}
	return true
}

func (tm *appManager) isAppFailing(app *v1alpha1.FLApp) bool {
	appID := app.Spec.AppID
	desiredReplica := int(*getReplicas(app, v1alpha1.FLReplicaTypeWorker))
	labelSet := util.GetLabelSetWithappID(app)
	labelSet[LabelKeyPS] = "true"
	activeJobs, _, _, _, err := tm.getCurrentJobs(app, tm.namespace)
	if err != nil {
		klog.Infof("app is failing because of err get current jobs, appID = %v, err = %v", appID, err)
		return true
	}
	for _, job := range activeJobs {
		failed := false
		for _, condition := range job.Status.Conditions {
			if condition.Status == v1.ConditionTrue && condition.Type == batchv1.JobFailed {
				failed = true
			}
		}
		if failed {
			klog.Infof("app is failing because of job failed, appID = %v, jobName = %v, err = %v", appID, job.Name, err)
			return true
		}
	}
	address := tm.getPodAddress(labelSet.AsSelector())
	if len(activeJobs) != desiredReplica {
		psAddressChanged := false
		if len(address) == 0 {
			psAddressChanged = app.Status.PSAddress.Len() != 0
		} else {
			psAddressChanged = !reflect.DeepEqual(address, app.Status.PSAddress)
		}
		if psAddressChanged {
			tm.appFailingCache.PutIfAbsent(appID)
			if tm.appFailingCache.Expired(appID) {
				klog.Infof("app is failing because of PS address changed, appID = %v, current address = %v, status address = %v, err = %v", appID, address, app.Status.PSAddress, err)
				return true
			}
		}
	}
	return false
}

func (tm *appManager) syncFailingApp(app *v1alpha1.FLApp) error {
	appID := app.Spec.AppID
	klog.Infof("sync failing app, appID = %v", appID)
	if err := tm.appEventHandler.OnFailedHandler(app); err != nil {
		klog.Errorf("failed to call Failed handler, appID = %v, err = %v", appID, err)
		return err
	}
	return tm.appStatusUpdater.UpdateAppStateWithRetry(app, v1alpha1.AppShuttingDown)
}

func (tm *appManager) syncShuttingDownApp(app *v1alpha1.FLApp) error {
	appID := app.Spec.AppID
	klog.Infof("sync shutting-down app, appID = %v", appID)
	if tm.isResourceFreed(app) {
		return tm.appStatusUpdater.UpdateAppStateWithRetry(app, v1alpha1.AppFailed)
	}
	return tm.freeResource(app)
}

func (tm *appManager) isResourceFreed(app *v1alpha1.FLApp) bool {
	appID := app.Spec.AppID
	set := util.GetLabelSetWithappID(app)
	jobs, err := tm.jobLister.Jobs(tm.namespace).List(set.AsSelector())
	if (err != nil && !errors.IsNotFound(err)) || len(jobs) > 0 {
		return false
	}
	master, err := tm.statefulsetLister.StatefulSets(tm.namespace).Get(masterName(appID))
	if (err != nil && !errors.IsNotFound(err)) || master != nil {
		return false
	}
	ps, err := tm.statefulsetLister.StatefulSets(tm.namespace).Get(psName(appID))
	if (err != nil && !errors.IsNotFound(err)) || ps != nil {
		return false
	}
	configMap, err := tm.configMapLister.ConfigMaps(tm.namespace).Get(masterConfigMapName(appID))
	if (err != nil && !errors.IsNotFound(err)) || configMap != nil {
		return false
	}
	configMap, err = tm.configMapLister.ConfigMaps(tm.namespace).Get(workerConfigMapName(appID))
	if (err != nil && !errors.IsNotFound(err)) || configMap != nil {
		return false
	}
	return true
}

func (tm *appManager) freeResource(app *v1alpha1.FLApp) error {
	appID := app.Spec.AppID
	policy := metav1.DeletePropagationBackground
	errs := util.NewErrors()

	errs.Add(tm.kubeClient.BatchV1().Jobs(tm.namespace).DeleteCollection(
		&metav1.DeleteOptions{PropagationPolicy: &policy},
		metav1.ListOptions{LabelSelector: util.GetLabelSetWithappID(app).String()}))
	errs.Add(tm.kubeClient.AppsV1().StatefulSets(tm.namespace).Delete(masterName(appID), &metav1.DeleteOptions{}))
	errs.Add(tm.kubeClient.AppsV1().StatefulSets(tm.namespace).Delete(psName(appID), &metav1.DeleteOptions{}))
	errs.Add(tm.kubeClient.CoreV1().ConfigMaps(tm.namespace).Delete(masterConfigMapName(appID), &metav1.DeleteOptions{}))
	errs.Add(tm.kubeClient.CoreV1().ConfigMaps(tm.namespace).Delete(workerConfigMapName(appID), &metav1.DeleteOptions{}))
	return errs.AsError()
}

func psName(appID string) string {
	return appID + "-ps"
}

func masterName(appID string) string {
	return appID + "-master"
}

func masterConfigMapName(appID string) string {
	return masterName(appID)
}

func workerConfigMapName(appID string) string {
	return appID + "-worker"
}

func getReplicas(app *v1alpha1.FLApp, rtype v1alpha1.FLReplicaType) *int32 {
	return app.Spec.FLReplicaSpecs[rtype].Replicas
}
