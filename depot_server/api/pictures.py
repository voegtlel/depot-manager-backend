import gridfs
import hashlib
from authlib.oidc.core import UserInfo
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from starlette.responses import StreamingResponse
from typing import List, cast

from depot_server.db import collections
from .auth import Authentication

router = APIRouter()


@router.get(
    '/pictures',
    tags=['Pictures'],
    response_model=List[str],
)
async def get_pictures(
        _user: UserInfo = Depends(Authentication(require_manager=True)),
) -> List[str]:
    return [picture.id async for picture in collections.item_picture_collection.find({})]


@router.get(
    '/picture/{picture_id}',
    tags=['User Manager'],
)
async def get_picture(picture_id: str):
    """Get picture data."""
    try:
        stream = await collections.item_picture_collection.open_download_stream(picture_id)
    except gridfs.errors.NoFile:
        raise HTTPException(404)

    async def stream_iterator():
        while True:
            chunk = await stream.readchunk()
            if not chunk:
                break
            yield chunk
        stream.close()

    return StreamingResponse(
        stream_iterator(), media_type=stream.metadata['content_type'], headers={
            'cache-control': 'public,max-age=31536000,immutable'
        }
    )


@router.post(
    '/pictures',
    tags=['Picture'],
    response_model=str,
    status_code=201,
)
async def create_picture(
        file: UploadFile = File(..., media_type='application/octet-stream'),
        _user: UserInfo = Depends(Authentication(require_manager=True)),
) -> str:
    hash_ = hashlib.sha512()
    while True:
        chunk = await file.read(4 * 1024)
        if not chunk:
            break
        hash_.update(cast(bytes, chunk))
    await file.seek(0)
    picture_id = hash_.digest().hex()
    try:
        await collections.item_picture_collection.delete(picture_id)
    except gridfs.errors.NoFile:
        pass
    file.file.seek(0)
    await collections.item_picture_collection.upload_from_stream_with_id(
        picture_id, _user['sub'], file.file, metadata={'content_type': file.content_type}
    )
    return picture_id
