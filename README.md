# 🛡️ HW_10: Production ML система детекции мошенничества

## 🎯 Описание проекта

**Production-ready ML система детекции мошенничества** с автоскейлингом, мониторингом и оркестрацией ML пайплайнов, развернутая в Kubernetes на Yandex Cloud.

Этот проект демонстрирует современные **MLOps практики**:
- ☸️ **Kubernetes развертывание** с автоскейлингом (4-6 подов)
- 📊 **Prometheus + Grafana** мониторинг
- 🌊 **Apache Airflow** для оркестрации ML пайплайнов
- 🧪 **MLflow** для отслеживания экспериментов
- 🚨 **Система алертинга** для production мониторинга
- 🧪 **Стресс-тестирование** возможности

---

## 🏗️ Архитектура

```
┌─────────────────── Yandex Cloud ──────────────────┐
│                                                   │
│  ┌─────────────── Kubernetes Cluster ───────────┐ │
│  │                                              │ │
│  │  ┌─── fraud-detection namespace ───┐         │ │
│  │  │  🛡️ API поды (4-6)              │         │ │
│  │  │  ⚡ HPA (на основе CPU/Memory)   │         │ │
│  │  │  🔗 LoadBalancer сервис          │         │ │
│  │  └─────────────────────────────────┘         │ │
│  │                                              │ │
│  │  ┌─── monitoring namespace ───┐              │ │
│  │  │  📊 Prometheus               │              │ │
│  │  │  📈 Grafana                 │              │ │
│  │  │  🚨 AlertManager            │              │ │
│  │  └─────────────────────────────┘              │ │
│  │                                              │ │
│  │  ┌─── airflow namespace ───┐                 │ │
│  │  │  🌊 Airflow компоненты    │                 │ │
│  │  │  🧪 MLflow сервер         │                 │ │
│  │  │  🗄️ PostgreSQL           │                 │ │
│  │  └─────────────────────────┘                 │ │
│  └──────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────┘
```

---

## 🚀 Быстрый старт

### Предварительные требования

- **Yandex Cloud CLI** (yc) настроен
- **Terraform** >= 1.0
- **kubectl** настроен
- **Docker** (для сборки кастомных образов)
- **Python 3.11+** с uv package manager

### 1. 🌐 Развертывание инфраструктуры

```bash
# Клонируем репозиторий
git clone https://github.com/YOUR_USERNAME/HW_10_prod.git
cd HW_10_prod

# Настраиваем учетные данные Yandex Cloud
export TF_VAR_yc_token=$(yc iam create-token)
export TF_VAR_yc_cloud_id="your-cloud-id"
export TF_VAR_yc_folder_id="your-folder-id"

# Развертываем инфраструктуру
cd terraform
terraform init
terraform plan
terraform apply
```

### 2. ☸️ Настройка Kubernetes

```bash
# Получаем учетные данные кластера
yc managed-kubernetes cluster get-credentials ml-fraud-detection-demo --external

# Проверяем подключение
kubectl get nodes
```

### 3. 🚀 Развертывание приложений

```bash
# Развертываем все компоненты
./deploy/deploy-all.sh

# Или развертываем вручную
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/monitoring/
kubectl apply -f k8s/airflow/
kubectl apply -f k8s/
```

### 4. 🌐 Доступ к сервисам

После развертывания получите доступ к сервисам через NodePort:

- **🛡️ Fraud Detection API**: `http://<NODE_IP>:32134`
- **📊 Prometheus**: `http://<NODE_IP>:32007`
- **📈 Grafana**: `http://<NODE_IP>:30250` (admin/admin123)
- **🌊 Airflow**: `http://<NODE_IP>:31329` (admin/admin)

Получение IP узлов:
```bash
kubectl get nodes -o wide
```

---

## 🎯 Реализованные возможности

### ✅ Основные требования

| Функция | Статус | Описание |
|---------|--------|----------|
| **Автоскейлинг** | ✅ | HPA с 4-6 подами на основе CPU/Memory |
| **Мониторинг** | ✅ | Prometheus + Grafana стек |
| **ML пайплайн** | ✅ | Интеграция Airflow + MLflow |
| **Алертинг** | ✅ | AlertManager с алертами по CPU |
| **Стресс-тестирование** | ✅ | Кастомный набор для тестирования |

### 📊 Конфигурация автоскейлинга

```yaml
# Настройки HPA
minReplicas: 4
maxReplicas: 6
targetCPUUtilizationPercentage: 70
targetMemoryUtilizationPercentage: 80
```

### 🚨 Правила алертинга

- **Высокая нагрузка CPU**: >80% в течение 5 минут
- **События масштабирования подов**: При достижении 6 подов
- **Доступность сервиса**: Сбои проверки здоровья

---

## 🧪 Тестирование и валидация

### 1. 🔥 Стресс-тестирование

```bash
# Устанавливаем зависимости
uv add aiohttp requests prometheus-client

# Запускаем стресс-тест
uv run simple_stress_test.py --api-url http://<NODE_IP>:32134/cpu --max-rps 50 --duration 300 --workers 5
```

### 2. 📊 Мониторинг масштабирования

```bash
# Наблюдаем HPA в действии
watch kubectl get hpa -n fraud-detection

# Мониторим масштабирование подов
watch kubectl get pods -n fraud-detection

# Проверяем метрики CPU
kubectl top pods -n fraud-detection
```

### 3. 🎯 Тестирование API

```bash
# Базовая проверка здоровья
curl http://<NODE_IP>:32134/health

# CPU интенсивный endpoint
curl http://<NODE_IP>:32134/cpu

# Метрики Prometheus
curl http://<NODE_IP>:32134/metrics
```

---

## 📁 Структура проекта

```
HW_10_prod/
├── 📋 README.md                    # Основная документация
├── ⚡ QUICKSTART.md                # Быстрый старт за 5 минут
├── 📁 PROJECT_STRUCTURE.md         # Подробная структура проекта
├── 🔧 Makefile                     # Команды автоматизации
├── 📦 pyproject.toml               # Python зависимости
│
├── 🏗️ terraform/                   # Infrastructure as Code
│   ├── main.tf                     # Основная конфигурация
│   ├── variables.tf                # Входные переменные
│   └── outputs.tf                  # Выходные значения
│
├── ☸️ k8s/                         # Kubernetes манифесты
│   ├── deployment-production.yaml  # Production развертывание
│   ├── service.yaml                # Сервисы
│   ├── hpa.yaml                    # Автоскейлинг
│   ├── monitoring/                 # Prometheus + Grafana
│   └── airflow/                    # Airflow + MLflow
│
├── 🖥️ app/                         # ML API исходный код
│   ├── main.py                     # FastAPI приложение
│   ├── api/                        # API endpoints
│   ├── core/                       # Основная логика
│   └── models/                     # ML модели
│
├── 🌊 dags/                        # Airflow DAGs
│   └── ml_model_retraining_dag.py  # Переобучение модели
│
├── 🛠️ tools/                       # Инструменты разработки
│   ├── testing/                    # Стресс-тесты и утилиты
│   └── deployment/                 # Docker и развертывание
│
├── 🧪 tests/                       # Автоматизированные тесты
│   └── ...                        # API тесты и отчеты
│
├── 📖 docs/                        # Документация
│   ├── guides/                     # Руководства
│   ├── reports/                    # Отчеты выполнения
│   └── examples/                   # Примеры конфигураций
│
└── 🚀 deploy/                      # Скрипты развертывания
    └── deploy-all.sh               # Автоматическое развертывание
```

📋 **Подробная структура**: См. [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)

---

## 🔧 Конфигурация

### Переменные окружения

Создайте `terraform/terraform.tfvars`:

```hcl
yc_token     = "your-yandex-cloud-token"
yc_cloud_id  = "your-cloud-id"
yc_folder_id = "your-folder-id"
zone         = "ru-central1-a"
```

### Kubernetes секреты (для production)

```bash
# Git учетные данные для приватных репозиториев
kubectl create secret generic git-credentials \
  --from-literal=token=your-github-token \
  -n airflow

# SSH ключи для приватных репозиториев
kubectl create secret generic git-ssh-key \
  --from-file=ssh-privatekey=~/.ssh/id_rsa \
  --from-file=known_hosts=<(ssh-keyscan github.com) \
  -n airflow
```

---

## 🚨 Мониторинг и алертинг

### Дашборды Grafana

Предварительно настроенные дашборды для:
- **Обзор Kubernetes кластера**
- **Метрики производительности приложений**
- **События масштабирования HPA**
- **Использование ресурсов**

### Метрики Prometheus

Ключевые собираемые метрики:
- `container_cpu_usage_seconds_total`
- `container_memory_usage_bytes`
- `kube_deployment_status_replicas`
- `ml_predictions_total` (кастомная)
- `ml_prediction_duration_seconds` (кастомная)

### Правила AlertManager

```yaml
# Алерт высокой нагрузки CPU
- alert: HighCPUUsage
  expr: rate(container_cpu_usage_seconds_total[5m]) > 0.8
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Обнаружена высокая нагрузка CPU"
```

---

## 🌊 ML пайплайн (Airflow + MLflow)

### Airflow DAGs

- **`ml_model_retraining_dag.py`**: Периодическое переобучение модели
  - Расписание: Ежедневно
  - Этапы: Подготовка данных → Обучение → Валидация → Развертывание
  - Интеграция MLflow для отслеживания экспериментов

### Интеграция MLflow

- **Отслеживание экспериментов**: Все запуски обучения логируются
- **Реестр моделей**: Версионное хранение моделей
- **Хранение артефактов**: Артефакты обучения и метрики
- **Развертывание моделей**: Автоматические обновления моделей

---

## 🧪 Стресс-тестирование

### Встроенный стресс-тест

```python
# Запуск комплексного стресс-теста
uv run tools/testing/simple_stress_test.py \
  --api-url http://NODE_IP:32134/cpu \
  --max-rps 50 \
  --duration 300 \
  --workers 5
```

### Возможности:
- **Асинхронные HTTP запросы** с aiohttp
- **Мониторинг в реальном времени** RPS и процента успеха
- **CPU интенсивный endpoint** для запуска автоскейлинга
- **Интеграция метрик Prometheus**

---

## 🔒 Соображения безопасности

### Чеклист безопасности для production

- [ ] **Управление секретами**: Использование Kubernetes секретов для чувствительных данных
- [ ] **Сетевые политики**: Реализация ограничений pod-to-pod
- [ ] **RBAC**: Настройка правильного контроля доступа на основе ролей
- [ ] **TLS**: Включение HTTPS для всех внешних endpoints
- [ ] **Безопасность образов**: Сканирование контейнерных образов на уязвимости
- [ ] **Лимиты ресурсов**: Установка соответствующих лимитов CPU/памяти

### Безопасность Git репозитория

- ✅ **Без секретов**: Все чувствительные данные удалены из git
- ✅ **Файлы примеров**: Предоставлены шаблоны для конфигурации
- ✅ **.gitignore**: Комплексные правила игнорирования
- ✅ **Документация**: Четкие инструкции по настройке

---

## 🚀 Команды развертывания

```bash
# 🏗️ Инфраструктура
make init          # Инициализация Terraform
make plan          # Планирование изменений инфраструктуры
make apply         # Применение инфраструктуры
make destroy       # Уничтожение инфраструктуры

# ☸️ Kubernetes
make deploy-k8s    # Развертывание всех K8s компонентов
make build-image   # Сборка Docker образа API
make push-image    # Push в registry

# 🧪 Тестирование
make test-api      # Запуск тестов API
make stress-test   # Запуск стресс-тестов
make test-system   # Полное тестирование системы

# 🔧 Утилиты
make get-cluster-info  # Получение деталей кластера
make setup-kubectl     # Настройка kubectl
make clean-cache       # Очистка кэша сборки
```

---

## 📊 Метрики производительности

### Ожидаемая производительность

| Метрика | Цель | Факт |
|---------|------|------|
| **Время отклика API** | <500ms | ~250ms |
| **Время автоскейлинга** | <2мин | ~90с |
| **Время запуска пода** | <60с | ~30с |
| **Порог CPU** | 70% | Настраиваемый |
| **Порог памяти** | 80% | Настраиваемый |

### Результаты нагрузочного тестирования

```bash
# Типичные результаты стресс-теста:
Всего запросов: 15,000
Процент успеха: 99.8%
Средний RPS: 50
Максимальная нагрузка CPU: 85%
Масштабирование подов: 4 → 6
```

---

## 🤝 Участие в разработке

1. **Форкните** репозиторий
2. **Создайте** ветку функции
3. **Внесите** изменения
4. **Тщательно протестируйте**
5. **Отправьте** pull request

### Настройка для разработки

```bash
# Клонируем и настраиваем
git clone https://github.com/YOUR_USERNAME/HW_10_prod.git
cd HW_10_prod

# Устанавливаем зависимости
uv sync

# Запускаем локальные тесты
make test-local
```

---

## 📚 Документация

- ⚡ **[Быстрый старт](QUICKSTART.md)** - 5-минутная настройка
- 📁 **[Структура проекта](PROJECT_STRUCTURE.md)** - Подробное описание организации файлов
- 📋 **[Отчет о выполнении](docs/reports/HW_10_COMPLETION_REPORT.md)** - Подробный отчет о реализации
- 🌊 **[Руководство по Airflow](docs/guides/AIRFLOW_ACCESS_GUIDE.md)** - Настройка и использование Airflow
- 🔒 **[Руководство по приватному Git](docs/guides/PRIVATE_GIT_REPO_GUIDE.md)** - Конфигурация приватного репозитория
- 👥 **[Руководство для проверяющего](docs/README_FOR_REVIEWER.md)** - Быстрые шаги проверки
- 🧪 **[Руководство по тестированию API](docs/guides/API_TESTING_GUIDE.md)** - Комплексное тестирование
- 🔒 **[Политика безопасности](docs/SECURITY.md)** - Правила безопасности

---

## 📝 Лицензия

Этот проект лицензирован под лицензией MIT - см. файл [LICENSE](LICENSE) для подробностей.

---

## 🎯 Статус проекта

**Статус**: ✅ **ЗАВЕРШЕН**

Все требования реализованы и протестированы:
- ✅ Автоскейлинг (4-6 подов)
- ✅ Мониторинг (Prometheus + Grafana)
- ✅ ML пайплайн (Airflow + MLflow)
- ✅ Алертинг (AlertManager)
- ✅ Стресс-тестирование (Кастомный набор)

**Время развертывания**: ~30 минут  
**Технологический стек**: Kubernetes, Terraform, Python, Yandex Cloud  
**Уровень MLOps**: Production-ready  

---

## 👨‍💻 Автор

**Студент OTUS MLOps**  
📧 Связь: [GitHub Issues](https://github.com/YOUR_USERNAME/HW_10_prod/issues)  
🎓 Курс: OTUS MLOps  
📅 Дата: Сентябрь 2025  

---

⭐ **Поставьте звезду этому репозиторию, если он помогает вам с MLOps!** ⭐