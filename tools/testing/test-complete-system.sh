#!/bin/bash

# test-complete-system.sh
# Комплексный тест всей системы HW_10
# 🎯 Проверка всех целей проекта

set -e

PROJECT_ROOT=$(dirname "$(realpath "$0")")

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# Функции логирования
log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }
log_header() { 
    echo ""
    echo -e "${PURPLE}$1${NC}"
    echo -e "${PURPLE}$(echo "$1" | sed 's/./═/g')${NC}"
}

# Глобальные переменные для результатов
TESTS_PASSED=0
TESTS_FAILED=0
GOALS_ACHIEVED=0
TOTAL_GOALS=4

# Функция для проверки цели
check_goal() {
    local goal_name="$1"
    local test_result="$2"
    
    if [ "$test_result" = "true" ]; then
        log_success "ЦЕЛЬ ДОСТИГНУТА: $goal_name"
        ((GOALS_ACHIEVED++))
    else
        log_error "ЦЕЛЬ НЕ ДОСТИГНУТА: $goal_name"
    fi
}

# Проверка готовности системы
check_system_readiness() {
    log_header "🔍 ПРОВЕРКА ГОТОВНОСТИ СИСТЕМЫ"
    
    local all_ready=true
    
    # Проверка namespaces
    log_info "Проверка namespaces..."
    for ns in fraud-detection monitoring airflow; do
        if kubectl get namespace "$ns" >/dev/null 2>&1; then
            log_success "Namespace $ns существует"
        else
            log_error "Namespace $ns не найден"
            all_ready=false
        fi
    done
    
    # Проверка подов
    log_info "Проверка подов..."
    local pods_not_ready=0
    
    while IFS= read -r line; do
        namespace=$(echo "$line" | awk '{print $1}')
        pod=$(echo "$line" | awk '{print $2}')
        ready=$(echo "$line" | awk '{print $3}')
        status=$(echo "$line" | awk '{print $4}')
        
        if [[ "$ready" == *"/"* ]]; then
            ready_count=$(echo "$ready" | cut -d'/' -f1)
            total_count=$(echo "$ready" | cut -d'/' -f2)
            
            if [ "$ready_count" -eq "$total_count" ] && [ "$status" = "Running" ]; then
                log_success "Pod $namespace/$pod готов ($ready)"
            else
                log_warning "Pod $namespace/$pod не готов ($ready, $status)"
                ((pods_not_ready++))
            fi
        fi
    done < <(kubectl get pods --all-namespaces --no-headers | grep -E "(fraud-detection|monitoring|airflow)")
    
    if [ $pods_not_ready -eq 0 ]; then
        log_success "Все поды готовы к работе"
        return 0
    else
        log_error "$pods_not_ready подов не готовы"
        return 1
    fi
}

# Получение External IP адресов
get_external_ips() {
    log_header "🔗 ПОЛУЧЕНИЕ АДРЕСОВ ДОСТУПА"
    
    # Функция для получения External IP
    get_service_ip() {
        local service=$1
        local namespace=$2
        local ip=$(kubectl get service "$service" -n "$namespace" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
        
        if [ -n "$ip" ] && [ "$ip" != "null" ]; then
            echo "$ip"
        else
            # Пробуем получить hostname (для некоторых cloud providers)
            local hostname=$(kubectl get service "$service" -n "$namespace" -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "")
            if [ -n "$hostname" ] && [ "$hostname" != "null" ]; then
                echo "$hostname"
            else
                echo ""
            fi
        fi
    }
    
    GRAFANA_IP=$(get_service_ip "grafana" "monitoring")
    PROMETHEUS_IP=$(get_service_ip "prometheus" "monitoring")
    AIRFLOW_IP=$(get_service_ip "airflow-webserver" "airflow")
    API_IP=$(get_service_ip "fraud-detection-loadbalancer" "fraud-detection")
    
    # Выводим адреса
    log_info "🔗 Адреса сервисов:"
    echo "  📊 Grafana:    ${GRAFANA_IP:-pending}:3000"
    echo "  📈 Prometheus: ${PROMETHEUS_IP:-pending}:9090"  
    echo "  🌊 Airflow:    ${AIRFLOW_IP:-pending}:8080"
    echo "  🛡️ API:        ${API_IP:-pending}"
    
    # Проверяем доступность
    if [ -n "$API_IP" ]; then
        if curl -f -s "http://$API_IP/health/ready" >/dev/null; then
            log_success "Fraud Detection API доступен"
            API_AVAILABLE=true
        else
            log_warning "Fraud Detection API недоступен"
            API_AVAILABLE=false
        fi
    else
        log_warning "External IP для API еще не назначен"
        API_AVAILABLE=false
    fi
}

# Тест 1: Автоскейлинг (4-6 экземпляров)
test_autoscaling() {
    log_header "🎯 ТЕСТ 1: АВТОСКЕЙЛИНГ (4-6 ЭКЗЕМПЛЯРОВ)"
    
    # Проверка начального количества подов
    local initial_replicas=$(kubectl get deployment fraud-detection-api -n fraud-detection -o jsonpath='{.status.replicas}' 2>/dev/null || echo "0")
    log_info "Начальное количество реплик: $initial_replicas"
    
    if [ "$initial_replicas" -ge 4 ]; then
        log_success "Начальное количество реплик соответствует требованиям (≥4)"
    else
        log_warning "Начальное количество реплик меньше 4"
    fi
    
    # Проверка HPA
    if kubectl get hpa fraud-detection-hpa -n fraud-detection >/dev/null 2>&1; then
        log_success "HPA настроен"
        
        # Показываем конфигурацию HPA
        local min_replicas=$(kubectl get hpa fraud-detection-hpa -n fraud-detection -o jsonpath='{.spec.minReplicas}')
        local max_replicas=$(kubectl get hpa fraud-detection-hpa -n fraud-detection -o jsonpath='{.spec.maxReplicas}')
        
        log_info "HPA конфигурация: минимум $min_replicas, максимум $max_replicas"
        
        if [ "$min_replicas" -eq 4 ] && [ "$max_replicas" -eq 6 ]; then
            log_success "HPA настроен правильно (4-6 реплик)"
            check_goal "Автоскейлинг от 4 до 6 экземпляров" "true"
        else
            log_error "HPA настроен неправильно (ожидается 4-6, получено $min_replicas-$max_replicas)"
            check_goal "Автоскейлинг от 4 до 6 экземпляров" "false"
        fi
    else
        log_error "HPA не найден"
        check_goal "Автоскейлинг от 4 до 6 экземпляров" "false"
    fi
}

# Тест 2: Мониторинг и алертинг
test_monitoring_and_alerting() {
    log_header "🎯 ТЕСТ 2: МОНИТОРИНГ И АЛЕРТИНГ"
    
    local monitoring_ready=true
    
    # Проверка Prometheus
    if [ -n "$PROMETHEUS_IP" ]; then
        if curl -f -s "http://$PROMETHEUS_IP:9090/-/ready" >/dev/null; then
            log_success "Prometheus доступен"
            
            # Проверка алертинг правил
            local alert_rules=$(curl -s "http://$PROMETHEUS_IP:9090/api/v1/rules" | grep -o '"FraudDetectionHighLoad"' | wc -l)
            if [ "$alert_rules" -gt 0 ]; then
                log_success "Алертинг правила настроены"
            else
                log_warning "Алертинг правила не найдены"
                monitoring_ready=false
            fi
        else
            log_error "Prometheus недоступен"
            monitoring_ready=false
        fi
    else
        log_warning "Prometheus IP не назначен"
        monitoring_ready=false
    fi
    
    # Проверка Grafana
    if [ -n "$GRAFANA_IP" ]; then
        if curl -f -s "http://$GRAFANA_IP:3000/api/health" >/dev/null; then
            log_success "Grafana доступен"
        else
            log_warning "Grafana недоступен"
        fi
    else
        log_warning "Grafana IP не назначен"
    fi
    
    # Проверка Alertmanager
    if kubectl get pod -n monitoring -l app.kubernetes.io/name=alertmanager >/dev/null 2>&1; then
        log_success "Alertmanager развернут"
    else
        log_warning "Alertmanager не найден"
        monitoring_ready=false
    fi
    
    check_goal "Настройка мониторинга (Prometheus + Grafana)" "$monitoring_ready"
}

# Тест 3: Apache Airflow и MLflow
test_airflow_mlflow() {
    log_header "🎯 ТЕСТ 3: APACHE AIRFLOW И MLFLOW"
    
    local airflow_ready=true
    
    # Проверка Airflow
    if [ -n "$AIRFLOW_IP" ]; then
        if curl -f -s "http://$AIRFLOW_IP:8080/health" >/dev/null 2>&1; then
            log_success "Airflow веб-интерфейс доступен"
        else
            log_warning "Airflow веб-интерфейс недоступен"
        fi
    else
        log_warning "Airflow IP не назначен"
    fi
    
    # Проверка подов Airflow
    local airflow_pods=$(kubectl get pods -n airflow -l app.kubernetes.io/name=airflow --no-headers | wc -l)
    if [ "$airflow_pods" -gt 0 ]; then
        log_success "Airflow поды запущены ($airflow_pods подов)"
        
        # Проверка DAG'ов
        if kubectl exec -n airflow deployment/airflow-scheduler -- airflow dags list >/dev/null 2>&1; then
            log_success "Airflow scheduler работает"
            
            # Поиск нашего DAG'а
            if kubectl exec -n airflow deployment/airflow-scheduler -- airflow dags list | grep -q "ml_model_retraining_pipeline"; then
                log_success "DAG переобучения модели найден"
            else
                log_warning "DAG переобучения модели не найден"
                airflow_ready=false
            fi
        else
            log_warning "Airflow scheduler недоступен"
            airflow_ready=false
        fi
    else
        log_error "Airflow поды не найдены"
        airflow_ready=false
    fi
    
    # Проверка MLflow
    if kubectl get pod -n airflow -l app.kubernetes.io/name=mlflow >/dev/null 2>&1; then
        log_success "MLflow server развернут"
    else
        log_warning "MLflow server не найден"
        airflow_ready=false
    fi
    
    check_goal "Настройка Airflow для переобучения модели" "$airflow_ready"
}

# Тест 4: Стресс-тест и алерты
test_stress_and_alerts() {
    log_header "🎯 ТЕСТ 4: СТРЕСС-ТЕСТ И АЛЕРТЫ"
    
    if [ "$API_AVAILABLE" != "true" ]; then
        log_error "API недоступен для стресс-тестирования"
        check_goal "Алертинг при превышении нагрузки >80% CPU" "false"
        return
    fi
    
    log_info "Запуск кратковременного стресс-теста..."
    
    # Запускаем стресс-тест на 2 минуты
    if python3 "$PROJECT_ROOT/scripts/kafka_stress_test.py" \
        --api-url "http://$API_IP" \
        --prometheus-url "http://${PROMETHEUS_IP:-localhost}:9090" \
        --max-rps 100 \
        --ramp-up-duration 30 \
        --sustain-duration 120 \
        --ramp-down-duration 30 2>/dev/null; then
        
        log_success "Стресс-тест выполнен"
        
        # Проверяем, изменилось ли количество подов
        sleep 30  # Даем время HPA среагировать
        
        local current_replicas=$(kubectl get deployment fraud-detection-api -n fraud-detection -o jsonpath='{.status.replicas}')
        local desired_replicas=$(kubectl get deployment fraud-detection-api -n fraud-detection -o jsonpath='{.spec.replicas}')
        
        log_info "Текущие реплики: $current_replicas, желаемые: $desired_replicas"
        
        if [ "$current_replicas" -gt 4 ] || [ "$desired_replicas" -gt 4 ]; then
            log_success "Автоскейлинг сработал (реплики увеличились)"
            
            # Проверяем алерты в Prometheus
            if [ -n "$PROMETHEUS_IP" ]; then
                local active_alerts=$(curl -s "http://$PROMETHEUS_IP:9090/api/v1/alerts" | grep -o '"FraudDetection.*"' | wc -l 2>/dev/null || echo "0")
                if [ "$active_alerts" -gt 0 ]; then
                    log_success "Алерты активированы ($active_alerts алертов)"
                    check_goal "Алертинг при превышении нагрузки >80% CPU" "true"
                else
                    log_warning "Алерты не активированы (возможно, нужно больше времени)"
                    check_goal "Алертинг при превышении нагрузки >80% CPU" "false"
                fi
            else
                log_warning "Prometheus недоступен для проверки алертов"
                check_goal "Алертинг при превышении нагрузки >80% CPU" "false"
            fi
        else
            log_warning "Автоскейлинг не сработал (возможно, нужна большая нагрузка)"
            check_goal "Алертинг при превышении нагрузки >80% CPU" "false"
        fi
    else
        log_error "Стресс-тест завершился с ошибкой"
        check_goal "Алертинг при превышении нагрузки >80% CPU" "false"
    fi
}

# Генерация итогового отчета
generate_final_report() {
    log_header "📊 ИТОГОВЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ"
    
    echo ""
    log_info "🎯 ДОСТИЖЕНИЕ ЦЕЛЕЙ ПРОЕКТА:"
    echo "   Достигнуто: $GOALS_ACHIEVED из $TOTAL_GOALS целей"
    
    local success_rate=$((GOALS_ACHIEVED * 100 / TOTAL_GOALS))
    
    if [ $success_rate -eq 100 ]; then
        log_success "🎉 ВСЕ ЦЕЛИ ДОСТИГНУТЫ! ($success_rate%)"
        echo ""
        echo "✅ Автоскейлинг от 4 до 6 экземпляров"
        echo "✅ Мониторинг с Prometheus и Grafana"  
        echo "✅ Airflow для переобучения модели"
        echo "✅ Алертинг при высокой нагрузке"
        
    elif [ $success_rate -ge 75 ]; then
        log_success "🌟 БОЛЬШИНСТВО ЦЕЛЕЙ ДОСТИГНУТО! ($success_rate%)"
        
    elif [ $success_rate -ge 50 ]; then
        log_warning "⚡ ПОЛОВИНА ЦЕЛЕЙ ДОСТИГНУТА ($success_rate%)"
        
    else
        log_error "⚠️ МАЛО ЦЕЛЕЙ ДОСТИГНУТО ($success_rate%)"
    fi
    
    echo ""
    log_info "🔗 ДОСТУП К СИСТЕМЕ:"
    if [ -n "$GRAFANA_IP" ]; then
        echo "   📊 Grafana Dashboard: http://$GRAFANA_IP:3000"
    fi
    if [ -n "$PROMETHEUS_IP" ]; then
        echo "   📈 Prometheus: http://$PROMETHEUS_IP:9090/alerts"
    fi
    if [ -n "$AIRFLOW_IP" ]; then
        echo "   🌊 Airflow: http://$AIRFLOW_IP:8080"
    fi
    if [ -n "$API_IP" ]; then
        echo "   🛡️ API Documentation: http://$API_IP/docs"
    fi
    
    echo ""
    log_info "📋 РЕКОМЕНДАЦИИ:"
    if [ $success_rate -lt 100 ]; then
        echo "   • Проверьте логи подов: kubectl logs -n NAMESPACE POD_NAME"
        echo "   • Убедитесь, что все External IP назначены"
        echo "   • Для стресс-теста может потребоваться больше времени"
        echo "   • Проверьте ресурсы кластера: kubectl top nodes"
    fi
    echo "   • Мониторьте систему через Grafana"
    echo "   • Регулярно запускайте стресс-тесты"
    echo "   • Проверяйте DAG'и в Airflow"
    
    echo ""
    if [ $success_rate -eq 100 ]; then
        log_success "🚀 СИСТЕМА ГОТОВА К PRODUCTION ИСПОЛЬЗОВАНИЮ!"
    else
        log_warning "🔧 СИСТЕМА ТРЕБУЕТ ДОПОЛНИТЕЛЬНОЙ НАСТРОЙКИ"
    fi
}

# Основная функция
main() {
    log_header "🚀 КОМПЛЕКСНОЕ ТЕСТИРОВАНИЕ СИСТЕМЫ HW_10"
    log_info "Тестирование production ML системы с автоскейлингом и мониторингом"
    
    # Этапы тестирования
    check_system_readiness
    get_external_ips
    test_autoscaling
    test_monitoring_and_alerting  
    test_airflow_mlflow
    test_stress_and_alerts
    
    # Итоговый отчет
    generate_final_report
    
    echo ""
    log_header "🏁 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО"
    
    # Возвращаем код выхода на основе успешности
    if [ $GOALS_ACHIEVED -eq $TOTAL_GOALS ]; then
        exit 0
    else
        exit 1
    fi
}

# Запуск
main "$@"
