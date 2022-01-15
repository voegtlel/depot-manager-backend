import base64
import json
from typing import Optional, List

import requests.auth
from authlib.oidc.core import UserInfo
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBasicCredentials, HTTPBasic, HTTPBearer

from depot_server.helper.auth import Authentication


class MockAuthentication(Authentication):
    async def __call__(
            self,
            authorization_code: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)),
    ) -> Optional[UserInfo]:
        if authorization_code is None:
            if self.auto_error:
                raise HTTPException(
                    status_code=403, detail="Not authenticated"
                )
            return None
        token_data = json.loads(base64.urlsafe_b64decode(authorization_code.credentials.encode()).decode())
        roles = token_data.get('roles', [])
        if self.require_admin and 'admin' not in roles:
            if self.auto_error:
                raise HTTPException(
                    status_code=403, detail="Need admin"
                )
            return None
        if self.require_manager and ('manager' not in roles and 'admin' not in roles):
            if self.auto_error:
                raise HTTPException(
                    status_code=403, detail="Need manager"
                )
            return None
        return token_data


class MockAuth(requests.auth.AuthBase):
    def __init__(self, sub: str, roles: List[str] = None, teams: List[str] = None):
        self.sub = sub
        self.roles = roles or []
        self.teams = teams or []

    def __call__(self, r):
        r.headers["authorization"] = "Bearer " + base64.urlsafe_b64encode(json.dumps(
            {'sub': self.sub, 'roles': self.roles, 'teams': self.teams}
        ).encode()).decode()
        return r
