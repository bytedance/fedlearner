package main

import (
	"flag"
	"fmt"
	"tcp_grpc_proxy/proxy"
)

func main() {
	var grpcServerPort int
	var targetTCPAddress string
	flag.IntVar(&grpcServerPort, "grpc_server_port", 7766, "gRPC server port")
	flag.StringVar(&targetTCPAddress, "target_tcp_address", "127.0.0.1:17766", "The target TCP server")
	flag.Parse()
	grpcServerAddress := fmt.Sprintf("0.0.0.0:%d", grpcServerPort)

	grpc2tcpServer := proxy.NewGrpc2TCPServer(grpcServerAddress, targetTCPAddress)
	grpc2tcpServer.Run()
}
