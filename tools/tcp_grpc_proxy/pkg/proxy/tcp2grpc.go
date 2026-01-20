package proxy

import (
	"context"
	"io"
	"net"
	"sync"

	"fedlearner.net/tools/tcp_grpc_proxy/pkg/proto"
	"github.com/sirupsen/logrus"
	"google.golang.org/grpc"
)

// Tcp2GrpcServer to proxy TCP traffic to gRPC
type Tcp2GrpcServer struct {
	tcpServerAddress  string
	targetGrpcAddress string
}

// NewTcp2GrpcServer constructs a TCP2GrpcServer
func NewTcp2GrpcServer(tcpServerAddress, targetGrpcAddress string) *Tcp2GrpcServer {
	return &Tcp2GrpcServer{
		tcpServerAddress:  tcpServerAddress,
		targetGrpcAddress: targetGrpcAddress,
	}
}

func handleTcpConnection(tcpConn net.Conn, targetGrpcAddress string) {
	contextLogger := logrus.WithFields(logrus.Fields{
		"prefix": "[TCP2GRPC]",
		"tcp_client_addr": tcpConn.RemoteAddr().String(),
	})

	contextLogger.Infoln("Handle tcp connection, target to:", targetGrpcAddress)
	defer tcpConn.Close()

	grpcConn, err := grpc.Dial(targetGrpcAddress, grpc.WithInsecure())
	if err != nil {
		contextLogger.Errorf("Failed to connect to grpc %s: %v\n", targetGrpcAddress, err)
		return
	}
	defer grpcConn.Close()

	grpcClient := proto.NewTunnelServiceClient(grpcConn)
	stream, err := grpcClient.Tunnel(context.Background())
	if err != nil {
		contextLogger.Errorln("Error of tunnel service:", err)
		return
	}

	var wg sync.WaitGroup

	// Gets data from remote gRPC server and proxy to TCP client
	wg.Add(1)
	go func() {
		defer wg.Done()

		tcpSentBytes := 0
		grpcReceivedBytes := 0
		defer func() {
			contextLogger.Infof("gRPC received %d bytes, TCP sent %d byte", grpcReceivedBytes, tcpSentBytes)
		}()

		for {
			chunk, err := stream.Recv()
			if err == io.EOF {
				contextLogger.Infoln("gRpc server EOF")
				tcpConn.Close()
				return
			}
			if err != nil {
				contextLogger.Errorf("Recv from grpc target %s terminated: %v", targetGrpcAddress, err)
				tcpConn.Close()
				return
			}
			grpcReceivedBytes += len(chunk.Data)

			contextLogger.Debugln("Sending %d bytes to TCP client", len(chunk.Data))
			_, err = tcpConn.Write(chunk.Data)
			if err != nil {
				contextLogger.Errorln("Failed to send data to TCP client:", err)
				return
			} else {
				tcpSentBytes += len(chunk.Data)
			}
		}
	}()

	// Gets data from TCP client and proxy to remote gRPC server
	wg.Add(1)
	go func() {
		defer wg.Done()

		tcpReceivedBytes := 0
		grpcSentBytes := 0
		defer func() {
			contextLogger.Infof("TCP received %d bytes, gRPC sent %d bytes", tcpReceivedBytes, grpcSentBytes)
		}()

		tcpData := make([]byte, 64*1024)
		for {
			bytesRead, err := tcpConn.Read(tcpData)

			if err == io.EOF {
				contextLogger.Infoln("Connection finished")
				stream.CloseSend()
				return
			}
			if err != nil {
				contextLogger.Errorln("Read from tcp error:", err)
				stream.CloseSend()
				return
			}
			tcpReceivedBytes += bytesRead

			contextLogger.Debugln("Sending %d bytes to gRPC server", bytesRead)
			err = stream.Send(&proto.Chunk{Data: tcpData[0:bytesRead]})
			if err != nil {
				contextLogger.Errorln("Failed to send gRPC data:", err)
				return
			}  else {
				grpcSentBytes += bytesRead
			}
		}
	}()

	wg.Wait()
}

// Run Starts the server
func (s *Tcp2GrpcServer) Run() {
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
		go handleTcpConnection(conn, s.targetGrpcAddress)
	}
}
