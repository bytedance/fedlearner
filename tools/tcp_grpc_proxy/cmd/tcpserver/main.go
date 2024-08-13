package main

import (
	"flag"
	"fmt"
	"net"

	"github.com/sirupsen/logrus"
)

func handleTCPConn(conn net.Conn) {
	for {
		tcpData := make([]byte, 64*1024)
		bytesRead, err := conn.Read(tcpData)
		if err != nil {
			logrus.Fatalln("Read from tcp error: ", err)
		}
		logrus.Infof("TCP server got %d bytes", bytesRead)
		conn.Write([]byte("This is a string from TCP server"))
	}
}

func main() {
	var tcpServerPort int
	flag.IntVar(&tcpServerPort, "tcp_server_port", 17766, "TCP server port")
	flag.Parse()
	tcpServerAddress := fmt.Sprintf("0.0.0.0:%d", tcpServerPort)

	listener, err := net.Listen("tcp", tcpServerAddress)
	if err != nil {
		logrus.Fatalln("Listen TCP error: ", err)
	}
	defer listener.Close()
	logrus.Infoln("Run TCPServer at ", tcpServerAddress)

	for {
		conn, err := listener.Accept()
		if err != nil {
			logrus.Errorln("TCP listener error:", err)
			continue
		}

		logrus.Infoln("Got tcp connection")
		go handleTCPConn(conn)
	}
}
