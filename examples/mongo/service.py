import logging
from asyncio_mongo._bson import ObjectId
from wolverine.module.service import MicroService

logger = logging.getLogger(__name__)


class MongoService(MicroService):

    def __init__(self, app):
        super(MongoService, self).__init__(app, 'mongo-demo')
        self.version = 2

    def read(self, data):

        obj_id = data.get('id')
        db_name = data.get('db')
        db = getattr(self.app.mongo, db_name)
        col_name = data.get('collection')
        if db:
            collection = getattr(db, col_name)
            if obj_id and collection:
                doc = yield from collection.find_one({'_id': ObjectId(obj_id)})
                logger.debug('doc: ' + str(doc))
                return fix_id(doc)
        return None


def fix_id(doc):
    """
    Replaces the _id value with id
    @:param document: mongo document with an object id
    """
    if doc is not None and '_id' in doc:
        doc['id'] = str(doc['_id'])
        del doc['_id']
    return doc
