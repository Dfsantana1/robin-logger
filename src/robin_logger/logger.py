"""
Módulo principal de RobinLogger
"""

import os
import json
import time
import threading
import asyncio
from typing import Any, Dict, Optional, Union
from datetime import datetime, timezone
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .cache import LogCache


class RobinLogger:
    """
    Cliente de logging que envía eventos a un backend centralizado.
    
    Características:
    - Envío asíncrono mediante threading
    - Retry automático con backoff exponencial
    - Cache local cuando no hay conexión
    - Soporte para cualquier tipo de dato JSON
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 10,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        enable_local_cache: bool = True,
        cache_dir: Optional[str] = None,
        cache_max_size_mb: float = 30.0,
        async_mode: bool = True,
        auto_retry_enabled: bool = True,
        auto_retry_interval: int = 60,
        auto_retry_max_interval: int = 3600,
        auto_retry_async: bool = True
    ):
        """
        Inicializa el cliente RobinLogger.
        
        Args:
            base_url: URL base del API (puede venir de ROBIN_LOGGER_URL env var)
            api_key: API key para autenticación (puede venir de ROBIN_LOGGER_API_KEY env var)
            timeout: Timeout en segundos para las peticiones HTTP
            max_retries: Número máximo de reintentos
            backoff_factor: Factor de backoff exponencial (0.5 = 0.5s, 1s, 2s, 4s...)
            enable_local_cache: Si True, guarda logs en cache local cuando falla el envío
            cache_dir: Directorio para el cache local (default: ~/.robin_logger_cache)
            cache_max_size_mb: Tamaño máximo del cache en MB (default: 30 MB)
            async_mode: Si True, envía los logs de forma asíncrona
            auto_retry_enabled: Si True, reintenta automáticamente logs en cache
            auto_retry_interval: Intervalo inicial en segundos para reintentos automáticos (default: 60s)
            auto_retry_max_interval: Intervalo máximo para backoff exponencial (default: 3600s = 1h)
            auto_retry_async: Si True, reintentos automáticos se hacen en background
        """
        self.base_url = base_url or os.getenv("ROBIN_LOGGER_URL")
        self.api_key = api_key or os.getenv("ROBIN_LOGGER_API_KEY")
        
        if not self.base_url:
            raise ValueError(
                "base_url es requerido. Proporciona el parámetro o configura "
                "la variable de entorno ROBIN_LOGGER_URL"
            )
        
        if not self.api_key:
            raise ValueError(
                "api_key es requerido. Proporciona el parámetro o configura "
                "la variable de entorno ROBIN_LOGGER_API_KEY"
            )
        
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.enable_local_cache = enable_local_cache
        self.async_mode = async_mode
        self.auto_retry_enabled = auto_retry_enabled
        self.auto_retry_interval = auto_retry_interval
        self.auto_retry_max_interval = auto_retry_max_interval
        self.auto_retry_async = auto_retry_async
        
        # Configurar sesión HTTP con retry automático
        self.session = self._create_session()
        
        # Inicializar cache local
        if self.enable_local_cache:
            self.cache = LogCache(cache_dir, max_cache_size_mb=cache_max_size_mb)
        else:
            self.cache = None
        
        # Variables para control de reintentos automáticos
        self._retry_thread = None
        self._retry_stop_event = threading.Event()
        self._current_retry_interval = auto_retry_interval
        self._retry_failures = 0
        
        # Iniciar thread de reintentos automáticos si está habilitado
        if self.auto_retry_enabled and self.enable_local_cache:
            self._start_auto_retry_thread()
    
    def _create_session(self) -> requests.Session:
        """Crea una sesión HTTP con retry automático."""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=self.backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _normalize_timestamp(self, ts: Optional[Union[str, int, float, datetime]]) -> str:
        """
        Normaliza el timestamp al formato "YYYY-MM-DD HH:MM:SS" (UTC).

        Acepta:
        - None: usa la hora actual en UTC
        - datetime: lo convierte a UTC sin tz y lo formatea
        - int/float (epoch segundos): convierte a UTC
        - str: si ya viene en string, lo devuelve tal cual (se asume correcto)
        """
        fmt = "%Y-%m-%d %H:%M:%S"
        try:
            if ts is None:
                return datetime.utcnow().strftime(fmt)
            if isinstance(ts, datetime):
                # Si tiene tz, convertir a UTC y quitar tzinfo para formateo
                if ts.tzinfo is not None:
                    # Convertir a UTC y luego quitar tzinfo
                    ts = ts.astimezone(timezone.utc).replace(tzinfo=None)
                return ts.strftime(fmt)
            if isinstance(ts, (int, float)):
                return datetime.utcfromtimestamp(ts).strftime(fmt)
            if isinstance(ts, str):
                # Confiamos en que el usuario proporciona el formato deseado
                return ts
        except Exception:
            # Fallback robusto
            return datetime.utcnow().strftime(fmt)

    def _prepare_payload(
        self,
        type: str,
        category: str,
        subcategory: str,
        level: str,
        data: Dict[str, Any],
        timestamp: Optional[Union[str, int, float, datetime]] = None
    ) -> Dict[str, Any]:
        """Prepara el payload para enviar al API."""
        normalized_ts = self._normalize_timestamp(timestamp)
        
        return {
            "type": type,
            "category": category,
            "subcategory": subcategory,
            "level": level,
            "data": data,
            "timestamp": normalized_ts,
        }
    
    def _send_to_api(self, payload: Dict[str, Any]) -> bool:
        """
        Envía el log al API.
        
        Returns:
            True si el envío fue exitoso, False en caso contrario
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "robin-logger-python/0.2.2"
        }
        
        try:
            response = self.session.post(
                self.base_url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return True
        
        except requests.exceptions.RequestException as e:
            print(f"[RobinLogger] Error al enviar log: {e}")
            return False
    
    def _send_log_sync(
        self,
        type: str,
        category: str,
        subcategory: str,
        level: str,
        data: Dict[str, Any],
        timestamp: Optional[str] = None
    ):
        """Envía el log de forma síncrona."""
        payload = self._prepare_payload(type, category, subcategory, level, data, timestamp)
        
        success = self._send_to_api(payload)
        
        if not success and self.enable_local_cache:
            print("[RobinLogger] Guardando en cache local...")
            self.cache.save_log(payload)
    
    def _send_log_async(
        self,
        type: str,
        category: str,
        subcategory: str,
        level: str,
        data: Dict[str, Any],
        timestamp: Optional[str] = None
    ):
        """Envía el log de forma asíncrona usando threading."""
        thread = threading.Thread(
            target=self._send_log_sync,
            args=(type, category, subcategory, level, data, timestamp),
            daemon=True
        )
        thread.start()
    
    def send_log(
        self,
        type: str,
        category: str,
        subcategory: str,
        level: str,
        data: Dict[str, Any],
        timestamp: Optional[str] = None
    ):
        """
        Envía un log al backend centralizado.
        
        Args:
            type: Tipo de evento (ej: "login", "audit", "activity")
            category: Categoría del evento (ej: "user_auth", "data_access")
            subcategory: Subcategoría del evento (ej: "success", "failure")
            level: Nivel de severidad (ej: "info", "warning", "error", "critical")
            data: Datos adicionales del evento (cualquier estructura JSON)
            timestamp: Timestamp del evento (ISO 8601). Si no se proporciona, se usa la hora actual
        
        Example:
            >>> logger.send_log(
            ...     type="login",
            ...     category="user_auth",
            ...     subcategory="success",
            ...     level="info",
            ...     data={"username": "william", "ip": "192.168.1.10"}
            ... )
        """
        if self.async_mode:
            self._send_log_async(type, category, subcategory, level, data, timestamp)
        else:
            self._send_log_sync(type, category, subcategory, level, data, timestamp)
    
    def retry_cached_logs(self) -> Dict[str, int]:
        """
        Reintenta enviar los logs guardados en cache local.
        
        Returns:
            Diccionario con estadísticas: {"sent": int, "failed": int, "total": int}
        """
        if not self.enable_local_cache:
            print("[RobinLogger] Cache local está deshabilitado")
            return {"sent": 0, "failed": 0, "total": 0}
        
        cached_logs = self.cache.get_all_logs()
        total = len(cached_logs)
        
        if total == 0:
            print("[RobinLogger] No hay logs en cache")
            return {"sent": 0, "failed": 0, "total": 0}
        
        print(f"[RobinLogger] Reintentando envío de {total} logs en cache...")
        
        sent = 0
        failed = 0
        
        for log_id, payload in cached_logs:
            success = self._send_to_api(payload)
            
            if success:
                self.cache.remove_log(log_id)
                sent += 1
            else:
                failed += 1
        
        print(f"[RobinLogger] Resultado: {sent} enviados, {failed} fallidos")
        
        return {"sent": sent, "failed": failed, "total": total}
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del cache local.
        
        Returns:
            Diccionario con estadísticas del cache
        """
        if not self.enable_local_cache:
            return {"enabled": False, "count": 0, "size_mb": 0}
        
        count = self.cache.count_logs()
        size_mb = self.cache.get_cache_size_mb()
        max_size_mb = self.cache.max_cache_size_bytes / 1024 / 1024
        
        return {
            "enabled": True,
            "count": count,
            "size_mb": round(size_mb, 2),
            "max_size_mb": round(max_size_mb, 2),
            "usage_percent": round((size_mb / max_size_mb * 100) if max_size_mb > 0 else 0, 2),
            "cache_dir": self.cache.cache_dir
        }
    
    def clear_cache(self):
        """Limpia todos los logs del cache local."""
        if self.enable_local_cache:
            self.cache.clear_all()
            print("[RobinLogger] Cache local limpiado")
        else:
            print("[RobinLogger] Cache local está deshabilitado")
    
    def _start_auto_retry_thread(self):
        """Inicia el thread de reintentos automáticos en background."""
        if self._retry_thread is not None and self._retry_thread.is_alive():
            return
        
        self._retry_stop_event.clear()
        self._retry_thread = threading.Thread(
            target=self._auto_retry_loop,
            daemon=True,
            name="RobinLogger-AutoRetry"
        )
        self._retry_thread.start()
        print(f"[RobinLogger] Sistema de reintentos automáticos iniciado (intervalo: {self.auto_retry_interval}s)")
    
    def _auto_retry_loop(self):
        """
        Loop principal para reintentos automáticos.
        Se ejecuta en background y reintenta enviar logs del cache periódicamente.
        """
        while not self._retry_stop_event.is_set():
            # Esperar el intervalo configurado
            if self._retry_stop_event.wait(timeout=self._current_retry_interval):
                break  # Stop event fue activado
            
            # Verificar si hay logs en cache
            if not self.enable_local_cache or self.cache.count_logs() == 0:
                continue
            
            # Reintentar envío
            if self.auto_retry_async:
                # Modo asíncrono: ejecutar en thread separado
                threading.Thread(
                    target=self._execute_auto_retry,
                    daemon=True
                ).start()
            else:
                # Modo síncrono: ejecutar en el mismo thread
                self._execute_auto_retry()
    
    def _execute_auto_retry(self):
        """Ejecuta el reintento de logs en cache."""
        try:
            cached_logs = self.cache.get_oldest_logs(limit=50)  # Procesar en lotes de 50
            
            if not cached_logs:
                return
            
            print(f"[RobinLogger] Reintentando envío de {len(cached_logs)} logs...")
            
            sent = 0
            failed = 0
            
            for log_id, payload in cached_logs:
                success = self._send_to_api(payload)
                
                if success:
                    self.cache.remove_log(log_id)
                    sent += 1
                else:
                    failed += 1
            
            # Ajustar intervalo según resultados
            if sent > 0:
                # Éxito: resetear intervalo y contador de fallos
                print(f"[RobinLogger] ✅ {sent} logs reenviados exitosamente")
                self._current_retry_interval = self.auto_retry_interval
                self._retry_failures = 0
            else:
                # Fallo: incrementar intervalo con backoff exponencial
                self._retry_failures += 1
                self._current_retry_interval = min(
                    self.auto_retry_interval * (2 ** self._retry_failures),
                    self.auto_retry_max_interval
                )
                print(f"[RobinLogger] ⚠️  Reintento falló. Próximo intento en {self._current_retry_interval}s")
        
        except Exception as e:
            print(f"[RobinLogger] Error en reintentos automáticos: {e}")
    
    def stop_auto_retry(self):
        """Detiene el sistema de reintentos automáticos."""
        if self._retry_thread is not None and self._retry_thread.is_alive():
            print("[RobinLogger] Deteniendo sistema de reintentos automáticos...")
            self._retry_stop_event.set()
            self._retry_thread.join(timeout=5)
            print("[RobinLogger] Sistema de reintentos detenido")
    
    def get_retry_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del sistema de reintentos automáticos.
        
        Returns:
            Diccionario con información sobre el estado de reintentos
        """
        return {
            "enabled": self.auto_retry_enabled,
            "running": self._retry_thread is not None and self._retry_thread.is_alive(),
            "current_interval": self._current_retry_interval,
            "max_interval": self.auto_retry_max_interval,
            "failures": self._retry_failures,
            "async_mode": self.auto_retry_async
        }
    
    def close(self):
        """Cierra la sesión HTTP y detiene reintentos automáticos."""
        self.stop_auto_retry()
        self.session.close()
    
    def __enter__(self):
        """Soporte para context manager."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cierra la sesión al salir del context manager."""
        self.close()
