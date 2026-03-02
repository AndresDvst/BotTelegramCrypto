# 🤖 Bot de Telegram Crypto - Análisis de Criptomonedas

Bot de Telegram multiusuario para análisis de criptomonedas con dashboard web de monitoreo, integración con múltiples exchanges y análisis por IA.

## 📋 Requisitos

- **Python 3.11+**
- Cuenta de Telegram Bot (obtener token de [@BotFather](https://t.me/BotFather))
- API Key de Groq (gratis en [console.groq.com](https://console.groq.com))
- API Key de CoinMarketCap (gratis en [coinmarketcap.com/api](https://coinmarketcap.com/api))

## 🚀 Instalación Paso a Paso

### 1. Clonar el repositorio

```bash
git clone https://github.com/AndresDvst/BotTelegramCrypto.git
cd BotTelegramCrypto
cd crypto_bot
```

### 2. Crear entorno virtual

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

```bash
# Copiar el archivo de ejemplo
cp .env.example .env

# Editar .env con tus valores
```

## 🔑 Cómo Obtener Cada API Key

### Telegram Bot Token

1. Abrir Telegram y buscar [@BotFather](https://t.me/BotFather)
2. Enviar `/newbot`
3. Seguir las instrucciones para nombrar tu bot
4. Copiar el token que te proporciona

### Groq API Key

1. Ir a [console.groq.com](https://console.groq.com)
2. Crear una cuenta gratuita
3. Ir a "API Keys" en el menú lateral
4. Crear una nueva API Key y copiarla

### CoinMarketCap API Key

1. Ir a [coinmarketcap.com/api](https://coinmarketcap.com/api)
2. Registrarse en el plan "Basic" (gratuito)
3. Copiar la API Key del dashboard

## ⚙️ Configuración del .env

```env
# Telegram
TELEGRAM_BOT_TOKEN=tu_token_aqui

# Groq IA
GROQ_API_KEY=tu_groq_api_key

# CoinMarketCap (para sentimiento)
COINMARKETCAP_API_KEY=tu_cmc_api_key

# Dashboard
DASHBOARD_PORT=5000
DASHBOARD_SECRET_KEY=cambia_esto_por_algo_seguro

# Base de datos
DATABASE_URL=sqlite:///crypto_bot.db

# Configuración del bot
MIN_CHANGE_PERCENT=5
TOP_N_RESULTS=10
TOP_RECOMMENDATIONS=3
INACTIVITY_TIMEOUT_SECONDS=300
```

## ▶️ Ejecutar el Bot

```bash
python main.py
```

Esto inicia simultáneamente:

- **Bot de Telegram** — escuchando mensajes
- **Dashboard Web** — en `http://localhost:5000`

## 🧪 Ejecutar Tests

```bash
# Ejecutar todos los tests
pytest tests/ -v

# Ejecutar un test específico
pytest tests/test_start.py -v

# Ejecutar con cobertura
pytest tests/ -v --tb=short
```

## 📊 Acceder al Dashboard

Una vez ejecutado el bot, accede al dashboard en tu navegador:

```
http://localhost:5000
```

El dashboard muestra:

- 👥 Total de usuarios (histórico)
- 🟢 Usuarios activos hoy
- 📨 Peticiones al bot hoy
- 🌐 Peticiones a APIs externas
- 📊 Gráficos de barras por comando y por API
- 📈 Gráfico de actividad por hora (24h)
- 📋 Tabla de últimas 20 peticiones en tiempo real

Se auto-refresca cada 30 segundos.

## 🤖 Comandos del Bot

| Comando                      | Descripción                            |
| ---------------------------- | -------------------------------------- |
| `/start` o "iniciar"         | Inicia el bot y muestra el menú        |
| `/TopSubidas4H`              | Top 10 criptos con mayor subida en 4h  |
| `/TopBajadas4H`              | Top 10 criptos con mayor bajada en 4h  |
| `/TopSubidas24H`             | Top 10 criptos con mayor subida en 24h |
| `/TopBajadas24H`             | Top 10 criptos con mayor bajada en 24h |
| `/SentimientoDelMercado`     | Índice Fear & Greed del mercado        |
| `/OrdenesDeMercado`          | Órdenes de compra/venta de una cripto  |
| `/ConsultarCryptoEspecifica` | Análisis completo de una cripto        |

## 📁 Estructura del Proyecto

```
crypto_bot/
├── main.py                          # Punto de entrada principal
├── bot/
│   ├── handlers/                    # Handlers de cada comando
│   ├── conversation/                # Manejo de estado por usuario
│   └── utils/                       # Formateo y timeout
├── services/
│   ├── exchanges/                   # Binance, Bybit, KuCoin, Kraken, Coinbase
│   ├── exchange_aggregator.py       # Agregador con fallback
│   ├── sentiment_service.py         # Fear & Greed + CoinGecko fallback
│   └── groq_service.py              # Análisis IA con Groq
├── dashboard/
│   ├── app.py                       # Flask API + Dashboard
│   ├── templates/dashboard.html     # UI con Chart.js
│   └── static/dashboard.js          # Auto-refresco JS
├── database/
│   ├── models.py                    # Modelos SQLAlchemy
│   └── metrics_manager.py           # CRUD de métricas
├── config/
│   └── config.py                    # Configuración desde .env
├── tests/                           # Tests con pytest
├── .env.example
├── requirements.txt
└── README.md
```

## 🔧 Exchanges Integrados

El bot consulta datos de 5 exchanges en paralelo:

- **Binance** — Exchange principal y fallback
- **Bybit** — Spot market
- **KuCoin** — Spot market
- **Kraken** — Pares USD
- **Coinbase** — Pares USD

Todos usan endpoints públicos sin necesidad de API Key.

## 🧠 IA con Groq

- Modelo principal: `llama-3.3-70b-versatile`
- Modelo fallback: `mixtral-8x7b-32768`
- Las recomendaciones se generan automáticamente para los top movers
- Si Groq falla, el bot envía los datos sin análisis IA
