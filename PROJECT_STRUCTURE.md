# 📁 Структура проекта HW_10_prod

## 🏗️ Организация файлов

```
HW_10_prod/
├── 📋 README.md                    # Основная документация проекта
├── ⚡ QUICKSTART.md                # Руководство по быстрому запуску
├── 📝 LICENSE                      # MIT лицензия
├── 🔧 Makefile                     # Команды автоматизации
├── 📦 pyproject.toml               # Python зависимости (uv)
├── 🔒 .gitignore                   # Правила игнорирования Git
├── 🐍 .python-version              # Версия Python
├── 🔐 uv.lock                      # Блокировка зависимостей
│
├── 🏗️ terraform/                   # Infrastructure as Code
│   ├── main.tf                     # Основная конфигурация
│   ├── variables.tf                # Входные переменные
│   ├── outputs.tf                  # Выходные значения
│   └── terraform.tfvars.example    # Пример переменных (в docs/examples/)
│
├── ☸️ k8s/                         # Kubernetes манифесты
│   ├── namespace.yaml              # Пространства имен
│   ├── deployment-production.yaml  # Production развертывание
│   ├── service.yaml                # Сервисы
│   ├── hpa.yaml                    # Horizontal Pod Autoscaler
│   ├── configmap.yaml              # Конфигурация
│   │
│   ├── 📊 monitoring/              # Стек мониторинга
│   │   ├── prometheus-deployment.yaml
│   │   ├── prometheus-config.yaml
│   │   ├── grafana-deployment.yaml
│   │   └── alertmanager.yaml
│   │
│   └── 🌊 airflow/                 # Airflow и MLflow
│       ├── airflow-deployment.yaml
│       ├── postgres.yaml
│       ├── simple-mlflow.yaml
│       └── airflow-private-git-deployment.yaml
│
├── 🌊 dags/                        # Airflow DAGs
│   ├── ml_model_retraining_dag.py  # Основной DAG переобучения
│   └── ml_pipeline/                # Дополнительные DAGs
│       └── ...
│
├── 🚀 deploy/                      # Скрипты развертывания
│   └── deploy-all.sh               # Автоматическое развертывание
│
├── 🖥️ app/                         # Исходный код ML API
│   ├── main.py                     # Основное приложение FastAPI
│   ├── requirements.txt            # Python зависимости API
│   ├── api/                        # API endpoints
│   │   ├── __init__.py
│   │   ├── health.py               # Health check endpoints
│   │   └── metrics.py              # Metrics endpoints
│   ├── core/                       # Основная логика
│   │   ├── __init__.py
│   │   ├── config.py               # Конфигурация
│   │   └── logging.py              # Логирование
│   └── models/                     # ML модели
│       ├── __init__.py
│       └── fraud_detector.py       # Модель детекции мошенничества
│
├── 🧪 tests/                       # Тесты
│   ├── requirements.txt            # Зависимости для тестирования
│   ├── test_public_api.py          # Тесты публичного API
│   ├── report_generator.py         # Генератор отчетов
│   ├── load_test.py                # Нагрузочные тесты
│   └── run_api_tests.py            # Основной скрипт тестирования
│
├── 📊 scripts/                     # Вспомогательные скрипты
│   ├── kafka_stress_test.py        # Kafka стресс-тест
│   └── ...                        # Другие утилитарные скрипты
│
├── 🛠️ tools/                       # Инструменты разработки
│   ├── main.py                     # Утилитарный скрипт
│   │
│   ├── 🧪 testing/                 # Инструменты тестирования
│   │   ├── simple_stress_test.py   # Простой стресс-тест
│   │   ├── simple_test.py          # Простые тесты
│   │   ├── run_api_tests.sh        # Скрипт запуска тестов
│   │   ├── test-ci-local.sh        # Локальный CI тест
│   │   └── test-complete-system.sh # Полное тестирование системы
│   │
│   └── 🚀 deployment/              # Инструменты развертывания
│       ├── Dockerfile              # Docker образ
│       ├── docker-compose.yml      # Docker Compose для локального запуска
│       └── demo_deployment.yaml    # Демонстрационное развертывание
│
├── 📖 docs/                        # Документация
│   ├── README_FOR_REVIEWER.md      # Руководство для проверяющего
│   ├── README_PUBLIC.md            # Публичная версия README
│   ├── SECURITY.md                 # Политика безопасности
│   │
│   ├── 📚 guides/                  # Руководства
│   │   ├── AIRFLOW_ACCESS_GUIDE.md          # Доступ к Airflow
│   │   ├── API_TESTING_GUIDE.md             # Тестирование API
│   │   ├── PRIVATE_GIT_REPO_GUIDE.md        # Приватные Git репозитории
│   │   ├── CI_CD_SETUP_COMPLETE.md          # Настройка CI/CD
│   │   └── GITHUB_SETUP.md                  # Настройка GitHub
│   │
│   ├── 📊 reports/                 # Отчеты
│   │   ├── HW_10_COMPLETION_REPORT.md       # Отчет о выполнении
│   │   └── ПРОЕКТ_ЗАВЕРШЕН.md               # Финальный отчет
│   │
│   └── 📝 examples/                # Примеры конфигураций
│       ├── terraform.tfvars.example         # Пример Terraform переменных
│       ├── env.example                      # Пример переменных окружения
│       ├── kubeconfig.example.yaml          # Пример kubeconfig
│       └── github-actions-setup.example.json # Пример GitHub Actions
│
├── 📊 artifacts/                   # Артефакты и доказательства
│   └── evidence/                   # Доказательства выполнения
│       ├── cluster_status.txt      # Статус кластера
│       ├── api_tests.txt           # Результаты тестов API
│       ├── deployment_checklist.md # Чеклист развертывания
│       └── system_urls.txt         # URL доступа к системе
│
└── 📊 monitoring/                  # Конфигурации мониторинга (legacy)
    └── prometheus.yml              # Prometheus конфигурация
```

---

## 🎯 Описание папок

### 📁 Основные директории

- **`terraform/`** - Infrastructure as Code для Yandex Cloud
- **`k8s/`** - Kubernetes манифесты для всех компонентов
- **`app/`** - Исходный код ML API на FastAPI
- **`dags/`** - Airflow DAGs для ML пайплайнов
- **`deploy/`** - Скрипты автоматического развертывания

### 🛠️ Инструменты разработки

- **`tools/testing/`** - Все инструменты для тестирования
- **`tools/deployment/`** - Docker файлы и конфигурации развертывания
- **`tests/`** - Автоматизированные тесты
- **`scripts/`** - Вспомогательные скрипты

### 📖 Документация

- **`docs/guides/`** - Подробные руководства
- **`docs/reports/`** - Отчеты о выполнении
- **`docs/examples/`** - Примеры конфигураций
- **`artifacts/`** - Доказательства и артефакты выполнения

---

## 🚀 Быстрая навигация

### Для начала работы:
1. **README.md** - Основная документация
2. **QUICKSTART.md** - Быстрый старт за 5 минут
3. **docs/examples/** - Примеры конфигураций

### Для развертывания:
1. **terraform/** - Создание инфраструктуры
2. **k8s/** - Kubernetes манифесты
3. **deploy/deploy-all.sh** - Автоматическое развертывание

### Для разработки:
1. **app/** - Исходный код API
2. **tools/testing/** - Инструменты тестирования
3. **tools/deployment/** - Docker конфигурации

### Для изучения:
1. **docs/guides/** - Подробные руководства
2. **docs/reports/** - Отчеты о выполнении
3. **artifacts/evidence/** - Доказательства работы

---

## 📋 Файлы в корне

В корне проекта остались только самые важные файлы:
- **README.md** - Главная документация
- **QUICKSTART.md** - Быстрый старт
- **LICENSE** - Лицензия проекта
- **Makefile** - Команды автоматизации
- **pyproject.toml** - Python зависимости
- **.gitignore** - Правила Git

Это обеспечивает чистоту и профессиональный вид репозитория! 🎯
