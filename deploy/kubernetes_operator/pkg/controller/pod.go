package controller

import (
	"context"
	"fmt"
	"strconv"
	"strings"

	v1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/labels"
	"k8s.io/apimachinery/pkg/util/uuid"
	"k8s.io/klog"

	"github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/apis/fedlearner.k8s.io/v1alpha1"
	trainutil "github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/util/train"
)

const (
	workerService     = "WORKER_ID"
	workerRank        = "WORKER_RANK"
	workerClusterSpec = "CLUSTER_SPEC"
	masterService     = "MASTER_ID"
	replicaIndex      = "INDEX"

	egressURL  = "EGRESS_URL"
	egressHost = "EGRESS_HOST"

	exitedWithCodeReason = "ExitedWithCode"
)

func (am *appManager) reconcilePods(ctx context.Context, app *v1alpha1.FLApp) error {
	pods, err := am.getPodsForApp(ctx, app)
	if err != nil {
		return err
	}

	for rtype, spec := range app.Spec.FLReplicaSpecs {
		terminated, err := am.reconcilePodsWithType(ctx, app, pods, rtype, spec)
		if err != nil {
			klog.Errorf("reconcilePods error: %v", err)
			return err
		}

		if terminated {
			am.appStatusUpdater.UpdateAppStateWithRetry(ctx, app, v1alpha1.FLStateFailing)
			break
		}
	}
	return nil
}

func (am *appManager) reconcilePodsWithType(
	ctx context.Context,
	app *v1alpha1.FLApp,
	pods []*v1.Pod,
	rtype v1alpha1.FLReplicaType,
	spec v1alpha1.ReplicaSpec,
) (terminated bool, err error) {
	rt := strings.ToLower(string(rtype))
	pods, err = FilterPodsForReplicaType(pods, rt)
	if err != nil {
		return false, err
	}
	replicas := int(*spec.Replicas)
	podSlices := am.makePodSlicesByIndex(pods, replicas)

	for index, podSlice := range podSlices {
		switch podCount := len(podSlice); podCount {
		case 0:
			// Need to create a new pod
			klog.Infof("need to create new pod for %s %d", rtype, index)
			if err = am.createNewPod(ctx, app, rtype, spec, strconv.Itoa(index)); err != nil {
				return false, err
			}
		case 1:
			// Check the status of current pod
			pod := podSlice[0]
			var exitCode int32
			updateAppReplicaStatuses(app, rtype, pod)

			for _, status := range pod.Status.ContainerStatuses {
				state := status.State
				if status.Name == v1alpha1.DefaultContainerName && state.Terminated != nil {
					exitCode = state.Terminated.ExitCode
					klog.Infof("Pod: %v.%v exited with code %v", pod.Namespace, pod.Name, exitCode)
					am.recorder.Eventf(app, v1.EventTypeNormal, exitedWithCodeReason, "Pod: %v.%v exited with code %v", pod.Namespace, pod.Name, exitCode)
				}
			}
			var restartPod bool
			switch spec.RestartPolicy {
			case v1alpha1.RestartPolicyAlways:
				restartPod = true

			case v1alpha1.RestartPolicyOnFailure:
				if pod.Status.Phase != v1.PodFailed {
					break
				}

				if exitCode == 0 {
					break
				}

				restartPod = true

			case v1alpha1.RestartPolicyExitCode:
				if pod.Status.Phase != v1.PodFailed {
					break
				}

				// terminate the fedlearner app if the exit code is not retryable.
				if !trainutil.IsRetryableExitCode(exitCode) {
					return true, nil
				}

				restartPod = true
			}

			if !restartPod {
				break
			}

			klog.Infof("Need to restart the pod: %v.%v", pod.Namespace, pod.Name)
			if err = am.podControl.DeletePod(ctx, pod.Namespace, pod.Name, app); err != nil {
				return false, err
			}

		default:
			// Kill unnecessary pods.
			for i := 1; i < podCount; i++ {
				pod := podSlice[i]
				if err = am.podControl.DeletePod(ctx, pod.Namespace, pod.Name, app); err != nil {
					return false, err
				}
			}
		}
	}
	return false, nil
}

func (am *appManager) getPodsForApp(ctx context.Context, app *v1alpha1.FLApp) ([]*v1.Pod, error) {
	// Create selector.
	selector, err := metav1.LabelSelectorAsSelector(&metav1.LabelSelector{
		MatchLabels: GenLabels(app),
	})

	if err != nil {
		return nil, fmt.Errorf("couldn't convert App selector: %v", err)
	}
	// List all pods to include those that don't match the selector anymore
	// but have a ControllerRef pointing to this controller.
	pods, err := am.podLister.Pods(app.GetNamespace()).List(labels.Everything())
	if err != nil {
		return nil, err
	}

	// If any adoptions are attempted, we should first recheck for deletion
	// with an uncached quorum read sometime after listing Pods (see #42639).
	canAdoptFunc := RecheckDeletionTimestamp(func() (metav1.Object, error) {
		fresh, err := am.crdClient.FedlearnerV1alpha1().FLApps(app.GetNamespace()).Get(app.GetName(), metav1.GetOptions{})
		if err != nil {
			return nil, err
		}
		if fresh.GetUID() != app.GetUID() {
			return nil, fmt.Errorf("original Job %v/%v is gone: got uid %v, wanted %v", app.GetNamespace(), app.GetName(), fresh.GetUID(), app.GetUID())
		}
		return fresh, nil
	})
	cm := NewPodControllerRefManager(am.podControl, app, selector, am.GetAPIGroupVersionKind(), canAdoptFunc)
	return cm.ClaimPods(ctx, pods)
}

// FilterPodsForReplicaType returns pods belong to a replicaType.
func FilterPodsForReplicaType(pods []*v1.Pod, replicaType string) ([]*v1.Pod, error) {
	var result []*v1.Pod

	replicaSelector := &metav1.LabelSelector{
		MatchLabels: make(map[string]string),
	}

	replicaSelector.MatchLabels[flReplicaTypeLabel] = replicaType

	selector, err := metav1.LabelSelectorAsSelector(replicaSelector)
	if err != nil {
		return nil, err
	}

	for _, pod := range pods {
		if !selector.Matches(labels.Set(pod.Labels)) {
			continue
		}
		result = append(result, pod)
	}
	return result, nil
}

func (am *appManager) createNewPod(
	ctx context.Context,
	app *v1alpha1.FLApp,
	rtype v1alpha1.FLReplicaType,
	spec v1alpha1.ReplicaSpec,
	index string,
) error {
	rt := strings.ToLower(string(rtype))
	controllerRef := am.GenOwnerReference(app)

	clusterSpec, err := makeClusterSpec(am.namespace, app)
	if err != nil {
		return err
	}

	labels := GenLabels(app)
	labels[flReplicaTypeLabel] = rt
	labels[flReplicaIndexLabel] = index

	podTemplate := spec.Template.DeepCopy()
	// The controller will restart pod according to FLReplicaSpec
	podTemplate.Spec.RestartPolicy = v1.RestartPolicyNever
	podTemplate.Name = GenIndexName(app.Name, strings.ToLower(app.Spec.Role), rt, index) + "-" + string(uuid.NewUUID())
	if podTemplate.Labels == nil {
		podTemplate.Labels = make(map[string]string)
	}
	for key, value := range labels {
		podTemplate.Labels[key] = value
	}

	// inject cluster spec and mount volume if needed
	if needPair(app, rtype) {
		volume := v1.Volume{
			Name: volumeName(rtype),
			VolumeSource: v1.VolumeSource{
				ConfigMap: &v1.ConfigMapVolumeSource{
					LocalObjectReference: v1.LocalObjectReference{
						Name: GenReplicaName(app.Name, strings.ToLower(app.Spec.Role), rt),
					},
				},
			},
		}
		podTemplate.Spec.Volumes = ensureVolume(podTemplate.Spec.Volumes, volume)
	}

	for idx := range podTemplate.Spec.Containers {
		container := &podTemplate.Spec.Containers[idx]
		if container.Name != v1alpha1.DefaultContainerName {
			continue
		}

		if needPair(app, rtype) {
			container.VolumeMounts = ensureVolumeMounts(container.VolumeMounts, v1.VolumeMount{
				Name:      volumeName(rtype),
				ReadOnly:  true,
				MountPath: mountPath(rtype),
			})
		}
		container.Env = ensureEnv(container.Env, v1.EnvVar{
			Name:  replicaIndex,
			Value: index,
		})

		switch rtype {
		case v1alpha1.FLReplicaTypeMaster:
			container.Env = ensureEnv(container.Env, v1.EnvVar{
				Name:  masterService,
				Value: GenIndexName(app.Name, strings.ToLower(app.Spec.Role), rt, index),
			})

		case v1alpha1.FLReplicaTypeWorker:
			container.Env = ensureEnv(container.Env, v1.EnvVar{
				Name:  workerService,
				Value: GenIndexName(app.Name, strings.ToLower(app.Spec.Role), rt, index),
			})
			container.Env = ensureEnv(container.Env, v1.EnvVar{
				Name:  workerRank,
				Value: index,
			})
			container.Env = ensureEnv(container.Env, v1.EnvVar{
				Name:  workerClusterSpec,
				Value: clusterSpec,
			})
		}

		if index != v1alpha1.ChiefWorkerIndex || spec.ChiefResources == nil {
			continue
		}

		container.Resources = *spec.ChiefResources
	}

	if err := am.podControl.CreatePodsWithControllerRef(ctx, am.namespace, podTemplate, app, controllerRef); err != nil && !errors.IsAlreadyExists(err) {
		return err
	}
	return nil
}

func (am *appManager) makePodSlicesByIndex(pods []*v1.Pod, replicas int) [][]*v1.Pod {
	podSlices := make([][]*v1.Pod, replicas)
	for _, pod := range pods {
		val, ok := pod.Labels[flReplicaIndexLabel]
		if !ok {
			klog.Warningln("The pod do not have the index label.")
			continue
		}
		index, err := strconv.Atoi(val)
		if err != nil {
			klog.Warningf("Error when strconv.Atoi: %v", err)
			continue
		}
		if index < 0 || index >= replicas {
			klog.Warningf("The label index is not expected: %d", index)
		} else {
			podSlices[index] = append(podSlices[index], pod)
		}
	}
	return podSlices
}

func makeClusterSpec(namespace string, app *v1alpha1.FLApp) (string, error) {
	clusterSpec := NewClusterSpec(namespace, app)
	bytes, err := clusterSpec.Marshal()
	if err != nil {
		return "", err
	}
	return string(bytes), nil
}

func ensureEnv(envVars []v1.EnvVar, item v1.EnvVar) []v1.EnvVar {
	for idx := range envVars {
		if envVars[idx].Name == item.Name {
			envVars[idx] = item
			return envVars
		}
	}
	envVars = append(envVars, item)
	return envVars
}

func volumeName(rtype v1alpha1.FLReplicaType) string {
	rt := strings.ToLower(string(rtype))
	return fmt.Sprintf("%s-pair", rt)
}

func mountPath(rtype v1alpha1.FLReplicaType) string {
	rt := strings.ToLower(string(rtype))
	return fmt.Sprintf("/etc/%s", rt)
}

func ensureVolumeMounts(volumeMounts []v1.VolumeMount, volumeMount v1.VolumeMount) []v1.VolumeMount {
	for idx := range volumeMounts {
		if volumeMounts[idx].Name == volumeMount.Name {
			volumeMounts[idx] = volumeMount
			return volumeMounts
		}
	}
	volumeMounts = append(volumeMounts, volumeMount)
	return volumeMounts
}

func ensureVolume(volumes []v1.Volume, volume v1.Volume) []v1.Volume {
	for idx := range volumes {
		if volumes[idx].Name == volume.Name {
			volumes[idx] = volume
			return volumes
		}
	}
	volumes = append(volumes, volume)
	return volumes
}
