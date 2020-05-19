package trainingset

import (
	"context"
	"fmt"
	"strconv"
	"strings"

	"github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/apis/fedlearner.k8s.io/v1alpha2"
	"github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/controller"
	trainutil "github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/util/train"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/labels"
	"k8s.io/apimachinery/pkg/util/uuid"
	"k8s.io/klog"
)

const (
	flReplicaTypeLabel            = "fl-replica-type"
	deprecatedFlReplicaIndexLabel = "fl-replica-index"

	trainingSetTypeLabel  = "training-set-type"
	trainingSetIndexLabel = "training-set-index"

	envWorkerService     = "WORKER_ID"
	envWorkerRank        = "WORKER_RANK"
	envWorkerClusterSpec = "CLUSTER_SPEC"
	envMasterService     = "MASTER_ID"
	envReplicaIndex      = "INDEX"
)

func (c *Controller) reconcilePods(ctx context.Context, ts *v1alpha2.TrainingSet) error {
	pods, err := c.getTrainingSetPods(ctx, ts)
	if err != nil {
		return err
	}

	replicas := int(*ts.Spec.Replicas)
	podSlices := c.makePodSlicesByIndex(pods, replicas)
	terminated, err := c.reconcilePodSlices(ctx, ts, podSlices)
	if err != nil {
		return err
	}

	if terminated {
		// TODO(draven): terminate the trainingset/flapp
	}

	return nil
}

func (c *Controller) reconcilePodSlices(ctx context.Context, ts *v1alpha2.TrainingSet, podSlices [][]*corev1.Pod) (terminated bool, err error) {
	for index, podSlice := range podSlices {
		switch podCount := len(podSlice); podCount {
		case 0:
			if err = c.createPod(ctx, ts, index); err != nil {
				return false, err
			}
		case 1:
			pod := podSlice[0]
			var exitCode int32
			updateTrainingSetStatus(ts, pod)

			for _, status := range pod.Status.ContainerStatuses {
				state := status.State
				if status.Name == v1alpha2.DefaultContainerName && state.Terminated != nil {
					exitCode = state.Terminated.ExitCode
					klog.Infof("Pod: %v.%v exited with code %v", pod.Namespace, pod.Name, exitCode)
					c.recorder.Eventf(ts, corev1.EventTypeNormal, "ExitedWithCod", "Pod: %v.%v exited with code %v", pod.Namespace, pod.Name, exitCode)
				}
			}
			var restartPod bool
			switch ts.Spec.RestartPolicy {
			case v1alpha2.RestartPolicyAlways:
				restartPod = true

			case v1alpha2.RestartPolicyOnFailure:
				if pod.Status.Phase != corev1.PodFailed {
					break
				}

				if exitCode == 0 {
					break
				}

				restartPod = true

			case v1alpha2.RestartPolicyExitCode:
				if pod.Status.Phase != corev1.PodFailed {
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
			if err = c.podControl.DeletePod(ctx, pod.Namespace, pod.Name, ts); err != nil {
				return false, err
			}

		default:
			for i := 1; i < podCount; i++ {
				pod := podSlice[i]
				if err = c.podControl.DeletePod(ctx, pod.Namespace, pod.Name, ts); err != nil {
					return false, err
				}
			}
		}
	}

	return false, nil
}

func (c *Controller) getTrainingSetPods(ctx context.Context, ts *v1alpha2.TrainingSet) ([]*corev1.Pod, error) {
	selector, err := metav1.LabelSelectorAsSelector(ts.Spec.Selector)
	if err != nil {
		return nil, err
	}

	pods, err := c.podsLister.Pods(ts.Namespace).List(labels.Everything())
	if err != nil {
		return nil, err
	}

	cm := controller.NewPodControllerRefManager(c.podControl, ts, selector, v1alpha2.SchemeGroupVersionKind, controller.RecheckDeletionTimestamp(func() (metav1.Object, error) {
		new, err := c.crdClient.FedlearnerV1alpha2().TrainingSets(ts.Namespace).Get(ts.Name, metav1.GetOptions{})
		if err != nil {
			return nil, err
		}

		if new.GetUID() != ts.GetUID() {
			return nil, fmt.Errorf("original %v/%v is gone: got uid %v, wanted %v", ts.Namespace, ts.Name, new.GetUID(), ts.GetUID())
		}

		return new, nil
	}))

	return cm.ClaimPods(ctx, pods)
}

func (c *Controller) createPod(ctx context.Context, ts *v1alpha2.TrainingSet, idx int) error {
	boolPtr := func(b bool) *bool { return &b }
	controllerRef := &metav1.OwnerReference{
		APIVersion:         v1alpha2.SchemeGroupVersion.String(),
		Kind:               v1alpha2.Kind,
		Name:               ts.Name,
		UID:                ts.UID,
		BlockOwnerDeletion: boolPtr(true),
		Controller:         boolPtr(true),
	}

	podTemplate := ts.Spec.Template.DeepCopy()
	podTemplate.Spec.RestartPolicy = corev1.RestartPolicyNever
	podTemplate.Name = fmt.Sprintf("%s-%d-%s", ts.Name, idx, string(uuid.NewUUID()))

	if podTemplate.Labels == nil {
		podTemplate.Labels = map[string]string{}
	}
	podTemplate.Labels[trainingSetIndexLabel] = fmt.Sprintf("%d", idx)
	podTemplate.Labels[trainingSetTypeLabel] = strings.ToLower(string(ts.Spec.Type))

	for idx := range podTemplate.Spec.Containers {
		container := &podTemplate.Spec.Containers[idx]
		if container.Name != v1alpha2.DefaultContainerName {
			continue
		}

		container.Env = ensureEnv(container.Env, corev1.EnvVar{
			Name:  envReplicaIndex,
			Value: fmt.Sprintf("%d", idx),
		})

		switch ts.Spec.Type {
		case v1alpha2.TrainingSetTypeMaster:
			container.Env = ensureEnv(container.Env, corev1.EnvVar{
				Name:  envMasterService,
				Value: fmt.Sprintf("%s-%d", ts.Name, idx),
			})

		case v1alpha2.TrainingSetTypeWorker:
			container.Env = ensureEnv(container.Env, corev1.EnvVar{
				Name:  envWorkerService,
				Value: fmt.Sprintf("%s-%d", ts.Name, idx),
			})
			container.Env = ensureEnv(container.Env, corev1.EnvVar{
				Name:  envWorkerRank,
				Value: fmt.Sprintf("%d", idx),
			})
		}
	}

	if err := c.podControl.CreatePodsWithControllerRef(
		ctx,
		ts.Namespace,
		podTemplate,
		ts,
		controllerRef,
	); err != nil && !errors.IsAlreadyExists(err) {
		return err
	}

	return nil
}

func (c *Controller) makePodSlicesByIndex(pods []*corev1.Pod, replicas int) [][]*corev1.Pod {
	podSlices := make([][]*corev1.Pod, replicas)
	for _, pod := range pods {
		val, ok := pod.Labels[trainingSetIndexLabel]
		if !ok {
			// compatible with previous v1alpha2's pod.
			val, ok = pod.Labels[deprecatedFlReplicaIndexLabel]
			if !ok {
				klog.Warningln("The pod do not have the index label.")
				continue
			}
		}

		index, err := strconv.Atoi(val)
		if err != nil {
			klog.Warningf("Error when strconv.Atoi: %v", err)
			continue
		}

		if index < 0 || index >= replicas {
			klog.Warningf("The label index is not expected: %d", index)
			continue
		}

		podSlices[index] = append(podSlices[index], pod)
	}
	return podSlices
}

// updateTrainingSetStatus .
func updateTrainingSetStatus(ts *v1alpha2.TrainingSet, pod *corev1.Pod) {
	status := ts.Status
	replicaStatus := status.DeepCopy()
	switch pod.Status.Phase {
	case corev1.PodRunning:
		replicaStatus.Active.Insert(pod.Name)
	case corev1.PodSucceeded:
		replicaStatus.Active.Delete(pod.Name)
		replicaStatus.Succeeded.Insert(pod.Name)
	case corev1.PodFailed:
		replicaStatus.Active.Delete(pod.Name)
		replicaStatus.Failed.Insert(pod.Name)
	}
	ts.Status = *replicaStatus
}

func ensureEnv(envVars []corev1.EnvVar, item corev1.EnvVar) []corev1.EnvVar {
	for idx := range envVars {
		if envVars[idx].Name == item.Name {
			envVars[idx] = item
			return envVars
		}
	}
	envVars = append(envVars, item)
	return envVars
}

func updateTrainingSetLocalStatus(ts *v1alpha2.TrainingSet, service *corev1.Service) {
	name := service.Name
	status := ts.Status
	replicaStatus := status.DeepCopy()
	replicaStatus.Local.Insert(name)
	ts.Status = *replicaStatus
}
