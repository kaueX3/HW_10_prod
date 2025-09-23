#!/usr/bin/env python3
"""
Простой стресс-тест для проверки автоскейлинга HW_10
"""

import asyncio
import aiohttp
import time
import argparse
from typing import Dict, Any

class StressTest:
    def __init__(self, api_url: str, max_rps: int = 50):
        self.api_url = api_url
        self.max_rps = max_rps
        self.session = None
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'start_time': None
        }
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def make_request(self) -> bool:
        """Отправляет HTTP запрос к API"""
        try:
            async with self.session.get(self.api_url, timeout=5) as response:
                self.stats['total_requests'] += 1
                if response.status == 200:
                    self.stats['successful_requests'] += 1
                    return True
                else:
                    self.stats['failed_requests'] += 1
                    return False
        except Exception as e:
            self.stats['total_requests'] += 1
            self.stats['failed_requests'] += 1
            print(f"❌ Request failed: {e}")
            return False
    
    async def stress_worker(self, worker_id: int, duration: int):
        """Воркер для отправки запросов"""
        print(f"🚀 Worker {worker_id} started")
        
        end_time = time.time() + duration
        request_interval = 1.0 / self.max_rps
        
        while time.time() < end_time:
            await self.make_request()
            await asyncio.sleep(request_interval)
        
        print(f"✅ Worker {worker_id} completed")
    
    async def run_stress_test(self, duration: int, num_workers: int = 1):
        """Запускает стресс-тест"""
        print(f"""
🚀 Запуск стресс-теста:
📍 URL: {self.api_url}
⏱️  Длительность: {duration} секунд
👥 Воркеры: {num_workers}
📊 Целевой RPS: {self.max_rps}
        """)
        
        self.stats['start_time'] = time.time()
        
        # Запускаем воркеры
        tasks = []
        for i in range(num_workers):
            task = asyncio.create_task(self.stress_worker(i, duration))
            tasks.append(task)
        
        # Мониторинг прогресса
        monitor_task = asyncio.create_task(self.monitor_progress(duration))
        
        # Ждем завершения всех задач
        await asyncio.gather(*tasks, monitor_task)
        
        # Выводим финальную статистику
        self.print_final_stats()
    
    async def monitor_progress(self, duration: int):
        """Мониторинг прогресса теста"""
        start_time = time.time()
        
        while time.time() - start_time < duration:
            elapsed = time.time() - start_time
            remaining = duration - elapsed
            
            if self.stats['total_requests'] > 0:
                success_rate = (self.stats['successful_requests'] / self.stats['total_requests']) * 100
                current_rps = self.stats['total_requests'] / elapsed if elapsed > 0 else 0
            else:
                success_rate = 0
                current_rps = 0
            
            print(f"""
📊 Прогресс теста:
⏱️  Время: {elapsed:.1f}s / {duration}s (осталось: {remaining:.1f}s)
📈 Запросы: {self.stats['total_requests']} (успешных: {self.stats['successful_requests']})
✅ Success Rate: {success_rate:.1f}%
🔥 Current RPS: {current_rps:.1f}
            """)
            
            await asyncio.sleep(10)  # Обновляем каждые 10 секунд
    
    def print_final_stats(self):
        """Выводит финальную статистику"""
        elapsed = time.time() - self.stats['start_time']
        avg_rps = self.stats['total_requests'] / elapsed if elapsed > 0 else 0
        success_rate = (self.stats['successful_requests'] / self.stats['total_requests'] * 100) if self.stats['total_requests'] > 0 else 0
        
        print(f"""
🎯 ФИНАЛЬНАЯ СТАТИСТИКА:
════════════════════════════════════════
⏱️  Общее время: {elapsed:.2f} секунд
📊 Всего запросов: {self.stats['total_requests']}
✅ Успешных: {self.stats['successful_requests']}
❌ Неудачных: {self.stats['failed_requests']}
📈 Средний RPS: {avg_rps:.2f}
✅ Success Rate: {success_rate:.2f}%
════════════════════════════════════════
        """)

async def main():
    parser = argparse.ArgumentParser(description='Стресс-тест для HW_10 API')
    parser.add_argument('--api-url', default='http://localhost:8080', help='URL API для тестирования')
    parser.add_argument('--max-rps', type=int, default=20, help='Максимальный RPS на воркер')
    parser.add_argument('--duration', type=int, default=120, help='Длительность теста в секундах')
    parser.add_argument('--workers', type=int, default=2, help='Количество воркеров')
    
    args = parser.parse_args()
    
    print(f"""
🛡️ HW_10 Fraud Detection API Stress Test
=========================================
🎯 Цель: достичь >80% CPU и автоскейлинга до 6 подов
    """)
    
    async with StressTest(args.api_url, args.max_rps) as stress_test:
        await stress_test.run_stress_test(args.duration, args.workers)
    
    print("""
✨ Стресс-тест завершен!
📋 Следующие шаги:
1. Проверить: kubectl get pods -n fraud-detection
2. Проверить HPA: kubectl get hpa -n fraud-detection  
3. Проверить метрики: kubectl top pods -n fraud-detection
    """)

if __name__ == '__main__':
    asyncio.run(main())
