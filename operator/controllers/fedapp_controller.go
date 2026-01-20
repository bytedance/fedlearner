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
	v1 "k8s.io/api/core/v1"
	networking "k8s.io/api/networking/v1beta1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/log"
)

// FedAppReconciler reconciles a FedApp object
type FedAppReconciler struct {
	client.Client
	Scheme *runtime.Scheme
}

const (
	flReplicaTypeLabel  = "fl-replica-type"
	flReplicaIndexLabel = "fl-replica-index"
	AppNameLabel        = "app-name"

	// Env key in pod
	serviceID    = "SERVICE_ID"
	clusterSpec  = "CLUSTER_SPEC"
	replicaIndex = "INDEX"
)

//+kubebuilder:rbac:groups=fedlearner.k8s.io,resources=fedapps,verbs=get;list;watch;create;update;patch;delete
//+kubebuilder:rbac:groups=fedlearner.k8s.io,resources=fedapps/status,verbs=get;update;patch
//+kubebuilder:rbac:groups=fedlearner.k8s.io,resources=fedapps/finalizers,verbs=update
//+kubebuilder:rbac:groups=core,resources=pods,verbs=get;list;watch;create;delete
//+kubebuilder:rbac:groups=core,resources=services,verbs=get;list;create;delete
//+kubebuilder:rbac:groups=networking,resources=ingress,verbs=get;create;delete

// Reconcile is part of the main kubernetes reconciliation loop which aims to
// move the current state of the cluster closer to the desired state.
// the FedApp object against the actual cluster state, and then
// perform operations to make the cluster state reflect the state specified by
// the user.
//
// For more details, check Reconcile and its Result here:
// - https://pkg.go.dev/sigs.k8s.io/controller-runtime@v0.10.0/pkg/reconcile
func (r *FedAppReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	log := log.FromContext(ctx)

	startTime := time.Now()
	defer func() {
		log.Info("Finished syncing job", req.NamespacedName.Name, time.Since(startTime).String())
	}()
	var app fedlearnerv2.FedApp
	if err := r.Get(ctx, req.NamespacedName, &app); err != nil {
		log.Info("unable to fetch FedApp")
		// we'll ignore not-found errors, since they can't be fixed by an immediate
		// requeue (we'll need to wait for a new notification), and we can get them
		// on deleted requests.
		return ctrl.Result{}, client.IgnoreNotFound(err)
	}

	// if job was finished previously, we don't want to redo the termination
	if isAppFinished(&app) {
		// release all resource
		// r.releaseAppResource(ctx, req)
		// Complete ttl check
		if app.Spec.TTLSecondsAfterFinished != nil {
			now := metav1.Now()
			var finished time.Time
			for _, c := range app.Status.Conditions {
				if c.Type == fedlearnerv2.Succeeded {
					finished = c.LastTransitionTime.Time
					break
				}
			}
			duration := now.Time.Sub(finished)
			allowedDuration := time.Duration(*app.Spec.TTLSecondsAfterFinished) * time.Second
			if duration >= allowedDuration {
				log.Info("FedApp TTLSecondsAfterFinished terminating")
				if err := r.Delete(ctx, &app); client.IgnoreNotFound(err) != nil {
					return ctrl.Result{}, err
				}
				return ctrl.Result{}, nil
			}
			return ctrl.Result{RequeueAfter: time.Duration(*app.Spec.TTLSecondsAfterFinished) * time.Second}, nil

		}
		return ctrl.Result{}, nil
	}

	if app.Status.TerminatedPodsMap == nil {
		app.Status.TerminatedPodsMap = InitTerminatedPodsMap(app)
	}

	if app.Status.StartTime == nil {
		// Check if pods of last execution have all been deleted.
		var childPods v1.PodList
		if err := r.List(ctx, &childPods, client.InNamespace(req.Namespace), client.MatchingFields{ownerKey: req.Name}); err != nil {
			log.Error(err, "unable to list child Pods")
			return ctrl.Result{}, err
		}
		if len(childPods.Items) > 0 {
			log.Info("Delete all pods for last Execution.")
			for _, pod := range childPods.Items {
				log.Info("Delete Pod", "Pod", pod.Name)
				if err := r.Delete(ctx, &pod, client.PropagationPolicy(metav1.DeletePropagationBackground)); client.IgnoreNotFound(err) != nil {
					log.Error(err, "Failed to delete pods")
					return ctrl.Result{}, err
				}
			}

			return ctrl.Result{}, nil
		}
		now := metav1.Now()
		app.Status.StartTime = &now
		if err := r.Status().Update(ctx, &app); err != nil {
			log.Error(err, "unable to update FedApp status StartTime")
			return ctrl.Result{}, err
		}

		// enqueue a sync to check if job past ActiveDeadlineSeconds
		if app.Spec.ActiveDeadlineSeconds != nil {
			log.Info("FedApp has ActiveDeadlineSeconds will sync after", "ActiveDeadlineSeconds", *app.Spec.ActiveDeadlineSeconds)
			return ctrl.Result{RequeueAfter: time.Duration(*app.Spec.ActiveDeadlineSeconds) * time.Second}, nil
		}
		return ctrl.Result{}, nil
	}
	if app.Spec.ActiveDeadlineSeconds != nil && app.Status.StartTime != nil {
		now := metav1.Now()
		start := app.Status.StartTime.Time
		duration := now.Time.Sub(start)
		allowedDuration := time.Duration(*app.Spec.ActiveDeadlineSeconds) * time.Second
		if duration >= allowedDuration {
			log.Info("FedApp has running exceeding activeDeadlineSeconds")
			app.Status.Conditions, _ = ensureConditionStatus(app.Status.Conditions, fedlearnerv2.Succeeded, v1.ConditionFalse, "DeadlineExceeded", "FedApp was active longer than specified deadline")
			if err := r.Status().Update(ctx, &app); err != nil {
				log.Error(err, "unable to update FedApp status DeadlineExceeded")
				return ctrl.Result{}, err
			}
			// Release the resource when next reconcile.
			// Can not release resources here synchronously, because the status update request's response can't insure the status has been updated in etcd.
			// And if delete the pods synchoronously, k8s cant't promise the delete requeset is behind the status update request, so the next reconcile may create new pods.
			return ctrl.Result{}, nil
		}

	}

	// sync service
	if err := r.syncServices(ctx, &app); err != nil {
		log.Error(err, "unable to sync service")
		return ctrl.Result{}, err
	}
	// sync ingress
	if err := r.syncIngress(ctx, &app); err != nil {
		log.Error(err, "unable to sync ingress")
		return ctrl.Result{}, err
	}
	// sync pod
	completed := true
	var childPods v1.PodList
	if err := r.List(ctx, &childPods, client.InNamespace(req.Namespace), client.MatchingFields{ownerKey: req.Name}); err != nil {
		log.Error(err, "unable to list child Pods")
		return ctrl.Result{}, err
	}
	for rtype, spec := range app.Spec.FedReplicaSpecs {
		replicaResult, err := r.SyncReplicas(ctx, &app, rtype, &childPods, &spec)
		if replicaResult.isFailed {
			log.Info("FedApp failed")
			// Dont's clean resource synchronously, becase we must wait for update request finished inorder to keep reconcile idempotent.
			return ctrl.Result{}, nil
		}
		if err != nil {
			return ctrl.Result{}, err
		}

		completed = completed && replicaResult.isCompleted

	}
	if completed {
		app.Status.Conditions, _ = ensureConditionStatus(app.Status.Conditions, fedlearnerv2.Succeeded, v1.ConditionTrue, "Completed", "")
		if err := r.Status().Update(ctx, &app); err != nil {
			log.Error(err, "unable to update FedApp status Completed")
			return ctrl.Result{}, err
		}
	}
	if err := r.Status().Update(ctx, &app); err != nil {
		log.Error(err, "unable to update FedApp status when reconcile finished")
		return ctrl.Result{}, err
	}
	return ctrl.Result{}, nil
}

type ReplicaResult struct {
	isFailed    bool
	isCompleted bool
}

// ensureJobConditionStatus appends or updates an existing job condition of the
// given type with the given status value.The function returns a bool to let the
// caller know if the list was changed (either appended or updated).
func ensureConditionStatus(list []fedlearnerv2.FedAppCondition, cType fedlearnerv2.FedAppConditionType, status v1.ConditionStatus, reason, message string) ([]fedlearnerv2.FedAppCondition, bool) {
	for i := range list {
		if list[i].Type == cType {
			if list[i].Status != status || list[i].Reason != reason || list[i].Message != message {
				list[i].Status = status
				list[i].LastTransitionTime = metav1.Now()
				list[i].Reason = reason
				list[i].Message = message
				return list, true
			}
			return list, false
		}
	}

	return append(list, *newCondition(cType, status, reason, message)), true
}

func newCondition(conditionType fedlearnerv2.FedAppConditionType, status v1.ConditionStatus, reason, message string) *fedlearnerv2.FedAppCondition {
	return &fedlearnerv2.FedAppCondition{
		Type:               conditionType,
		Status:             status,
		LastTransitionTime: metav1.Now(),
		Reason:             reason,
		Message:            message,
	}
}

// IsAppFinished checks whether the given fedapp has finished execution.
// It does not discriminate between successful and failed terminations.
func isAppFinished(app *fedlearnerv2.FedApp) bool {
	for _, c := range app.Status.Conditions {
		if c.Type == fedlearnerv2.Succeeded && (c.Status == v1.ConditionTrue || c.Status == v1.ConditionFalse) {
			return true
		}
	}
	return false
}

func (r *FedAppReconciler) releaseAppResource(ctx context.Context, req ctrl.Request) error {
	log := log.FromContext(ctx)
	var ingress networking.Ingress
	err := r.Get(ctx, req.NamespacedName, &ingress)
	if client.IgnoreNotFound(err) != nil {
		log.Error(err, "Get Ingress failed")
		return err
	}
	if err == nil {
		log.Info("Delete Ingress")
		if err := r.Delete(ctx, &ingress, client.PropagationPolicy(metav1.DeletePropagationBackground)); client.IgnoreNotFound(err) != nil {
			log.Error(err, "Delete Ingress failed")
			return err
		}
	}

	var childPods v1.PodList
	if err := r.List(ctx, &childPods, client.InNamespace(req.Namespace), client.MatchingFields{ownerKey: req.Name}); err != nil {
		log.Error(err, "unable to list child Pods")
		return err
	}
	for _, pod := range childPods.Items {
		log.Info("Delete Pod", "Pod", pod.Name)
		if err := r.Delete(ctx, &pod, client.PropagationPolicy(metav1.DeletePropagationBackground)); client.IgnoreNotFound(err) != nil {
			log.Error(err, "Failed to delete pods")
			return err
		}
	}
	var childServices v1.ServiceList
	if err := r.List(ctx, &childServices, client.InNamespace(req.Namespace), client.MatchingFields{ownerKey: req.Name}); err != nil {
		log.Error(err, "unable to list child Pods")
		return err
	}
	for _, service := range childServices.Items {
		log.Info("Delete Service", "Pod", service.Name)
		if err := r.Delete(ctx, &service, client.PropagationPolicy(metav1.DeletePropagationBackground)); client.IgnoreNotFound(err) != nil {
			log.Error(err, "Failed to delete pods")
			return err
		}
	}
	return nil
}

var (
	ownerKey = ".metadata.controller"
	apiGVStr = fedlearnerv2.GroupVersion.String()
)

// SetupWithManager sets up the controller with the Manager.
func (r *FedAppReconciler) SetupWithManager(mgr ctrl.Manager) error {
	//  For a more efficient lookup, these Pods and Service will be indexed locally on their controller(FedApp)'s name.
	if err := mgr.GetFieldIndexer().IndexField(context.Background(), &v1.Pod{}, ownerKey, func(rawObj client.Object) []string {
		// grab the job object, extract the owner...
		pod := rawObj.(*v1.Pod)
		owner := metav1.GetControllerOf(pod)
		if owner == nil {
			return nil
		}
		// ...make sure it's a FedApp...
		if owner.APIVersion != apiGVStr || owner.Kind != "FedApp" {
			return nil
		}

		// ...and if so, return it
		return []string{owner.Name}
	}); err != nil {
		return err
	}
	if err := mgr.GetFieldIndexer().IndexField(context.Background(), &v1.Service{}, ownerKey, func(rawObj client.Object) []string {
		// grab the job object, extract the owner...
		service := rawObj.(*v1.Service)
		owner := metav1.GetControllerOf(service)
		if owner == nil {
			return nil
		}
		// ...make sure it's a FedApp...
		if owner.APIVersion != apiGVStr || owner.Kind != "FedApp" {
			return nil
		}

		// ...and if so, return it
		return []string{owner.Name}
	}); err != nil {
		return err
	}
	return ctrl.NewControllerManagedBy(mgr).
		For(&fedlearnerv2.FedApp{}).
		Owns(&v1.Pod{}).
		Complete(r)
}
