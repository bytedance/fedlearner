package main

import (
	"fedlearner.net/tools/tcp_grpc_proxy/pkg/proxy"
	"flag"
	"fmt"
)

func main() {
	var tcpServerPort int
	var targetGrpcAddress string
	flag.IntVar(&tcpServerPort, "tcp_server_port", 17767, "TCP server port")
	flag.StringVar(&targetGrpcAddress, "target_grpc_address", "127.0.0.1:7766", "The target gRPC server")
	flag.Parse()
	tcpServerAddress := fmt.Sprintf("0.0.0.0:%d", tcpServerPort)

	tcp2grpcServer := proxy.NewTcp2GrpcServer(tcpServerAddress, targetGrpcAddress)
	tcp2grpcServer.Run()
}
