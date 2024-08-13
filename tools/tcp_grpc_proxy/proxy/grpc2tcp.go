package proxy

import (
	"fmt"
	"io"
	"net"

	"tcp_grpc_proxy/proxy/proto"

	"github.com/sirupsen/logrus"
	"google.golang.org/grpc"
)

// Grpc2TCPServer A server to proxy grpc traffic to TCP
type Grpc2TCPServer struct {
	proto.UnimplementedTunnelServiceServer
	grpcServerAddress string
	targetTCPAddress  string
}

// Tunnel the implementation of gRPC Tunnel service
func (s *Grpc2TCPServer) Tunnel(stream proto.TunnelService_TunnelServer) error {
	tcpConnection, err := net.Dial("tcp", s.targetTCPAddress)
	if err != nil {
		logrus.Errorf("Dail to tcp target %s error: %v", s.targetTCPAddress, err)
		return err
	}
	logrus.Infoln("Connected to", s.targetTCPAddress)
	// Makes sure the connection gets closed
	defer tcpConnection.Close()
	defer logrus.Infoln("Connection closed to ", s.targetTCPAddress)

	errChan := make(chan error)

	// Gets data from gRPC client and proxy to remote TCP server
	go func() {
		for {
			chunk, err := stream.Recv()
			if err == io.EOF {
				return
			}
			if err != nil {
				errChan <- fmt.Errorf("error while receiving gRPC data: %v", err)
				return
			}

			data := chunk.Data
			logrus.Infof("Sending %d bytes to tcp server", len(data))
			_, err = tcpConnection.Write(data)
			if err != nil {
				errChan <- fmt.Errorf("error while sending TCP data: %v", err)
				return
			}
		}
	}()

	// Gets data from remote TCP server and proxy to gRPC client
	go func() {
		buff := make([]byte, 64*1024)
		for {
			bytesRead, err := tcpConnection.Read(buff)
			if err == io.EOF {
				logrus.Infoln("Remote TCP connection closed")
				return
			}
			if err != nil {
				errChan <- fmt.Errorf("error while receiving TCP data: %v", err)
				return
			}

			logrus.Infof("Sending %d bytes to gRPC client", bytesRead)
			if err = stream.Send(&proto.Chunk{Data: buff[0:bytesRead]}); err != nil {
				errChan <- fmt.Errorf("Error while sending gRPC data: %v", err)
				return
			}
		}
	}()

	// Blocking read
	returnedError := <-errChan
	return returnedError
}

// NewGrpc2TCPServer constructs a Grpc2TCP server
func NewGrpc2TCPServer(grpcServerAddress, targetTCPAddress string) *Grpc2TCPServer {
	return &Grpc2TCPServer{
		grpcServerAddress: grpcServerAddress,
		targetTCPAddress:  targetTCPAddress,
	}
}

// Run starts the Grpc2TCP server
func (s *Grpc2TCPServer) Run() {
	listener, err := net.Listen("tcp", s.grpcServerAddress)
	if err != nil {
		logrus.Errorf("Failed to listen: ", err)
	}

	// Starts a gRPC server and register services
	grpcServer := grpc.NewServer()
	proto.RegisterTunnelServiceServer(grpcServer, s)
	logrus.Infof("Starting gRPC server at: %s, target to %s", s.grpcServerAddress, s.targetTCPAddress)
	if err := grpcServer.Serve(listener); err != nil {
		logrus.Errorln("Unable to start gRPC serve:", err)
	}
}
