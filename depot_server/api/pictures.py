from io import BytesIO

import gridfs
import hashlib
from authlib.oidc.core import UserInfo
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Header, Response
from starlette.responses import StreamingResponse
from typing import List, cast, Tuple

from PIL import Image


from depot_server.db import collections
from depot_server.helper.auth import Authentication
from depot_server.model import Picture

router = APIRouter()


@router.get(
    '/pictures',
    tags=['Pictures'],
    response_model=List[Picture],
)
async def get_pictures(
        _user: UserInfo = Depends(Authentication(require_manager=True)),
) -> List[Picture]:
    return [
        Picture(
            id=picture._id,
            size=picture.length,
            original_name=picture.filename,
            mime_type=picture.metadata['contentType'],
            upload_timestamp=picture.upload_date
        )
        async for picture in collections.item_picture_collection().find()
    ]


async def _async_get_picture(
        picture_id: str,
        if_none_match: str = Header(None),
        if_match: str = Header(None),
) -> Tuple[gridfs.GridOut, dict]:
    try:
        if picture_id.endswith('/preview'):
            stream = await collections.item_picture_thumbnail_collection().open_download_stream(picture_id)
        else:
            stream = await collections.item_picture_collection().open_download_stream(picture_id)
    except gridfs.errors.NoFile:
        raise HTTPException(404)
    file_hash = stream.metadata['hash'].hex()
    if if_none_match is not None and file_hash in [m.strip() for m in if_none_match.split(',')]:
        stream.close()
        raise HTTPException(304)
    if if_match is not None and file_hash not in [m.strip() for m in if_match.split(',')]:
        stream.close()
        raise HTTPException(304)
    return stream, {'ETag': file_hash, 'cache-control': 'public,max-age=31536000,immutable'}


@router.head(
    '/pictures/{picture_id}',
    include_in_schema=False,
)
async def get_picture_meta(
        picture_id: str,
        if_none_match: str = Header(None),
        if_match: str = Header(None),
):
    """Get picture metadata."""
    try:
        stream, headers = await _async_get_picture(picture_id, if_none_match, if_match)
        stream.close()
    except HTTPException as e:
        return Response(status_code=e.status_code)
    return Response(status_code=200, headers=headers)


@router.get(
    '/pictures/{picture_id:path}',
    responses={
        200: {
            "content": {"image/*": {}},
            "description": "The picture",
        },
    },
)
async def get_picture(
        picture_id: str,
        if_none_match: str = Header(None),
        if_match: str = Header(None),
):
    """Get picture data."""
    try:
        stream, headers = await _async_get_picture(picture_id, if_none_match, if_match)
    except HTTPException as e:
        return Response(status_code=e.status_code)

    async def stream_iterator():
        while True:
            chunk = await stream.readchunk()
            if not chunk:
                break
            yield chunk
        stream.close()

    return StreamingResponse(
        stream_iterator(), media_type=stream.metadata['contentType'], headers=headers
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
    hashval = hash_.digest()
    picture_id = hashval.hex()
    try:
        await collections.item_picture_collection().delete(picture_id)
        await collections.item_picture_thumbnail_collection().delete(picture_id + '/preview')
    except gridfs.errors.NoFile:
        pass
    file.file.seek(0)

    img: Image.Image = Image.open(file.file)
    img.thumbnail((250, 250), Image.BOX)
    thumb_f = BytesIO()
    img.save(thumb_f, format="JPEG", quality=85)
    thumb_f.seek(0)

    file.file.seek(0)

    await collections.item_picture_collection().upload_from_stream_with_id(
        picture_id, file.filename, file.file, metadata={'contentType': file.content_type, 'hash': hashval}
    )
    await collections.item_picture_thumbnail_collection().upload_from_stream_with_id(
        picture_id + '/preview', file.filename, thumb_f, metadata={'contentType': 'image/jpeg', 'hash': hashval}
    )
    return picture_id
