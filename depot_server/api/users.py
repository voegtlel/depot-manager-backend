from authlib.oidc.core import UserInfo
from fastapi import APIRouter, Depends, HTTPException
from typing import List

from depot_server.helper.auth import Authentication, get_profiles, get_profile

router = APIRouter()


@router.get(
    '/users',
    tags=['Users'],
    response_model=List[dict],
)
async def get_users(
        _user: UserInfo = Depends(Authentication()),
) -> List[dict]:
    if 'admin' not in _user['roles']:
        raise HTTPException(403, f"Not admin")
    return await get_profiles()


@router.get(
    '/users/{user_id}',
    tags=['Users'],
    response_model=dict,
)
async def get_user(
        user_id: str,
        _user: UserInfo = Depends(Authentication()),
) -> dict:
    return await get_profile(user_id)
