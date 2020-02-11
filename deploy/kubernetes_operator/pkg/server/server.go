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

func (ph *PairHandler) handleSync(name string, pairs []*pb.Pair) (*pb.Status, error) {
	allFilled := true
	allEmpty := true
	leaderReplicas := make(map[string][]string)
	followerReplicas := make(map[string][]string)
	for _, pair := range pairs {
		if len(pair.LeaderIds) != len(pair.FollowerIds) && len(pair.FollowerIds) != 0 {
			message := fmt.Sprintf("follower length should either be 0 or equal to leader, len(leader) = %v, len(follower) = %v", len(pair.LeaderIds), len(pair.FollowerIds))
			return &pb.Status{
				Code:         int32(codes.InvalidArgument),
				ErrorMessage: message,
			}, status.Error(codes.InvalidArgument, message)
		}
		allFilled = allFilled && len(pair.FollowerIds) > 0
		allEmpty = allEmpty && len(pair.FollowerIds) == 0

		if _, ok := leaderReplicas[pair.Role]; ok {
			message := fmt.Sprintf("role %v already exits in leader", pair.Role)
			return &pb.Status{
				Code:         int32(codes.InvalidArgument),
				ErrorMessage: message,
			}, status.Error(codes.InvalidArgument, message)
		}
		if _, ok := followerReplicas[pair.Role]; ok {
			message := fmt.Sprintf("role %v already exits in follower", pair.Role)
			return &pb.Status{
				Code:         int32(codes.InvalidArgument),
				ErrorMessage: message,
			}, status.Error(codes.InvalidArgument, message)
		}
		leaderReplicas[pair.Role] = pair.LeaderIds
		followerReplicas[pair.Role] = pair.FollowerIds
	}

	switch {
	case allEmpty:
		return ph.handler.SyncHandler(name, leaderReplicas)
	case allFilled:
		return ph.handler.SyncCallbackHandler(name, leaderReplicas, followerReplicas)
	default:
		message := fmt.Sprintf("follower should either be allEmpty or allFilled, allEmpty = %v, allFilled = %v", allEmpty, allFilled)
		return &pb.Status{
			Code:         int32(codes.InvalidArgument),
			ErrorMessage: message,
		}, status.Error(codes.InvalidArgument, message)
	}
}

func (ph *PairHandler) Pair(ctx context.Context, request *pb.PairRequest) (*pb.Status, error) {
	name := request.AppId
	ctrlFlag := request.CtrlFlag

	switch ctrlFlag {
	case pb.CtrlFlag_CREATE:
		return ph.handleSync(name, request.Pairs)
	case pb.CtrlFlag_SHUTDOWN:
		return ph.handler.ShutdownHandler(name)
	case pb.CtrlFlag_FINISH:
		return ph.handler.FinishHandler(name)
	}
	errMessage := fmt.Sprintf("CtrlFlag %v not defined", ctrlFlag)
	return &pb.Status{
		Code:         int32(codes.InvalidArgument),
		ErrorMessage: errMessage,
	}, status.Error(codes.InvalidArgument, errMessage)
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
