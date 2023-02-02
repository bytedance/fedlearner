package proxy

import (
	"fmt"
	"io"
	"net"
	"testing"
	"time"

	"fedlearner.net/tools/tcp_grpc_proxy/pkg/proto"
	"github.com/sirupsen/logrus"
	"github.com/stretchr/testify/assert"
	"google.golang.org/grpc"
)

// mockGrpc2TcpServer is used to mock TunnelServer
type mockTunnelServer struct {
	proto.UnimplementedTunnelServiceServer
}

func (s *mockTunnelServer) Tunnel(stream proto.TunnelService_TunnelServer) error {
	for {
		chunk, err := stream.Recv()
		if err == io.EOF {
			logrus.Infoln("[gRPC server] Stream EOF")
			return nil
		}
		if err != nil {
			logrus.Errorln("[gRPC server] error:", err)
			return err
		}
		response := fmt.Sprintf("[Proxy] %s", string(chunk.Data))
		if err = stream.Send(&proto.Chunk{Data: []byte(response)}); err != nil {
			return err
		}
	}
}

func runFakeGrpcServer(listener net.Listener) {
	// Starts a gRPC server and register services
	grpcServer := grpc.NewServer()
	proto.RegisterTunnelServiceServer(grpcServer, &mockTunnelServer{})
	if err := grpcServer.Serve(listener); err != nil {
		logrus.Fatalln("Unable to start gRPC serve:", err)
	}
}

func TestTcp2Grpc(t *testing.T) {
	tcpServerAddress := "localhost:12001"
	targetGrpcAddress := "localhost:12002"

	// Sets up a fake gRPC server
	listener, err := net.Listen("tcp", targetGrpcAddress)
	if err != nil {
		assert.Fail(t, "Failed to listen")
	}
	go runFakeGrpcServer(listener)

	// Starts the proxy
	tcp2grpcServer := NewTcp2GrpcServer(tcpServerAddress, targetGrpcAddress)
	go tcp2grpcServer.Run()
	time.Sleep(1 * time.Second)

	// Sends data by tcp connection and gets response in the same channel
	responseChan := make(chan string)
	for i := 0; i < 3; i++ {
		go func(message string) {
			tcpConnection, _ := net.Dial("tcp", tcpServerAddress)
			tcpConnection.Write([]byte(message))
			response := make([]byte, 64*1024)
			bytesRead, _ := tcpConnection.Read(response)
			responseChan <- string(response[0:bytesRead])
			tcpConnection.Close()
		}(fmt.Sprintf("hello %d", i))
	}

	responses := make([]string, 0)
	for i := 0; i < 3; i++ {
		r := <-responseChan
		responses = append(responses, r)
	}

	assert.ElementsMatch(t, responses,
		[]string{"[Proxy] hello 0", "[Proxy] hello 1", "[Proxy] hello 2"})
}
