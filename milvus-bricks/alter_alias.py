import sys
import os
import logging
from pymilvus import utility, connections, \
    Collection
import create_n_insert
import pymilvus.exceptions

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%m/%d/%Y %H:%M:%S %p"


if __name__ == '__main__':
    host = sys.argv[1]
    c_name = sys.argv[2]                            # collection name is <c_name>_aa or <c_name>_bb
    index_type = str(sys.argv[3]).upper()           # index type is hnsw or diskann
    metric_type = str(sys.argv[4]).upper()          # metric type is L2 or IP
    need_insert = str(sys.argv[5]).upper()          # need insert data or not

    alias_name = f"{c_name}_alias"                  # alias mame
    port = 19530
    conn = connections.connect('default', host=host, port=port)

    file_handler = logging.FileHandler(filename=f"/tmp/alter_alias_{alias_name}.log")
    stdout_handler = logging.StreamHandler(stream=sys.stdout)
    handlers = [file_handler, stdout_handler]
    logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT, datefmt=DATE_FORMAT, handlers=handlers)
    logger = logging.getLogger('LOGGER_NAME')

    dim = 768
    nb = 2000
    need_insert = True if need_insert == "TRUE" else False
    insert_times = 500 if need_insert else 0
    # check and get the collection info
    if not utility.has_collection(collection_name=f'{c_name}_aa'):
        logging.info(f"creating collection {c_name}_aa")
        create_n_insert.create_n_insert(collection_name=f'{c_name}_aa',
                                        dim=dim, nb=nb, insert_times=insert_times,
                                        index_type=index_type, metric_type=metric_type)
    if not utility.has_collection(collection_name=f'{c_name}_bb'):
        logging.info(f"creating collection {c_name}_bb")
        create_n_insert.create_n_insert(collection_name=f'{c_name}_bb',
                                        dim=dim, nb=nb, insert_times=insert_times,
                                        index_type=index_type, metric_type=metric_type)

    # alter alias
    try:
        aliases = utility.list_aliases(collection_name=alias_name)
        if alias_name in aliases:
            collection = Collection(alias_name)
            description = collection.description
            logging.info(f"collection alias before altered: {description}")
            collection_name = f"{c_name}_bb" if description == f"{c_name}_aa" else f"{c_name}_aa"
            utility.alter_alias(collection_name=collection_name, alias=alias_name)
        else:
            collection_name = f"{c_name}_aa"
            utility.create_alias(collection_name=collection_name, alias=alias_name)
    except pymilvus.exceptions.DescribeCollectionException as e:
        collection_name = f"{c_name}_aa"
        utility.create_alias(collection_name=collection_name, alias=alias_name)
    collection = Collection(alias_name)
    logging.info(f"collection alias after altered: {collection.description}")

    logging.info(f"alter alias completed")
