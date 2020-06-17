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
	"github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/controller"
	"github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/server"
)

var (
	master                      = flag.String("master", "", "The address of the Kubernetes API server. Overrides any value in kubeconfig. Only required if out-of-cluster.")
	kubeConfig                  = flag.String("kube-config", "", "Path to a kube config. Only required if out-of-cluster.")
	port                        = flag.String("port", "8080", "The http port controller listening.")
	debugPort                   = flag.String("debug-port", "8081", "The debug http port controller listening.")
	workerNum                   = flag.Int("worker-num", 10, "Number of worker threads used by the fedlearner controller.")
	resyncInterval              = flag.Int("resync-interval", 30, "Informer resync interval in seconds.")
	namespace                   = flag.String("namespace", "default", "The namespace to which controller listen FLApps.")
	enableLeaderElection        = flag.Bool("leader-election", false, "Enable fedlearner controller leader election.")
	leaderElectionLockNamespace = flag.String("leader-election-lock-namespace", "fedlearner-system", "Namespace in which to create the Endpoints for leader election.")
	leaderElectionLockName      = flag.String("leader-election-lock-name", "fedlearner-kubernetes-operator-lock", "Name of the Endpoint for leader election.")
	leaderElectionLeaseDuration = flag.Duration("leader-election-lease-duration", 15*time.Second, "Leader election lease duration.")
	leaderElectionRenewDeadline = flag.Duration("leader-election-renew-deadline", 5*time.Second, "Leader election renew deadline.")
	leaderElectionRetryPeriod   = flag.Duration("leader-election-retry-period", 4*time.Second, "Leader election retry period.")
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

func startLeaderElection(
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
		*leaderElectionLockNamespace,
		*leaderElectionLockName,
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
		LeaseDuration: *leaderElectionLeaseDuration,
		RenewDeadline: *leaderElectionRenewDeadline,
		RetryPeriod:   *leaderElectionRetryPeriod,
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
	flag.Parse()

	kubeClient, crdClient, err := buildClientset(*master, *kubeConfig)
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

	if *namespace == metav1.NamespaceAll {
		klog.Fatalf("cluster scoped operator is not supported")
	}
	klog.Infof("scoping operator to namespace %s", *namespace)

	kubeInformerFactory := informers.NewSharedInformerFactoryWithOptions(
		kubeClient,
		time.Duration(*resyncInterval)*time.Second,
		informers.WithNamespace(*namespace),
	)
	crdInformerFactory := crdinformers.NewSharedInformerFactoryWithOptions(
		crdClient,
		time.Duration(*resyncInterval)*time.Second,
		crdinformers.WithNamespace(*namespace),
	)

	appEventHandler := controller.NewAppEventHandler(*namespace, crdClient)
	flController := controller.NewFLController(*namespace, recorder, *resyncInterval, kubeClient, crdClient, kubeInformerFactory, crdInformerFactory, appEventHandler, stopCh)

	go func() {
		klog.Infof("starting adapter listening %v", *port)
		server.ServeGrpc("0.0.0.0", *port, appEventHandler)
	}()
	go func() {
		mux := http.NewServeMux()
		mux.HandleFunc("/debug/pprof/", pprof.Index)
		mux.HandleFunc("/debug/pprof/cmdline", pprof.Cmdline)
		mux.HandleFunc("/debug/pprof/profile", pprof.Profile)
		mux.HandleFunc("/debug/pprof/symbol", pprof.Symbol)
		mux.HandleFunc("/debug/pprof/trace", pprof.Trace)
		klog.Fatal(http.ListenAndServe(fmt.Sprintf("0.0.0.0:%s", *debugPort), mux))
	}()

	if *enableLeaderElection {
		startLeaderElection(kubeClient, recorder, startCh, stopCh)
	}

	klog.Info("starting the fedlearner operator")
	if *enableLeaderElection {
		klog.Info("waiting to be elected leader before starting application controller goroutines")
		<-startCh
	}

	go kubeInformerFactory.Start(stopCh)
	go crdInformerFactory.Start(stopCh)

	klog.Info("starting application controller goroutines")
	if err := flController.Start(*workerNum); err != nil {
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
