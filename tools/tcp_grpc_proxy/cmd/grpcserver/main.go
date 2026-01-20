package main

import (
	"tcp_grpc_proxy/grpc2tcp"
)

func main() {
	grpcServerAddress := "0.0.0.0:7766"
	targetTCPAddress := "127.0.0.1:17766"
	grpc2tcp.RunServer(grpcServerAddress, targetTCPAddress)
}
