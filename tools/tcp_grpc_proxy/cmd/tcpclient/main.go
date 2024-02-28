package main

import (
	"flag"
	"net"
	"time"

	"github.com/sirupsen/logrus"
)

func main() {
	var tcpServerAddress string
	flag.StringVar(&tcpServerAddress, "tcp_server_address", "127.0.0.1:17767",
		"TCP server address which the client connects to.")

	conn, err := net.Dial("tcp", tcpServerAddress)
	if err != nil {
		logrus.Fatalf("Dail to tcp target %s error: %v", tcpServerAddress, err)
	}
	logrus.Infoln("Connected to", tcpServerAddress)
	// Makes sure the connection gets closed
	defer conn.Close()
	defer logrus.Infoln("Connection closed to ", tcpServerAddress)

	for {
		conn.Write([]byte("hello world"))
		logrus.Infof("Sent 'hello world' to server %s", tcpServerAddress)

		tcpData := make([]byte, 64*1024)
		_, err := conn.Read(tcpData)
		if err != nil {
			logrus.Fatalln("Read from tcp error: ", err)
		}
		logrus.Infof("Received '%s' from server", string(tcpData))

		time.Sleep(time.Duration(5) * time.Second)
	}
}
