#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 Kafka Stress Test для тестирования автоскейлинга
===================================================

Скрипт для генерации высокой нагрузки на Fraud Detection API через Kafka:
- Постепенное увеличение интенсивности запросов
- Мониторинг времени отклика
- Автоматическое срабатывание алертов при превышении лимитов
- Интеграция с Prometheus метриками

Цель: Протестировать автоскейлинг от 4 до 6 экземпляров и алерты при >80% CPU
Автор: ML Engineering Team
"""

import asyncio
import aiohttp
import json
import time
import random
import logging
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Any
import signal
import sys
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import threading

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class StressTestConfig:
    """Конфигурация стресс-теста"""
    api_url: str = "http://localhost:8000"
    initial_rps: int = 10          # Начальная нагрузка (requests per second)
    max_rps: int = 200             # Максимальная нагрузка
    ramp_up_duration: int = 300    # Время нарастания нагрузки (секунды)
    sustain_duration: int = 600    # Время поддержания пиковой нагрузки
    ramp_down_duration: int = 120  # Время снижения нагрузки
    batch_size: int = 5            # Количество одновременных запросов
    prometheus_url: str = "http://localhost:9090"
    
class StressTestRunner:
    """Основной класс для запуска стресс-теста"""
    
    def __init__(self, config: StressTestConfig):
        self.config = config
        self.current_rps = config.initial_rps
        self.running = True
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'response_times': [],
            'start_time': None,
            'current_replicas': 0,
            'max_replicas_reached': False,
            'high_cpu_detected': False
        }
        
        # Обработчик сигналов для graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Обработчик сигналов для остановки теста"""
        logger.info(f"🛑 Получен сигнал {signum}, останавливаем стресс-тест...")
        self.running = False
    
    async def generate_transaction_data(self) -> Dict[str, Any]:
        """Генерация случайных данных транзакции"""
        transaction_types = [
            "online_purchase", "atm_withdrawal", "pos_payment", 
            "transfer", "bill_payment", "subscription"
        ]
        
        merchant_categories = [
            "grocery", "restaurant", "gas_station", "retail", 
            "electronics", "travel", "entertainment", "healthcare"
        ]
        
        # Генерируем разные типы транзакций с разной вероятностью мошенничества
        fraud_probability = random.random()
        
        if fraud_probability < 0.1:  # 10% потенциально мошеннических
            amount = random.uniform(500, 5000)  # Большие суммы
            hour = random.choice([2, 3, 4, 23, 0, 1])  # Ночное время
            location_risk = random.uniform(0.7, 1.0)  # Высокий риск локации
        else:
            amount = random.uniform(5, 500)  # Обычные суммы
            hour = random.randint(8, 22)  # Дневное время
            location_risk = random.uniform(0.0, 0.3)  # Низкий риск
        
        return {
            "transaction_id": f"stress_test_{int(time.time() * 1000)}_{random.randint(1000, 9999)}",
            "amount": round(amount, 2),
            "merchant_category": random.choice(merchant_categories),
            "hour_of_day": hour,
            "day_of_week": datetime.now().weekday(),
            "user_age": random.randint(18, 80),
            "location_risk_score": round(location_risk, 3)
        }
    
    async def send_prediction_request(self, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """Отправка одного запроса на предсказание"""
        start_time = time.time()
        
        try:
            transaction_data = await self.generate_transaction_data()
            
            async with session.post(
                f"{self.config.api_url}/predict",
                json=transaction_data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                response_time = time.time() - start_time
                
                if response.status == 200:
                    result = await response.json()
                    self.stats['successful_requests'] += 1
                    self.stats['response_times'].append(response_time)
                    
                    return {
                        'status': 'success',
                        'response_time': response_time,
                        'transaction_id': transaction_data['transaction_id'],
                        'prediction': result
                    }
                else:
                    self.stats['failed_requests'] += 1
                    logger.warning(f"❌ Request failed: {response.status}")
                    
                    return {
                        'status': 'failed',
                        'response_time': response_time,
                        'status_code': response.status
                    }
                    
        except asyncio.TimeoutError:
            self.stats['failed_requests'] += 1
            response_time = time.time() - start_time
            logger.warning(f"⏰ Request timeout after {response_time:.2f}s")
            
            return {
                'status': 'timeout',
                'response_time': response_time
            }
            
        except Exception as e:
            self.stats['failed_requests'] += 1
            response_time = time.time() - start_time
            logger.error(f"💥 Request error: {e}")
            
            return {
                'status': 'error',
                'response_time': response_time,
                'error': str(e)
            }
        
        finally:
            self.stats['total_requests'] += 1
    
    async def send_batch_requests(self, session: aiohttp.ClientSession, batch_size: int) -> List[Dict]:
        """Отправка пакета запросов"""
        tasks = [
            self.send_prediction_request(session)
            for _ in range(batch_size)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Обрабатываем исключения
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"💥 Batch request exception: {result}")
                self.stats['failed_requests'] += 1
                processed_results.append({
                    'status': 'exception',
                    'error': str(result)
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def monitor_kubernetes_metrics(self):
        """Мониторинг метрик Kubernetes через Prometheus"""
        while self.running:
            try:
                async with aiohttp.ClientSession() as session:
                    
                    # Запрос количества реплик
                    replicas_query = 'kube_deployment_status_replicas{namespace="fraud-detection", deployment="fraud-detection-api"}'
                    async with session.get(
                        f"{self.config.prometheus_url}/api/v1/query",
                        params={'query': replicas_query}
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            if data['data']['result']:
                                current_replicas = int(float(data['data']['result'][0]['value'][1]))
                                self.stats['current_replicas'] = current_replicas
                                
                                if current_replicas >= 6:
                                    self.stats['max_replicas_reached'] = True
                                    logger.warning(f"🔥 МАКСИМАЛЬНЫЕ РЕПЛИКИ ДОСТИГНУТЫ: {current_replicas}")
                    
                    # Запрос CPU утилизации
                    cpu_query = 'rate(container_cpu_usage_seconds_total{namespace="fraud-detection", pod=~"fraud-detection-api-.*"}[5m]) * 100'
                    async with session.get(
                        f"{self.config.prometheus_url}/api/v1/query",
                        params={'query': cpu_query}
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            if data['data']['result']:
                                for result in data['data']['result']:
                                    cpu_usage = float(result['value'][1])
                                    pod_name = result['metric']['pod']
                                    
                                    if cpu_usage > 80:
                                        self.stats['high_cpu_detected'] = True
                                        logger.warning(f"🔥 ВЫСОКАЯ CPU УТИЛИЗАЦИЯ: {pod_name} = {cpu_usage:.1f}%")
                
            except Exception as e:
                logger.error(f"❌ Ошибка мониторинга метрик: {e}")
            
            await asyncio.sleep(15)  # Проверяем каждые 15 секунд
    
    def calculate_current_rps(self, elapsed_time: float) -> int:
        """Расчет текущего RPS на основе времени выполнения"""
        if elapsed_time < self.config.ramp_up_duration:
            # Фаза нарастания нагрузки
            progress = elapsed_time / self.config.ramp_up_duration
            rps = self.config.initial_rps + (self.config.max_rps - self.config.initial_rps) * progress
            
        elif elapsed_time < self.config.ramp_up_duration + self.config.sustain_duration:
            # Фаза поддержания пиковой нагрузки
            rps = self.config.max_rps
            
        elif elapsed_time < self.config.ramp_up_duration + self.config.sustain_duration + self.config.ramp_down_duration:
            # Фаза снижения нагрузки
            ramp_down_elapsed = elapsed_time - self.config.ramp_up_duration - self.config.sustain_duration
            progress = ramp_down_elapsed / self.config.ramp_down_duration
            rps = self.config.max_rps - (self.config.max_rps - self.config.initial_rps) * progress
            
        else:
            # Завершение теста
            rps = self.config.initial_rps
            self.running = False
        
        return max(int(rps), 1)
    
    def print_stats(self, elapsed_time: float):
        """Вывод текущей статистики"""
        if self.stats['response_times']:
            avg_response_time = sum(self.stats['response_times']) / len(self.stats['response_times'])
            p95_response_time = sorted(self.stats['response_times'])[int(len(self.stats['response_times']) * 0.95)]
        else:
            avg_response_time = 0
            p95_response_time = 0
        
        success_rate = (self.stats['successful_requests'] / max(self.stats['total_requests'], 1)) * 100
        
        print(f"\n📊 СТРЕСС-ТЕСТ СТАТИСТИКА (T+{elapsed_time:.0f}s)")
        print("=" * 60)
        print(f"🎯 Текущий RPS: {self.current_rps}")
        print(f"📈 Всего запросов: {self.stats['total_requests']}")
        print(f"✅ Успешных: {self.stats['successful_requests']}")
        print(f"❌ Неудачных: {self.stats['failed_requests']}")
        print(f"📊 Success Rate: {success_rate:.1f}%")
        print(f"⚡ Avg Response Time: {avg_response_time:.3f}s")
        print(f"🔥 P95 Response Time: {p95_response_time:.3f}s")
        print(f"🔄 Текущих реплик: {self.stats['current_replicas']}")
        print(f"🚨 Макс. реплики достигнуты: {'✅ ДА' if self.stats['max_replicas_reached'] else '❌ НЕТ'}")
        print(f"🔥 Высокая CPU обнаружена: {'✅ ДА' if self.stats['high_cpu_detected'] else '❌ НЕТ'}")
        print("=" * 60)
    
    async def run_stress_test(self):
        """Основной метод запуска стресс-теста"""
        logger.info("🚀 Запуск стресс-теста Kafka для Fraud Detection API")
        logger.info(f"🎯 API URL: {self.config.api_url}")
        logger.info(f"📈 Нагрузка: {self.config.initial_rps} → {self.config.max_rps} RPS")
        logger.info(f"⏱️ Длительность: {self.config.ramp_up_duration + self.config.sustain_duration + self.config.ramp_down_duration}s")
        
        self.stats['start_time'] = time.time()
        
        # Запускаем мониторинг метрик в фоне
        monitoring_task = asyncio.create_task(self.monitor_kubernetes_metrics())
        
        async with aiohttp.ClientSession() as session:
            
            while self.running:
                loop_start_time = time.time()
                elapsed_time = loop_start_time - self.stats['start_time']
                
                # Обновляем текущий RPS
                self.current_rps = self.calculate_current_rps(elapsed_time)
                
                # Рассчитываем интервал между пакетами
                requests_per_batch = self.config.batch_size
                batches_per_second = self.current_rps / requests_per_batch
                batch_interval = 1.0 / batches_per_second if batches_per_second > 0 else 1.0
                
                # Отправляем пакет запросов
                batch_results = await self.send_batch_requests(session, requests_per_batch)
                
                # Выводим статистику каждые 30 секунд
                if int(elapsed_time) % 30 == 0:
                    self.print_stats(elapsed_time)
                
                # Проверяем условия завершения теста
                if self.stats['max_replicas_reached'] and self.stats['high_cpu_detected']:
                    logger.info("🎉 УСПЕХ! Достигнуты все цели стресс-теста:")
                    logger.info("  ✅ Масштабирование до 6 экземпляров")
                    logger.info("  ✅ CPU нагрузка > 80%")
                    logger.info("  ✅ Алерты должны сработать")
                    break
                
                # Ждем до следующего пакета
                loop_duration = time.time() - loop_start_time
                sleep_time = max(0, batch_interval - loop_duration)
                
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
        
        # Останавливаем мониторинг
        monitoring_task.cancel()
        
        # Финальная статистика
        total_duration = time.time() - self.stats['start_time']
        self.print_final_report(total_duration)
    
    def print_final_report(self, duration: float):
        """Печать финального отчета"""
        print("\n" + "="*80)
        print("🏁 ФИНАЛЬНЫЙ ОТЧЕТ СТРЕСС-ТЕСТА")
        print("="*80)
        
        if self.stats['response_times']:
            avg_response_time = sum(self.stats['response_times']) / len(self.stats['response_times'])
            p95_response_time = sorted(self.stats['response_times'])[int(len(self.stats['response_times']) * 0.95)]
            p99_response_time = sorted(self.stats['response_times'])[int(len(self.stats['response_times']) * 0.99)]
        else:
            avg_response_time = p95_response_time = p99_response_time = 0
        
        success_rate = (self.stats['successful_requests'] / max(self.stats['total_requests'], 1)) * 100
        avg_rps = self.stats['total_requests'] / duration if duration > 0 else 0
        
        print(f"⏱️ Общая длительность: {duration:.1f} секунд")
        print(f"📊 Всего запросов: {self.stats['total_requests']}")
        print(f"📈 Средний RPS: {avg_rps:.1f}")
        print(f"✅ Успешных запросов: {self.stats['successful_requests']}")
        print(f"❌ Неудачных запросов: {self.stats['failed_requests']}")
        print(f"📊 Success Rate: {success_rate:.1f}%")
        print(f"⚡ Avg Response Time: {avg_response_time:.3f}s")
        print(f"🔥 P95 Response Time: {p95_response_time:.3f}s")
        print(f"🌡️ P99 Response Time: {p99_response_time:.3f}s")
        
        print("\n🎯 ЦЕЛИ ТЕСТИРОВАНИЯ:")
        print(f"🔄 Максимальные реплики (6): {'✅ ДОСТИГНУТО' if self.stats['max_replicas_reached'] else '❌ НЕ ДОСТИГНУТО'}")
        print(f"🔥 Высокая CPU нагрузка (>80%): {'✅ ОБНАРУЖЕНО' if self.stats['high_cpu_detected'] else '❌ НЕ ОБНАРУЖЕНО'}")
        
        if self.stats['max_replicas_reached'] and self.stats['high_cpu_detected']:
            print("\n🎉 СТРЕСС-ТЕСТ УСПЕШНО ЗАВЕРШЕН!")
            print("💡 Проверьте алерты в Prometheus/Grafana для подтверждения срабатывания")
        else:
            print("\n⚠️ СТРЕСС-ТЕСТ ЗАВЕРШЕН ЧАСТИЧНО")
            print("💡 Рассмотрите увеличение нагрузки или проверку конфигурации HPA")
        
        print("="*80)

async def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(description='Stress test для Fraud Detection API')
    parser.add_argument('--api-url', default='http://localhost:8000', help='URL API для тестирования')
    parser.add_argument('--initial-rps', type=int, default=10, help='Начальная нагрузка (RPS)')
    parser.add_argument('--max-rps', type=int, default=200, help='Максимальная нагрузка (RPS)')
    parser.add_argument('--ramp-up-duration', type=int, default=300, help='Время нарастания (секунды)')
    parser.add_argument('--sustain-duration', type=int, default=600, help='Время поддержания пика (секунды)')
    parser.add_argument('--ramp-down-duration', type=int, default=120, help='Время снижения (секунды)')
    parser.add_argument('--batch-size', type=int, default=5, help='Размер пакета запросов')
    parser.add_argument('--prometheus-url', default='http://localhost:9090', help='URL Prometheus')
    
    args = parser.parse_args()
    
    config = StressTestConfig(
        api_url=args.api_url,
        initial_rps=args.initial_rps,
        max_rps=args.max_rps,
        ramp_up_duration=args.ramp_up_duration,
        sustain_duration=args.sustain_duration,
        ramp_down_duration=args.ramp_down_duration,
        batch_size=args.batch_size,
        prometheus_url=args.prometheus_url
    )
    
    runner = StressTestRunner(config)
    await runner.run_stress_test()

if __name__ == "__main__":
    asyncio.run(main())
