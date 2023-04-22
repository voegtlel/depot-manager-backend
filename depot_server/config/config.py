from datetime import time

from typing import Optional, List

from pydantic import BaseModel, Field


class MongoConfig(BaseModel):
    uri: str = Field(...)


class MailConfig(BaseModel):
    host: str = Field(...)
    port: Optional[int]
    sender: str = Field(...)

    ssl: bool = False
    starttls: bool = False
    keyfile: Optional[str]
    certfile: Optional[str]
    user: Optional[str]
    password: Optional[str]


class OAuth2ClientConfig(BaseModel):
    client_id: str
    client_secret: Optional[str]
    request_token_url: Optional[str]
    request_token_params: Optional[str]
    access_token_url: Optional[str]
    access_token_params: Optional[str]
    refresh_token_url: Optional[str]
    refresh_token_params: Optional[str]
    authorize_url: Optional[str]
    authorize_params: Optional[str]
    api_base_url: Optional[str]
    server_metadata_url: Optional[str]

    teams_property: str = 'teams'


class Config(BaseModel):
    mongo: MongoConfig = Field(...)
    mail: MailConfig = Field(...)
    oauth2: OAuth2ClientConfig = Field(...)
    frontend_base_url: str = Field(...)
    allow_origins: List[str] = Field(...)

    return_reservation_reminder_cron_time: time = Field(...)

    reservation_code_length: int = Field(...)
    reservation_code_chars: str = Field(...)
    reservation_automatic_return: bool = Field(...)

    device_api_key: Optional[str] = Field(...)
