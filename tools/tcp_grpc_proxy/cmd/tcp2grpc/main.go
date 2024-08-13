package main

import (
	"flag"
	"fmt"
	"io"
	"net"
	"os"
	"tcp_grpc_proxy/proxy"
)

func test() {
	client, err := net.Dial("tcp", "127.0.0.1:17767")
	if err != nil {
		fmt.Println("err:", err)
		return
	}
	defer client.Close()

	go func() {
		input := make([]byte, 1024)
		for {
			n, err := os.Stdin.Read(input)
			if err != nil {
				fmt.Println("input err:", err)
				continue
			}
			client.Write([]byte(input[:n]))
		}
	}()

	buf := make([]byte, 1024)
	for {
		n, err := client.Read(buf)
		if err != nil {
			if err == io.EOF {
				return
			}
			fmt.Println("read err:", err)
			continue
		}
		fmt.Println(string(buf[:n]))

	}
}

func main() {
	var tcpServerPort int
	var targetGrpcAddress string
	flag.IntVar(&tcpServerPort, "tcp_server_port", 17767, "TCP server port")
	flag.StringVar(&targetGrpcAddress, "target_grpc_address", "127.0.0.1:7766", "The target gRPC server")
	flag.Parse()
	tcpServerAddress := fmt.Sprintf("0.0.0.0:%d", tcpServerPort)

	tcp2grpcServer := proxy.NewTCP2GrpcServer(tcpServerAddress, targetGrpcAddress)
	tcp2grpcServer.Run()
}
