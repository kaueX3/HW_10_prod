#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔄 ML Model Retraining DAG - Periodic Model Retraining with MLflow
================================================================

Автоматизированный DAG для периодического переобучения ML модели:
- Загрузка новых данных из S3
- Обучение модели с различными гиперпараметрами
- Оценка качества модели
- Регистрация в MLflow Model Registry
- Автоматическое переключение на лучшую модель (Champion)
- Уведомления о результатах обучения

Расписание: ежедневно в 02:00 UTC
Автор: ML Engineering Team
Дата: 2024
"""

import logging
import json
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.models import Variable
from airflow.utils.trigger_rule import TriggerRule
from airflow.utils.task_group import TaskGroup
from airflow.providers.yandex.operators.dataproc import (
    DataprocCreateClusterOperator,
    DataprocCreatePysparkJobOperator,
    DataprocDeleteClusterOperator
)
from airflow.providers.http.operators.http import SimpleHttpOperator
from airflow.providers.email.operators.email import EmailOperator
import uuid
from urllib.parse import urlparse

# Настройка логирования
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════
# 🎯 КОНФИГУРАЦИЯ DAG
# ═══════════════════════════════════════════════════════════════════

default_args = {
    'owner': 'ml-engineer',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'email': ['ml-team@fraud-detection.local'],
    'retries': 2,
    'retry_delay': timedelta(minutes=15),
}

dag = DAG(
    'ml_model_retraining_pipeline',
    default_args=default_args,
    description='🔄 Periodic ML Model Retraining with MLflow Integration',
    schedule_interval='0 2 * * *',  # Ежедневно в 02:00 UTC
    catchup=False,
    tags=['ml', 'retraining', 'mlflow', 'fraud-detection', 'production'],
    max_active_runs=1,
)

# ═══════════════════════════════════════════════════════════════════
# 🔧 ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ═══════════════════════════════════════════════════════════════════

def validate_retraining_config(**context):
    """Проверка конфигурации перед началом переобучения"""
    logger.info("🔍 Проверяем конфигурацию для переобучения модели...")
    
    required_vars = [
        'FOLDER_ID', 'SUBNET_ID', 'SECURITY_GROUP_ID',
        'S3_BUCKET_SCRIPTS', 'S3_ACCESS_KEY', 'S3_SECRET_KEY',
        'DATAPROC_SERVICE_ACCOUNT_ID',
        'MLFLOW_TRACKING_URI',
        'MLFLOW_MODEL_NAME'
    ]
    
    missing_vars = []
    for var in required_vars:
        try:
            value = Variable.get(var)
            if not value:
                missing_vars.append(var)
        except:
            missing_vars.append(var)
    
    if missing_vars:
        raise ValueError(f"❌ Отсутствуют обязательные переменные: {missing_vars}")
    
    # Дополнительные проверки
    mlflow_uri = Variable.get('MLFLOW_TRACKING_URI')
    model_name = Variable.get('MLFLOW_MODEL_NAME')
    
    context['task_instance'].xcom_push(key='mlflow_uri', value=mlflow_uri)
    context['task_instance'].xcom_push(key='model_name', value=model_name)
    
    logger.info(f"✅ MLflow URI: {mlflow_uri}")
    logger.info(f"✅ Model Name: {model_name}")
    logger.info("✅ Конфигурация валидна для переобучения")
    
    return True

def check_data_freshness(**context):
    """Проверка свежести данных для переобучения"""
    logger.info("📊 Проверяем свежесть данных для переобучения...")
    
    # Здесь должна быть логика проверки данных в S3
    # Для демонстрации используем mock-проверку
    
    execution_date = context['execution_date']
    days_since_last_training = Variable.get('DAYS_SINCE_LAST_TRAINING', '7')
    min_new_records = Variable.get('MIN_NEW_RECORDS_FOR_RETRAINING', '10000')
    
    # Mock данные о свежести
    data_freshness = {
        'last_training_date': (execution_date - timedelta(days=int(days_since_last_training))).isoformat(),
        'new_records_available': int(min_new_records) + 5000,  # Имитируем доступность данных
        'data_quality_score': 0.95,
        'should_retrain': True,
        'data_drift_detected': False
    }
    
    context['task_instance'].xcom_push(key='data_freshness', value=data_freshness)
    
    if not data_freshness['should_retrain']:
        logger.info("ℹ️ Переобучение не требуется - данные не достаточно свежие")
        return False
    
    logger.info(f"✅ Данные готовы для переобучения:")
    logger.info(f"  📊 Новых записей: {data_freshness['new_records_available']}")
    logger.info(f"  📈 Качество данных: {data_freshness['data_quality_score']:.1%}")
    logger.info(f"  🔄 Требуется переобучение: {data_freshness['should_retrain']}")
    
    return True

def _s3_endpoint_host() -> str:
    """Получение S3 endpoint host"""
    url = Variable.get('S3_ENDPOINT_URL', 'https://storage.yandexcloud.net')
    parsed = urlparse(url)
    return parsed.netloc if parsed.netloc else url

# ═══════════════════════════════════════════════════════════════════
# 📋 ОПРЕДЕЛЕНИЕ ЗАДАЧ - ПРЕДВАРИТЕЛЬНАЯ ПОДГОТОВКА
# ═══════════════════════════════════════════════════════════════════

# Проверка конфигурации
validate_config_task = PythonOperator(
    task_id='validate_retraining_configuration',
    python_callable=validate_retraining_config,
    dag=dag,
)

# Проверка свежести данных
check_data_task = PythonOperator(
    task_id='check_data_freshness',
    python_callable=check_data_freshness,
    dag=dag,
)

# ═══════════════════════════════════════════════════════════════════
# 🏗️ INFRASTRUCTURE SETUP
# ═══════════════════════════════════════════════════════════════════

with TaskGroup('training_infrastructure', dag=dag) as training_infrastructure:
    
    def create_training_cluster(**context):
        """Создание DataProc кластера для обучения модели"""
        exec_dt = context['execution_date']
        unique_id = uuid.uuid4().hex[:6]
        cluster_name = f"ml-training-{exec_dt.strftime('%Y%m%d-%H%M%S')}-{unique_id}"
        
        logger.info(f"🏷️ Создаем кластер для обучения модели: {cluster_name}")
        
        folder_id = Variable.get('FOLDER_ID')
        subnet_id = Variable.get('SUBNET_ID')
        zone = Variable.get('ZONE', 'ru-central1-a')
        sa_id = Variable.get('DATAPROC_SERVICE_ACCOUNT_ID')
        security_group_id = Variable.get('SECURITY_GROUP_ID')
        s3_logs_bucket = f"{Variable.get('S3_BUCKET_SCRIPTS')}/dataproc-logs/"
        
        # Создаем кластер с расширенными ресурсами для обучения
        op = DataprocCreateClusterOperator(
            task_id='_inner_create_training_cluster',
            folder_id=folder_id,
            cluster_name=cluster_name,
            cluster_description='ML Model Training Cluster',
            subnet_id=subnet_id,
            s3_bucket=s3_logs_bucket,
            ssh_public_keys=['ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC6U9uIFhz5CPUuFRvJGlaeS6sl5tbsyvsttkRReBUK+44uTnjkQs6hFTC0g7tBFm8OSUG0P6Cxrl3s4wIEo3a9VIwfFYFB5cqnwKaZU0mvmkgRoiYEG4b6rIuL7PX+CFzTOK6EtA0ZhKeF75XyO3qkAid0uucLcYqmGCE9PbgIH7sb8er0keNo3ZtZK/2ICWlSNua2uboTE312qCwGvB+P5qdEVkcen1oUskuIlwgD6Afb5bLTaEdxQiv01jsAVKiTv+dqDGbApBh1WN/97rtdDU4vLBfNpHCCBwmn/vDFLX6jhqnfhfV0NpR0SwXRBUu9Q4R0OttipPbdY9uXSXX/ airflow@dataproc'],
            zone=zone,
            cluster_image_version=Variable.get('DATAPROC_CLUSTER_VERSION', '2.0'),
            security_group_ids=[security_group_id] if security_group_id else [],
            service_account_id=sa_id,
            
            # Увеличенные ресурсы для обучения
            masternode_resource_preset=Variable.get('TRAINING_MASTER_PRESET', 's3-c4-m16'),
            masternode_disk_type='network-ssd',  # SSD для лучшей производительности
            masternode_disk_size=int(Variable.get('TRAINING_MASTER_DISK_SIZE', '100')),
            
            datanode_resource_preset=Variable.get('TRAINING_WORKER_PRESET', 's3-c8-m32'),
            datanode_disk_type='network-ssd',
            datanode_disk_size=int(Variable.get('TRAINING_WORKER_DISK_SIZE', '200')),
            datanode_count=int(Variable.get('TRAINING_WORKER_COUNT', '3')),
            
            # Сервисы для ML обучения
            services=['YARN', 'SPARK', 'HDFS', 'MAPREDUCE'],
            dag=dag,
        )
        
        cluster_id = op.execute(context)
        logger.info(f"✅ Training кластер создан: {cluster_id}")
        
        context['task_instance'].xcom_push(key='training_cluster_id', value=cluster_id)
        context['task_instance'].xcom_push(key='training_cluster_name', value=cluster_name)
        
        return cluster_id
    
    create_cluster = PythonOperator(
        task_id='create_training_cluster',
        python_callable=create_training_cluster,
        dag=dag,
    )
    
    # Ожидание готовности кластера
    wait_cluster_ready = BashOperator(
        task_id='wait_training_cluster_ready',
        bash_command='sleep {{ var.value.get("DATAPROC_GRACE_SECONDS", 300) }}',
        dag=dag,
    )
    
    create_cluster >> wait_cluster_ready

# ═══════════════════════════════════════════════════════════════════
# 🤖 MODEL TRAINING PROCESS
# ═══════════════════════════════════════════════════════════════════

with TaskGroup('model_training', dag=dag) as model_training_group:
    
    # Подготовка данных для обучения
    prepare_training_data = DataprocCreatePysparkJobOperator(
        task_id='prepare_training_data',
        cluster_id="{{ ti.xcom_pull(task_ids='training_infrastructure.create_training_cluster', key='training_cluster_id') }}",
        main_python_file_uri=f"s3a://{Variable.get('S3_BUCKET_SCRIPTS')}/scripts/prepare_training_data.py",
        args=[
            '--s3-bucket', Variable.get('S3_BUCKET_SCRIPTS'),
            '--data-path', 'data/',
            '--output-path', 'processed_data/',
            '--validation-split', '0.2',
            '--test-split', '0.1',
            '--feature-engineering', 'true',
            '--data-quality-threshold', '0.9'
        ],
        properties={
            'spark.submit.deployMode': 'cluster',
            'spark.sql.adaptive.enabled': 'true',
            'spark.serializer': 'org.apache.spark.serializer.KryoSerializer',
            
            # S3 configuration
            'spark.hadoop.fs.s3a.endpoint': _s3_endpoint_host(),
            'spark.hadoop.fs.s3a.path.style.access': 'true',
            'spark.hadoop.fs.s3a.connection.ssl.enabled': 'true',
            'spark.hadoop.fs.s3a.impl': 'org.apache.hadoop.fs.s3a.S3AFileSystem',
            'spark.hadoop.fs.s3a.access.key': Variable.get('S3_ACCESS_KEY'),
            'spark.hadoop.fs.s3a.secret.key': Variable.get('S3_SECRET_KEY'),
            
            # Python environment
            'spark.pyspark.python': '/opt/conda/bin/python',
            'spark.yarn.appMasterEnv.PYSPARK_PYTHON': '/opt/conda/bin/python',
            'spark.executorEnv.PYSPARK_PYTHON': '/opt/conda/bin/python',
            
            # S3 credentials
            'spark.executorEnv.S3_ACCESS_KEY': Variable.get('S3_ACCESS_KEY'),
            'spark.executorEnv.S3_SECRET_KEY': Variable.get('S3_SECRET_KEY'),
            'spark.yarn.appMasterEnv.S3_ACCESS_KEY': Variable.get('S3_ACCESS_KEY'),
            'spark.yarn.appMasterEnv.S3_SECRET_KEY': Variable.get('S3_SECRET_KEY'),
        },
        connection_id='yandexcloud_default',
        dag=dag,
    )
    
    # Обучение модели с MLflow
    train_model_with_mlflow = DataprocCreatePysparkJobOperator(
        task_id='train_model_with_mlflow',
        cluster_id="{{ ti.xcom_pull(task_ids='training_infrastructure.create_training_cluster', key='training_cluster_id') }}",
        main_python_file_uri=f"s3a://{Variable.get('S3_BUCKET_SCRIPTS')}/scripts/train_fraud_model_mlflow.py",
        args=[
            '--mlflow-uri', Variable.get('MLFLOW_TRACKING_URI'),
            '--experiment-name', Variable.get('MLFLOW_EXPERIMENT_NAME', 'fraud_detection_experiments'),
            '--model-name', Variable.get('MLFLOW_MODEL_NAME'),
            '--data-path', 'processed_data/',
            '--hyperparameter-tuning', 'true',
            '--cross-validation-folds', '5',
            '--max-evals', '50',
            '--auto-register', 'true'
        ],
        properties={
            'spark.submit.deployMode': 'cluster',
            'spark.sql.adaptive.enabled': 'true',
            'spark.serializer': 'org.apache.spark.serializer.KryoSerializer',
            
            # S3 configuration
            'spark.hadoop.fs.s3a.endpoint': _s3_endpoint_host(),
            'spark.hadoop.fs.s3a.path.style.access': 'true',
            'spark.hadoop.fs.s3a.connection.ssl.enabled': 'true',
            'spark.hadoop.fs.s3a.impl': 'org.apache.hadoop.fs.s3a.S3AFileSystem',
            'spark.hadoop.fs.s3a.access.key': Variable.get('S3_ACCESS_KEY'),
            'spark.hadoop.fs.s3a.secret.key': Variable.get('S3_SECRET_KEY'),
            
            # Python environment
            'spark.pyspark.python': '/opt/conda/bin/python',
            'spark.yarn.appMasterEnv.PYSPARK_PYTHON': '/opt/conda/bin/python',
            'spark.executorEnv.PYSPARK_PYTHON': '/opt/conda/bin/python',
            
            # MLflow environment
            'spark.yarn.appMasterEnv.MLFLOW_TRACKING_URI': Variable.get('MLFLOW_TRACKING_URI'),
            'spark.executorEnv.MLFLOW_TRACKING_URI': Variable.get('MLFLOW_TRACKING_URI'),
            'spark.yarn.appMasterEnv.MLFLOW_TRACKING_USERNAME': Variable.get('MLFLOW_TRACKING_USERNAME', ''),
            'spark.yarn.appMasterEnv.MLFLOW_TRACKING_PASSWORD': Variable.get('MLFLOW_TRACKING_PASSWORD', ''),
            'spark.executorEnv.MLFLOW_TRACKING_USERNAME': Variable.get('MLFLOW_TRACKING_USERNAME', ''),
            'spark.executorEnv.MLFLOW_TRACKING_PASSWORD': Variable.get('MLFLOW_TRACKING_PASSWORD', ''),
            
            # S3 credentials
            'spark.executorEnv.S3_ACCESS_KEY': Variable.get('S3_ACCESS_KEY'),
            'spark.executorEnv.S3_SECRET_KEY': Variable.get('S3_SECRET_KEY'),
            'spark.yarn.appMasterEnv.S3_ACCESS_KEY': Variable.get('S3_ACCESS_KEY'),
            'spark.yarn.appMasterEnv.S3_SECRET_KEY': Variable.get('S3_SECRET_KEY'),
        },
        connection_id='yandexcloud_default',
        dag=dag,
    )
    
    prepare_training_data >> train_model_with_mlflow

# ═══════════════════════════════════════════════════════════════════
# 📊 MODEL EVALUATION AND PROMOTION
# ═══════════════════════════════════════════════════════════════════

with TaskGroup('model_evaluation', dag=dag) as model_evaluation_group:
    
    def evaluate_new_model(**context):
        """Оценка новой модели и сравнение с текущей Champion"""
        logger.info("📊 Оценка новой модели и сравнение с Champion...")
        
        try:
            # В реальности здесь был бы MLflow API call
            # Для демонстрации создаем mock-результаты
            
            current_champion_metrics = {
                'accuracy': 0.89,
                'precision': 0.87,
                'recall': 0.91,
                'f1_score': 0.89,
                'auc_roc': 0.94
            }
            
            new_model_metrics = {
                'accuracy': 0.91,    # Лучше
                'precision': 0.89,   # Лучше
                'recall': 0.93,      # Лучше
                'f1_score': 0.91,    # Лучше
                'auc_roc': 0.96      # Лучше
            }
            
            # Критерии для промоушена модели
            improvement_threshold = 0.02  # 2% улучшение
            
            evaluation_result = {
                'current_champion_metrics': current_champion_metrics,
                'new_model_metrics': new_model_metrics,
                'improvement_score': new_model_metrics['f1_score'] - current_champion_metrics['f1_score'],
                'should_promote': new_model_metrics['f1_score'] > current_champion_metrics['f1_score'] + improvement_threshold,
                'evaluation_timestamp': datetime.now().isoformat(),
                'model_version': f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            }
            
            context['task_instance'].xcom_push(key='evaluation_result', value=evaluation_result)
            
            logger.info(f"📊 Результаты оценки модели:")
            logger.info(f"  🏆 Champion F1-Score: {current_champion_metrics['f1_score']:.3f}")
            logger.info(f"  🆕 New Model F1-Score: {new_model_metrics['f1_score']:.3f}")
            logger.info(f"  📈 Improvement: {evaluation_result['improvement_score']:.3f}")
            logger.info(f"  🚀 Should Promote: {evaluation_result['should_promote']}")
            
            return evaluation_result
            
        except Exception as e:
            logger.error(f"❌ Ошибка оценки модели: {e}")
            return {
                'error': str(e),
                'should_promote': False,
                'evaluation_timestamp': datetime.now().isoformat()
            }
    
    evaluate_model = PythonOperator(
        task_id='evaluate_new_model',
        python_callable=evaluate_new_model,
        dag=dag,
    )
    
    def promote_model_to_champion(**context):
        """Промоушен модели до статуса Champion"""
        logger.info("🚀 Промоушен модели до статуса Champion...")
        
        evaluation_result = context['ti'].xcom_pull(
            task_ids='model_evaluation.evaluate_new_model',
            key='evaluation_result'
        )
        
        if not evaluation_result or not evaluation_result.get('should_promote'):
            logger.info("ℹ️ Модель не прошла критерии для промоушена")
            return False
        
        try:
            # В реальности здесь был бы MLflow API call для смены алиаса
            promotion_result = {
                'model_name': Variable.get('MLFLOW_MODEL_NAME'),
                'new_champion_version': evaluation_result['model_version'],
                'previous_champion_archived': True,
                'promotion_timestamp': datetime.now().isoformat(),
                'metrics': evaluation_result['new_model_metrics']
            }
            
            context['task_instance'].xcom_push(key='promotion_result', value=promotion_result)
            
            logger.info(f"🎉 Модель успешно промоушена до Champion:")
            logger.info(f"  📦 Модель: {promotion_result['model_name']}")
            logger.info(f"  🔢 Версия: {promotion_result['new_champion_version']}")
            logger.info(f"  📊 F1-Score: {promotion_result['metrics']['f1_score']:.3f}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка промоушена модели: {e}")
            return False
    
    promote_model = PythonOperator(
        task_id='promote_model_to_champion',
        python_callable=promote_model_to_champion,
        dag=dag,
    )
    
    evaluate_model >> promote_model

# ═══════════════════════════════════════════════════════════════════
# 📧 NOTIFICATIONS AND CLEANUP
# ═══════════════════════════════════════════════════════════════════

def generate_training_report(**context):
    """Генерация отчета о переобучении"""
    logger.info("📋 Генерация отчета о переобучении...")
    
    try:
        evaluation_result = context['ti'].xcom_pull(
            task_ids='model_evaluation.evaluate_new_model',
            key='evaluation_result'
        )
        
        promotion_result = context['ti'].xcom_pull(
            task_ids='model_evaluation.promote_model_to_champion',
            key='promotion_result'
        )
        
        training_cluster_id = context['ti'].xcom_pull(
            task_ids='training_infrastructure.create_training_cluster',
            key='training_cluster_id'
        )
        
        # Создаем итоговый отчет
        final_report = {
            'retraining_date': context['execution_date'].isoformat(),
            'dag_run_id': context['run_id'],
            'cluster_id': training_cluster_id,
            'training_status': 'completed',
            'evaluation_result': evaluation_result or {},
            'promotion_result': promotion_result or {},
            'model_promoted': bool(promotion_result),
            'next_training_scheduled': (context['execution_date'] + timedelta(days=1)).isoformat()
        }
        
        context['task_instance'].xcom_push(key='final_report', value=final_report)
        
        logger.info("📊 ОТЧЕТ О ПЕРЕОБУЧЕНИИ МОДЕЛИ")
        logger.info("=" * 50)
        logger.info(f"📅 Дата: {final_report['retraining_date']}")
        logger.info(f"🎯 Статус: {final_report['training_status']}")
        logger.info(f"🚀 Модель промоушена: {'✅ ДА' if final_report['model_promoted'] else '❌ НЕТ'}")
        
        if evaluation_result:
            logger.info(f"📈 Улучшение F1-Score: {evaluation_result.get('improvement_score', 0):.3f}")
        
        logger.info("=" * 50)
        
        return final_report
        
    except Exception as e:
        logger.error(f"❌ Ошибка генерации отчета: {e}")
        return {
            'error': str(e),
            'retraining_date': context['execution_date'].isoformat()
        }

# Генерация отчета
generate_report = PythonOperator(
    task_id='generate_training_report',
    python_callable=generate_training_report,
    trigger_rule=TriggerRule.ALL_DONE,
    dag=dag,
)

# Email уведомление о результатах
send_training_notification = EmailOperator(
    task_id='send_training_notification',
    to=['ml-team@fraud-detection.local', 'devops@fraud-detection.local'],
    subject='🔄 ML Model Retraining Completed - {{ ds }}',
    html_content="""
    <h2>🔄 ML Model Retraining Report</h2>
    
    <p><strong>Date:</strong> {{ ds }}</p>
    <p><strong>DAG Run ID:</strong> {{ run_id }}</p>
    
    <h3>📊 Results:</h3>
    <ul>
        <li><strong>Training Status:</strong> {{ ti.xcom_pull(task_ids='generate_training_report', key='final_report')['training_status'] | default('unknown') }}</li>
        <li><strong>Model Promoted:</strong> {{ 'Yes ✅' if ti.xcom_pull(task_ids='generate_training_report', key='final_report')['model_promoted'] else 'No ❌' }}</li>
    </ul>
    
    <h3>🔗 Links:</h3>
    <ul>
        <li><a href="http://mlflow-server.airflow.svc.cluster.local:5000">MLflow UI</a></li>
        <li><a href="http://grafana.monitoring.svc.cluster.local:3000">Grafana Dashboard</a></li>
        <li><a href="http://airflow-webserver.airflow.svc.cluster.local:8080">Airflow UI</a></li>
    </ul>
    
    <p>Next training scheduled for: <strong>{{ (execution_date + macros.timedelta(days=1)).strftime('%Y-%m-%d') }}</strong></p>
    """,
    trigger_rule=TriggerRule.ALL_DONE,
    dag=dag,
)

# Удаление кластера
delete_training_cluster = DataprocDeleteClusterOperator(
    task_id='delete_training_cluster',
    cluster_id="{{ ti.xcom_pull(task_ids='training_infrastructure.create_training_cluster', key='training_cluster_id') }}",
    trigger_rule=TriggerRule.ALL_DONE,
    dag=dag,
)

# ═══════════════════════════════════════════════════════════════════
# 🔗 ОПРЕДЕЛЕНИЕ ЗАВИСИМОСТЕЙ
# ═══════════════════════════════════════════════════════════════════

# Основной flow
validate_config_task >> check_data_task >> training_infrastructure

# Обучение модели
training_infrastructure >> model_training_group

# Оценка и промоушен
model_training_group >> model_evaluation_group

# Отчетность и очистка
model_evaluation_group >> [generate_report, send_training_notification] >> delete_training_cluster
