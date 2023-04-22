from authlib.oidc.core import UserInfo
from fastapi import APIRouter, Depends, HTTPException
from typing import List

from depot_server.helper.auth import Authentication, get_profiles, get_profile
from depot_server.model import User

router = APIRouter()


@router.get(
    '/users',
    tags=['Users'],
    response_model=List[User],
)
async def get_users(
        _user: UserInfo = Depends(Authentication()),
) -> List[User]:
    if 'admin' not in _user['roles']:
        raise HTTPException(403, "Not admin")
    return [
        User.validate(profile)
        for profile in await get_profiles()
        if profile.get('email') and profile.get('name')
    ]


@router.get(
    '/users/{user_id}',
    tags=['Users'],
    response_model=User,
)
async def get_user(
        user_id: str,
        _user: UserInfo = Depends(Authentication()),
) -> User:
    return User.validate(await get_profile(user_id))
