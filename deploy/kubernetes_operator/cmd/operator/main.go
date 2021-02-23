/* Copyright 2020 The FedLearner Authors. All Rights Reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package main

import (
	"context"
	"flag"
	"fmt"
	"net/http"
	"net/http/pprof"
	"os"
	"os/signal"
	"syscall"
	"time"

	apiv1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/util/uuid"
	"k8s.io/client-go/informers"
	clientset "k8s.io/client-go/kubernetes"
	"k8s.io/client-go/kubernetes/scheme"
	typedcorev1 "k8s.io/client-go/kubernetes/typed/core/v1"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/clientcmd"
	"k8s.io/client-go/tools/leaderelection"
	"k8s.io/client-go/tools/leaderelection/resourcelock"
	"k8s.io/client-go/tools/record"
	"k8s.io/klog"

	"github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/apis/fedlearner.k8s.io/v1alpha1"
	crdclientset "github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/client/clientset/versioned"
	crdinformers "github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/client/informers/externalversions"
	"github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/operator"
	"github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/server"
)

type config struct {
	master                      string
	kubeConfig                  string
	port                        string
	debugPort                   string
	workerNum                   int
	resyncInterval              int
	namespace                   string
	qps                         float64
	burst                       int
	ingressExtraHostSuffix      string
	ingressSecretName           string
	ingressEnableClientAuth     bool
	ingressClientAuthSecretName string
	enableLeaderElection        bool
	leaderElectionLockNamespace string
	leaderElectionLockName      string
	leaderElectionLeaseDuration time.Duration
	leaderElectionRenewDeadline time.Duration
	leaderElectionRetryPeriod   time.Duration
	grpcClientTimeout           time.Duration
}

func newConfig() *config {
	config := config{}
	config.port = "8080"
	config.debugPort = "8081"
	config.workerNum = 10
	config.resyncInterval = 30
	config.namespace = "default"
	config.qps = 20.0
	config.burst = 30
	config.leaderElectionLockNamespace = "fedlearner-system"
	config.leaderElectionLockName = "fedlearner-kubernetes-operator-lock"
	config.leaderElectionLeaseDuration = 15 * time.Second
	config.leaderElectionRenewDeadline = 5 * time.Second
	config.leaderElectionRetryPeriod = 4 * time.Second
	config.grpcClientTimeout = 15 * time.Second
	return &config
}

func initFlags() *config {
	fl := flag.NewFlagSet(os.Args[0], flag.ExitOnError)
	config := newConfig()
	fl.StringVar(&config.master, "master", config.master, "The address of the Kubernetes API server. Overrides any value in kubeconfig. Only required if out-of-cluster.")
	fl.StringVar(&config.kubeConfig, "kube-config", config.kubeConfig, "Path to a kube config. Only required if out-of-cluster.")
	fl.StringVar(&config.port, "port", config.port, "The http port controller listening.")
	fl.StringVar(&config.debugPort, "debug-port", config.debugPort, "The debug http port controller listening.")
	fl.IntVar(&config.workerNum, "worker-num", config.workerNum, "Number of worker threads used by the fedlearner controller.")
	fl.IntVar(&config.resyncInterval, "resync-interval", config.resyncInterval, "Informer resync interval in seconds.")
	fl.StringVar(&config.namespace, "namespace", config.namespace, "The namespace to which controller listen FLApps.")
	fl.Float64Var(&config.qps, "qps", config.qps, "The clientset config QPS")
	fl.IntVar(&config.burst, "burst", config.burst, "The clientset config Burst")
	fl.StringVar(&config.ingressExtraHostSuffix, "ingress-extra-host-suffix", config.ingressExtraHostSuffix, "The extra suffix of hosts when creating ingress.")
	fl.StringVar(&config.ingressSecretName, "ingress-secret-name", config.ingressSecretName, "The secret name used for tls, only one secret supported now.")
	fl.BoolVar(&config.ingressEnableClientAuth, "ingress-enabled-client-auth", config.ingressEnableClientAuth, "Whether enable client auth for created ingress.")
	fl.StringVar(&config.ingressClientAuthSecretName, "ingress-client-auth-secret-name", config.ingressClientAuthSecretName, "The secret name used for client auth, only one secret supported now.")
	fl.BoolVar(&config.enableLeaderElection, "leader-election", config.enableLeaderElection, "Enable fedlearner controller leader election.")
	fl.StringVar(&config.leaderElectionLockNamespace, "leader-election-lock-namespace", config.leaderElectionLockNamespace, "Namespace in which to create the Endpoints for leader election.")
	fl.StringVar(&config.leaderElectionLockName, "leader-election-lock-name", config.leaderElectionLockName, "Name of the Endpoint for leader election.")
	fl.DurationVar(&config.leaderElectionLeaseDuration, "leader-election-lease-duration", config.leaderElectionLeaseDuration, "Leader election lease duration.")
	fl.DurationVar(&config.leaderElectionRenewDeadline, "leader-election-renew-deadline", config.leaderElectionRenewDeadline, "Leader election renew deadline.")
	fl.DurationVar(&config.leaderElectionRetryPeriod, "leader-election-retry-period", config.leaderElectionRetryPeriod, "Leader election retry period.")
	fl.DurationVar(&config.grpcClientTimeout, "grpc-client-timeout", config.grpcClientTimeout, "GRPC Client timetout")
	klog.InitFlags(fl)
	fl.Parse(os.Args[1:])
	return config
}

func buildConfig(masterURL string, kubeConfig string, qps float32, burst int) (*rest.Config, error) {
	if kubeConfig != "" {
		return clientcmd.BuildConfigFromFlags(masterURL, kubeConfig)
	}
	config, err := rest.InClusterConfig()
	if err != nil {
		return nil, err
	}
	config.QPS = qps
	config.Burst = burst
	klog.V(6).Infof("clientset config = %v", config)

	if masterURL != "" {
		config.Host = masterURL
	}
	return config, nil
}

func buildClientset(masterURL string, kubeConfig string, qps float64, burst int) (*clientset.Clientset, *crdclientset.Clientset, error) {
	config, err := buildConfig(masterURL, kubeConfig, float32(qps), burst)
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

func startLeaderElection(
	config *config,
	kubeClient *clientset.Clientset,
	recorder record.EventRecorder,
	startCh chan struct{},
	stopCh chan struct{},
) {
	hostName, err := os.Hostname()
	if err != nil {
		klog.Error("failed to get hostname")
		return
	}
	hostName = hostName + "_" + string(uuid.NewUUID())

	resourceLock, err := resourcelock.New(resourcelock.EndpointsResourceLock,
		config.leaderElectionLockNamespace,
		config.leaderElectionLockName,
		kubeClient.CoreV1(),
		nil,
		resourcelock.ResourceLockConfig{
			Identity:      hostName,
			EventRecorder: recorder,
		})
	if err != nil {
		return
	}

	electionCfg := leaderelection.LeaderElectionConfig{
		Lock:          resourceLock,
		LeaseDuration: config.leaderElectionLeaseDuration,
		RenewDeadline: config.leaderElectionRenewDeadline,
		RetryPeriod:   config.leaderElectionRetryPeriod,
		Callbacks: leaderelection.LeaderCallbacks{
			OnStartedLeading: func(c context.Context) {
				close(startCh)
			},
			OnStoppedLeading: func() {
				close(stopCh)
			},
		},
	}
	elector, err := leaderelection.NewLeaderElector(electionCfg)
	if err != nil {
		klog.Fatal(err)
	}

	go elector.Run(context.Background())
}

func main() {
	config := initFlags()

	kubeClient, crdClient, err := buildClientset(config.master, config.kubeConfig, config.qps, config.burst)
	if err != nil {
		klog.Fatalf("failed to build clientset, err = %v", err)
	}
	if err := v1alpha1.AddToScheme(scheme.Scheme); err != nil {
		klog.Fatalf("Failed to add flapp scheme: %v", err)
	}

	signalCh := make(chan os.Signal, 1)
	signal.Notify(signalCh, syscall.SIGINT, syscall.SIGTERM)
	stopCh := make(chan struct{}, 1)
	startCh := make(chan struct{}, 1)

	eventBroadcaster := record.NewBroadcaster()
	eventBroadcaster.StartLogging(klog.Infof)
	eventBroadcaster.StartRecordingToSink(&typedcorev1.EventSinkImpl{
		Interface: kubeClient.CoreV1().Events(""),
	})
	recorder := eventBroadcaster.NewRecorder(scheme.Scheme, apiv1.EventSource{Component: "fedlearner-operator"})

	if config.namespace == metav1.NamespaceAll {
		klog.Fatalf("cluster scoped operator is not supported")
	}
	klog.Infof("scoping operator to namespace %s", config.namespace)

	kubeInformerFactory := informers.NewSharedInformerFactoryWithOptions(
		kubeClient,
		time.Duration(config.resyncInterval)*time.Second,
		informers.WithNamespace(config.namespace),
	)
	crdInformerFactory := crdinformers.NewSharedInformerFactoryWithOptions(
		crdClient,
		time.Duration(config.resyncInterval)*time.Second,
		crdinformers.WithNamespace(config.namespace),
	)

	appEventHandler := operator.NewAppEventHandlerWithClientTimeout(config.namespace, crdClient, config.grpcClientTimeout)
	flController := operator.NewFLController(
		config.namespace,
		recorder,
		config.resyncInterval,
		config.ingressExtraHostSuffix,
		config.ingressSecretName,
		config.ingressEnableClientAuth,
		config.ingressClientAuthSecretName,
		kubeClient,
		crdClient,
		kubeInformerFactory,
		crdInformerFactory,
		appEventHandler,
		stopCh)

	go func() {
		klog.Infof("starting adapter listening %v", config.port)
		server.ServeGrpc("0.0.0.0", config.port, appEventHandler)
	}()
	go func() {
		mux := http.NewServeMux()
		mux.HandleFunc("/debug/pprof/", pprof.Index)
		mux.HandleFunc("/debug/pprof/cmdline", pprof.Cmdline)
		mux.HandleFunc("/debug/pprof/profile", pprof.Profile)
		mux.HandleFunc("/debug/pprof/symbol", pprof.Symbol)
		mux.HandleFunc("/debug/pprof/trace", pprof.Trace)
		klog.Fatal(http.ListenAndServe(fmt.Sprintf("0.0.0.0:%s", config.debugPort), mux))
	}()

	if config.enableLeaderElection {
		startLeaderElection(config, kubeClient, recorder, startCh, stopCh)
	}

	klog.Info("starting the fedlearner operator")
	if config.enableLeaderElection {
		klog.Info("waiting to be elected leader before starting application controller goroutines")
		<-startCh
	}

	go kubeInformerFactory.Start(stopCh)
	go crdInformerFactory.Start(stopCh)

	klog.Info("starting application controller goroutines")
	if err := flController.Start(config.workerNum); err != nil {
		klog.Fatal(err)
	}

	select {
	case <-signalCh:
		close(stopCh)
	case <-stopCh:
	}

	klog.Info("shutting down the fedlearner kubernetes operator")
	flController.Stop()
}
