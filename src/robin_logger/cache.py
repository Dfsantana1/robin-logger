"""
Sistema de cache local para logs cuando no hay conexión
"""

import os
import json
import uuid
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
from datetime import datetime


class LogCache:
    """
    Gestiona el almacenamiento local de logs cuando no se pueden enviar al servidor.
    Incluye límite de tamaño y rotación automática.
    """
    
    def __init__(
        self, 
        cache_dir: Optional[str] = None,
        max_cache_size_mb: float = 30.0
    ):
        """
        Inicializa el cache local.
        
        Args:
            cache_dir: Directorio donde guardar los logs. 
                      Si es None, usa ~/.robin_logger_cache
            max_cache_size_mb: Tamaño máximo del cache en MB (default: 30 MB)
        """
        if cache_dir is None:
            cache_dir = os.path.join(str(Path.home()), ".robin_logger_cache")
        
        self.cache_dir = cache_dir
        self.max_cache_size_bytes = int(max_cache_size_mb * 1024 * 1024)
        self._ensure_cache_dir()
    
    def _ensure_cache_dir(self):
        """Crea el directorio de cache si no existe."""
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def _get_log_path(self, log_id: str) -> str:
        """Obtiene la ruta completa para un log."""
        return os.path.join(self.cache_dir, f"{log_id}.json")
    
    def _get_cache_size_bytes(self) -> int:
        """Calcula el tamaño total del cache en bytes."""
        total_size = 0
        
        if not os.path.exists(self.cache_dir):
            return 0
        
        for filename in os.listdir(self.cache_dir):
            if filename.endswith('.json'):
                file_path = os.path.join(self.cache_dir, filename)
                try:
                    total_size += os.path.getsize(file_path)
                except Exception:
                    pass
        
        return total_size
    
    def _cleanup_old_logs_if_needed(self):
        """
        Elimina logs antiguos si el cache excede el tamaño máximo.
        Usa política FIFO (First In First Out).
        """
        current_size = self._get_cache_size_bytes()
        
        if current_size <= self.max_cache_size_bytes:
            return
        
        print(f"[LogCache] Cache excede límite ({current_size / 1024 / 1024:.2f} MB). Limpiando logs antiguos...")
        
        # Obtener todos los logs con su timestamp
        logs_with_time = []
        for filename in os.listdir(self.cache_dir):
            if not filename.endswith('.json'):
                continue
            
            log_id = filename[:-5]
            cache_entry = self.get_log(log_id)
            
            if cache_entry:
                cached_at = cache_entry.get('cached_at', '')
                file_path = self._get_log_path(log_id)
                file_size = os.path.getsize(file_path)
                logs_with_time.append((log_id, cached_at, file_size))
        
        # Ordenar por timestamp (más antiguos primero)
        logs_with_time.sort(key=lambda x: x[1])
        
        # Eliminar logs hasta estar por debajo del límite
        removed_count = 0
        for log_id, _, file_size in logs_with_time:
            if current_size <= self.max_cache_size_bytes * 0.8:  # 80% del límite
                break
            
            if self.remove_log(log_id):
                current_size -= file_size
                removed_count += 1
        
        print(f"[LogCache] Eliminados {removed_count} logs antiguos. Tamaño actual: {current_size / 1024 / 1024:.2f} MB")
    
    def save_log(self, payload: Dict[str, Any]) -> str:
        """
        Guarda un log en el cache local.
        Elimina logs antiguos si se excede el límite de tamaño.
        
        Args:
            payload: Datos del log a guardar
            
        Returns:
            ID único del log guardado
        """
        # Verificar límite de tamaño antes de guardar
        self._cleanup_old_logs_if_needed()
        
        log_id = str(uuid.uuid4())
        
        # Agregar metadata
        cache_entry = {
            "id": log_id,
            "cached_at": datetime.utcnow().isoformat() + "Z",
            "payload": payload
        }
        
        log_path = self._get_log_path(log_id)
        
        try:
            with open(log_path, 'w', encoding='utf-8') as f:
                json.dump(cache_entry, f, ensure_ascii=False, indent=2)
            
            return log_id
        
        except Exception as e:
            print(f"[LogCache] Error al guardar log en cache: {e}")
            return None
    
    def get_log(self, log_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene un log específico del cache.
        
        Args:
            log_id: ID del log
            
        Returns:
            Datos del log o None si no existe
        """
        log_path = self._get_log_path(log_id)
        
        if not os.path.exists(log_path):
            return None
        
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        except Exception as e:
            print(f"[LogCache] Error al leer log {log_id}: {e}")
            return None
    
    def get_all_logs(self) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Obtiene todos los logs del cache.
        
        Returns:
            Lista de tuplas (log_id, payload)
        """
        logs = []
        
        if not os.path.exists(self.cache_dir):
            return logs
        
        for filename in os.listdir(self.cache_dir):
            if not filename.endswith('.json'):
                continue
            
            log_id = filename[:-5]  # Remover .json
            cache_entry = self.get_log(log_id)
            
            if cache_entry and 'payload' in cache_entry:
                logs.append((log_id, cache_entry['payload']))
        
        return logs
    
    def remove_log(self, log_id: str) -> bool:
        """
        Elimina un log del cache.
        
        Args:
            log_id: ID del log a eliminar
            
        Returns:
            True si se eliminó, False en caso contrario
        """
        log_path = self._get_log_path(log_id)
        
        try:
            if os.path.exists(log_path):
                os.remove(log_path)
                return True
            return False
        
        except Exception as e:
            print(f"[LogCache] Error al eliminar log {log_id}: {e}")
            return False
    
    def count_logs(self) -> int:
        """
        Cuenta el número de logs en cache.
        
        Returns:
            Número de logs guardados
        """
        if not os.path.exists(self.cache_dir):
            return 0
        
        count = 0
        for filename in os.listdir(self.cache_dir):
            if filename.endswith('.json'):
                count += 1
        
        return count
    
    def clear_all(self) -> int:
        """
        Elimina todos los logs del cache.
        
        Returns:
            Número de logs eliminados
        """
        if not os.path.exists(self.cache_dir):
            return 0
        
        count = 0
        for filename in os.listdir(self.cache_dir):
            if filename.endswith('.json'):
                log_id = filename[:-5]
                if self.remove_log(log_id):
                    count += 1
        
        return count
    
    def get_oldest_logs(self, limit: int = 10) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Obtiene los logs más antiguos del cache.
        
        Args:
            limit: Número máximo de logs a retornar
            
        Returns:
            Lista de tuplas (log_id, payload) ordenadas por antigüedad
        """
        all_logs = []
        
        if not os.path.exists(self.cache_dir):
            return all_logs
        
        for filename in os.listdir(self.cache_dir):
            if not filename.endswith('.json'):
                continue
            
            log_id = filename[:-5]
            cache_entry = self.get_log(log_id)
            
            if cache_entry and 'payload' in cache_entry:
                cached_at = cache_entry.get('cached_at', '')
                all_logs.append((log_id, cache_entry['payload'], cached_at))
        
        # Ordenar por cached_at
        all_logs.sort(key=lambda x: x[2])
        
        # Retornar solo log_id y payload
        return [(log_id, payload) for log_id, payload, _ in all_logs[:limit]]
    
    def get_cache_size_mb(self) -> float:
        """
        Obtiene el tamaño actual del cache en MB.
        
        Returns:
            Tamaño del cache en megabytes
        """
        return self._get_cache_size_bytes() / 1024 / 1024
