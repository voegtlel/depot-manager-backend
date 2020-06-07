import gridfs
import mongomock
import mongomock.gridfs
import motor.motor_asyncio
import pytest
from _pytest.monkeypatch import MonkeyPatch
from motor.metaprogramming import AsyncCommand, AsyncRead, DelegateMethod, ReadOnlyProperty, \
    AsyncWrite, MotorCursorChainingMethod


mongomock.gridfs.enable_gridfs_integration()


class AgnosticBase(motor.motor_asyncio.core.AgnosticBase):
    io_loop = None

    def __init__(self, *args, **kwargs):
        self._extract_io_loop(kwargs)
        super(AgnosticBase, self).__init__(*args, **kwargs)

    def _extract_io_loop(self, kwargs):
        if self.io_loop is None:
            if 'io_loop' in kwargs:
                io_loop = kwargs.pop('io_loop')
                self._framework.check_event_loop(io_loop)
            else:
                io_loop = self._framework.get_event_loop()
            self.io_loop = io_loop

    def get_io_loop(self):
        return self.io_loop

    def wrap(self, value):
        if isinstance(value, mongomock.Database):
            return AsyncIOMotorDatabase(value)
        elif isinstance(value, mongomock.Collection):
            return AsyncIOMotorCollection(value)
        elif isinstance(value, mongomock.collection.Cursor):
            return AsyncIOMotorCursor(value)
        elif isinstance(value, gridfs.GridFSBucket):
            return AsyncIOMotorGridFSBucket(value)
        elif isinstance(value, gridfs.GridIn):
            return AsyncIOMotorGridIn(value)
        elif isinstance(value, gridfs.GridOut):
            return AsyncIOMotorGridOut(value)
        elif isinstance(value, gridfs.GridOutCursor):
            return AsyncIOMotorGridOutCursor(value)
        return value


class AgnosticClient(AgnosticBase):
    __motor_class_name__ = 'MotorClient'
    __delegate_class__ = mongomock.MongoClient

    def __init__(self, *args, **kwargs):
        self._extract_io_loop(kwargs)
        super(AgnosticBase, self).__init__(mongomock.MongoClient(*args, **kwargs))

    close = DelegateMethod()
    drop_database = AsyncCommand().unwrap('MotorDatabase')
    get_database = DelegateMethod().wrap(mongomock.Database)
    get_default_database = DelegateMethod().wrap(mongomock.Database)
    list_database_names = AsyncRead()
    server_info = AsyncRead()


class AgnosticDatabase(AgnosticBase):
    __motor_class_name__ = 'MotorDatabase'
    __delegate_class__ = mongomock.Database

    command = AsyncCommand()
    create_collection = AsyncCommand().wrap(mongomock.Collection)
    dereference = AsyncRead()
    drop_collection = AsyncCommand().unwrap('MotorCollection')
    get_collection = DelegateMethod().wrap(mongomock.Collection)
    list_collection_names = AsyncRead()
    with_options = DelegateMethod().wrap(mongomock.Database)

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(
                "%s has no attribute %r. To access the %s"
                " collection, use database['%s']." % (
                    self.__class__.__name__, name, name, name))

        return self[name]

    def __getitem__(self, name):
        return self.wrap(self.delegate[name])


class AgnosticCollection(AgnosticBase):
    __motor_class_name__ = 'MotorCollection'
    __delegate_class__ = mongomock.Collection

    bulk_write = AsyncCommand()
    count_documents = AsyncRead()
    create_index = AsyncCommand()
    create_indexes = AsyncCommand()
    delete_many = AsyncCommand()
    delete_one = AsyncCommand()
    distinct = AsyncRead()
    drop = AsyncCommand()
    drop_index = AsyncCommand()
    drop_indexes = AsyncCommand()
    estimated_document_count = AsyncCommand()
    find_one = AsyncRead()
    find_one_and_delete = AsyncCommand()
    find_one_and_replace = AsyncCommand()
    find_one_and_update = AsyncCommand()
    full_name = ReadOnlyProperty()
    insert_many = AsyncWrite()
    insert_one = AsyncCommand()
    map_reduce = AsyncCommand().wrap(mongomock.Collection)
    name = ReadOnlyProperty()
    reindex = AsyncCommand()
    rename = AsyncCommand()
    replace_one = AsyncCommand()
    update_many = AsyncCommand()
    update_one = AsyncCommand()
    with_options = DelegateMethod().wrap(mongomock.Collection)

    def find(self, *args, **kwargs):
        return AsyncIOMotorCursor(self.delegate.find(*args, **kwargs))


class AgnosticCursorBase(AgnosticBase):

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self.delegate)
        except StopIteration:
            raise StopAsyncIteration()


class AgnosticCursor(AgnosticCursorBase):
    __delegate_class__ = mongomock.collection.Cursor
    __motor_class_name__ = 'MotorCursor'

    alive = ReadOnlyProperty()
    distinct = AsyncRead()
    limit = MotorCursorChainingMethod()
    skip = MotorCursorChainingMethod()
    sort = MotorCursorChainingMethod()
    hint = MotorCursorChainingMethod()
    max_time_ms = MotorCursorChainingMethod()


class AgnosticGridOutCursor(AgnosticCursorBase):
    __delegate_class__ = gridfs.grid_file.GridOutCursor
    __motor_class_name__ = 'MotorGridOutCursor'

    distinct = AsyncRead()
    limit = MotorCursorChainingMethod()
    skip = MotorCursorChainingMethod()
    sort = MotorCursorChainingMethod()
    hint = MotorCursorChainingMethod()
    max_time_ms = MotorCursorChainingMethod()


class AgnosticGridOut(AgnosticBase):
    __delegate_class__ = gridfs.GridOut
    __motor_class_name__ = 'MotorGridOut'

    chunk_size = ReadOnlyProperty()
    close = ReadOnlyProperty()
    content_type = ReadOnlyProperty()
    filename = ReadOnlyProperty()
    length = ReadOnlyProperty()
    md5 = ReadOnlyProperty()
    metadata = ReadOnlyProperty()
    name = ReadOnlyProperty()
    read = AsyncRead()
    readable = DelegateMethod()
    readchunk = AsyncRead()
    readline = AsyncRead()
    seek = DelegateMethod()
    seekable = DelegateMethod()
    tell = DelegateMethod()
    upload_date = ReadOnlyProperty()
    write = DelegateMethod()

    def __aiter__(self):
        return self

    async def __anext__(self):
        return next(self.delegate)

    def __getattr__(self, item):
        return getattr(self.delegate, item)


class AgnosticGridIn(AgnosticBase):
    __delegate_class__ = gridfs.GridIn
    __motor_class_name__ = 'MotorGridIn'

    abort = AsyncCommand()
    chunk_size = ReadOnlyProperty()
    closed = ReadOnlyProperty()
    close = AsyncCommand()
    content_type = ReadOnlyProperty()
    filename = ReadOnlyProperty()
    length = ReadOnlyProperty()
    md5 = ReadOnlyProperty()
    name = ReadOnlyProperty()
    read = DelegateMethod()
    readable = DelegateMethod()
    seekable = DelegateMethod()
    upload_date = ReadOnlyProperty()
    write = AsyncCommand().unwrap('MotorGridOut')
    writeable = DelegateMethod()
    writelines = AsyncCommand().unwrap('MotorGridOut')

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.delegate.close()

    def __getattr__(self, item):
        return getattr(self.delegate, item)

    def __setattr__(self, item, value):
        return getattr(self.delegate, item, value)


class AgnosticGridFSBucket(AgnosticBase):
    __delegate_class__ = gridfs.GridFSBucket
    __motor_class_name__ = 'MotorGridFSBucket'

    delete = AsyncCommand()
    download_to_stream = AsyncCommand()
    download_to_stream_by_name = AsyncCommand()
    open_download_stream = AsyncCommand().wrap(gridfs.GridOut)
    open_download_stream_by_name = AsyncCommand().wrap(gridfs.GridOut)
    open_upload_stream = DelegateMethod().wrap(gridfs.GridIn)
    open_upload_stream_with_id = DelegateMethod().wrap(gridfs.GridIn)
    rename = AsyncCommand()
    upload_from_stream = AsyncCommand()
    upload_from_stream_with_id = AsyncCommand()

    def __init__(self, db, *args, **kwargs):
        self._extract_io_loop(kwargs)
        super(AgnosticBase, self).__init__(gridfs.GridFSBucket(db.delegate, *args, **kwargs))


AsyncIOMotorClient = motor.motor_asyncio.create_asyncio_class(AgnosticClient)
AsyncIOMotorDatabase = motor.motor_asyncio.create_asyncio_class(AgnosticDatabase)
AsyncIOMotorCollection = motor.motor_asyncio.create_asyncio_class(AgnosticCollection)
AsyncIOMotorCursor = motor.motor_asyncio.create_asyncio_class(AgnosticCursor)
AsyncIOMotorGridFSBucket = motor.motor_asyncio.create_asyncio_class(AgnosticGridFSBucket)
AsyncIOMotorGridIn = motor.motor_asyncio.create_asyncio_class(AgnosticGridIn)
AsyncIOMotorGridOut = motor.motor_asyncio.create_asyncio_class(AgnosticGridOut)
AsyncIOMotorGridOutCursor = motor.motor_asyncio.create_asyncio_class(AgnosticGridOutCursor)


@pytest.fixture()
def motor_mock():
    mp = MonkeyPatch()
    import motor.motor_asyncio
    mp.setattr(motor.motor_asyncio, 'AsyncIOMotorClient', AsyncIOMotorClient)
    mp.setattr(motor.motor_asyncio, 'AsyncIOMotorDatabase', AsyncIOMotorDatabase)
    mp.setattr(motor.motor_asyncio, 'AsyncIOMotorCollection', AsyncIOMotorCollection)
    mp.setattr(motor.motor_asyncio, 'AsyncIOMotorCursor', AsyncIOMotorCursor)

    mp.setattr(motor.motor_asyncio, 'AsyncIOMotorGridFSBucket', AsyncIOMotorGridFSBucket)
    mp.setattr(motor.motor_asyncio, 'AsyncIOMotorGridIn', AsyncIOMotorGridIn)
    mp.setattr(motor.motor_asyncio, 'AsyncIOMotorGridOut', AsyncIOMotorGridOut)
    mp.setattr(motor.motor_asyncio, 'AsyncIOMotorGridOutCursor', AsyncIOMotorGridOutCursor)

    yield
    mp.undo()
