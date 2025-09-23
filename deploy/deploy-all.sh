#!/bin/bash

# deploy-all.sh
# Скрипт для развертывания всей инфраструктуры HW_10
# 🚀 ML Fraud Detection с автоскейлингом, мониторингом и алертингом

set -e  # Остановиться при ошибке

PROJECT_ROOT=$(dirname "$(dirname "$(realpath "$0")")")
K8S_DIR="${PROJECT_ROOT}/k8s"

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функции для логирования
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_header() {
    echo ""
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}$(echo "$1" | sed 's/./-/g')${NC}"
}

# Проверка наличия kubectl
check_prerequisites() {
    log_header "🔍 Checking Prerequisites"
    
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl не найден. Установите kubectl и настройте доступ к кластеру"
        exit 1
    fi
    
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Не удается подключиться к Kubernetes кластеру"
        exit 1
    fi
    
    log_success "kubectl доступен и подключен к кластеру"
    
    # Показываем информацию о кластере
    CLUSTER_INFO=$(kubectl cluster-info | head -1)
    log_info "Кластер: $CLUSTER_INFO"
    
    NODES=$(kubectl get nodes --no-headers | wc -l)
    log_info "Узлов в кластере: $NODES"
}

# Создание namespace'ов
create_namespaces() {
    log_header "🏗️ Creating Namespaces"
    
    kubectl apply -f "${K8S_DIR}/namespace.yaml"
    log_success "Namespaces созданы"
    
    # Проверяем созданные namespace'ы
    log_info "Созданные namespaces:"
    kubectl get namespaces fraud-detection monitoring airflow --no-headers | while read line; do
        log_info "  • $line"
    done
}

# Развертывание мониторинга (Prometheus + Grafana + Alertmanager)
deploy_monitoring() {
    log_header "📊 Deploying Monitoring Stack"
    
    log_info "Развертывание Prometheus..."
    kubectl apply -f "${K8S_DIR}/monitoring/prometheus-config.yaml"
    kubectl apply -f "${K8S_DIR}/monitoring/prometheus-deployment.yaml"
    
    log_info "Развертывание Alertmanager..."
    kubectl apply -f "${K8S_DIR}/monitoring/alertmanager.yaml"
    
    log_info "Развертывание Grafana..."
    kubectl apply -f "${K8S_DIR}/monitoring/grafana-deployment.yaml"
    
    log_success "Monitoring stack развернут"
    
    # Ждем готовности pods
    log_info "Ожидание готовности monitoring pods..."
    kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=prometheus -n monitoring --timeout=300s
    kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=grafana -n monitoring --timeout=300s
    kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=alertmanager -n monitoring --timeout=300s
    
    log_success "Monitoring stack готов"
}

# Развертывание Airflow
deploy_airflow() {
    log_header "🌊 Deploying Apache Airflow"
    
    log_info "Развертывание PostgreSQL для Airflow..."
    kubectl apply -f "${K8S_DIR}/airflow/postgres.yaml"
    
    log_info "Ожидание готовности PostgreSQL..."
    kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=postgres -n airflow --timeout=300s
    
    log_info "Развертывание MLflow Server..."
    kubectl apply -f "${K8S_DIR}/airflow/mlflow-server.yaml"
    
    log_info "Развертывание Airflow..."
    kubectl apply -f "${K8S_DIR}/airflow/airflow-deployment.yaml"
    
    log_success "Airflow развернут"
    
    # Ждем готовности
    log_info "Ожидание готовности Airflow pods..."
    kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=airflow -n airflow --timeout=600s
    
    log_success "Airflow готов"
}

# Развертывание Fraud Detection API
deploy_fraud_detection_api() {
    log_header "🛡️ Deploying Fraud Detection API"
    
    log_info "Создание ConfigMap и Secrets..."
    kubectl apply -f "${K8S_DIR}/configmap.yaml"
    
    log_info "Создание Service..."
    kubectl apply -f "${K8S_DIR}/service.yaml"
    
    log_info "Развертывание API..."
    kubectl apply -f "${K8S_DIR}/deployment-production.yaml"
    
    log_info "Настройка HPA (Horizontal Pod Autoscaler)..."
    kubectl apply -f "${K8S_DIR}/hpa.yaml"
    
    log_success "Fraud Detection API развернут"
    
    # Ждем готовности pods
    log_info "Ожидание готовности API pods..."
    kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=fraud-detection -n fraud-detection --timeout=300s
    
    log_success "Fraud Detection API готов"
}

# Проверка статуса развертывания
check_deployment_status() {
    log_header "🔍 Checking Deployment Status"
    
    echo ""
    log_info "📊 Monitoring Namespace:"
    kubectl get pods -n monitoring -o wide
    
    echo ""
    log_info "🌊 Airflow Namespace:"
    kubectl get pods -n airflow -o wide
    
    echo ""
    log_info "🛡️ Fraud Detection Namespace:"
    kubectl get pods -n fraud-detection -o wide
    
    echo ""
    log_info "🔄 HPA Status:"
    kubectl get hpa -n fraud-detection
    
    echo ""
    log_info "📡 Services:"
    kubectl get services --all-namespaces | grep -E "(monitoring|airflow|fraud-detection)"
}

# Получение URL'ов для доступа
get_access_urls() {
    log_header "🔗 Access URLs"
    
    # Получаем External IPs
    GRAFANA_IP=$(kubectl get service grafana -n monitoring -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "pending")
    PROMETHEUS_IP=$(kubectl get service prometheus -n monitoring -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "pending")
    AIRFLOW_IP=$(kubectl get service airflow-webserver -n airflow -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "pending")
    FRAUD_API_IP=$(kubectl get service fraud-detection-loadbalancer -n fraud-detection -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "pending")
    
    echo ""
    log_info "📊 Grafana Dashboard:"
    if [ "$GRAFANA_IP" != "pending" ]; then
        echo "   🔗 http://$GRAFANA_IP:3000"
        echo "   👤 admin / admin123"
    else
        echo "   ⏳ External IP еще не назначен. Проверьте позже: kubectl get service grafana -n monitoring"
    fi
    
    echo ""
    log_info "📈 Prometheus:"
    if [ "$PROMETHEUS_IP" != "pending" ]; then
        echo "   🔗 http://$PROMETHEUS_IP:9090"
    else
        echo "   ⏳ External IP еще не назначен. Проверьте позже: kubectl get service prometheus -n monitoring"
    fi
    
    echo ""
    log_info "🌊 Airflow Web UI:"
    if [ "$AIRFLOW_IP" != "pending" ]; then
        echo "   🔗 http://$AIRFLOW_IP:8080"
        echo "   👤 admin / admin"
    else
        echo "   ⏳ External IP еще не назначен. Проверьте позже: kubectl get service airflow-webserver -n airflow"
    fi
    
    echo ""
    log_info "🛡️ Fraud Detection API:"
    if [ "$FRAUD_API_IP" != "pending" ]; then
        echo "   🔗 http://$FRAUD_API_IP/docs"
        echo "   🔗 http://$FRAUD_API_IP/health/ready"
    else
        echo "   ⏳ External IP еще не назначен. Проверьте позже: kubectl get service fraud-detection-loadbalancer -n fraud-detection"
    fi
    
    echo ""
    log_info "📋 Port Forward команды (если LoadBalancer недоступен):"
    echo "   kubectl port-forward -n monitoring svc/grafana 3000:3000"
    echo "   kubectl port-forward -n monitoring svc/prometheus 9090:9090"
    echo "   kubectl port-forward -n airflow svc/airflow-webserver 8080:8080"
    echo "   kubectl port-forward -n fraud-detection svc/fraud-detection-service 8000:80"
}

# Инструкции по тестированию
print_testing_instructions() {
    log_header "🧪 Testing Instructions"
    
    echo ""
    log_info "1️⃣ Проверка API:"
    echo "   curl http://FRAUD_API_IP/health/ready"
    echo "   curl http://FRAUD_API_IP/"
    
    echo ""
    log_info "2️⃣ Запуск стресс-теста:"
    echo "   cd ${PROJECT_ROOT}"
    echo "   python scripts/kafka_stress_test.py --api-url http://FRAUD_API_IP --max-rps 200"
    
    echo ""
    log_info "3️⃣ Мониторинг автоскейлинга:"
    echo "   watch kubectl get hpa -n fraud-detection"
    echo "   watch kubectl get pods -n fraud-detection"
    
    echo ""
    log_info "4️⃣ Проверка алертов:"
    echo "   Grafana: http://GRAFANA_IP:3000 → Alerting → Alert Rules"
    echo "   Prometheus: http://PROMETHEUS_IP:9090/alerts"
    
    echo ""
    log_info "5️⃣ Запуск DAG'а для переобучения:"
    echo "   Airflow: http://AIRFLOW_IP:8080 → DAGs → ml_model_retraining_pipeline"
    
    echo ""
    log_warning "🎯 Цели тестирования:"
    echo "   • Автоскейлинг от 4 до 6 экземпляров"
    echo "   • Алерт при 6 экземплярах и >80% CPU в течение 5 минут"
    echo "   • Периодическое переобучение модели"
    echo "   • Мониторинг через Grafana"
}

# Основная функция
main() {
    log_header "🚀 ML Fraud Detection Production Deployment"
    log_info "Начинаем развертывание полной инфраструктуры..."
    
    # Этапы развертывания
    check_prerequisites
    create_namespaces
    deploy_monitoring
    deploy_airflow
    deploy_fraud_detection_api
    
    echo ""
    log_success "🎉 РАЗВЕРТЫВАНИЕ ЗАВЕРШЕНО УСПЕШНО!"
    
    # Статус и URL'ы
    check_deployment_status
    get_access_urls
    print_testing_instructions
    
    echo ""
    log_success "🚀 Система готова к использованию!"
    log_info "Дождитесь назначения External IP адресов для сервисов (может занять несколько минут)"
}

# Запуск
main "$@"
