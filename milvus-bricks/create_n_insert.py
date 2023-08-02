import time
import sys
import random
import sklearn.preprocessing
import numpy as np
import logging
from pymilvus import connections, DataType, \
    Collection, FieldSchema, CollectionSchema, utility
from common import insert_entities, get_vector_field_name


LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%m/%d/%Y %H:%M:%S %p"

id_field = FieldSchema(name="id", dtype=DataType.INT64, description="primary id")
age_field = FieldSchema(name="age", dtype=DataType.INT64, description="age")
groupid_field = FieldSchema(name="groupid", dtype=DataType.INT64, description="groupid")
device_field = FieldSchema(name="device", dtype=DataType.VARCHAR, max_length=500, description="device")
fname_field = FieldSchema(name="fname", dtype=DataType.VARCHAR, max_length=256, description="fname")
ext_field = FieldSchema(name="ext", dtype=DataType.VARCHAR, max_length=20, description="ext")
mtime_field = FieldSchema(name="mtime", dtype=DataType.INT64, description="mtime")
content_field = FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535, description="content")
flag_field = FieldSchema(name="flag", dtype=DataType.BOOL, description="flag")


def create_n_insert(collection_name, dim, nb, insert_times, index_type, metric_type="L2",
                    auto_id=True, ttl=0, build_index=True):
    if not utility.has_collection(collection_name=collection_name):
        embedding_field = FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim)
        schema = CollectionSchema(fields=[id_field, age_field, flag_field, embedding_field],
                                  auto_id=auto_id, primary_field=id_field.name,
                                  description=f"{collection_name}")    # do not change the description
        # schema = CollectionSchema(fields=[id_field, age_field, groupid_field, flag_field, device_field,
        #                                   fname_field, ext_field, mtime_field, content_field, embedding_field],
        #                           auto_id=auto_id, primary_field=id_field.name,
        #                           description=f"{collection_name}")  # do not change the description
        collection = Collection(name=collection_name, schema=schema, properties={"collection.ttl.seconds": ttl})
        logging.info(f"create {collection_name} successfully, auto_id: {auto_id}, dim: {dim}")
    else:
        collection = Collection(name=collection_name)
        logging.info(f"{collection_name} already exists")
    index_params_dict = {
        "HNSW": {"index_type": "HNSW", "metric_type": metric_type, "params": {"M": 30, "efConstruction": 360}},
        "DISKANN": {"index_type": "DISKANN", "metric_type": metric_type, "params": {}}
    }
    index_params = index_params_dict.get(index_type.upper(), None)
    if index_params is None:
        logging.error(f"index type {index_type} no supported")
        exit(1)

    # insert data
    insert_entities(collection=collection, nb=nb, rounds=insert_times)

    collection.flush()
    logging.info(f"collection entities: {collection.num_entities}")

    if build_index:
        if not collection.has_index():
            t0 = time.time()
            collection.create_index(field_name=get_vector_field_name(collection), index_params=index_params)
            tt = round(time.time() - t0, 3)
            logging.info(f"build index {index_params} costs {tt}")
        else:
            idx = collection.index()
            logging.info(f"index {idx.params} already exists")
    else:
        logging.info("skip build index")


if __name__ == '__main__':
    host = sys.argv[1]  # host address
    name = str(sys.argv[2])  # collection name
    dim = int(sys.argv[3])  # collection dimension
    nb = int(sys.argv[4])  # collection insert batch size
    insert_times = int(sys.argv[5])  # collection insert times
    index = str(sys.argv[6]).upper()    # index type
    metric = str(sys.argv[7]).upper()   # metric type, L2 or IP
    auto_id = str(sys.argv[8]).upper()     # auto id
    ttl = int(sys.argv[9])     # ttl for the collection property
    port = 19530
    log_name = f"prepare_{name}"

    auto_id = True if auto_id == "TRUE" else False
    file_handler = logging.FileHandler(filename=f"/tmp/{log_name}.log")
    stdout_handler = logging.StreamHandler(stream=sys.stdout)
    handlers = [file_handler, stdout_handler]
    logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT, datefmt=DATE_FORMAT, handlers=handlers)
    logger = logging.getLogger('LOGGER_NAME')

    logging.info("start")
    connections.add_connection(default={"host": host, "port": 19530})
    connections.connect('default')

    create_n_insert(collection_name=name, dim=dim, nb=nb, insert_times=insert_times,
                    index_type=index, metric_type=metric, auto_id=auto_id, ttl=ttl)

    # load the collection
    c = Collection(name=name)
    c.load()

    logging.info("collection prepared completed")

