# 🔐 РАБОТА С ПРИВАТНЫМИ GIT РЕПОЗИТОРИЯМИ В AIRFLOW

## 📋 Ответ на ваш вопрос

**Git репозиторий может быть как публичным, так и приватным!** 

Текущая конфигурация использует **публичный репозиторий**, но можно легко настроить работу с **приватными репозиториями**.

---

## 🌐 ТЕКУЩАЯ НАСТРОЙКА (Публичный репозиторий)

### ✅ Что работает сейчас:
- **Репозиторий**: https://github.com/mrPDA/HW_9_prod.git (публичный)
- **Протокол**: HTTPS без аутентификации
- **Статус**: ✅ Работает успешно

```bash
# Проверить текущее состояние
kubectl logs -n airflow deployment/airflow-webserver -c git-sync --tail=5
```

---

## 🔐 ВАРИАНТЫ ДЛЯ ПРИВАТНЫХ РЕПОЗИТОРИЕВ

### 1. 🔑 SSH ключи (Рекомендуется)

#### Шаг 1: Создание SSH ключа
```bash
# Генерация SSH ключа (если нет)
ssh-keygen -t rsa -b 4096 -C "airflow@k8s-cluster"

# Добавление публичного ключа в GitHub
cat ~/.ssh/id_rsa.pub
# Скопировать и добавить в GitHub -> Settings -> SSH Keys
```

#### Шаг 2: Создание Kubernetes Secret
```bash
# Создание secret с SSH ключом
kubectl create secret generic git-ssh-key \
  --from-file=ssh-privatekey=~/.ssh/id_rsa \
  --from-file=known_hosts=<(ssh-keyscan github.com) \
  -n airflow

# Проверка secret
kubectl get secret git-ssh-key -n airflow -o yaml
```

#### Шаг 3: Обновление deployment
```yaml
# В git-sync контейнере:
env:
- name: GIT_SYNC_REPO
  value: "git@github.com:username/private-repo.git"  # SSH URL
- name: GIT_SYNC_SSH
  value: "true"
- name: GIT_SSH_KEY_FILE
  value: "/etc/git-secret/ssh-privatekey"

volumeMounts:
- name: git-ssh-key
  mountPath: /etc/git-secret
  readOnly: true
```

### 2. 🎫 Personal Access Token

#### Шаг 1: Создание токена в GitHub
1. GitHub -> Settings -> Developer settings -> Personal access tokens
2. Generate new token (classic)
3. Выбрать scope: `repo` (Full control of private repositories)

#### Шаг 2: Создание Secret в Kubernetes
```bash
# Создание secret с токеном
kubectl create secret generic git-credentials \
  --from-literal=token=YOUR_PERSONAL_ACCESS_TOKEN \
  -n airflow
```

#### Шаг 3: Использование в git-sync
```yaml
env:
- name: GIT_SYNC_REPO
  value: "https://username:$(GIT_TOKEN)@github.com/username/private-repo.git"
- name: GIT_TOKEN
  valueFrom:
    secretKeyRef:
      name: git-credentials
      key: token
```

### 3. 📝 Username/Password

```bash
# Создание secret с логином/паролем
kubectl create secret generic git-auth \
  --from-literal=username=YOUR_USERNAME \
  --from-literal=password=YOUR_PASSWORD \
  -n airflow
```

---

## 🚀 БЫСТРАЯ НАСТРОЙКА ПРИВАТНОГО РЕПОЗИТОРИЯ

### Вариант A: SSH (Безопаснее)

```bash
# 1. Создание SSH secret
kubectl create secret generic git-ssh-key \
  --from-file=ssh-privatekey=~/.ssh/id_rsa \
  --from-file=known_hosts=<(ssh-keyscan github.com) \
  -n airflow

# 2. Применение конфигурации
kubectl apply -f k8s/airflow/airflow-private-git-deployment.yaml

# 3. Обновление URL репозитория в deployment
kubectl patch deployment airflow-webserver-private -n airflow -p '
{
  "spec": {
    "template": {
      "spec": {
        "containers": [
          {
            "name": "git-sync-private",
            "env": [
              {
                "name": "GIT_SYNC_REPO",
                "value": "git@github.com:USERNAME/PRIVATE_REPO.git"
              }
            ]
          }
        ]
      }
    }
  }
}'
```

### Вариант B: Personal Access Token (Проще)

```bash
# 1. Создание secret с токеном
kubectl create secret generic git-credentials \
  --from-literal=token=ghp_xxxxxxxxxxxxxxxxxxxx \
  -n airflow

# 2. Обновление существующего deployment
kubectl patch deployment airflow-webserver -n airflow -p '
{
  "spec": {
    "template": {
      "spec": {
        "containers": [
          {
            "name": "git-sync",
            "env": [
              {
                "name": "GIT_SYNC_REPO",
                "value": "https://username:$(GIT_TOKEN)@github.com/username/private-repo.git"
              },
              {
                "name": "GIT_TOKEN",
                "valueFrom": {
                  "secretKeyRef": {
                    "name": "git-credentials",
                    "key": "token"
                  }
                }
              }
            ]
          }
        ]
      }
    }
  }
}'
```

---

## 🔍 ПРОВЕРКА И ДИАГНОСТИКА

### Проверка синхронизации:
```bash
# Логи git-sync
kubectl logs -n airflow deployment/airflow-webserver -c git-sync --tail=20

# Логи dag-processor
kubectl logs -n airflow deployment/airflow-webserver -c dag-processor --tail=10

# Проверка DAGs в Airflow
kubectl exec -n airflow deployment/airflow-webserver -c airflow-webserver -- ls -la /opt/airflow/dags/
```

### Типичные ошибки:

#### 1. SSH: Permission denied
```bash
# Проверить права на SSH ключ
kubectl exec -n airflow deployment/airflow-webserver -c git-sync -- ls -la /etc/git-secret/

# Должно быть: -rw------- (600)
```

#### 2. HTTPS: Authentication failed
```bash
# Проверить токен
kubectl get secret git-credentials -n airflow -o jsonpath='{.data.token}' | base64 -d

# Проверить URL
kubectl logs -n airflow deployment/airflow-webserver -c git-sync | grep "cloning repo"
```

#### 3. Repository not found
```bash
# Проверить URL репозитория
# SSH: git@github.com:username/repo.git
# HTTPS: https://github.com/username/repo.git
```

---

## 📊 СРАВНЕНИЕ МЕТОДОВ

| Метод | Безопасность | Простота | Рекомендация |
|-------|-------------|----------|--------------|
| **SSH ключи** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 🏆 **Лучший** для production |
| **Personal Access Token** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ **Хорошо** для dev/test |
| **Username/Password** | ⭐⭐ | ⭐⭐⭐⭐ | ❌ Не рекомендуется |

---

## 🎯 РЕКОМЕНДАЦИИ

### Для Production:
1. **Используйте SSH ключи** с ограниченными правами
2. **Ротируйте ключи** регулярно
3. **Используйте отдельные ключи** для каждого кластера
4. **Мониторьте доступ** к репозиторию

### Для Development:
1. **Personal Access Token** достаточно
2. **Ограничьте scope** токена только нужными правами
3. **Используйте временные токены** для тестирования

---

## 💡 ТЕКУЩАЯ РЕКОМЕНДАЦИЯ ДЛЯ HW_10

**Для демонстрации HW_10 можно оставить публичный репозиторий**, так как:

✅ **Плюсы публичного репозитория:**
- Простота настройки
- Нет проблем с аутентификацией
- Проще для проверяющего
- Быстрее развертывание

🔐 **Если нужен приватный репозиторий:**
1. Используйте Personal Access Token (проще)
2. Или SSH ключи (безопаснее)
3. Следуйте инструкциям выше

---

## 🔧 КОМАНДЫ ДЛЯ ПЕРЕКЛЮЧЕНИЯ

### На приватный репозиторий с токеном:
```bash
# 1. Создать токен в GitHub
# 2. Создать secret
kubectl create secret generic git-credentials --from-literal=token=YOUR_TOKEN -n airflow

# 3. Обновить deployment
kubectl patch deployment airflow-webserver -n airflow --patch-file private-git-patch.yaml
```

### Вернуться к публичному:
```bash
# Откатить к оригинальной конфигурации
kubectl rollout undo deployment/airflow-webserver -n airflow
```

---

## ✅ ЗАКЛЮЧЕНИЕ

**Ответ**: Git репозиторий для Airflow DAGs может быть **как публичным, так и приватным**. 

- **Текущая настройка**: ✅ Публичный репозиторий (работает)
- **Приватный репозиторий**: ✅ Поддерживается через SSH или токены
- **Рекомендация для HW_10**: Публичный репозиторий (проще для демонстрации)

Если нужно переключиться на приватный - используйте инструкции выше! 🚀
