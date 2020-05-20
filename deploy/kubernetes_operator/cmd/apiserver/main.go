package main

import (
	"flag"
	"fmt"
	"time"

	"github.com/gin-gonic/gin"
	"k8s.io/client-go/informers"
	clientset "k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/clientcmd"
	"k8s.io/klog"

	"github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/apiserver/handler"
)

var (
	master         = flag.String("master", "", "The address of the Kubernetes API server. Overrides any value in kubeconfig. Only required if out-of-cluster.")
	kubeConfig     = flag.String("kube-config", "", "Path to a kube config. Only required if out-of-cluster.")
	port           = flag.String("port", "8080", "The http port controller listening.")
	resyncInterval = flag.Int("resync-interval", 30, "Informer resync interval in seconds.")
)

func buildConfig(masterURL string, kubeConfig string) (*rest.Config, error) {
	if kubeConfig != "" {
		return clientcmd.BuildConfigFromFlags(masterURL, kubeConfig)
	}

	config, err := rest.InClusterConfig()
	if err != nil {
		return nil, err
	}

	if masterURL != "" {
		config.Host = masterURL
	}

	return config, nil
}

func buildClientset(masterURL string, kubeConfig string) (*clientset.Clientset, error) {
	config, err := buildConfig(masterURL, kubeConfig)
	if err != nil {
		return nil, err
	}

	kubeClient, err := clientset.NewForConfig(config)
	if err != nil {
		return nil, err
	}

	return kubeClient, err
}
func main() {
	flag.Parse()

	stopCh := make(chan struct{}, 1)

	kubeClient, err := buildClientset(*master, *kubeConfig)
	if err != nil {
		klog.Fatalf("failed to build clientset, err: %s", err.Error())
	}

	informerFactory := informers.NewSharedInformerFactoryWithOptions(
		kubeClient,
		time.Duration(*resyncInterval)*time.Second,
	)

	go informerFactory.Start(stopCh)

	h := handler.NewHandler(informerFactory)
	if err := h.Run(stopCh); err != nil {
		klog.Fatalf("failed to run handler, err: %s", err.Error())
	}

	r := gin.Default()

	r.GET("/ping", func(c *gin.Context) {
		c.JSON(200, gin.H{
			"message": "pong",
		})
	})
	r.GET("/namespaces/:namespace/pods", h.ListPods)
	r.GET("/namespaces/:namespace/pods/:name", h.GetPod)

	if err := r.Run(fmt.Sprintf(":%s", *port)); err != nil {
		klog.Fatalf("run gin engine error, err: %s", err.Error())
	}
}
