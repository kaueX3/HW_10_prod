# 🌊 ИНСТРУКЦИЯ ПО ПОДКЛЮЧЕНИЮ К AIRFLOW WEBSERVER

## ✅ Статус развертывания
Airflow успешно развернут и работает в Kubernetes кластере!

---

## 🌐 Способы подключения

### 1. 🔗 Через внешний IP (NodePort)

**URLs:**
- **Primary**: http://89.169.137.245:31329
- **Secondary**: http://89.169.139.226:31329

### 2. 🔧 Через port-forward (локально)

```bash
# Создать port-forward
kubectl port-forward -n airflow svc/airflow-webserver 8081:8080

# Открыть в браузере
open http://localhost:8081
```

---

## 👤 УЧЕТНЫЕ ДАННЫЕ

```
Логин: admin
Пароль: admin
```

---

## 📊 ТЕКУЩЕЕ СОСТОЯНИЕ

### Поды Airflow:
```bash
kubectl get pods -n airflow
```

**Результат:**
```
NAME                                 READY   STATUS    RESTARTS   AGE
airflow-scheduler-6744689f57-ss8sr   3/3     Running   0          5m
airflow-webserver-7586c94677-99rsd   3/3     Running   0          5m
mlflow-postgres-865d49d7d4-bvdkz     1/1     Running   0          73m
mlflow-server-5678d45fcb-dgj6t       1/1     Running   0          71m
postgres-6db9f96899-cxhvl            1/1     Running   0          74m
```

### Сервисы:
```bash
kubectl get services -n airflow
```

**Результат:**
```
NAME                TYPE           CLUSTER-IP      EXTERNAL-IP   PORT(S)          AGE
airflow-webserver   LoadBalancer   10.96.151.157   <pending>     8080:31329/TCP   5m
mlflow-postgres     ClusterIP      10.96.213.37    <none>        5432/TCP         74m
mlflow-server       ClusterIP      10.96.246.123   <none>        5000/TCP         74m
postgres            ClusterIP      10.96.248.137   <none>        5432/TCP         75m
```

---

## 🎯 КОМПОНЕНТЫ AIRFLOW

### 1. 🖥️ Webserver
- **Функция**: Web интерфейс для управления DAGs
- **Порт**: 8080 (внутренний), 31329 (внешний)
- **Статус**: ✅ Running

### 2. ⚡ Scheduler  
- **Функция**: Планировщик задач
- **Статус**: ✅ Running
- **Executor**: LocalExecutor

### 3. 🗄️ PostgreSQL
- **Функция**: База данных метаданных
- **Статус**: ✅ Running
- **Connection**: postgresql+psycopg2://airflow:airflow@postgres:5432/airflow

### 4. 🔄 Git Sync
- **Функция**: Синхронизация DAGs из Git репозитория
- **Репозиторий**: https://github.com/mrPDA/HW_9_prod.git
- **Статус**: ✅ Running

---

## 📋 ДОСТУПНЫЕ DAGs

Airflow настроен на автоматическую загрузку DAGs из Git репозитория:

### ML Model Retraining DAG
- **Файл**: `dags/ml_model_retraining_dag.py`
- **Функция**: Периодическое переобучение модели
- **Интеграция**: MLflow для логирования метрик
- **Расписание**: Ежедневно

---

## 🔧 КОМАНДЫ ДЛЯ УПРАВЛЕНИЯ

### Проверка состояния:
```bash
# Статус подов
kubectl get pods -n airflow

# Логи webserver
kubectl logs -n airflow deployment/airflow-webserver -c airflow-webserver

# Логи scheduler
kubectl logs -n airflow deployment/airflow-scheduler -c airflow-scheduler
```

### Port-forward для локального доступа:
```bash
# Airflow Webserver
kubectl port-forward -n airflow svc/airflow-webserver 8081:8080

# MLflow Server
kubectl port-forward -n airflow svc/mlflow-server 5001:5000
```

### Перезапуск компонентов:
```bash
# Перезапуск webserver
kubectl rollout restart deployment/airflow-webserver -n airflow

# Перезапуск scheduler
kubectl rollout restart deployment/airflow-scheduler -n airflow
```

---

## 🌐 ИНТЕГРАЦИЯ С ДРУГИМИ СЕРВИСАМИ

### 1. 🧪 MLflow Integration
- **URL**: http://mlflow-server.airflow.svc.cluster.local:5000
- **Функция**: Логирование экспериментов и моделей
- **Доступ через port-forward**: http://localhost:5001

### 2. 📊 Prometheus Metrics
- **Endpoint**: /admin/metrics (настраивается)
- **Мониторинг**: Автоматический сбор метрик Airflow

### 3. 🗄️ PostgreSQL
- **Host**: postgres.airflow.svc.cluster.local
- **Port**: 5432
- **Database**: airflow

---

## 🚀 БЫСТРЫЙ СТАРТ

1. **Откройте Airflow UI**: http://89.169.137.245:31329
2. **Войдите**: admin / admin
3. **Проверьте DAGs**: Должны быть загружены из Git
4. **Запустите тестовый DAG**: Для проверки работоспособности

---

## 🔍 TROUBLESHOOTING

### Если Airflow не доступен:
```bash
# Проверить статус подов
kubectl get pods -n airflow

# Проверить логи
kubectl logs -n airflow deployment/airflow-webserver -c airflow-webserver --tail=50

# Проверить сервисы
kubectl get services -n airflow
```

### Если DAGs не загружаются:
```bash
# Проверить git-sync контейнер
kubectl logs -n airflow deployment/airflow-webserver -c git-sync

# Проверить dag-processor
kubectl logs -n airflow deployment/airflow-webserver -c dag-processor
```

---

## ✅ ЗАКЛЮЧЕНИЕ

Airflow Webserver успешно развернут и готов к использованию!

**🔗 Главный URL**: http://89.169.137.245:31329  
**👤 Логин**: admin / admin

Система готова для:
- Создания и управления ML пайплайнами
- Периодического переобучения моделей
- Интеграции с MLflow для отслеживания экспериментов
- Мониторинга через Prometheus

**Статус**: ✅ **ГОТОВО К ИСПОЛЬЗОВАНИЮ** ✅
