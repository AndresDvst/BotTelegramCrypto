"""
Formateo de mensajes del bot con emojis decorativos.
Todos los mensajes del bot pasan por estas funciones.
"""

import logging

logger = logging.getLogger(__name__)


def format_welcome_message(first_name: str) -> str:
    """Formatea el mensaje de bienvenida.

    Args:
        first_name: Nombre del usuario.

    Returns:
        Mensaje de bienvenida formateado con emojis.
    """
    return (
        f"👋 ¡Hola {first_name}! Soy tu asistente de análisis crypto 🤖\n\n"
        f"📋 Estos son los comandos disponibles:\n\n"
        f"📈 /TopSubidas4H — Top 10 criptos con mayor subida en 4h\n"
        f"📉 /TopBajadas4H — Top 10 criptos con mayor bajada en 4h\n"
        f"🚀 /TopSubidas24H — Top 10 criptos con mayor subida en 24h\n"
        f"💥 /TopBajadas24H — Top 10 criptos con mayor bajada en 24h\n"
        f"🧠 /SentimientoDelMercado — Fear & Greed Index del mercado\n"
        f"📊 /OrdenesDeMercado — Órdenes de compra/venta de una cripto\n"
        f"🔍 /ConsultarCryptoEspecifica — Análisis completo de una cripto\n\n"
        f"¡Elige un comando para comenzar! 💪"
    )


def format_menu_message() -> str:
    """Formatea el menú de comandos sin saludo.

    Returns:
        Menú de comandos formateado.
    """
    return (
        "📋 Comandos disponibles:\n\n"
        "📈 /TopSubidas4H — Top 10 criptos con mayor subida en 4h\n"
        "📉 /TopBajadas4H — Top 10 criptos con mayor bajada en 4h\n"
        "🚀 /TopSubidas24H — Top 10 criptos con mayor subida en 24h\n"
        "💥 /TopBajadas24H — Top 10 criptos con mayor bajada en 24h\n"
        "🧠 /SentimientoDelMercado — Fear & Greed Index del mercado\n"
        "📊 /OrdenesDeMercado — Órdenes de compra/venta de una cripto\n"
        "🔍 /ConsultarCryptoEspecifica — Análisis completo de una cripto\n\n"
        "¡Elige un comando! 💪"
    )


def format_top_movers_message(
    movers: list[dict],
    timeframe: str,
    direction: str,
    recommendations: str,
    sentiment: dict
) -> str:
    """Formatea el mensaje de top movers (subidas o bajadas).

    Args:
        movers: Lista de dicts con datos de las top monedas.
        timeframe: '4h' o '24h'.
        direction: 'up' o 'down'.
        recommendations: Texto de recomendaciones de IA.
        sentiment: Dict con datos de sentimiento.

    Returns:
        Mensaje formateado con emojis.
    """
    timeframe_text = "4 horas" if timeframe == "4h" else "24 horas"

    if direction == "up":
        header = f"📈 TOP 10 SUBIDAS — Últimas {timeframe_text}\n\n"
        emoji = "🟢"
    else:
        header = f"📉 TOP 10 BAJADAS — Últimas {timeframe_text}\n\n"
        emoji = "🔴"

    lines = [header]

    for i, mover in enumerate(movers, 1):
        symbol = mover.get("symbol", "N/A")
        price = mover.get("price", 0)
        change = mover.get("change_pct", 0)
        market_cap = mover.get("market_cap", "N/A")
        buy_sell = mover.get("buy_sell_ratio", "N/A")

        change_sign = "+" if change >= 0 else ""

        lines.append(
            f"{i}. {emoji} {symbol}\n"
            f"   💰 Precio: ${price:,.2f}\n"
            f"   📊 Cambio {timeframe}: {change_sign}{change:.2f}%\n"
            f"   🏦 Cap. Mercado: {market_cap}\n"
            f"   ⚖️ Compra/Venta: {buy_sell}\n"
        )

    lines.append("━━━━━━━━━━━━━━━━━━━━━")
    lines.append("🤖 RECOMENDACIONES IA (Groq)\n")
    lines.append(recommendations)
    lines.append("\n━━━━━━━━━━━━━━━━━━━━━")

    sentiment_value = sentiment.get("value", "N/A")
    sentiment_class = sentiment.get("classification", "N/A")
    lines.append(f"🧠 Sentimiento del mercado: {sentiment_class} ({sentiment_value}/100)")

    return "\n".join(lines)


def format_sentiment_message(sentiment: dict) -> str:
    """Formatea el mensaje de sentimiento del mercado.

    Args:
        sentiment: Dict con value, classification, previous_day, previous_week.

    Returns:
        Mensaje formateado.
    """
    value = sentiment.get("value", "N/A")
    classification = sentiment.get("classification", "N/A")
    source = sentiment.get("source", "N/A")

    message = (
        f"🧠 SENTIMIENTO DEL MERCADO\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 Índice Fear & Greed: {value}/100\n"
        f"📋 Clasificación: {classification}\n"
        f"📡 Fuente: {source.capitalize()}\n"
    )

    if sentiment.get("previous_day"):
        message += f"📅 Actualización: {sentiment['previous_day']}\n"

    return message


def format_orderbook_message(
    symbol: str,
    bids: list[dict],
    asks: list[dict],
    sentiment: dict
) -> str:
    """Formatea el mensaje del libro de órdenes.

    Args:
        symbol: Símbolo de la moneda.
        bids: Lista de órdenes de compra.
        asks: Lista de órdenes de venta.
        sentiment: Dict con datos de sentimiento.

    Returns:
        Mensaje formateado.
    """
    lines = [
        f"📊 ÓRDENES DE MERCADO — {symbol}\n",
        "━━━━━━━━━━━━━━━━━━━━━\n",
        "🟢 ÓRDENES DE COMPRA (Top 20):\n"
    ]

    for i, bid in enumerate(bids[:20], 1):
        price = bid.get("price", 0)
        qty = bid.get("quantity", 0)
        lines.append(f"  {i}. 💰 ${price:,.2f} — Cantidad: {qty:,.4f}")

    lines.append("\n🔴 ÓRDENES DE VENTA (Top 20):\n")

    for i, ask in enumerate(asks[:20], 1):
        price = ask.get("price", 0)
        qty = ask.get("quantity", 0)
        lines.append(f"  {i}. 💰 ${price:,.2f} — Cantidad: {qty:,.4f}")

    lines.append("\n━━━━━━━━━━━━━━━━━━━━━")

    sentiment_value = sentiment.get("value", "N/A")
    sentiment_class = sentiment.get("classification", "N/A")
    lines.append(f"🧠 Sentimiento del mercado: {sentiment_class} ({sentiment_value}/100)")

    return "\n".join(lines)


def format_coin_detail_message(coin_data: dict, sentiment: dict) -> str:
    """Formatea el mensaje de consulta de crypto específica.

    Args:
        coin_data: Dict con datos de la moneda.
        sentiment: Dict con datos de sentimiento.

    Returns:
        Mensaje formateado.
    """
    symbol = coin_data.get("symbol", "N/A")
    price = coin_data.get("price", 0)
    change_4h = coin_data.get("change_pct_4h", 0)
    change_24h = coin_data.get("price_change_percent_24h", 0)
    market_cap = coin_data.get("market_cap", "N/A")
    buy_sell = coin_data.get("buy_sell_ratio", "N/A")

    change_4h_sign = "+" if change_4h >= 0 else ""
    change_24h_sign = "+" if change_24h >= 0 else ""

    sentiment_value = sentiment.get("value", "N/A")
    sentiment_class = sentiment.get("classification", "N/A")

    return (
        f"🔍 ANÁLISIS — {symbol}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 Precio actual: ${price:,.2f}\n"
        f"📊 Cambio 4h: {change_4h_sign}{change_4h:.2f}%\n"
        f"📊 Cambio 24h: {change_24h_sign}{change_24h:.2f}%\n"
        f"🏦 Cap. Mercado: {market_cap}\n"
        f"⚖️ Ratio Compra/Venta: {buy_sell}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🧠 Sentimiento del mercado: {sentiment_class} ({sentiment_value}/100)"
    )


def format_continue_message() -> str:
    """Formatea el mensaje de pregunta para continuar.

    Returns:
        Mensaje formateado.
    """
    return (
        "\n¿Deseas hacer otra consulta?\n"
        "👉 Escribe /si para continuar\n"
        "👉 Escribe /no para terminar"
    )


def format_goodbye_message() -> str:
    """Formatea el mensaje de despedida.

    Returns:
        Mensaje de despedida.
    """
    return (
        "👋 ¡Hasta luego! Fue un placer ayudarte.\n"
        "Para volver, escribe \"iniciar\" en cualquier momento. 😊"
    )


def format_timeout_message() -> str:
    """Formatea el mensaje de timeout por inactividad.

    Returns:
        Mensaje de timeout.
    """
    return (
        "⏰ Tu sesión ha expirado por inactividad (5 minutos).\n"
        "Para volver, escribe \"iniciar\" en cualquier momento. 👋"
    )


def format_loading_message() -> str:
    """Formatea el mensaje de carga.

    Returns:
        Mensaje de carga.
    """
    return "🔄 Consultando exchanges, espera un momento..."


def format_ask_coin_input() -> str:
    """Formatea la pregunta para buscar una moneda.

    Returns:
        Mensaje de pregunta.
    """
    return (
        '¿Cómo prefieres buscar la moneda? Escribe el **nombre** '
        '(ej: Bitcoin) o el **símbolo** (ej: BTC)'
    )
