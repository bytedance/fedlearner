package trainingset

import (
	"context"
	"fmt"

	"github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/apis/fedlearner.k8s.io/v1alpha2"
	apiequality "k8s.io/apimachinery/pkg/api/equality"
	"k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/klog"
)

// NOTE: this func will overwrite the whole ts status, may raise race condition
// if multiple clients concurrently updates status.
func (c *Controller) updateStatus(ctx context.Context, ts *v1alpha2.TrainingSet) error {
	_, err := c.updateStatusWithRetry(ctx, ts, func(mutatingTs *v1alpha2.TrainingSet) bool {
		fmt.Println(ts.Status)
		fmt.Println(mutatingTs.Status)
		if apiequality.Semantic.DeepEqual(ts.Status, mutatingTs.Status) {
			return false
		}

		ts.Status.DeepCopyInto(&mutatingTs.Status)
		return true
	})
	return err
}

func (c *Controller) updateStatusWithRetry(
	ctx context.Context,
	ts *v1alpha2.TrainingSet,
	updateFunc func(*v1alpha2.TrainingSet) bool,
) (*v1alpha2.TrainingSet, error) {
	var (
		err     error
		refresh bool
	)

	tsCopy := ts.DeepCopy()

	for {
		if refresh {
			tsCopy, err = c.crdClient.FedlearnerV1alpha2().TrainingSets(ts.Namespace).Get(ts.Name, metav1.GetOptions{})
			if err != nil || tsCopy == nil {
				return nil, fmt.Errorf("failed to get ts %s: %v", tsCopy.Name, err)
			}
		}

		updated := updateFunc(tsCopy)
		if !updated {
			if !refresh {
				refresh = true
				continue
			}

			return tsCopy, nil
		}

		klog.Infof(
			"updating trainingset %v status, namespace = %v",
			tsCopy.Name,
			tsCopy.Namespace,
		)
		_, err = c.crdClient.FedlearnerV1alpha2().TrainingSets(tsCopy.Namespace).UpdateStatus(tsCopy)
		if err != nil && errors.IsConflict(err) {
			refresh = true
			continue
		}

		if err != nil {
			klog.Errorf("failed to update ts %s: %v", tsCopy.Name, err)
			return nil, err
		}
		return tsCopy, nil
	}
}
