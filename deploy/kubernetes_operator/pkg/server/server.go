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

package server

import (
	"context"
	"fmt"
	"net"

	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
	"k8s.io/klog"

	"github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/controller"
	pb "github.com/bytedance/fedlearner/deploy/kubernetes_operator/proto"
)

type PairHandler struct {
	handler controller.AppEventHandler
}

func (ph *PairHandler) Register(ctx context.Context, request *pb.RegisterRequest) (*pb.Status, error) {
	name := request.AppId
	role := request.Role
	klog.Infof("Register received, name = %v, role = %v", name, role)
	if controller.IsLeader(role) {
		msg := fmt.Sprintf("Register is only accepted from followers, name = %v, role = %v", name, role)
		return makeInvalidArgumentStatus(msg)
	}
	replicas := make(map[string][]string)
	for _, pair := range request.Pairs {
		pairCopy := *pair
		if len(pairCopy.LeaderIds) > 0 {
			message := fmt.Sprintf("Register should only send FollowerIds, name = %v, replicaType = %v", name, pairCopy.Type)
			return makeInvalidArgumentStatus(message)
		}
		replicas[pairCopy.Type] = pairCopy.FollowerIds
	}
	return ph.handler.RegisterHandler(name, role, replicas)
}

func (ph *PairHandler) Pair(ctx context.Context, request *pb.PairRequest) (*pb.Status, error) {
	name := request.AppId

	leaderReplicas := make(map[string][]string)
	followerReplicas := make(map[string][]string)
	for _, pair := range request.Pairs {
		pairCopy := *pair
		if len(pair.LeaderIds) != len(pair.FollowerIds) {
			message := fmt.Sprintf(
				"Pair the length of leader and follower doesn't match, name = %v, replicaType = %v, len(leader) = %v, len(follower) = %v",
				name,
				pairCopy.Type,
				len(pair.LeaderIds),
				len(pair.FollowerIds),
			)
			return makeInvalidArgumentStatus(message)
		}
		leaderReplicas[pairCopy.Type] = pairCopy.LeaderIds
		followerReplicas[pairCopy.Type] = pairCopy.FollowerIds
	}
	return ph.handler.PairHandler(name, leaderReplicas, followerReplicas)
}

func (ph *PairHandler) Finish(ctx context.Context, request *pb.FinishRequest) (*pb.Status, error) {
	name := request.AppId
	klog.Infof("Finish received, name = %v, role = %v", name, request.Role)
	return ph.handler.FinishHandler(name)
}

func (ph *PairHandler) ShutDown(ctx context.Context, request *pb.ShutDownRequest) (*pb.Status, error) {
	name := request.AppId
	klog.Infof("ShutDown received, name = %v, role = %v", name, request.Role)
	return ph.handler.ShutdownHandler(name)
}

func ServeGrpc(host, port string, handler controller.AppEventHandler) {
	lis, err := net.Listen("tcp", fmt.Sprintf("%s:%s", host, port))
	if err != nil {
		klog.Fatalf("failed to listen: %v", err)
	}
	grpcServer := grpc.NewServer()
	pb.RegisterPairingServiceServer(grpcServer, &PairHandler{handler: handler})
	if err := grpcServer.Serve(lis); err != nil {
		klog.Fatalf("failed to serve grpc service, err = %v", err)
	}
}

func makeInvalidArgumentStatus(msg string) (*pb.Status, error) {
	return &pb.Status{
		Code:         int32(codes.InvalidArgument),
		ErrorMessage: msg,
	}, status.Error(codes.InvalidArgument, msg)
}
