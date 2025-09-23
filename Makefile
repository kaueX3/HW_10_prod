# Makefile for HW_10 - ML Fraud Detection Production Deployment
# 🚀 Kubernetes + Monitoring + Autoscaling + Airflow

.PHONY: help install deploy status test stress-test clean

# Default target
.DEFAULT_GOAL := help

# Configuration
PROJECT_NAME := fraud-detection-ml
K8S_DIR := k8s
SCRIPTS_DIR := scripts
DEPLOY_DIR := deploy
NS_FRAUD := fraud-detection
NS_MONITORING := monitoring  
NS_AIRFLOW := airflow

help: ## 📋 Show this help message
	@echo "🚀 ML Fraud Detection Production Deployment"
	@echo "==========================================="
	@echo ""
	@echo "Available commands:"
	@awk 'BEGIN {FS = ":.*##"; printf ""} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 } ' $(MAKEFILE_LIST)

install: ## 📦 Install dependencies and check prerequisites
	@echo "📦 Installing dependencies..."
	@command -v kubectl >/dev/null 2>&1 || { echo "❌ kubectl не найден"; exit 1; }
	@kubectl cluster-info >/dev/null 2>&1 || { echo "❌ Нет доступа к Kubernetes"; exit 1; }
	@echo "✅ Все зависимости установлены"
	@pip install -r app/requirements.txt aiohttp asyncio

deploy: ## 🚀 Deploy full infrastructure
	@echo "🚀 Deploying full infrastructure..."
	@chmod +x $(DEPLOY_DIR)/deploy-all.sh
	@$(DEPLOY_DIR)/deploy-all.sh

status: ## 📊 Show deployment status
	@echo "📊 Deployment Status"
	@echo "==================="
	@kubectl get pods,svc,hpa -n $(NS_FRAUD) 2>/dev/null || echo "Fraud Detection not deployed"
	@kubectl get pods,svc -n $(NS_MONITORING) 2>/dev/null || echo "Monitoring not deployed"
	@kubectl get pods,svc -n $(NS_AIRFLOW) 2>/dev/null || echo "Airflow not deployed"

test: ## 🧪 Run basic API tests
	@echo "🧪 Running API tests..."
	@API_IP=$$(kubectl get service fraud-detection-loadbalancer -n $(NS_FRAUD) -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null); \
	 if [ "$$API_IP" != "" ]; then \
	   curl -f "http://$$API_IP/health/ready" && echo "✅ Health check passed"; \
	 else \
	   echo "❌ API not available. Use: kubectl port-forward -n $(NS_FRAUD) svc/fraud-detection-service 8000:80"; \
	 fi

stress-test: ## 🔥 Run stress test
	@echo "🔥 Running stress test..."
	@python3 $(SCRIPTS_DIR)/kafka_stress_test.py --api-url http://localhost:8000 --max-rps 200

clean: ## 🗑️ Delete all resources
	@echo "🗑️ Cleaning up..."
	@kubectl delete namespace $(NS_FRAUD) $(NS_MONITORING) $(NS_AIRFLOW) --ignore-not-found=true
	@echo "✅ Cleanup complete"

urls: ## 🔗 Show access URLs
	@echo "🔗 Access URLs:"
	@echo "Grafana: http://$$(kubectl get svc grafana -n $(NS_MONITORING) -o jsonpath='{.status.loadBalancer.ingress[0].ip}'):3000"
	@echo "Prometheus: http://$$(kubectl get svc prometheus -n $(NS_MONITORING) -o jsonpath='{.status.loadBalancer.ingress[0].ip}'):9090"
	@echo "Airflow: http://$$(kubectl get svc airflow-webserver -n $(NS_AIRFLOW) -o jsonpath='{.status.loadBalancer.ingress[0].ip}'):8080"