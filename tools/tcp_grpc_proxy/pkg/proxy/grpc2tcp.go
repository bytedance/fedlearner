package proxy

import (
	"fmt"
	"io"
	"net"

	"fedlearner.net/tools/tcp_grpc_proxy/pkg/proto"
	"github.com/sirupsen/logrus"
	"google.golang.org/grpc"
)

// Grpc2TcpServer A server to proxy grpc traffic to TCP
type Grpc2TcpServer struct {
	proto.UnimplementedTunnelServiceServer
	grpcServerAddress string
	targetTcpAddress  string
}

// Tunnel the implementation of gRPC Tunnel service
func (s *Grpc2TcpServer) Tunnel(stream proto.TunnelService_TunnelServer) error {
	tcpConnection, err := net.Dial("tcp", s.targetTcpAddress)
	if err != nil {
		logrus.Errorf("[GRPC2TCP] Dail to tcp target %s error: %v", s.targetTcpAddress, err)
		return err
	}
	contextLogger := logrus.WithFields(logrus.Fields{
		"prefix": "[GRPC2TCP]",
		"tcp_client_addr": tcpConnection.LocalAddr().String(),
	})
	contextLogger.Infoln("Connected to", s.targetTcpAddress)
	// Makes sure the connection gets closed
	defer tcpConnection.Close()
	defer contextLogger.Infoln("Connection closed to", s.targetTcpAddress)

	errChan := make(chan error)

	// Gets data from gRPC client and proxy to remote TCP server
	go func() {
		tcpSentBytes := 0
		grpcReceivedBytes := 0
		defer func() {
			contextLogger.Infof("gRPC received %d bytes, TCP sent %d byte", grpcReceivedBytes, tcpSentBytes)
		}()

		for {
			chunk, err := stream.Recv()
			if err == io.EOF {
				contextLogger.Infoln("gRpc client EOF")
				return
			}
			if err != nil {
				errChan <- fmt.Errorf("error while receiving gRPC data: %v", err)
				return
			}
			data := chunk.Data
			grpcReceivedBytes += len(data)

			contextLogger.Debugln("Sending %d bytes to tcp server", len(data))
			_, err = tcpConnection.Write(data)
			if err != nil {
				errChan <- fmt.Errorf("error while sending TCP data: %v", err)
				return
			} else {
				tcpSentBytes += len(data)
			}
		}
	}()

	// Gets data from remote TCP server and proxy to gRPC client
	go func() {
		tcpReceivedBytes := 0
		grpcSentBytes := 0
		defer func() {
			contextLogger.Infof("Tcp received %d bytes, gRPC sent %d bytes", tcpReceivedBytes, grpcSentBytes)
		} ()

		buff := make([]byte, 64*1024)
		for {
			bytesRead, err := tcpConnection.Read(buff)
			if err == io.EOF {
				contextLogger.Infoln("Remote TCP connection closed")
				errChan <- nil
				return
			}
			if err != nil {
				errChan <- fmt.Errorf("error while receiving TCP data: %v", err)
				return
			}
			tcpReceivedBytes += bytesRead

			contextLogger.Debugf("Sending %d bytes to gRPC client\n", bytesRead)
			err = stream.Send(&proto.Chunk{Data: buff[0:bytesRead]})
			if err != nil {
				errChan <- fmt.Errorf("error while sending gRPC data: %v", err)
				return
			} else {
				grpcSentBytes += bytesRead
			}
		}
	}()

	// Blocking read
	returnedError := <-errChan
	if returnedError != nil {
		contextLogger.Errorln(returnedError)
	}
	return returnedError
}

// NewGrpc2TcpServer constructs a Grpc2TCP server
func NewGrpc2TcpServer(grpcServerAddress, targetTcpAddress string) *Grpc2TcpServer {
	return &Grpc2TcpServer{
		grpcServerAddress: grpcServerAddress,
		targetTcpAddress:  targetTcpAddress,
	}
}

// Run starts the Grpc2TCP server
func (s *Grpc2TcpServer) Run() {
	listener, err := net.Listen("tcp", s.grpcServerAddress)
	if err != nil {
		logrus.Fatalln("Failed to listen: ", err)
	}
	defer listener.Close()

	// Starts a gRPC server and register services
	grpcServer := grpc.NewServer()
	proto.RegisterTunnelServiceServer(grpcServer, s)
	logrus.Infof("Starting gRPC server at: %s, target to %s", s.grpcServerAddress, s.targetTcpAddress)
	if err := grpcServer.Serve(listener); err != nil {
		logrus.Fatalln("Unable to start gRPC serve:", err)
	}
}
