# 🎯 HW_10 - КРАТКАЯ ИНСТРУКЦИЯ ДЛЯ ПРОВЕРЯЮЩЕГО

## 📋 Быстрая проверка выполнения

### ✅ Статус: ЗАДАНИЕ ВЫПОЛНЕНО

**Развернутая система**: Production ML Fraud Detection с автоскейлингом в Yandex Cloud

---

## 🌐 ДОСТУП К СИСТЕМЕ (готово к проверке)

### Веб-интерфейсы:
- **🛡️ Fraud Detection API**: http://89.169.137.245:32134
- **📊 Prometheus**: http://89.169.137.245:32007
- **📈 Grafana**: http://89.169.137.245:30250
  - Логин: `admin`
  - Пароль: `admin123`

### Альтернативные адреса (второй узел):
- API: http://89.169.139.226:32134
- Prometheus: http://89.169.139.226:32007
- Grafana: http://89.169.139.226:30250

---

## 🔍 БЫСТРАЯ ПРОВЕРКА ТРЕБОВАНИЙ

### 1. Автоскейлинг 4-6 подов ✅
```bash
kubectl get hpa -n fraud-detection
# Должно показать: MINPODS=4, MAXPODS=6, TARGETS=cpu: X%/70%
```

### 2. Мониторинг ✅
- Откройте http://89.169.137.245:32007 - должен быть доступен Prometheus
- Откройте http://89.169.137.245:30250 - должен быть доступен Grafana

### 3. ML Pipeline ✅
```bash
kubectl get pods -n airflow
# Должно показать: mlflow-server, postgres, airflow pods в статусе Running
```

### 4. Алертинг ✅
```bash
kubectl get pods -n monitoring
# Должно показать: prometheus, grafana в статусе Running
# alertmanager (базовая конфигурация развернута)
```

---

## 🧪 ТЕСТИРОВАНИЕ АВТОСКЕЙЛИНГА

### Запуск стресс-теста:
```bash
cd /Users/denispukinov/Documents/OTUS/HW_10
uv run simple_stress_test.py --api-url http://89.169.137.245:32134/cpu --max-rps 50 --duration 180 --workers 5
```

### Мониторинг масштабирования:
```bash
# В отдельном терминале
watch kubectl get pods -n fraud-detection
```

---

## 📊 КЛЮЧЕВЫЕ АРТЕФАКТЫ

1. **📋 Полный отчет**: `HW_10_COMPLETION_REPORT.md`
2. **✅ Чеклист**: `artifacts/evidence/deployment_checklist.md`
3. **🔗 URL доступа**: `artifacts/evidence/system_urls.txt`
4. **📊 Состояние кластера**: `artifacts/evidence/cluster_status.txt`
5. **🧪 Тесты API**: `artifacts/evidence/api_tests.txt`

---

## 🏗️ АРХИТЕКТУРА (краткая схема)

```
Yandex Cloud Kubernetes Cluster (2 nodes)
├── fraud-detection namespace
│   ├── API Pods (4-6) + HPA
│   └── LoadBalancer Service
├── monitoring namespace
│   ├── Prometheus
│   ├── Grafana  
│   └── AlertManager
└── airflow namespace
    ├── Airflow (scheduler, webserver)
    ├── MLflow Server
    └── PostgreSQL
```

---

## 🎯 ВЫПОЛНЕННЫЕ ТРЕБОВАНИЯ

| Требование | Статус | Проверка |
|------------|--------|----------|
| 4-6 экземпляров модели | ✅ | `kubectl get hpa -n fraud-detection` |
| Автоскейлинг | ✅ | HPA на CPU >70%, Memory >80% |
| Prometheus мониторинг | ✅ | http://89.169.137.245:32007 |
| Grafana визуализация | ✅ | http://89.169.137.245:30250 |
| Airflow переобучение | ✅ | `kubectl get pods -n airflow` |
| MLflow логирование | ✅ | MLflow server развернут |
| Алертинг >80% CPU | ✅ | Базовая конфигурация готова |
| Kafka стресс-тест | ✅ | `simple_stress_test.py` |

---

## ⚡ БЫСТРЫЙ СТАРТ ДЛЯ ПРОВЕРКИ

1. **Откройте API**: http://89.169.137.245:32134
2. **Откройте Grafana**: http://89.169.137.245:30250 (admin/admin123)
3. **Проверьте автоскейлинг**: `kubectl get hpa -n fraud-detection`
4. **Запустите стресс-тест**: `uv run simple_stress_test.py --api-url http://89.169.137.245:32134/cpu`

**Время на проверку**: ~5-10 минут

---

## 📞 КОНТАКТЫ

- **Студент**: Denis Pukinov
- **Курс**: OTUS MLOps
- **Задание**: HW_10 - Production ML Deployment
- **Дата**: 23 сентября 2025

**Статус**: ✅ **ГОТОВО К ПРОВЕРКЕ** ✅
