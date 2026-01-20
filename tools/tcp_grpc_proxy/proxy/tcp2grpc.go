package proxy

import (
	"context"
	"io"
	"net"
	"tcp_grpc_proxy/proxy/proto"

	"github.com/sirupsen/logrus"
	"google.golang.org/grpc"
)

// TCP2GrpcServer to proxy TCP traffic to gRPC
type TCP2GrpcServer struct {
	tcpServerAddress  string
	targetGrpcAddress string
}

// NewTCP2GrpcServer constructs a TCP2GrpcServer
func NewTCP2GrpcServer(tcpServerAddress, targetGrpcAddress string) *TCP2GrpcServer {
	return &TCP2GrpcServer{
		tcpServerAddress:  tcpServerAddress,
		targetGrpcAddress: targetGrpcAddress,
	}
}

func handleTCPConn(tcpConn net.Conn, targetGrpcAddress string) {
	logrus.Infoln("Handle tcp connection, target to:", targetGrpcAddress)
	defer tcpConn.Close()

	grpcConn, err := grpc.Dial(targetGrpcAddress, grpc.WithInsecure())
	if err != nil {
		logrus.Errorf("Error during connect to grpc %s: %v", targetGrpcAddress, err)
		return
	}
	defer grpcConn.Close()

	grpcClient := proto.NewTunnelServiceClient(grpcConn)
	stream, err := grpcClient.Tunnel(context.Background())
	if err != nil {
		logrus.Errorf("Error of tunnel service: %v", err)
		return
	}

	// Gets data from remote gRPC server and proxy to TCP client
	go func() {
		for {
			chunk, err := stream.Recv()
			if err != nil {
				logrus.Errorf("Recv from grpc target %s terminated: %v", targetGrpcAddress, err)
				return
			}
			logrus.Infof("Sending %d bytes to TCP client", len(chunk.Data))
			tcpConn.Write(chunk.Data)
		}
	}()

	// Gets data from TCP client and proxy to remote gRPC server
	func() {
		for {
			tcpData := make([]byte, 64*1024)
			bytesRead, err := tcpConn.Read(tcpData)

			if err == io.EOF {
				logrus.Infoln("Connection finished")
				return
			}
			if err != nil {
				logrus.Errorf("Read from tcp error: %v", err)
				return
			}
			logrus.Infof("Sending %d bytes to gRPC server", bytesRead)
			if err := stream.Send(&proto.Chunk{Data: tcpData[0:bytesRead]}); err != nil {
				logrus.Errorf("Failed to send gRPC data: %v", err)
				return
			}
		}
	}()

	// If tcp connection gets closed, then we close the gRPC connection.
	stream.CloseSend()
	return
}

// Run Starts the server
func (s *TCP2GrpcServer) Run() {
	listener, err := net.Listen("tcp", s.tcpServerAddress)
	if err != nil {
		logrus.Fatalln("Listen TCP error: ", err)
	}
	defer listener.Close()
	logrus.Infoln("Run TCPServer at ", s.tcpServerAddress)

	for {
		conn, err := listener.Accept()
		if err != nil {
			logrus.Errorln("TCP listener error:", err)
			continue
		}

		logrus.Infoln("Got tcp connection")
		go handleTCPConn(conn, s.targetGrpcAddress)
	}
}
