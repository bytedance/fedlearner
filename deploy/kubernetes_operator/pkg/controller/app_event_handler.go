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
	"context"
	"fmt"

	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/util/sets"
	"k8s.io/klog"

	"github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/apis/fedlearner.k8s.io/v1alpha1"
	crdclientset "github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/client/clientset/versioned"
	pb "github.com/bytedance/fedlearner/deploy/kubernetes_operator/proto"
)

type AppEventHandler interface {
	// Called after leader bootstrapped
	OnBootstrappedHandler(app *v1alpha1.FLApp) error
	// Called after follower finished pairing
	SyncWorkers(*v1alpha1.FLApp) error
	// Called when either leader or follower needs to shutdown peer
	OnFailedHandler(*v1alpha1.FLApp) error
	// Called when either leader or follower is finished
	OnFinishedHandler(*v1alpha1.FLApp) error
	// Received when peer send sync request
	Sync(appID string, peerWorkers sets.String, peerMasters sets.String) (*pb.Status, error)
	// Received when peer send sync callback request
	SyncCallback(appID string, workerPair map[string]string, peerWorkers sets.String, masterPair map[string]string, peerMasters sets.String) (*pb.Status, error)
	// Received when peer send shutdown request
	Shutdown(appID string) (*pb.Status, error)
	// Received when peer send finish request
	Finish(appID string) (*pb.Status, error)
}

type appEventHandler struct {
	peerURL string

	namespace string
	crdClient crdclientset.Interface

	grpcClient pb.PairingServiceClient
}

var _ AppEventHandler = &appEventHandler{}

func NewappEventHandler(peerURL string, namespace string, crdClient crdclientset.Interface) AppEventHandler {
	opts := []grpc.DialOption{grpc.WithInsecure()}
	connection, err := grpc.Dial(peerURL, opts...)
	if err != nil {
		klog.Fatalf("failed to create connection, err = %v", err)
	}
	client := pb.NewPairingServiceClient(connection)
	return &appEventHandler{
		peerURL:    peerURL,
		namespace:  namespace,
		crdClient:  crdClient,
		grpcClient: client,
	}
}

func (handler *appEventHandler) OnBootstrappedHandler(app *v1alpha1.FLApp) error {
	appID := app.Spec.AppID
	masters := app.Status.PairStatus[v1alpha1.FLReplicaTypeMaster].Local.List()
	var masterPairs []*pb.Pair
	for _, master := range masters {
		pair := &pb.Pair{
			LeaderId:   master,
			FollowerId: "",
		}
		masterPairs = append(masterPairs, pair)
	}

	workers := app.Status.PairStatus[v1alpha1.FLReplicaTypeWorker].Local.List()
	var workerPairs []*pb.Pair
	for _, leader := range workers {
		pair := &pb.Pair{
			LeaderId:   leader,
			FollowerId: "",
		}
		workerPairs = append(workerPairs, pair)
	}
	request := &pb.PairRequest{
		AppId:       appID,
		MasterPairs: masterPairs,
		WorkerPairs: workerPairs,
	}
	response, err := handler.grpcClient.Pair(context.Background(), request)
	if err != nil || response.Code != int32(codes.OK) {
		return fmt.Errorf("OnBootstrappedHandler peer not ready appID = %v, err = %v", appID, err)
	}
	klog.Infof("OnBootstrappedHandler appID = %v, message = %v", appID, response.ErrorMessage)
	return nil
}

func (handler *appEventHandler) SyncWorkers(app *v1alpha1.FLApp) error {
	appID := app.Spec.AppID
	masterPair := app.Status.PairStatus[v1alpha1.FLReplicaTypeMaster].Mapping
	var masterPairs []*pb.Pair
	for followerMaster, leaderMaster := range masterPair {
		pair := &pb.Pair{
			LeaderId:   leaderMaster,
			FollowerId: followerMaster,
		}
		masterPairs = append(masterPairs, pair)
	}

	workerPair := app.Status.PairStatus[v1alpha1.FLReplicaTypeWorker].Mapping
	var workerPairs []*pb.Pair
	for followerWorker, leaderWorker := range workerPair {
		pair := &pb.Pair{
			LeaderId:   leaderWorker,
			FollowerId: followerWorker,
		}
		workerPairs = append(workerPairs, pair)
	}
	request := &pb.PairRequest{
		AppId:       appID,
		MasterPairs: masterPairs,
		WorkerPairs: workerPairs,
	}
	response, err := handler.grpcClient.Pair(context.Background(), request)
	if err != nil || response.Code != int32(codes.OK) {
		return fmt.Errorf("SyncWorkers failed appID = %v, err = %v", appID, err)
	}
	klog.Infof("SyncWorkers success appID = %v, message = %v", appID, response.ErrorMessage)
	return nil
}

func (handler *appEventHandler) OnFailedHandler(app *v1alpha1.FLApp) error {
	appID := app.Spec.AppID
	request := &pb.PairRequest{
		AppId:       appID,
		MasterPairs: nil,
		WorkerPairs: nil,
	}
	response, err := handler.grpcClient.Pair(context.Background(), request)
	if err != nil || response.Code != int32(codes.OK) {
		return fmt.Errorf("OnFailedHandler failed appID = %v, err = %v", app.Spec.AppID, err)
	}
	klog.Infof("OnFailedHandler success appID = %v, message = %v", app.Spec.AppID, response.ErrorMessage)
	return nil
}

func (handler *appEventHandler) OnFinishedHandler(app *v1alpha1.FLApp) error {
	appID := app.Spec.AppID
	request := &pb.PairRequest{
		AppId:       appID,
		MasterPairs: nil,
		WorkerPairs: nil,
	}
	response, err := handler.grpcClient.Pair(context.Background(), request)
	if err != nil || response.Code != int32(codes.OK) {
		return fmt.Errorf("OnFinishedHandler failed appID = %v, err = %v", appID, err)
	}
	klog.Infof("OnFinishedHandler success appID = %v, message = %v", appID, response.ErrorMessage)
	return nil
}

func (handler *appEventHandler) Sync(appID string, peerWorkers sets.String, peerMasters sets.String) (*pb.Status, error) {
	app, err := handler.crdClient.FedlearnerV1alpha1().FLApps(handler.namespace).Get(appID, metav1.GetOptions{})
	if err != nil {
		klog.Errorf("Sync appID = %v, err = %v", appID, err)
		return &pb.Status{
			Code:         int32(codes.Internal),
			ErrorMessage: err.Error(),
		}, status.Error(codes.Internal, err.Error())
	}

	appCopy := app.DeepCopy()
	appCopy.Status.PairStatus[v1alpha1.FLReplicaTypeWorker].Remote = peerWorkers
	appCopy.Status.PairStatus[v1alpha1.FLReplicaTypeMaster].Remote = peerMasters
	_, err = handler.crdClient.FedlearnerV1alpha1().FLApps(handler.namespace).UpdateStatus(appCopy)
	if err != nil {
		err = fmt.Errorf("Sync appID = %v, err = %v", appID, err)
		klog.Error(err)
		return &pb.Status{
			Code:         int32(codes.Internal),
			ErrorMessage: err.Error(),
		}, status.Error(codes.Internal, err.Error())
	}
	return &pb.Status{
		Code:         int32(codes.OK),
		ErrorMessage: "",
	}, nil
}

func (handler *appEventHandler) SyncCallback(appID string, workerPair map[string]string, peerWorkers sets.String, masterPair map[string]string, peerMasters sets.String) (*pb.Status, error) {
	app, err := handler.crdClient.FedlearnerV1alpha1().FLApps(handler.namespace).Get(appID, metav1.GetOptions{})
	if err != nil {
		err = fmt.Errorf("SyncCallback appID = %v, err = %v", appID, err)
		klog.Error(err)
		return &pb.Status{
			Code:         int32(codes.Internal),
			ErrorMessage: err.Error(),
		}, status.Error(codes.Internal, err.Error())
	}

	appCopy := app.DeepCopy()
	appCopy.Status.PairStatus[v1alpha1.FLReplicaTypeWorker].Mapping = workerPair
	appCopy.Status.PairStatus[v1alpha1.FLReplicaTypeMaster].Mapping = masterPair
	appCopy.Status.PairStatus[v1alpha1.FLReplicaTypeWorker].Remote = peerWorkers
	appCopy.Status.PairStatus[v1alpha1.FLReplicaTypeMaster].Remote = peerMasters
	_, err = handler.crdClient.FedlearnerV1alpha1().FLApps(handler.namespace).UpdateStatus(appCopy)
	if err != nil {
		err = fmt.Errorf("SyncCallback appID = %v, err = %v", appID, err)
		klog.Error(err)
		return &pb.Status{
			Code:         int32(codes.Internal),
			ErrorMessage: err.Error(),
		}, status.Error(codes.Internal, err.Error())
	}
	return &pb.Status{
		Code:         int32(codes.OK),
		ErrorMessage: "",
	}, nil
}

func (handler *appEventHandler) Shutdown(appID string) (*pb.Status, error) {
	app, err := handler.crdClient.FedlearnerV1alpha1().FLApps(handler.namespace).Get(appID, metav1.GetOptions{})
	if err != nil {
		err = fmt.Errorf("Shutdown appID = %v, err = %v", appID, err)
		klog.Error(err)
		return &pb.Status{
			Code:         int32(codes.Internal),
			ErrorMessage: err.Error(),
		}, status.Errorf(codes.Internal, err.Error())
	}

	appState := app.Status.AppState
	if appState == "" {
		appState = v1alpha1.AppNew
	}
	switch appState {
	case v1alpha1.AppShuttingDown, v1alpha1.AppFailing, v1alpha1.AppFailed, v1alpha1.AppComplete:
		klog.Infof("Shutdown appID = %v can not shutdown, appState = %v", appID, appState)
	default:
		appCopy := app.DeepCopy()
		appCopy.Status.AppState = v1alpha1.AppShuttingDown
		_, err = handler.crdClient.FedlearnerV1alpha1().FLApps(handler.namespace).UpdateStatus(appCopy)
		if err != nil {
			err = fmt.Errorf("Shutdown appID = %v, err = %v", appID, err)
			klog.Error(err)
			return &pb.Status{
				Code:         int32(codes.Internal),
				ErrorMessage: err.Error(),
			}, status.Error(codes.Internal, err.Error())
		}
	}
	return &pb.Status{
		Code:         int32(codes.OK),
		ErrorMessage: "",
	}, nil
}

func (handler *appEventHandler) Finish(appID string) (*pb.Status, error) {
	klog.Infof("Finish app application %v, just echo ok", appID)
	return &pb.Status{
		Code:         int32(codes.OK),
		ErrorMessage: "",
	}, nil
}
