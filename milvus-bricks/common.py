import time
import sys
import string
import random
import logging
import numpy as np
from pymilvus import utility, connections, DataType, \
    Collection, FieldSchema, CollectionSchema


def get_dim(collection):
    fields = collection.schema.fields
    for field in fields:
        if field.dtype == DataType.FLOAT_VECTOR:
            dim = field.params.get("dim")
    return dim


def get_vector_field_name(collection):
    fields = collection.schema.fields
    for field in fields:
        if field.dtype == DataType.FLOAT_VECTOR:
            vector_field_name = field.name
    return vector_field_name


def delete_entities(collection, nb, search_params, rounds):
    dim = get_dim(collection=collection)
    auto_id = collection.schema.auto_id
    primary_field_name = collection.primary_field.name
    vector_field_name = get_vector_field_name(collection=collection)
    if auto_id:
        for r in range(rounds):
            search_vector = [[random.random() for _ in range(dim)] for _ in range(1)]
            results = collection.search(data=search_vector, anns_field=vector_field_name,
                                        param=search_params, limit=nb)
            for hits in results:
                ids = hits.ids
                collection.delete(expr=f"{primary_field_name} in {ids}")
                logging.info(f"deleted {len(ids)} entities")
    else:
        for r in range(rounds):
            start_uid = r * nb
            end_uid = start_uid + nb
            collection.delete(expr=f"{primary_field_name} in [{start_uid}, {end_uid}]")
            logging.info(f"deleted entities {start_uid}-{end_uid}")


def gen_data_by_collection(collection, nb, r):
    data = []
    start_uid = r * nb
    fields = collection.schema.fields
    auto_id = collection.schema.auto_id
    for field in fields:
        field_values = []
        if field.dtype == DataType.FLOAT_VECTOR:
            dim = field.params.get("dim")
            field_values = [[random.random() for _ in range(dim)] for _ in range(nb)]
        if field.dtype in [DataType.INT64, DataType.INT32, DataType.INT16, DataType.INT8]:
            if field.is_primary:
                if not auto_id:
                    field_values = [_ for _ in range(start_uid, start_uid + nb)]
                else:
                    continue
            else:
                field_values = [_ for _ in range(start_uid, start_uid + nb)]
        if field.dtype == DataType.VARCHAR:
            max_length = field.params.get("max_length")
            field_values = [gen_str_by_length(max_length//10) for _ in range(nb)]
        if field.dtype == DataType.FLOAT:
            field_values = [random.random() for _ in range(nb)]
        if field.dtype == DataType.BOOL:
            field_values = [False for _ in range(nb)]
        data.append(field_values)
    return data


def gen_upsert_data_by_intPK_collection(collection, nb):
    data = []
    fields = collection.schema.fields
    auto_id = collection.schema.auto_id
    num = collection.num_entities
    for field in fields:
        field_values = []
        if field.dtype == DataType.FLOAT_VECTOR:
            dim = field.params.get("dim")
            field_values = [[random.random() for _ in range(dim)] for _ in range(nb)]
        if field.dtype in [DataType.INT64, DataType.INT32, DataType.INT16, DataType.INT8]:
            if field.is_primary:
                if not auto_id:
                    field_values = [random.randint(0, num) for _ in range(nb)]
                else:
                    continue
            else:
                field_values = [_ for _ in range(nb)]
        if field.dtype == DataType.VARCHAR:
            max_length = field.params.get("max_length")
            field_values = [gen_str_by_length(max_length // 10) for _ in range(nb)]
        if field.dtype == DataType.FLOAT:
            field_values = [random.random() for _ in range(nb)]
        if field.dtype == DataType.BOOL:
            field_values = [True for _ in range(nb)]        # update to true in upsert
        data.append(field_values)
    return data


def insert_entities(collection, nb, rounds):
    for r in range(rounds):
        data = gen_data_by_collection(collection=collection, nb=nb, r=r)
        t1 = time.time()
        collection.insert(data)
        t2 = round(time.time() - t1, 3)
        logging.info(f"{collection.name} insert {r} costs {t2}")


def upsert_entities(collection, nb, rounds):
    for r in range(rounds):
        data = gen_upsert_data_by_intPK_collection(collection=collection, nb=nb)
        t1 = time.time()
        collection.upsert(data)
        t2 = round(time.time() - t1, 3)
        logging.info(f"{collection.name} upsert2 {r} costs {t2}")


def get_search_params(collection, topk):
    idx = collection.index()
    metric_type = idx.params.get("metric_type")
    index_type = idx.params.get("index_type")
    if index_type == "HNSW":
        ef = max(64, topk)
        search_params = {"metric_type": metric_type, "params": {"ef": ef}}
    elif index_type in ["IVF_SQ8", "IVF_FLAT"]:
        search_params = {"metric_type": metric_type, "params": {"nprobe": 32}}
    elif index_type == "DISKANN":
        search_params = {"metric_type": metric_type, "params": {"search_list": 100}}
    else:
        logging.error(f"index: {index_type} does not support yet")
        exit(0)
    return search_params


def get_index_params(collection):
    idx = collection.index()
    return idx.params


def gen_str_by_length(length=8, letters_only=False):
    if letters_only:
        return "".join(random.choice(string.ascii_letters) for _ in range(length))
    return "".join(random.choice(string.ascii_letters + string.digits) for _ in range(length))

