package handler

import (
	"fmt"

	"github.com/gin-gonic/gin"
	"k8s.io/apimachinery/pkg/labels"
	"k8s.io/client-go/informers"
	"k8s.io/client-go/tools/cache"
)

// Handler .
type Handler struct {
	informerFactory informers.SharedInformerFactory
}

// NewHandler returns a new handler.
func NewHandler(informerFactory informers.SharedInformerFactory) *Handler {
	return &Handler{
		informerFactory: informerFactory,
	}
}

// Run .
func (h *Handler) Run(stopCh <-chan struct{}) error {
	if !cache.WaitForCacheSync(
		stopCh,
		h.informerFactory.Core().V1().Pods().Informer().HasSynced,
	) {
		return fmt.Errorf("timed out waiting for cache to sync")
	}

	return nil
}

// ListPods returns pods in namespace.
func (h *Handler) ListPods(c *gin.Context) {
	namespace := c.Param("namespace")

	pods, err := h.informerFactory.Core().V1().Pods().Lister().Pods(namespace).List(labels.Everything())
	if err != nil {
		c.JSON(500, gin.H{
			"error": err.Error(),
		})
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

	pod, err := h.informerFactory.Core().V1().Pods().Lister().Pods(namespace).Get(name)
	if err != nil {
		c.JSON(500, gin.H{
			"error": err.Error(),
		})
		return
	}

	c.JSON(200, gin.H{
		"pod": pod,
	})
}
