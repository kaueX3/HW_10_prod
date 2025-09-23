# ⚡ Руководство по быстрому запуску - HW_10 Production ML система

## 🎯 Настройка за 5 минут

Запустите ML систему детекции мошенничества за 5 минут!

### 📋 Чеклист предварительных требований

- [ ] **Аккаунт Yandex Cloud** с включенным биллингом
- [ ] **yc CLI** установлен и настроен (`yc init`)
- [ ] **Terraform** установлен (`brew install terraform`)
- [ ] **kubectl** установлен (`brew install kubectl`)
- [ ] **Python 3.11+** с uv (`pip install uv`)

### 🚀 Шаг 1: Клонирование и настройка

```bash
# Клонируем репозиторий
git clone https://github.com/mrPDA/HW_10_prod.git
cd HW_10_prod

# Настраиваем учетные данные Yandex Cloud
export TF_VAR_yc_token=$(yc iam create-token)
export TF_VAR_yc_cloud_id=$(yc config get cloud-id)
export TF_VAR_yc_folder_id=$(yc config get folder-id)
```

### 🏗️ Шаг 2: Развертывание инфраструктуры

```bash
cd terraform
terraform init
terraform apply -auto-approve
```

⏱️ **Время**: ~15 минут на создание Kubernetes кластера

### ☸️ Шаг 3: Настройка Kubernetes

```bash
# Получаем учетные данные кластера
yc managed-kubernetes cluster get-credentials ml-fraud-detection-demo --external

# Проверяем подключение
kubectl get nodes
```

### 🚀 Шаг 4: Развертывание приложений

```bash
# Развертываем все компоненты
cd ..
chmod +x deploy/deploy-all.sh
./deploy/deploy-all.sh
```

⏱️ **Время**: ~5 минут на все компоненты

### 🌐 Шаг 5: Доступ к сервисам

```bash
# Получаем IP узлов
kubectl get nodes -o wide

# URL доступа (замените NODE_IP на реальный IP):
echo "🛡️ API: http://NODE_IP:32134"
echo "📊 Prometheus: http://NODE_IP:32007"
echo "📈 Grafana: http://NODE_IP:30250 (admin/admin123)"
echo "🌊 Airflow: http://NODE_IP:31329 (admin/admin)"
```

### 🧪 Шаг 6: Тестирование автоскейлинга

```bash
# Устанавливаем зависимости для тестирования
uv add aiohttp requests prometheus-client

# Запускаем стресс-тест
uv run tools/testing/simple_stress_test.py --api-url http://NODE_IP:32134/cpu --max-rps 50 --duration 180 --workers 5

# Наблюдаем за масштабированием в другом терминале
watch kubectl get hpa -n fraud-detection
```

---

## 🎯 Ожидаемые результаты

Через 20 минут у вас должно быть:

✅ **Kubernetes кластер** (2 узла) работает  
✅ **Fraud Detection API** (4 пода) отвечает  
✅ **Автоскейлинг** настроен (4-6 подов)  
✅ **Prometheus** собирает метрики  
✅ **Grafana** показывает дашборды  
✅ **Airflow** оркеструет ML пайплайны  
✅ **MLflow** отслеживает эксперименты  

### 📊 Команды проверки

```bash
# Проверяем все компоненты
kubectl get pods --all-namespaces

# Тестируем API
curl http://NODE_IP:32134/health

# Проверяем HPA
kubectl get hpa -n fraud-detection

# Просматриваем логи
kubectl logs -n fraud-detection deployment/fraud-detection-api
```

---

## 🚨 Устранение неполадок

### Частые проблемы

**1. Terraform ошибается с правами доступа**
```bash
# Проверяем конфигурацию yc
yc config list

# Перегенерируем токен
export TF_VAR_yc_token=$(yc iam create-token)
```

**2. kubectl не может подключиться**
```bash
# Заново получаем учетные данные
yc managed-kubernetes cluster get-credentials ml-fraud-detection-demo --external --force
```

**3. Поды не запускаются**
```bash
# Проверяем логи подов
kubectl describe pod POD_NAME -n NAMESPACE
kubectl logs POD_NAME -n NAMESPACE
```

**4. Внешние IP в статусе pending**
```bash
# Используем NodePort вместо этого
kubectl get services --all-namespaces
# Доступ через IP узла + NodePort
```

---

## 🧹 Очистка

После завершения тестирования:

```bash
# Уничтожаем инфраструктуру
cd terraform
terraform destroy -auto-approve
```

💰 **Важно**: Это остановит биллинг для всех ресурсов!

---

## 📚 Следующие шаги

1. **📋 Читайте полную документацию**: [README.md](README.md)
2. **🔧 Настройте конфигурацию**: Редактируйте манифесты `k8s/`
3. **🌊 Настройте Airflow DAGs**: См. [AIRFLOW_ACCESS_GUIDE.md](AIRFLOW_ACCESS_GUIDE.md)
4. **🔒 Настройте безопасность**: Просмотрите [раздел безопасности](README.md#соображения-безопасности)
5. **📊 Настройте мониторинг**: Настройте дашборды Grafana

---

## 🆘 Нужна помощь?

- **📖 Полная документация**: [README.md](README.md)
- **🐛 Проблемы**: [GitHub Issues](https://github.com/mrPDA/HW_10_prod/issues)
- **💬 Обсуждения**: [GitHub Discussions](https://github.com/mrPDA/HW_10_prod/discussions)

---

**🎉 Поздравляем!** Теперь у вас работает production-ready ML система! 🚀