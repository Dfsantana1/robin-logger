# 🪶 Robin Logger

**Robin Logger** es una librería Python para enviar eventos de login, auditoría y actividad hacia un backend centralizado mediante una API HTTP.

**Versión:** 0.2.0

## ✨ Características

- 🚀 **Envío asíncrono** mediante threading (no bloquea tu aplicación)
- 🔄 **Retry automático** con backoff exponencial para manejar fallos de red
- 💾 **Cache local** con límite de tamaño (30 MB por defecto)
- 🔁 **Reintentos automáticos** en background para logs en cache
- ⏱️ **Backoff exponencial inteligente** que se ajusta automáticamente
- 📦 **Fácil de usar** con una API simple e intuitiva
- 🔧 **Altamente configurable** mediante parámetros o variables de entorno
- 📊 **Soporte completo para JSON** acepta cualquier estructura de datos

## 📦 Instalación

```bash
pip install robin-logger
```

## 🚀 Uso Rápido

### Ejemplo básico

```python
from robin_logger import RobinLogger

# Inicializar el logger
logger = RobinLogger(
    base_url="https://api.robinlogs.com/v1/logs",
    api_key="tu_api_key_aqui"
)

# Enviar un log de login exitoso
logger.send_log(
    type="login",
    category="user_auth",
    subcategory="success",
    level="info",
    data={
        "username": "william",
        "ip": "192.168.1.10",
        "timestamp": "2025-10-29T11:23:00Z"
    }
)

# Enviar un log de auditoría
logger.send_log(
    type="audit",
    category="data_access",
    subcategory="read",
    level="info",
    data={
        "user_id": 1234,
        "resource": "users_table",
        "action": "SELECT",
        "affected_rows": 150
    }
)
```

### Usando variables de entorno

```python
import os

# Configurar variables de entorno
os.environ["ROBIN_LOGGER_URL"] = "https://api.robinlogs.com/v1/logs"
os.environ["ROBIN_LOGGER_API_KEY"] = "tu_api_key_aqui"

# Inicializar sin parámetros (usa las variables de entorno)
from robin_logger import RobinLogger

logger = RobinLogger()

logger.send_log(
    type="activity",
    category="user_action",
    subcategory="document_created",
    level="info",
    data={
        "user_id": 789,
        "document_id": "doc-456",
        "title": "Informe Q4 2025"
    }
)
```

### Context Manager

```python
from robin_logger import RobinLogger

with RobinLogger(
    base_url="https://api.robinlogs.com/v1/logs",
    api_key="tu_api_key"
) as logger:
    logger.send_log(
        type="login",
        category="user_auth",
        subcategory="success",
        level="info",
        data={"username": "alice"}
    )
# La conexión se cierra automáticamente
```

## 🔧 Configuración

### Parámetros del constructor

```python
RobinLogger(
    base_url: str = None,                    # URL del API (o ROBIN_LOGGER_URL)
    api_key: str = None,                     # API Key (o ROBIN_LOGGER_API_KEY)
    timeout: int = 10,                       # Timeout en segundos
    max_retries: int = 3,                    # Número máximo de reintentos
    backoff_factor: float = 0.5,             # Factor de backoff (0.5, 1, 2, 4 segundos...)
    enable_local_cache: bool = True,         # Habilitar cache local
    cache_dir: str = None,                   # Directorio de cache (default: ~/.robin_logger_cache)
    cache_max_size_mb: float = 30.0,         # 🆕 Límite de tamaño del cache en MB
    async_mode: bool = True,                 # Envío asíncrono (True) o síncrono (False)
    auto_retry_enabled: bool = True,         # 🆕 Reintentos automáticos en background
    auto_retry_interval: int = 60,           # 🆕 Intervalo inicial de reintentos (segundos)
    auto_retry_max_interval: int = 3600,     # 🆕 Intervalo máximo de reintentos (segundos)
    auto_retry_async: bool = True            # 🆕 Modo asíncrono para reintentos
)
```

### Variables de entorno

| Variable | Descripción | Requerida |
|----------|-------------|-----------|
| `ROBIN_LOGGER_URL` | URL base del API de logging | Sí* |
| `ROBIN_LOGGER_API_KEY` | API Key para autenticación | Sí* |

*Si no se proporcionan como parámetros en el constructor

### Ejemplo con archivo `.env`

```bash
# .env
ROBIN_LOGGER_URL=https://api.robinlogs.com/v1/logs
ROBIN_LOGGER_API_KEY=sk_live_abc123xyz789
```

```python
from dotenv import load_dotenv
from robin_logger import RobinLogger

load_dotenv()
logger = RobinLogger()  # Lee las variables automáticamente
```

## 📊 Parámetros del método `send_log()`

```python
logger.send_log(
    type: str,          # Tipo de evento: "login", "audit", "activity", etc.
    category: str,      # Categoría: "user_auth", "data_access", "system", etc.
    subcategory: str,   # Subcategoría: "success", "failure", "read", "write", etc.
    level: str,         # Nivel: "info", "warning", "error", "critical"
    data: dict,         # Cualquier estructura JSON con los datos del evento
    timestamp: str = None  # Timestamp ISO 8601 (opcional, se genera automáticamente)
)
```

## 💾 Cache Local

Cuando el envío falla (por ejemplo, sin conexión a internet), los logs se guardan automáticamente en cache local.

### 🆕 Límite de Tamaño del Cache

El cache tiene un límite configurable (default: 30 MB). Cuando se excede, elimina logs antiguos automáticamente (FIFO).

```python
logger = RobinLogger(
    base_url="...",
    api_key="...",
    cache_max_size_mb=50.0  # Límite de 50 MB
)
```

### 🆕 Reintentos Automáticos en Background

El logger reintenta automáticamente enviar logs del cache en segundo plano:

```python
logger = RobinLogger(
    base_url="...",
    api_key="...",
    auto_retry_enabled=True,        # Activar reintentos automáticos
    auto_retry_interval=60,         # Reintentar cada 60 segundos
    auto_retry_max_interval=3600,   # Máximo 1 hora
    auto_retry_async=True           # En background
)

# El sistema automáticamente:
# 1. Reintenta enviar logs cada 60 segundos
# 2. Usa backoff exponencial si falla (60s → 120s → 240s → ...)
# 3. Se resetea a 60s después de éxitos
# 4. No bloquea tu aplicación
```

### Ver estadísticas del cache

```python
stats = logger.get_cache_stats()
print(stats)
# {
#     'enabled': True,
#     'count': 10,
#     'size_mb': 5.2,
#     'max_size_mb': 30.0,
#     'usage_percent': 17.33,
#     'cache_dir': '/Users/user/.robin_logger_cache'
# }
```

### Ver estado de reintentos automáticos

```python
retry_stats = logger.get_retry_stats()
print(retry_stats)
# {
#     'enabled': True,
#     'running': True,
#     'current_interval': 60,
#     'max_interval': 3600,
#     'failures': 0,
#     'async_mode': True
# }
```

### Reintentar logs manualmente

```python
# Reintento manual (útil si desactivas reintentos automáticos)
result = logger.retry_cached_logs()
print(result)
# {'sent': 5, 'failed': 0, 'total': 5}
```

### Detener reintentos automáticos

```python
logger.stop_auto_retry()

# O automáticamente al cerrar
logger.close()
```

### Limpiar cache

```python
logger.clear_cache()
```

## 🔄 Sistema de Retry Completo

Robin Logger implementa dos niveles de retry:

### 1. Retry HTTP Inmediato

Para errores temporales durante el envío:
- **Reintentos**: 3 por defecto (configurable)
- **Backoff**: 0.5s, 1s, 2s, 4s... (configurable)
- **Códigos HTTP reintentables**: 429, 500, 502, 503, 504

```python
logger = RobinLogger(
    base_url="https://api.robinlogs.com/v1/logs",
    api_key="tu_api_key",
    max_retries=5,        # 5 reintentos inmediatos
    backoff_factor=1.0    # 1s, 2s, 4s, 8s, 16s
)
```

### 2. 🆕 Reintentos Automáticos en Background

Para logs que van al cache (sin conexión o fallo persistente):
- **Reintentos periódicos**: Cada N segundos en background
- **Backoff exponencial inteligente**: Se ajusta automáticamente
- **Recuperación automática**: Cuando el servidor vuelve

```python
logger = RobinLogger(
    base_url="https://api.robinlogs.com/v1/logs",
    api_key="tu_api_key",
    auto_retry_enabled=True,        # Activar reintentos automáticos
    auto_retry_interval=60,         # Empezar con 60 segundos
    auto_retry_max_interval=3600    # Máximo 1 hora
)

# Secuencia de backoff si el servidor sigue caído:
# Intento 1: 60s
# Intento 2 (fallo): 120s
# Intento 3 (fallo): 240s
# Intento 4 (fallo): 480s
# Intento 5+ (fallo): 3600s (máximo)
# Después de éxito: vuelve a 60s
```

## 🌐 Ejemplos de Uso Real

### Aplicación Web (Flask)

```python
from flask import Flask, request
from robin_logger import RobinLogger

app = Flask(__name__)
logger = RobinLogger()

@app.route('/login', methods=['POST'])
def login():
    username = request.json.get('username')
    password = request.json.get('password')
    
    # Autenticar usuario...
    if authenticate(username, password):
        logger.send_log(
            type="login",
            category="user_auth",
            subcategory="success",
            level="info",
            data={
                "username": username,
                "ip": request.remote_addr,
                "user_agent": request.headers.get('User-Agent')
            }
        )
        return {"status": "success"}
    else:
        logger.send_log(
            type="login",
            category="user_auth",
            subcategory="failure",
            level="warning",
            data={
                "username": username,
                "ip": request.remote_addr,
                "reason": "invalid_credentials"
            }
        )
        return {"status": "error"}, 401
```

### Script de ETL

```python
from robin_logger import RobinLogger
import pandas as pd

logger = RobinLogger()

def process_data():
    try:
        # Cargar datos
        df = pd.read_csv('data.csv')
        
        logger.send_log(
            type="etl",
            category="data_processing",
            subcategory="start",
            level="info",
            data={
                "rows": len(df),
                "source": "data.csv"
            }
        )
        
        # Procesar...
        result = df.groupby('category').sum()
        
        logger.send_log(
            type="etl",
            category="data_processing",
            subcategory="success",
            level="info",
            data={
                "rows_processed": len(df),
                "output_rows": len(result),
                "duration_seconds": 45.2
            }
        )
        
    except Exception as e:
        logger.send_log(
            type="etl",
            category="data_processing",
            subcategory="error",
            level="error",
            data={
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        )
```

### API REST (FastAPI)

```python
from fastapi import FastAPI, Request
from robin_logger import RobinLogger

app = FastAPI()
logger = RobinLogger()

@app.middleware("http")
async def log_requests(request: Request, call_next):
    # Log entrada de request
    logger.send_log(
        type="api_request",
        category="http",
        subcategory="incoming",
        level="info",
        data={
            "method": request.method,
            "path": request.url.path,
            "client_ip": request.client.host
        }
    )
    
    response = await call_next(request)
    
    # Log respuesta
    logger.send_log(
        type="api_response",
        category="http",
        subcategory="outgoing",
        level="info",
        data={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code
        }
    )
    
    return response
```

## 📝 Estructura de datos enviados

El logger envía el siguiente payload al API:

```json
{
  "type": "login",
  "category": "user_auth",
  "subcategory": "success",
  "level": "info",
  "timestamp": "2025-10-31T12:00:00Z",
  "data": {
    "username": "william",
    "ip": "192.168.1.10"
  }
}
```

Los headers incluyen:

```
Content-Type: application/json
Authorization: Bearer {api_key}
User-Agent: robin-logger-python/0.1.0
```

## 🔀 Modos de Operación

### Envío de Logs

Por defecto, los logs se envían de forma asíncrona. Para envío síncrono (bloqueante):

```python
logger = RobinLogger(
    base_url="https://api.robinlogs.com/v1/logs",
    api_key="tu_api_key",
    async_mode=False  # Modo síncrono
)

# Este call bloqueará hasta que se complete
logger.send_log(type="test", category="sync", subcategory="test", level="info", data={})
```

### 🆕 Reintentos Automáticos

Los reintentos también pueden ser síncronos o asíncronos:

```python
# Modo asíncrono (recomendado): Reintentos en threads separados
logger = RobinLogger(
    base_url="...",
    api_key="...",
    auto_retry_async=True  # Default: No bloquea
)

# Modo síncrono: Reintentos en el mismo thread de control
logger = RobinLogger(
    base_url="...",
    api_key="...",
    auto_retry_async=False  # Más predecible pero potencialmente más lento
)
```

## 🆕 Casos de Uso

### Aplicación Móvil con Conectividad Intermitente

```python
logger = RobinLogger(
    base_url="https://api.example.com/logs",
    api_key="mobile_key",
    cache_max_size_mb=10.0,      # Espacio limitado
    auto_retry_interval=120,     # Cada 2 minutos
    auto_retry_max_interval=3600 # Máximo 1 hora
)
# Los logs se guardan cuando no hay red
# Se reenvían automáticamente cuando hay conexión
```

### Servidor de Alta Disponibilidad

```python
logger = RobinLogger(
    base_url="https://api.example.com/logs",
    api_key="server_key",
    cache_max_size_mb=100.0,     # Más capacidad
    auto_retry_interval=30,      # Reintentos rápidos (30s)
    auto_retry_max_interval=600  # Máximo 10 minutos
)
# Recuperación rápida de fallos temporales
```

### Dispositivo IoT con Recursos Limitados

```python
logger = RobinLogger(
    base_url="https://api.example.com/logs",
    api_key="iot_key",
    cache_max_size_mb=5.0,       # Muy limitado
    auto_retry_interval=300,     # Cada 5 minutos
    auto_retry_async=False       # Síncrono para control de recursos
)
```

### Control Manual (Sin Reintentos Automáticos)

```python
logger = RobinLogger(
    base_url="https://api.example.com/logs",
    api_key="manual_key",
    auto_retry_enabled=False     # Desactivar automático
)

# Reintentar manualmente cuando sea necesario
result = logger.retry_cached_logs()
print(f"Enviados: {result['sent']}, Fallidos: {result['failed']}")

### Usando Makefile (comandos útiles)

```bash
make help           # Ver todos los comandos disponibles
make install-dev    # Instalar en modo desarrollo
make test           # Ejecutar tests
make test-cov       # Tests con cobertura
make format         # Formatear código
make build          # Construir paquete
make clean          # Limpiar archivos temporales
make quick-test     # Prueba rápida con httpbin
```

## 📦 Instalación y Publicación

### Instalar desde código fuente

```bash
git clone https://github.com/tu-usuario/robin-logger.git
cd robin-logger
pip install -e .
```

### Publicar en PyPI

```bash
# 1. Instalar herramientas
pip install build twine

# 2. Construir el paquete
python -m build

# 3. Subir a PyPI
twine upload dist/*
# Username: __token__
# Password: [tu-token-de-pypi]
```

## 📋 Resumen de Funcionalidades

| Funcionalidad | Descripción | Configurable |
|--------------|-------------|--------------|
| 🚀 Envío Asíncrono | No bloquea tu aplicación | `async_mode` |
| 🔄 Retry HTTP | Reintentos inmediatos con backoff | `max_retries`, `backoff_factor` |
| 💾 Cache Local | Guarda logs cuando no hay conexión | `enable_local_cache` |
| 📦 Límite de Cache | Límite de tamaño con rotación automática | `cache_max_size_mb` |
| 🔁 Reintentos Automáticos | Reintenta en background periódicamente | `auto_retry_enabled` |
| ⏱️ Backoff Exponencial | Intervalos crecientes inteligentes | `auto_retry_interval`, `auto_retry_max_interval` |
| 🔀 Modos Async/Sync | Configurable para envío y reintentos | `async_mode`, `auto_retry_async` |
| 🌍 Variables de Entorno | Configuración desde env vars | `ROBIN_LOGGER_URL`, `ROBIN_LOGGER_API_KEY` |
| 📊 JSON Completo | Cualquier estructura en `data` | ✅ |

## 🤝 Contribuir

Las contribuciones son bienvenidas! Por favor:

1. Fork el repositorio
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está licenciado bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para más detalles.

## 🆕 Novedades v0.2.0

- ✅ **Límite de tamaño del cache** (30 MB default, configurable)
- ✅ **Rotación automática** de logs antiguos cuando se excede el límite
- ✅ **Reintentos automáticos** en background con thread dedicado
- ✅ **Backoff exponencial inteligente** para reintentos automáticos
- ✅ **Modos asíncrono/síncrono** para reintentos
- ✅ **Estadísticas mejoradas** con tamaño de cache y estado de reintentos
- ✅ **Recuperación automática** cuando el servidor vuelve a estar disponible

## 🔗 Enlaces

- **GitHub**: https://github.com/tu-usuario/robin-logger
- **Issues**: https://github.com/tu-usuario/robin-logger/issues

## 📧 Soporte

Para preguntas o soporte, por favor abre un issue en GitHub.

## 📄 Licencia

Este proyecto está licenciado bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para más detalles.

---

**Robin Logger v0.2.0** - Sistema de logging centralizado con reintentos automáticos y cache inteligente  
Hecho con ❤️ por Diego
