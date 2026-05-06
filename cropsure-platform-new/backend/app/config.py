"""Application configuration via environment variables."""

import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://cropsure:cropsure@localhost:5432/cropsure"

    # ML service
    ml_service_url: str = "http://localhost:8001"

    # M-Pesa Daraja (Safaricom)
    mpesa_consumer_key: str = ""
    mpesa_consumer_secret: str = ""
    mpesa_shortcode: str = "174379"          # Safaricom sandbox shortcode
    mpesa_passkey: str = ""
    mpesa_initiator_name: str = "testapi"
    mpesa_security_credential: str = ""
    mpesa_callback_url: str = "https://your-ngrok-url.ngrok.io/mpesa/stk-callback"
    mpesa_b2c_result_url: str = "https://your-ngrok-url.ngrok.io/mpesa/b2c-callback"
    mpesa_b2c_timeout_url: str = "https://your-ngrok-url.ngrok.io/mpesa/b2c-timeout"
    mpesa_sandbox: bool = True

    # Africa's Talking
    at_api_key: str = ""
    at_username: str = "sandbox"

    # Twilio WhatsApp
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_whatsapp_from: str = "whatsapp:+14155238886"  # Twilio sandbox

    # App
    frontend_url: str = "http://localhost:5173"
    debug: bool = True
    coverage_multiplier: float = 8.0   # coverage = premium × 8
    premium_per_acre_kes: float = 300.0

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
