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
	"k8s.io/apimachinery/pkg/util/sets"
	"k8s.io/klog"

	"github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/controller"
	pb "github.com/bytedance/fedlearner/deploy/kubernetes_operator/proto"
)

type SyncController struct {
	handler controller.AppEventHandler
}

func (sc *SyncController) handleSync(appID string, workerPairs []*pb.Pair, masterPairs []*pb.Pair) (*pb.Status, error) {
	leaderWorker, followerWorker, workerMapping, followerCnt := extract(workerPairs)
	if followerCnt != 0 && followerCnt != len(workerPairs) {
		message := fmt.Sprintf("follower cnt is not consistent, empty follower cnt = %v", followerCnt)
		return &pb.Status{
			Code:         int32(codes.InvalidArgument),
			ErrorMessage: message,
		}, status.Error(codes.InvalidArgument, message)
	}

	leaderMaster, followerMaster, masterMapping, masterCnt := extract(masterPairs)
	if masterCnt != 0 && masterCnt != len(masterPairs) {
		message := fmt.Sprintf("master cnt is not consistent, empty master cnt = %v", masterCnt)
		return &pb.Status{
			Code:         int32(codes.InvalidArgument),
			ErrorMessage: message,
		}, status.Error(codes.InvalidArgument, message)
	}

	switch {
	case followerCnt == len(workerPairs) && masterCnt == len(masterPairs):
		return sc.handler.Sync(appID, leaderWorker, leaderMaster)
	case followerCnt == 0 && masterCnt == 0:
		return sc.handler.SyncCallback(appID, workerMapping, followerWorker, masterMapping, followerMaster)
	default:
		message := fmt.Sprintf("master/follower cnt is not consistent, empty master cnt = %v, follower cnt = %v", masterCnt, followerCnt)
		return &pb.Status{
			Code:         int32(codes.InvalidArgument),
			ErrorMessage: message,
		}, status.Error(codes.InvalidArgument, message)
	}
}

func extract(pairs []*pb.Pair) (keys sets.String, values sets.String, mapping map[string]string, cnt int) {
	keys = sets.NewString()
	values = sets.NewString()
	mapping = make(map[string]string)
	cnt = 0

	for _, pair := range pairs {
		keys.Insert(pair.LeaderId)
		values.Insert(pair.FollowerId)
		mapping[pair.LeaderId] = pair.FollowerId
		if pair.FollowerId == "" {
			cnt++
		}
	}
	return keys, values, mapping, cnt
}

func (sc *SyncController) Pair(ctx context.Context, request *pb.PairRequest) (*pb.Status, error) {
	appID := request.AppId
	ctrlFlag := request.CtrlFlag

	switch ctrlFlag {
	case pb.CtrlFlag_CREATE:
		return sc.handleSync(appID, request.WorkerPairs, request.MasterPairs)
	case pb.CtrlFlag_SHUTDOWN:
		return sc.handler.Shutdown(appID)
	case pb.CtrlFlag_FINISH:
		return sc.handler.Finish(appID)
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
	pb.RegisterPairingServiceServer(grpcServer, &SyncController{handler: handler})
	if err := grpcServer.Serve(lis); err != nil {
		klog.Fatalf("failed to serve grpc service, err = %v", err)
	}
}
