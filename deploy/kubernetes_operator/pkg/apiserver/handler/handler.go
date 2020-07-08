package handler

import (
	"fmt"
	"net/http"

	"github.com/gin-gonic/gin"
	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	networkingv1beta1 "k8s.io/api/networking/v1beta1"
	"k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/fields"
	"k8s.io/apimachinery/pkg/runtime/schema"
	"k8s.io/apimachinery/pkg/util/validation/field"
	clientset "k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/cache"
	"k8s.io/client-go/tools/remotecommand"

	"github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/apis/fedlearner.k8s.io/v1alpha1"
	crdclientset "github.com/bytedance/fedlearner/deploy/kubernetes_operator/pkg/client/clientset/versioned"
)

// Handler .
type Handler struct {
	restConfig *rest.Config
	kubeClient *clientset.Clientset
	crdClient  *crdclientset.Clientset
}

// NewHandler returns a new handler.
func NewHandler(
	restConfig *rest.Config,
	kubeClient *clientset.Clientset,
	crdClientset *crdclientset.Clientset,
) *Handler {
	return &Handler{
		restConfig: restConfig,
		kubeClient: kubeClient,
		crdClient:  crdClientset,
	}
}

// Run .
func (h *Handler) Run(stopCh <-chan struct{}) error {
	if !cache.WaitForCacheSync(stopCh) {
		return fmt.Errorf("timed out waiting for cache to sync")
	}

	return nil
}

// ListNamespaces .
func (h *Handler) ListNamespaces(c *gin.Context) {
	namespaces, err := h.kubeClient.CoreV1().Namespaces().List(metav1.ListOptions{})
	if err != nil {
		h.handleError(c, err)
		return
	}

	c.JSON(200, gin.H{
		"namespaces": namespaces,
	})
}

// ListPods returns pods in namespace.
func (h *Handler) ListPods(c *gin.Context) {
	namespace := c.Param("namespace")

	pods, err := h.kubeClient.CoreV1().Pods(namespace).List(metav1.ListOptions{})
	if err != nil {
		h.handleError(c, err)
		return
	}

	c.JSON(200, gin.H{
		"pods": pods,
	})
}

// GetPod returns a pod with name.
func (h *Handler) GetPod(c *gin.Context) {
	namespace := c.Param("namespace")
	name := c.Param("name")

	pod, err := h.kubeClient.CoreV1().Pods(namespace).Get(name, metav1.GetOptions{})
	if err != nil {
		h.handleError(c, err)
		return
	}

	c.JSON(200, gin.H{
		"pod": pod,
	})
}

// ListPodEvents returns pod's events.
func (h *Handler) ListPodEvents(c *gin.Context) {
	namespace := c.Param("namespace")
	name := c.Param("name")

	events, err := h.kubeClient.CoreV1().Events(namespace).List(metav1.ListOptions{
		FieldSelector: fields.OneTermEqualSelector("involvedObject.name", name).String(),
	})
	if err != nil {
		h.handleError(c, err)
		return
	}

	c.JSON(200, gin.H{
		"events": events,
	})
}

// ListServices returns services in namespace.
func (h *Handler) ListServices(c *gin.Context) {
	namespace := c.Param("namespace")

	services, err := h.kubeClient.CoreV1().Services(namespace).List(metav1.ListOptions{})
	if err != nil {
		h.handleError(c, err)
		return
	}

	c.JSON(200, gin.H{
		"services": services,
	})
}

// GetService returns a service with name.
func (h *Handler) GetService(c *gin.Context) {
	namespace := c.Param("namespace")
	name := c.Param("name")

	service, err := h.kubeClient.CoreV1().Services(namespace).Get(name, metav1.GetOptions{})
	if err != nil {
		h.handleError(c, err)
		return
	}

	c.JSON(200, gin.H{
		"service": service,
	})
}

// CreateService create a service.
func (h *Handler) CreateService(c *gin.Context) {
	namespace := c.Param("namespace")

	service := &corev1.Service{}
	if err := c.BindJSON(&service); err != nil {
		h.handleError(c, err)
		return
	}

	newService, err := h.kubeClient.CoreV1().Services(namespace).Create(service)
	if err != nil {
		h.handleError(c, err)
		return
	}

	c.JSON(201, gin.H{
		"service": newService,
	})
}

// DeleteService delete a service with name.
func (h *Handler) DeleteService(c *gin.Context) {
	namespace := c.Param("namespace")
	name := c.Param("name")

	if err := h.kubeClient.CoreV1().Services(namespace).Delete(name, &metav1.DeleteOptions{}); err != nil {
		h.handleError(c, err)
		return
	}

	c.JSON(200, gin.H{})
}

// ListSecrets returns secrets in namespace.
func (h *Handler) ListSecrets(c *gin.Context) {
	namespace := c.Param("namespace")

	secrets, err := h.kubeClient.CoreV1().Secrets(namespace).List(metav1.ListOptions{})
	if err != nil {
		h.handleError(c, err)
		return
	}

	c.JSON(200, gin.H{
		"secrets": secrets,
	})
}

// GetSecret returns a secret with name.
func (h *Handler) GetSecret(c *gin.Context) {
	namespace := c.Param("namespace")
	name := c.Param("name")

	secret, err := h.kubeClient.CoreV1().Secrets(namespace).Get(name, metav1.GetOptions{})
	if err != nil {
		h.handleError(c, err)
		return
	}

	c.JSON(200, gin.H{
		"secret": secret,
	})
}

// CreateSecret create a secret.
func (h *Handler) CreateSecret(c *gin.Context) {
	namespace := c.Param("namespace")

	secret := &corev1.Secret{}
	if err := c.BindJSON(&secret); err != nil {
		h.handleError(c, err)
		return
	}

	newSecret, err := h.kubeClient.CoreV1().Secrets(namespace).Create(secret)
	if err != nil {
		h.handleError(c, err)
		return
	}

	c.JSON(201, gin.H{
		"secret": newSecret,
	})
}

// DeleteSecret delete a secret with name.
func (h *Handler) DeleteSecret(c *gin.Context) {
	namespace := c.Param("namespace")
	name := c.Param("name")

	if err := h.kubeClient.CoreV1().Secrets(namespace).Delete(name, &metav1.DeleteOptions{}); err != nil {
		h.handleError(c, err)
		return
	}

	c.JSON(200, gin.H{})
}

// ListDeployments returns services in namespace.
func (h *Handler) ListDeployments(c *gin.Context) {
	namespace := c.Param("namespace")

	deployments, err := h.kubeClient.AppsV1().Deployments(namespace).List(metav1.ListOptions{})
	if err != nil {
		h.handleError(c, err)
		return
	}

	c.JSON(200, gin.H{
		"deployments": deployments,
	})
}

// GetDeployment returns a deloyment with name.
func (h *Handler) GetDeployment(c *gin.Context) {
	namespace := c.Param("namespace")
	name := c.Param("name")

	deployment, err := h.kubeClient.AppsV1().Deployments(namespace).Get(name, metav1.GetOptions{})
	if err != nil {
		h.handleError(c, err)
		return
	}

	c.JSON(200, gin.H{
		"deployment": deployment,
	})
}

// CreateDeployment create a deployment.
func (h *Handler) CreateDeployment(c *gin.Context) {
	namespace := c.Param("namespace")

	deployment := &appsv1.Deployment{}
	if err := c.BindJSON(&deployment); err != nil {
		h.handleError(c, err)
		return
	}

	newDeployment, err := h.kubeClient.AppsV1().Deployments(namespace).Create(deployment)
	if err != nil {
		h.handleError(c, err)
		return
	}

	c.JSON(201, gin.H{
		"deployment": newDeployment,
	})
}

// UpdateDeployment update a deployment.
func (h *Handler) UpdateDeployment(c *gin.Context) {
	namespace := c.Param("namespace")
	name := c.Param("name")

	deployment := &appsv1.Deployment{}
	if err := c.BindJSON(&deployment); err != nil {
		h.handleError(c, err)
		return
	}

	if name != deployment.Name {
		err := errors.NewInvalid(schema.GroupKind{Kind: "Deployment"}, name, field.ErrorList{field.Invalid(field.NewPath("Name"), nil, "in url must be the same with deployment name.")})
		h.handleError(c, err)
		return
	}

	newDeployment, err := h.kubeClient.AppsV1().Deployments(namespace).Update(deployment)
	if err != nil {
		h.handleError(c, err)
		return
	}

	c.JSON(201, gin.H{
		"deployment": newDeployment,
	})
}

// DeleteDeployment delete a deployment with name.
func (h *Handler) DeleteDeployment(c *gin.Context) {
	namespace := c.Param("namespace")
	name := c.Param("name")

	if err := h.kubeClient.AppsV1().Deployments(namespace).Delete(name, &metav1.DeleteOptions{}); err != nil {
		h.handleError(c, err)
		return
	}

	c.JSON(200, gin.H{})
}

// ListIngresses returns ingresses in namespace.
func (h *Handler) ListIngresses(c *gin.Context) {
	namespace := c.Param("namespace")

	ingresses, err := h.kubeClient.NetworkingV1beta1().Ingresses(namespace).List(metav1.ListOptions{})
	if err != nil {
		h.handleError(c, err)
		return
	}

	c.JSON(200, gin.H{
		"ingresses": ingresses,
	})
}

// GetIngress returns a ingress with name.
func (h *Handler) GetIngress(c *gin.Context) {
	namespace := c.Param("namespace")
	name := c.Param("name")

	ingress, err := h.kubeClient.NetworkingV1beta1().Ingresses(namespace).Get(name, metav1.GetOptions{})
	if err != nil {
		h.handleError(c, err)
		return
	}

	c.JSON(200, gin.H{
		"ingress": ingress,
	})
}

// CreateIngress create a ingress.
func (h *Handler) CreateIngress(c *gin.Context) {
	namespace := c.Param("namespace")

	ingress := &networkingv1beta1.Ingress{}
	if err := c.BindJSON(&ingress); err != nil {
		h.handleError(c, err)
		return
	}

	newIngress, err := h.kubeClient.NetworkingV1beta1().Ingresses(namespace).Create(ingress)
	if err != nil {
		h.handleError(c, err)
		return
	}

	c.JSON(201, gin.H{
		"ingress": newIngress,
	})
}

// DeleteIngress delete a ingress with name.
func (h *Handler) DeleteIngress(c *gin.Context) {
	namespace := c.Param("namespace")
	name := c.Param("name")

	if err := h.kubeClient.NetworkingV1beta1().Ingresses(namespace).Delete(name, &metav1.DeleteOptions{}); err != nil {
		h.handleError(c, err)
		return
	}

	c.JSON(200, gin.H{})
}

// GetFLApp .
func (h *Handler) GetFLApp(c *gin.Context) {
	namespace := c.Param("namespace")
	name := c.Param("name")

	flapp, err := h.crdClient.FedlearnerV1alpha1().FLApps(namespace).Get(name, metav1.GetOptions{})
	if err != nil {
		h.handleError(c, err)
		return
	}

	c.JSON(200, gin.H{
		"flapp": flapp,
	})
}

// ListFLAppPods .
func (h *Handler) ListFLAppPods(c *gin.Context) {
	namespace := c.Param("namespace")
	name := c.Param("name")

	pods, err := h.kubeClient.CoreV1().Pods(namespace).List(metav1.ListOptions{
		LabelSelector: fmt.Sprintf("app-name=%s", name),
	})
	if err != nil {
		h.handleError(c, err)
		return
	}

	c.JSON(200, gin.H{
		"pods": pods,
	})
}

// ListFLApps .
func (h *Handler) ListFLApps(c *gin.Context) {
	namespace := c.Param("namespace")

	flapps, err := h.crdClient.FedlearnerV1alpha1().FLApps(namespace).List(metav1.ListOptions{})
	if err != nil {
		h.handleError(c, err)
		return
	}

	c.JSON(200, gin.H{
		"flapps": flapps,
	})
}

// CreateFLApp .
func (h *Handler) CreateFLApp(c *gin.Context) {
	namespace := c.Param("namespace")

	flapp := &v1alpha1.FLApp{}
	if err := c.BindJSON(&flapp); err != nil {
		h.handleError(c, err)
		return
	}

	newFlapp, err := h.crdClient.FedlearnerV1alpha1().FLApps(namespace).Create(flapp)
	if err != nil {
		h.handleError(c, err)
		return
	}

	c.JSON(201, gin.H{
		"flapp": newFlapp,
	})
}

// DeleteFLApp .
func (h *Handler) DeleteFLApp(c *gin.Context) {
	namespace := c.Param("namespace")
	name := c.Param("name")

	if err := h.crdClient.FedlearnerV1alpha1().FLApps(namespace).Delete(name, &metav1.DeleteOptions{}); err != nil {
		h.handleError(c, err)
		return
	}

	c.JSON(200, gin.H{})
}

func (h *Handler) ExecShell(c *gin.Context) {
	namespace := c.Param("namespace")
	podName := c.Param("name")
	containerName := c.Param("container")

	sessionID, err := genTerminalSessionId()
	if err != nil {
		h.handleError(c, err)
		return
	}

	terminalSessions.Set(sessionID, TerminalSession{
		id:       sessionID,
		bound:    make(chan error),
		sizeChan: make(chan remotecommand.TerminalSize),
	})
	go WaitForTerminal(h.kubeClient, h.restConfig, namespace, podName, containerName, sessionID)
	c.JSON(http.StatusOK, gin.H{
		"id": sessionID,
	})
}

func (h *Handler) handleError(c *gin.Context, err error) {
	statusCode := 500
	if errors.IsNotFound(err) {
		statusCode = 404
	}

	c.JSON(statusCode, gin.H{
		"error": err.Error(),
	})
}
