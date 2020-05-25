package main

import (
	"flag"
	"fmt"

	"github.com/gin-gonic/gin"
	clientset "k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/clientcmd"
	"k8s.io/klog"

	"github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/apiserver/handler"
	crdclientset "github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/client/clientset/versioned"
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

func buildClientset(masterURL string, kubeConfig string) (*clientset.Clientset, *crdclientset.Clientset, error) {
	config, err := buildConfig(masterURL, kubeConfig)
	if err != nil {
		return nil, nil, err
	}

	kubeClient, err := clientset.NewForConfig(config)
	if err != nil {
		return nil, nil, err
	}

	crdClient, err := crdclientset.NewForConfig(config)
	if err != nil {
		return nil, nil, err
	}

	return kubeClient, crdClient, err
}
func main() {
	flag.Parse()

	stopCh := make(chan struct{}, 1)

	kubeClient, crdClient, err := buildClientset(*master, *kubeConfig)
	if err != nil {
		klog.Fatalf("failed to build clientset, err: %s", err.Error())
	}

	h := handler.NewHandler(kubeClient, crdClient)

	if err := h.Run(stopCh); err != nil {
		klog.Fatalf("failed to run handler, err: %s", err.Error())
	}

	r := gin.Default()

	r.GET("/ping", func(c *gin.Context) {
		c.JSON(200, gin.H{
			"message": "pong",
		})
	})
	r.GET("/namespaces", h.ListNamespaces)
	r.GET("/namespaces/:namespace/pods", h.ListPods)
	r.GET("/namespaces/:namespace/pods/:name", h.GetPod)
	r.GET("/namespaces/:namespace/pods/:name/events", h.ListPodEvents)
	r.GET("/namespaces/:namespace/fedlearner/v1alpha1/flapps", h.ListFLApps)
	r.GET("/namespaces/:namespace/fedlearner/v1alpha1/flapps/:name", h.GetFLApp)
	r.POST("/namespaces/:namespace/fedlearner/v1alpha1/flapps", h.CreateFLApp)
	r.DELETE("/namespaces/:namespace/fedlearner/v1alpha1/flapps/:name", h.DeleteFLApp)
	r.GET("/namespaces/:namespace/fedlearner/v1alpha1/flapps/:name/pods", h.ListFLAppPods)

	if err := r.Run(fmt.Sprintf(":%s", *port)); err != nil {
		klog.Fatalf("run gin engine error, err: %s", err.Error())
	}
}
