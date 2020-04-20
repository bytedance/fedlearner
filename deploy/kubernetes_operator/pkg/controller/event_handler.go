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
	"strings"

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
	Register(context.Context, *v1alpha1.FLApp) error
	// Called after leader finished pairing
	Pair(context.Context, *v1alpha1.FLApp) error
	// Called when leader/follower needs to shutdown peer
	Shutdown(context.Context, *v1alpha1.FLApp) error
	// Called when leader/follower is finished
	Finish(context.Context, *v1alpha1.FLApp) error
	// Received when peer send sync request
	RegisterHandler(ctx context.Context, name string, role string, followerReplicas map[string][]string) (*pb.Status, error)
	// Received when peer send sync callback request
	PairHandler(ctx context.Context, name string, leaderReplicas map[string][]string, followerReplicas map[string][]string) (*pb.Status, error)
	// Received when peer send shutdown request
	ShutdownHandler(ctx context.Context, name string) (*pb.Status, error)
	// Received when peer send finish request
	FinishHandler(ctx context.Context, name string) (*pb.Status, error)
}

type appEventHandler struct {
	namespace string
	crdClient crdclientset.Interface
}

var _ AppEventHandler = &appEventHandler{}

func NewAppEventHandler(namespace string, crdClient crdclientset.Interface) AppEventHandler {
	return &appEventHandler{
		namespace: namespace,
		crdClient: crdClient,
	}
}

func (handler *appEventHandler) Register(ctx context.Context, app *v1alpha1.FLApp) error {
	name := app.Name
	if IsLeader(app.Spec.Role) {
		return fmt.Errorf("only followers should register, name = %v", name)
	}
	leaderSpec, ok := app.Spec.PeerSpecs[RoleLeader]
	if !ok {
		return fmt.Errorf("leader spec is not specified, name = %v", name)
	}
	client, err := newClient(leaderSpec.PeerURL, leaderSpec.Authority)
	if err != nil {
		return fmt.Errorf("failed to build client, name = %v", name)
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

	response, err := client.Register(newContextWithHeaders(leaderSpec.ExtraHeaders), request)
	if err != nil || response.Code != int32(codes.OK) {
		return fmt.Errorf("Register failed, name = %v, err = %v", name, err)
	}
	klog.Infof("Register success name = %v, message = %v", name, response.ErrorMessage)
	return nil
}

func (handler *appEventHandler) Pair(ctx context.Context, app *v1alpha1.FLApp) error {
	name := app.Name
	if !IsLeader(app.Spec.Role) {
		return fmt.Errorf("only leader should pair with followers, name = %v", name)
	}

	for role, peerSpec := range app.Spec.PeerSpecs {
		klog.Infof("start to pair for app %v, role = %v", app.Name, app.Spec.Role)
		client, err := newClient(peerSpec.PeerURL, peerSpec.Authority)
		if err != nil {
			return fmt.Errorf("failed to build client, name = %v, role = %v", name, role)
		}

		request := &pb.PairRequest{
			AppId: name,
			Pairs: makePairs(app, role),
		}
		response, err := client.Pair(newContextWithHeaders(peerSpec.ExtraHeaders), request)
		if err != nil || response.Code != int32(codes.OK) {
			return fmt.Errorf("Pair failed name = %v, err = %v", name, err)
		}
		klog.Infof("Pair success name = %v, message = %v", name, response.ErrorMessage)
	}
	return nil
}

func (handler *appEventHandler) Shutdown(ctx context.Context, app *v1alpha1.FLApp) error {
	name := app.Name
	request := &pb.ShutDownRequest{
		AppId: name,
		Role:  app.Spec.Role,
	}
	for role, peerSpec := range app.Spec.PeerSpecs {
		client, err := newClient(peerSpec.PeerURL, peerSpec.Authority)
		if err != nil {
			return fmt.Errorf("failed to build client, name = %v, role = %v", name, role)
		}
		response, err := client.ShutDown(newContextWithHeaders(peerSpec.ExtraHeaders), request)
		if err != nil || response.Code != int32(codes.OK) {
			return fmt.Errorf("Shutdown failed name = %v, role = %v, err = %v", name, role, err)
		}
		klog.Infof("Shutdown success name = %v, role = %v, message = %v", name, role, response.ErrorMessage)
	}
	return nil
}

func (handler *appEventHandler) Finish(ctx context.Context, app *v1alpha1.FLApp) error {
	name := app.Name
	request := &pb.FinishRequest{
		AppId: name,
		Role:  app.Spec.Role,
	}
	for role, peerSpec := range app.Spec.PeerSpecs {
		client, err := newClient(peerSpec.PeerURL, peerSpec.Authority)
		if err != nil {
			return fmt.Errorf("failed to build client, name = %v, role = %v", name, role)
		}
		response, err := client.Finish(newContextWithHeaders(peerSpec.ExtraHeaders), request)
		if err != nil || response.Code != int32(codes.OK) {
			return fmt.Errorf("Finish failed name = %v, role = %v, err = %v", name, role, err)
		}
		klog.Infof("Finish success name = %v, role = %v, message = %v", name, role, response.ErrorMessage)
	}
	return nil
}

func (handler *appEventHandler) RegisterHandler(ctx context.Context, name string, role string, followerReplicas map[string][]string) (*pb.Status, error) {
	app, err := handler.crdClient.FedlearnerV1alpha1().FLApps(handler.namespace).Get(name, metav1.GetOptions{})
	if err != nil {
		klog.Errorf("RegisterHandler name = %v, role = %v, err = %v", name, role, err)
		return &pb.Status{
			Code:         int32(codes.Internal),
			ErrorMessage: err.Error(),
		}, status.Error(codes.Internal, err.Error())
	}
	if app.Status.AppState != v1alpha1.FLStateBootstrapped {
		err := fmt.Errorf("RegisterHandler leader is not bootstrapped, name = %v, role = %v, state = %v", name, role, app.Status.AppState)
		klog.Error(err)
		return &pb.Status{
			Code:         int32(codes.Internal),
			ErrorMessage: err.Error(),
		}, status.Error(codes.Internal, err.Error())
	}

	appCopy := app.DeepCopy()
	for rtype := range app.Spec.FLReplicaSpecs {
		if needPair(appCopy, rtype) {
			if followerIDs, ok := followerReplicas[string(rtype)]; ok {
				status := appCopy.Status.FLReplicaStatus[rtype]
				replicaStatus := status.DeepCopy()
				for _, followerID := range followerIDs {
					replicaStatus.Remote.Insert(followerID)
				}
				appCopy.Status.FLReplicaStatus[rtype] = *replicaStatus
			} else {
				err := fmt.Errorf("RegisterHandler %v follower not found, name = %v, role = %v, err = %v", rtype, name, role, err)
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
		err = fmt.Errorf("RegisterHandler name = %v, role = %v, err = %v", name, role, err)
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

func (handler *appEventHandler) PairHandler(ctx context.Context, name string, leaderReplicas map[string][]string, followerReplicas map[string][]string) (*pb.Status, error) {
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
			if leaderIDs, ok := leaderReplicas[string(rtype)]; ok {
				mapping := make(map[string]string)
				followerIDs := followerReplicas[string(rtype)]
				status := appCopy.Status.FLReplicaStatus[rtype]
				replicaStatus := status.DeepCopy()

				replicaStatus.Remote = sets.NewString(leaderIDs...)
				for idx := 0; idx < len(followerIDs); idx++ {
					mapping[followerIDs[idx]] = leaderIDs[idx]
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

func (handler *appEventHandler) ShutdownHandler(ctx context.Context, appID string) (*pb.Status, error) {
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

func (handler *appEventHandler) FinishHandler(ctx context.Context, name string) (*pb.Status, error) {
	klog.Infof("FinishHandler app application %v, just echo ok", name)
	return &pb.Status{
		Code:         int32(codes.OK),
		ErrorMessage: "",
	}, nil
}

func newClient(peerURL, authority string) (pb.PairingServiceClient, error) {
	opts := []grpc.DialOption{grpc.WithInsecure()}
	if authority != "" {
		opts = append(opts, grpc.WithAuthority(authority))
	}
	connection, err := grpc.Dial(peerURL, opts...)
	if err != nil {
		return nil, err
	}
	return pb.NewPairingServiceClient(connection), nil
}

func newContextWithHeaders(headers map[string]string) context.Context {
	return metadata.NewOutgoingContext(context.Background(), metadata.New(headers))
}

func makePairs(app *v1alpha1.FLApp, role string) []*pb.Pair {
	prefix := app.Name + "-" + strings.ToLower(role) + "-"
	var pairs []*pb.Pair
	for rtype := range app.Spec.FLReplicaSpecs {
		if needPair(app, rtype) {
			mapping := app.Status.FLReplicaStatus[rtype].Mapping
			pair := &pb.Pair{
				Type:        string(rtype),
				LeaderIds:   nil,
				FollowerIds: nil,
			}
			for leaderID, followerID := range mapping {
				if strings.HasPrefix(followerID, prefix) {
					pair.LeaderIds = append(pair.LeaderIds, leaderID)
					pair.FollowerIds = append(pair.FollowerIds, followerID)
				}
			}
			pairs = append(pairs, pair)
		}
	}
	return pairs
}
