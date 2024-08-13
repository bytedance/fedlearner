install:
	go get tcp_grpc_proxy
	go mod download

protobuf: install
	go install google.golang.org/protobuf/cmd/protoc-gen-go@v1.26
	go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@v1.1
	PATH="${PATH}:$(shell go env GOPATH)/bin" \
		protoc -I=proto --go_out=. --go-grpc_out=. proto/*.proto

build: protobuf
	go build -o tcp2grpc cmd/tcp2grpc/main.go
	go build -o grpc2tcp cmd/grpc2tcp/main.go
