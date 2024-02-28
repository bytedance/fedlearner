package main

import (
	"bytes"
	"context"
	"os"
	"time"

	"tcp_grpc_proxy/proto"

	"github.com/sirupsen/logrus"
	"google.golang.org/grpc"
)

func main() {
	// Set up a connection to the server.
	grpcServer := "127.0.0.1:7766"
	conn, err := grpc.Dial(grpcServer, grpc.WithInsecure())
	if err != nil {
		logrus.Fatalf("did not connect: %v", err)
	}
	defer conn.Close()
	tsc := proto.NewTunnelServiceClient(conn)

	tc, err := tsc.Tunnel(context.Background())
	if err != nil {
		logrus.Fatalln(err)
	}

	sendPacket := func(data []byte) error {
		return tc.Send(&proto.Chunk{Data: data})
	}

	go func() {
		for {
			chunk, err := tc.Recv()
			if err != nil {
				logrus.Println("Recv terminated:", err)
				os.Exit(0)
			}
			logrus.Println(string(chunk.Data))
		}

	}()

	for {
		time.Sleep(time.Duration(2) * time.Second)
		buf := bytes.NewBufferString("************Hello World**********").Bytes()
		sendPacket(buf)
	}
}
