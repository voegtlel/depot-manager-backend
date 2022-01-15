import httpx
from authlib.common.errors import AuthlibBaseError, AuthlibHTTPError
from authlib.integrations.starlette_client import OAuth as _OAuth, StarletteRemoteApp as _StarletteRemoteApp
from authlib.oidc.core import UserInfo
from datetime import date
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN, HTTP_401_UNAUTHORIZED
from typing import Optional, List, Tuple

from depot_server.config import config
from depot_server.db import collections, DbReservation
from depot_server.model import User


class StarletteRemoteApp(_StarletteRemoteApp):

    # Hotfix patch
    async def _fetch_server_metadata(self, url):
        async with self._get_oauth_client() as client:
            from httpx import USE_CLIENT_DEFAULT
            resp = await client.request('GET', url, auth=USE_CLIENT_DEFAULT, withhold_token=True)
            return resp.json()

    async def parse_access_token_raw(self, token: str) -> UserInfo:
        return await self._parse_id_token({'id_token': token, 'access_token': True}, nonce=None, claims_options=None)


class OAuth(_OAuth):
    framework_client_cls = StarletteRemoteApp

    server: StarletteRemoteApp


oauth = OAuth()
oauth.register('server', **config.oauth2.dict())


async def get_profile(user_id: str) -> dict:
    server_metadata = await oauth.server.load_server_metadata()
    issuer = server_metadata['issuer']
    profile_url = f"{issuer}/profiles/{user_id}"
    async with httpx.AsyncClient(auth=httpx.BasicAuth(config.oauth2.client_id, config.oauth2.client_secret)) as client:
        r = await client.get(profile_url)
        r.raise_for_status()
    return r.json()


async def get_profiles() -> List[dict]:
    server_metadata = await oauth.server.load_server_metadata()
    issuer = server_metadata['issuer']
    profiles_url = f"{issuer}/profiles"
    async with httpx.AsyncClient(auth=httpx.BasicAuth(config.oauth2.client_id, config.oauth2.client_secret)) as client:
        r = await client.get(profiles_url)
        r.raise_for_status()
    return r.json()


class Authentication:
    def __init__(
            self,
            require_manager: bool = False,
            require_admin: bool = False,
            auto_error: bool = True,
            require_userinfo: bool = False,
    ):
        self.require_manager = require_manager
        self.require_admin = require_admin
        self.auto_error = auto_error
        self.require_userinfo = require_userinfo

    async def __call__(
            self,
            authorization_code: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)),
    ) -> Optional[UserInfo]:
        if authorization_code is None:
            if self.auto_error:
                raise HTTPException(
                    status_code=HTTP_403_FORBIDDEN, detail="Not authenticated"
                )
            return None
        try:
            token_data = await oauth.server.parse_access_token_raw(authorization_code.credentials)
        except AuthlibHTTPError as e:
            raise HTTPException(*e())
        except AuthlibBaseError as e:
            raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail=f"{e.error}: {e.description}")
        if self.require_admin and 'admin' not in token_data['roles']:
            if self.auto_error:
                raise HTTPException(
                    status_code=HTTP_403_FORBIDDEN, detail="Need admin"
                )
            return None
        if self.require_manager and ('manager' not in token_data['roles'] and 'admin' not in token_data['roles']):
            if self.auto_error:
                raise HTTPException(
                    status_code=HTTP_403_FORBIDDEN, detail="Need manager"
                )
            return None
        if self.require_userinfo:
            userinfo = await oauth.server.userinfo(
                token={'token_type': 'bearer', 'access_token': authorization_code.credentials}
            )
            token_data.update(userinfo)
        return token_data


class DeviceAuthentication:
    def __init__(
            self,
            auto_error: bool = True,
    ):
        self.auto_error = auto_error

    async def __call__(
            self,
            device_api_key: Optional[str] = Depends(APIKeyHeader(name="X-Device-Api-Key", auto_error=False)),
            reservation_code: Optional[str] = Depends(APIKeyHeader(name="X-Reservation-Code", auto_error=False)),
    ) -> Tuple[Optional[User], Optional[DbReservation]]:
        if device_api_key is None or reservation_code is None:
            if self.auto_error:
                raise HTTPException(
                    status_code=HTTP_403_FORBIDDEN, detail="Not authenticated"
                )
            return None, None
        if device_api_key != config.device_api_key:
            raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid token")
        reservation = await collections.reservation_collection.find_one(
            {'code': reservation_code, 'start': {'$lte': date.today().toordinal()}},
        )
        if reservation is None:
            raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="No reservation for token")
        user_id = reservation.user_id
        profile = await get_profile(user_id)
        if profile is None:
            raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="No profile for user id")

        return User.validate(profile), reservation
