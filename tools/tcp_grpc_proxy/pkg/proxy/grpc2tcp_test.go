package proxy

import (
	"context"
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

func runFakeTcpServer(listener net.Listener) {
	for {
		conn, err := listener.Accept()
		if err != nil {
			logrus.Infoln("Intended TCP listener error:", err)
			return
		}

		go func(conn net.Conn) {
			defer conn.Close()
			for {
				request := make([]byte, 64*1024)
				bytesRead, err := conn.Read(request)
				if err == io.EOF {
					logrus.Infoln("[TCP server] Connection finished")
					return
				}
				if err != nil {
					logrus.Errorln("[TCP seerver] Error:", err)
					return
				}
				response := fmt.Sprintf("[Proxy] %s", string(request[0:bytesRead]))
				conn.Write([]byte(response))
			}
		}(conn)
	}
}

func TestGrpc2Tcp(t *testing.T) {
	grpcServerAddress := "localhost:13001"
	targetTcpAddress := "localhost:13002"

	// Sets up a fake TCP server
	listener, err := net.Listen("tcp", targetTcpAddress)
	if err != nil {
		assert.Fail(t, "Failed to listen")
	}
	go runFakeTcpServer(listener)

	// Starts the proxy
	tcp2grpcServer := NewGrpc2TcpServer(grpcServerAddress, targetTcpAddress)
	go tcp2grpcServer.Run()
	time.Sleep(1 * time.Second)

	// Sends data by grpc connection and gets response in the same channel
	responseChan := make(chan string)
	for i := 0; i < 3; i++ {
		go func(message string) {
			grpcConn, _ := grpc.Dial(grpcServerAddress, grpc.WithInsecure())
			grpcClient := proto.NewTunnelServiceClient(grpcConn)
			stream, _ := grpcClient.Tunnel(context.Background())

			stream.Send(&proto.Chunk{Data: []byte(message)})
			stream.CloseSend()
			chunk, _ := stream.Recv()
			responseChan <- string(chunk.Data)
			grpcConn.Close()
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
