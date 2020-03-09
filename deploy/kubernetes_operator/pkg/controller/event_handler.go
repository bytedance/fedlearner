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
	"google.golang.org/grpc/metadata"
	"google.golang.org/grpc/status"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/util/sets"
	"k8s.io/klog"

	"github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/apis/fedlearner.k8s.io/v1alpha1"
	crdclientset "github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/client/clientset/versioned"
	pb "github.com/bytedance/fedlearner/deploy/kubernetes_operator/proto"
)

type AppEventHandler interface {
	// Called after follower bootstrapped
	Register(*v1alpha1.FLApp) error
	// Called after leader finished pairing
	Pair(*v1alpha1.FLApp) error
	// Called when leader/follower needs to shutdown peer
	Shutdown(*v1alpha1.FLApp) error
	// Called when leader/follower is finished
	Finish(*v1alpha1.FLApp) error
	// Received when peer send sync request
	RegisterHandler(name string, followerReplicas map[string][]string) (*pb.Status, error)
	// Received when peer send sync callback request
	PairHandler(name string, leaderReplicas map[string][]string, followerReplicas map[string][]string) (*pb.Status, error)
	// Received when peer send shutdown request
	ShutdownHandler(name string) (*pb.Status, error)
	// Received when peer send finish request
	FinishHandler(name string) (*pb.Status, error)
}

type appEventHandler struct {
	peerURL   string
	namespace string
	crdClient crdclientset.Interface

	grpcClient pb.PairingServiceClient
}

var _ AppEventHandler = &appEventHandler{}

func NewAppEventHandler(peerURL, grpcDefaultAuthority, namespace string, crdClient crdclientset.Interface) AppEventHandler {
	opts := []grpc.DialOption{grpc.WithInsecure()}
	if grpcDefaultAuthority != "" {
		opts = append(opts, grpc.WithAuthority(grpcDefaultAuthority))
	}
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

func (handler *appEventHandler) Register(app *v1alpha1.FLApp) error {
	name := app.Name
	if IsLeader(app.Spec.Role) {
		return fmt.Errorf("only followers should register, name = %v", name)
	}

	var pairs []*pb.Pair
	for rtype := range app.Spec.FLReplicaSpecs {
		if needPair(app, rtype) {
			pair := &pb.Pair{
				Type:        string(rtype),
				LeaderIds:   nil,
				FollowerIds: app.Status.FLReplicaStatus[rtype].Local.List(),
			}
			pairs = append(pairs, pair)
		}
	}
	request := &pb.RegisterRequest{
		AppId: name,
		Role:  app.Spec.Role,
		Pairs: pairs,
	}
	response, err := handler.grpcClient.Register(newContextXHost(), request)
	if err != nil || response.Code != int32(codes.OK) {
		return fmt.Errorf("Register failed, name = %v, err = %v", name, err)
	}
	klog.Infof("Register success name = %v, message = %v", name, response.ErrorMessage)
	return nil
}

func (handler *appEventHandler) Pair(app *v1alpha1.FLApp) error {
	name := app.Name
	var pairs []*pb.Pair
	if !IsLeader(app.Spec.Role) {
		return fmt.Errorf("only leader should pair with followers, name = %v", name)
	}

	for rtype := range app.Spec.FLReplicaSpecs {
		if needPair(app, rtype) {
			mapping := app.Status.FLReplicaStatus[rtype].Mapping
			pair := &pb.Pair{
				Type:        string(rtype),
				LeaderIds:   nil,
				FollowerIds: nil,
			}
			for leaderId, followerId := range mapping {
				pair.LeaderIds = append(pair.LeaderIds, leaderId)
				pair.FollowerIds = append(pair.FollowerIds, followerId)
			}
			pairs = append(pairs, pair)
		}
	}

	request := &pb.PairRequest{
		AppId: name,
		Pairs: pairs,
	}
	response, err := handler.grpcClient.Pair(newContextXHost(), request)
	if err != nil || response.Code != int32(codes.OK) {
		return fmt.Errorf("Pair failed name = %v, err = %v", name, err)
	}
	klog.Infof("Pair success name = %v, message = %v", name, response.ErrorMessage)
	return nil
}

func (handler *appEventHandler) Shutdown(app *v1alpha1.FLApp) error {
	name := app.Name
	request := &pb.ShutDownRequest{
		AppId: name,
		Role:  app.Spec.Role,
	}
	response, err := handler.grpcClient.ShutDown(newContextXHost(), request)
	if err != nil || response.Code != int32(codes.OK) {
		return fmt.Errorf("Shutdown failed name = %v, err = %v", name, err)
	}
	klog.Infof("Shutdown success name = %v, message = %v", name, response.ErrorMessage)
	return nil
}

func (handler *appEventHandler) Finish(app *v1alpha1.FLApp) error {
	name := app.Name
	request := &pb.FinishRequest{
		AppId: name,
		Role:  app.Spec.Role,
	}
	response, err := handler.grpcClient.Finish(newContextXHost(), request)
	if err != nil || response.Code != int32(codes.OK) {
		return fmt.Errorf("Finish failed name = %v, err = %v", name, err)
	}
	klog.Infof("Finish success name = %v, message = %v", name, response.ErrorMessage)
	return nil
}

func (handler *appEventHandler) RegisterHandler(name string, followerReplicas map[string][]string) (*pb.Status, error) {
	app, err := handler.crdClient.FedlearnerV1alpha1().FLApps(handler.namespace).Get(name, metav1.GetOptions{})
	if err != nil {
		klog.Errorf("RegisterHandler name = %v, err = %v", name, err)
		return &pb.Status{
			Code:         int32(codes.Internal),
			ErrorMessage: err.Error(),
		}, status.Error(codes.Internal, err.Error())
	}
	if app.Status.AppState != v1alpha1.FLStateBootstrapped {
		err := fmt.Errorf("RegisterHandler leader is not bootstrapped, name = %v, state = %v", name, app.Status.AppState)
		klog.Error(err)
		return &pb.Status{
			Code:         int32(codes.Internal),
			ErrorMessage: err.Error(),
		}, status.Error(codes.Internal, err.Error())
	}

	appCopy := app.DeepCopy()
	for rtype := range app.Spec.FLReplicaSpecs {
		if needPair(appCopy, rtype) {
			if followerIds, ok := followerReplicas[string(rtype)]; ok {
				status := appCopy.Status.FLReplicaStatus[rtype]
				replicaStatus := status.DeepCopy()
				replicaStatus.Remote = sets.NewString(followerIds...)
				appCopy.Status.FLReplicaStatus[rtype] = *replicaStatus
			} else {
				err := fmt.Errorf("RegisterHandler %v follower not found, name = %v, err = %v", rtype, name, err)
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
		err = fmt.Errorf("RegisterHandler name = %v, err = %v", name, err)
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

func (handler *appEventHandler) PairHandler(name string, leaderReplicas map[string][]string, followerReplicas map[string][]string) (*pb.Status, error) {
	app, err := handler.crdClient.FedlearnerV1alpha1().FLApps(handler.namespace).Get(name, metav1.GetOptions{})
	if err != nil {
		err = fmt.Errorf("PairHandler name = %v, err = %v", name, err)
		klog.Error(err)
		return &pb.Status{
			Code:         int32(codes.Internal),
			ErrorMessage: err.Error(),
		}, status.Error(codes.Internal, err.Error())
	}

	appCopy := app.DeepCopy()
	for rtype := range app.Spec.FLReplicaSpecs {
		if needPair(app, rtype) {
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
				err := fmt.Errorf("PairHandler %v leader/follower not found, name = %v, err = %v", rtype, name, err)
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
		err = fmt.Errorf("PairHandler name = %v, err = %v", name, err)
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
	case v1alpha1.FLStateFailing, v1alpha1.FLStateFailed, v1alpha1.FLStateComplete, v1alpha1.FLStateShutDown:
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

func newContextXHost() context.Context {
	return newContextWithHeader("x-host", "flapp.operator")
}

func newContextWithHeader(key, value string) context.Context {
	header := metadata.New(map[string]string{key: value})
	return metadata.NewOutgoingContext(context.Background(), header)
}
