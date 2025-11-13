"""
Dynamic fact fetcher for real-time information
Supports news headlines, weather data, and other dynamic content
"""

import logging
import urllib.request
import urllib.parse
import json
from typing import List, Dict, Optional
from datetime import datetime


def get_world_news_headlines(category: str = "general", max_results: int = 10) -> List[Dict]:
    """
    Fetch world news headlines from a public news API

    Args:
        category: News category (general, business, technology, etc.)
        max_results: Maximum number of headlines to return

    Returns:
        List of news article dictionaries
    """
    try:
        # Using NewsAPI.org (requires API key in production)
        # For demo purposes, we'll return sample data structure

        # In production, you would do:
        # api_key = os.getenv('NEWS_API_KEY')
        # url = f"https://newsapi.org/v2/top-headlines?category={category}&apiKey={api_key}"

        # For now, return mock data structure
        logging.info(f"Fetching {category} news headlines...")

        # Mock data - replace with actual API call when NEWS_API_KEY is configured
        sample_news = [
            {
                "title": "Latest Technology Breakthrough Announced",
                "source": "Tech News",
                "description": "Major advancement in AI technology revealed today.",
                "url": "https://example.com/news/1",
                "published_at": datetime.now().isoformat(),
                "category": category
            },
            {
                "title": "Global Economic Updates",
                "source": "Business Wire",
                "description": "Markets respond to latest economic indicators.",
                "url": "https://example.com/news/2",
                "published_at": datetime.now().isoformat(),
                "category": category
            }
        ]

        return sample_news[:max_results]

    except Exception as e:
        logging.error(f"Failed to fetch news: {e}")
        return [{
            "title": "Error fetching news",
            "source": "System",
            "description": str(e),
            "url": "",
            "published_at": datetime.now().isoformat(),
            "category": "error"
        }]


def get_weather_snapshot(location: str = "London") -> Dict:
    """
    Fetch weather data for a location using OpenWeatherMap API

    Args:
        location: City name or location

    Returns:
        Weather data dictionary
    """
    try:
        # Using OpenWeatherMap API (requires API key in production)
        # For demo purposes, we'll return sample data structure

        # In production, you would do:
        # api_key = os.getenv('OPENWEATHER_API_KEY')
        # url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={api_key}&units=metric"

        logging.info(f"Fetching weather for {location}...")

        # Mock data - replace with actual API call when OPENWEATHER_API_KEY is configured
        weather_data = {
            "location": location,
            "temperature": 15.5,
            "temperature_unit": "°C",
            "condition": "Partly cloudy",
            "humidity": 65,
            "wind_speed": 12.5,
            "wind_speed_unit": "km/h",
            "pressure": 1013,
            "pressure_unit": "hPa",
            "visibility": 10,
            "visibility_unit": "km",
            "timestamp": datetime.now().isoformat(),
            "note": "Demo data - configure OPENWEATHER_API_KEY for real data"
        }

        return weather_data

    except Exception as e:
        logging.error(f"Failed to fetch weather: {e}")
        return {
            "location": location,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


def get_weather_forecast(location: str = "London", days: int = 5) -> List[Dict]:
    """
    Fetch weather forecast for multiple days

    Args:
        location: City name or location
        days: Number of days to forecast

    Returns:
        List of daily forecast dictionaries
    """
    try:
        logging.info(f"Fetching {days}-day forecast for {location}...")

        # Mock forecast data
        forecast = []
        for i in range(days):
            forecast.append({
                "day": i + 1,
                "date": datetime.now().isoformat(),
                "temperature_high": 18 + i,
                "temperature_low": 10 + i,
                "condition": "Partly cloudy",
                "precipitation_chance": 30,
                "note": "Demo data - configure OPENWEATHER_API_KEY for real data"
            })

        return forecast

    except Exception as e:
        logging.error(f"Failed to fetch forecast: {e}")
        return [{
            "error": str(e),
            "location": location
        }]


def get_stock_quote(symbol: str) -> Dict:
    """
    Fetch stock quote data (requires API key in production)

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL", "GOOGL")

    Returns:
        Stock data dictionary
    """
    try:
        logging.info(f"Fetching stock data for {symbol}...")

        # Mock stock data
        stock_data = {
            "symbol": symbol.upper(),
            "price": 150.25,
            "change": 2.50,
            "change_percent": 1.69,
            "volume": 1234567,
            "market_cap": "2.5T",
            "timestamp": datetime.now().isoformat(),
            "note": "Demo data - configure stock API key for real data"
        }

        return stock_data

    except Exception as e:
        logging.error(f"Failed to fetch stock data: {e}")
        return {
            "symbol": symbol,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


def get_crypto_price(symbol: str = "BTC") -> Dict:
    """
    Fetch cryptocurrency price using CoinGecko API (free, no key required)

    Args:
        symbol: Crypto symbol (BTC, ETH, etc.)

    Returns:
        Crypto price data dictionary
    """
    try:
        # Map common symbols to CoinGecko IDs
        symbol_map = {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "USDT": "tether",
            "BNB": "binancecoin",
            "XRP": "ripple",
            "ADA": "cardano",
            "DOGE": "dogecoin",
            "SOL": "solana"
        }

        coin_id = symbol_map.get(symbol.upper(), symbol.lower())

        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd&include_24hr_change=true&include_market_cap=true"

        logging.info(f"Fetching crypto price for {symbol}...")

        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0')

        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read())

        if coin_id in data:
            coin_data = data[coin_id]
            return {
                "symbol": symbol.upper(),
                "coin_id": coin_id,
                "price_usd": coin_data.get('usd', 0),
                "change_24h": coin_data.get('usd_24h_change', 0),
                "market_cap": coin_data.get('usd_market_cap', 0),
                "timestamp": datetime.now().isoformat(),
                "source": "CoinGecko"
            }
        else:
            return {
                "symbol": symbol,
                "error": "Coin not found",
                "timestamp": datetime.now().isoformat()
            }

    except Exception as e:
        logging.error(f"Failed to fetch crypto price: {e}")
        return {
            "symbol": symbol,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


def get_exchange_rate(from_currency: str = "USD", to_currency: str = "EUR") -> Dict:
    """
    Fetch currency exchange rate

    Args:
        from_currency: Source currency code
        to_currency: Target currency code

    Returns:
        Exchange rate data
    """
    try:
        logging.info(f"Fetching exchange rate {from_currency}/{to_currency}...")

        # Using exchangerate-api.com (free tier available)
        url = f"https://api.exchangerate-api.com/v4/latest/{from_currency.upper()}"

        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0')

        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read())

        rates = data.get('rates', {})
        to_upper = to_currency.upper()

        if to_upper in rates:
            return {
                "from": from_currency.upper(),
                "to": to_upper,
                "rate": rates[to_upper],
                "timestamp": datetime.now().isoformat(),
                "source": "ExchangeRate-API"
            }
        else:
            return {
                "from": from_currency,
                "to": to_currency,
                "error": "Currency not found",
                "timestamp": datetime.now().isoformat()
            }

    except Exception as e:
        logging.error(f"Failed to fetch exchange rate: {e}")
        return {
            "from": from_currency,
            "to": to_currency,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


def get_time_info(timezone: str = "UTC") -> Dict:
    """
    Get current time and date information for a timezone

    Args:
        timezone: Timezone name (e.g., "UTC", "America/New_York")

    Returns:
        Time information dictionary
    """
    try:
        from datetime import datetime, timezone as tz
        import pytz

        try:
            tz_obj = pytz.timezone(timezone)
            now = datetime.now(tz_obj)

            return {
                "timezone": timezone,
                "datetime": now.isoformat(),
                "date": now.strftime("%Y-%m-%d"),
                "time": now.strftime("%H:%M:%S"),
                "day_of_week": now.strftime("%A"),
                "timestamp": now.timestamp()
            }
        except:
            # Fallback to UTC if timezone not recognized
            now = datetime.now(tz.utc)
            return {
                "timezone": "UTC",
                "datetime": now.isoformat(),
                "date": now.strftime("%Y-%m-%d"),
                "time": now.strftime("%H:%M:%S"),
                "day_of_week": now.strftime("%A"),
                "timestamp": now.timestamp(),
                "note": f"Timezone '{timezone}' not found, showing UTC"
            }

    except Exception as e:
        logging.error(f"Failed to get time info: {e}")
        return {
            "timezone": timezone,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
