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
	SyncLeaderPairs(*v1alpha1.FLApp) error
	// Called after follower finished pairing
	SyncFollowerPairs(*v1alpha1.FLApp) error
	// Called when either leader or follower needs to shutdown peer
	ShutdownPeer(*v1alpha1.FLApp) error
	// Called when either leader or follower is finished
	FinishPeer(*v1alpha1.FLApp) error
	// Received when peer send sync request
	SyncHandler(name string, leaderReplicas map[string][]string) (*pb.Status, error)
	// Received when peer send sync callback request
	SyncCallbackHandler(name string, leaderReplicas map[string][]string, followerReplicas map[string][]string) (*pb.Status, error)
	// Received when peer send shutdown request
	ShutdownHandler(name string) (*pb.Status, error)
	// Received when peer send finish request
	FinishHandler(name string) (*pb.Status, error)
}

type appEventHandler struct {
	peerURL string

	namespace string
	crdClient crdclientset.Interface

	grpcClient pb.PairingServiceClient
}

var _ AppEventHandler = &appEventHandler{}

func NewAppEventHandler(peerURL string, namespace string, crdClient crdclientset.Interface) AppEventHandler {
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

func (handler *appEventHandler) SyncLeaderPairs(app *v1alpha1.FLApp) error {
	var allPairs []*pb.Pair
	name := app.Name

	for rtype := range app.Spec.FLReplicaSpecs {
		if shouldPair(app, rtype) {
			pair := &pb.Pair{
				Role:        string(rtype),
				LeaderIds:   app.Status.FLReplicaStatus[rtype].Local.List(),
				FollowerIds: nil,
			}
			allPairs = append(allPairs, pair)
		}
	}

	request := &pb.PairRequest{
		AppId:    name,
		Pairs:    allPairs,
		CtrlFlag: pb.CtrlFlag_CREATE,
	}
	response, err := handler.grpcClient.Pair(context.Background(), request)
	if err != nil || response.Code != int32(codes.OK) {
		return fmt.Errorf("SyncLeaderPairs failed, name = %v, err = %v", name, err)
	}
	klog.Infof("SyncLeaderPairs name = %v, message = %v", name, response.ErrorMessage)
	return nil
}

func (handler *appEventHandler) SyncFollowerPairs(app *v1alpha1.FLApp) error {
	var allPairs []*pb.Pair
	name := app.Name

	for rtype := range app.Spec.FLReplicaSpecs {
		if shouldPair(app, rtype) {
			mapping := app.Status.FLReplicaStatus[rtype].Mapping
			pair := &pb.Pair{
				Role:        string(rtype),
				LeaderIds:   nil,
				FollowerIds: nil,
			}
			for followerId, leaderId := range mapping {
				pair.LeaderIds = append(pair.LeaderIds, leaderId)
				pair.FollowerIds = append(pair.FollowerIds, followerId)
			}
			allPairs = append(allPairs, pair)
		}
	}

	request := &pb.PairRequest{
		AppId:    name,
		Pairs:    allPairs,
		CtrlFlag: pb.CtrlFlag_CREATE,
	}
	response, err := handler.grpcClient.Pair(context.Background(), request)
	if err != nil || response.Code != int32(codes.OK) {
		return fmt.Errorf("SyncFollowerPairs failed name = %v, err = %v", name, err)
	}
	klog.Infof("SyncFollowerPairs success name = %v, message = %v", name, response.ErrorMessage)
	return nil
}

func (handler *appEventHandler) ShutdownPeer(app *v1alpha1.FLApp) error {
	name := app.Name
	request := &pb.PairRequest{
		AppId:    name,
		Pairs:    nil,
		CtrlFlag: pb.CtrlFlag_SHUTDOWN,
	}
	response, err := handler.grpcClient.Pair(context.Background(), request)
	if err != nil || response.Code != int32(codes.OK) {
		return fmt.Errorf("ShutdownPeer failed name = %v, err = %v", name, err)
	}
	klog.Infof("ShutdownPeer success name = %v, message = %v", name, response.ErrorMessage)
	return nil
}

func (handler *appEventHandler) FinishPeer(app *v1alpha1.FLApp) error {
	name := app.Name
	request := &pb.PairRequest{
		AppId:    name,
		Pairs:    nil,
		CtrlFlag: pb.CtrlFlag_FINISH,
	}
	response, err := handler.grpcClient.Pair(context.Background(), request)
	if err != nil || response.Code != int32(codes.OK) {
		return fmt.Errorf("FinishPeer failed name = %v, err = %v", name, err)
	}
	klog.Infof("FinishPeer success name = %v, message = %v", name, response.ErrorMessage)
	return nil
}

func (handler *appEventHandler) SyncHandler(name string, leaderReplicas map[string][]string) (*pb.Status, error) {
	app, err := handler.crdClient.FedlearnerV1alpha1().FLApps(handler.namespace).Get(name, metav1.GetOptions{})
	if err != nil {
		klog.Errorf("SyncHandler name = %v, err = %v", name, err)
		return &pb.Status{
			Code:         int32(codes.Internal),
			ErrorMessage: err.Error(),
		}, status.Error(codes.Internal, err.Error())
	}
	if app.Status.AppState != v1alpha1.FLStateBootstrapped {
		err := fmt.Errorf("SyncHandler state is not bootstrapped, name = %v, state = %v", name, app.Status.AppState)
		klog.Error(err)
		return &pb.Status{
			Code:         int32(codes.Internal),
			ErrorMessage: err.Error(),
		}, status.Error(codes.Internal, err.Error())
	}

	appCopy := app.DeepCopy()
	for rtype := range app.Spec.FLReplicaSpecs {
		if shouldPair(appCopy, rtype) {
			if leaderIds, ok := leaderReplicas[string(rtype)]; ok {
				status := appCopy.Status.FLReplicaStatus[rtype]
				replicaStatus := status.DeepCopy()
				replicaStatus.Remote = sets.NewString(leaderIds...)
				appCopy.Status.FLReplicaStatus[rtype] = *replicaStatus
			} else {
				err := fmt.Errorf("SyncHandler %v leader not found, name = %v, err = %v", rtype, name, err)
				klog.Error(err)
				return &pb.Status{
					Code:         int32(codes.Internal),
					ErrorMessage: err.Error(),
				}, status.Error(codes.Internal, err.Error())
			}
		}
	}
	_, err = handler.crdClient.FedlearnerV1alpha1().FLApps(handler.namespace).UpdateStatus(appCopy)
	if err != nil {
		err = fmt.Errorf("SyncHandler name = %v, err = %v", name, err)
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

func (handler *appEventHandler) SyncCallbackHandler(name string, leaderReplicas map[string][]string, followerReplicas map[string][]string) (*pb.Status, error) {
	app, err := handler.crdClient.FedlearnerV1alpha1().FLApps(handler.namespace).Get(name, metav1.GetOptions{})
	if err != nil {
		err = fmt.Errorf("SyncCallbackHandler name = %v, err = %v", name, err)
		klog.Error(err)
		return &pb.Status{
			Code:         int32(codes.Internal),
			ErrorMessage: err.Error(),
		}, status.Error(codes.Internal, err.Error())
	}

	appCopy := app.DeepCopy()
	for rtype := range app.Spec.FLReplicaSpecs {
		if shouldPair(app, rtype) {
			if leaderIds, ok := leaderReplicas[string(rtype)]; ok {
				mapping := make(map[string]string)
				followerIds := followerReplicas[string(rtype)]
				status := appCopy.Status.FLReplicaStatus[rtype]
				replicaStatus := status.DeepCopy()

				replicaStatus.Remote = sets.NewString(leaderIds...)
				for idx := 0; idx < len(followerIds); idx++ {
					mapping[followerIds[idx]] = leaderIds[idx]
				}
				replicaStatus.Mapping = mapping
				appCopy.Status.FLReplicaStatus[rtype] = *replicaStatus
			} else {
				err := fmt.Errorf("SyncHandler %v leader/follower not found, name = %v, err = %v", rtype, name, err)
				klog.Error(err)
				return &pb.Status{
					Code:         int32(codes.Internal),
					ErrorMessage: err.Error(),
				}, status.Error(codes.Internal, err.Error())
			}
		}
	}
	_, err = handler.crdClient.FedlearnerV1alpha1().FLApps(handler.namespace).UpdateStatus(appCopy)
	if err != nil {
		err = fmt.Errorf("SyncCallbackHandler name = %v, err = %v", name, err)
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

func (handler *appEventHandler) ShutdownHandler(appID string) (*pb.Status, error) {
	app, err := handler.crdClient.FedlearnerV1alpha1().FLApps(handler.namespace).Get(appID, metav1.GetOptions{})
	if err != nil {
		err = fmt.Errorf("ShutdownHandler appID = %v, err = %v", appID, err)
		klog.Error(err)
		return &pb.Status{
			Code:         int32(codes.Internal),
			ErrorMessage: err.Error(),
		}, status.Errorf(codes.Internal, err.Error())
	}

	appState := app.Status.AppState
	switch appState {
	case v1alpha1.FLStateFailing, v1alpha1.FLStateFailed, v1alpha1.FLStateComplete:
		klog.Infof("ShutdownHandler appID = %v can not shutdown, appState = %v", appID, appState)
	default:
		appCopy := app.DeepCopy()
		appCopy.Status.AppState = v1alpha1.FLStateShutDown
		_, err = handler.crdClient.FedlearnerV1alpha1().FLApps(handler.namespace).UpdateStatus(appCopy)
		if err != nil {
			err = fmt.Errorf("ShutdownHandler appID = %v, err = %v", appID, err)
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

func (handler *appEventHandler) FinishHandler(name string) (*pb.Status, error) {
	klog.Infof("FinishHandler app application %v, just echo ok", name)
	return &pb.Status{
		Code:         int32(codes.OK),
		ErrorMessage: "",
	}, nil
}
