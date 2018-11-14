# coding=utf-8
from scipy.sparse import csr_matrix
import numpy as np
import random
from multiprocessing.dummy import Pool as ThreadPool

# N_TYPE denotes node type
N_TYPE_NODE = "N_NODE"
N_TYPE_LABEL = "N_LABEL"


def dict_get_or_create_value(dict_object, key, default_value):
    if key in dict_object:
        return dict_object[key]
    else:
        dict_object[key] = default_value
        return default_value


# Heterogeneous Network
# edges are based on meta-paths
class MetaNetwork(object):

    # read data from data_dir
    # if ignore_featureless_node is True, nodes without content or features will be ignored
    def __init__(self):
        # node_type:str => node_id:str => node_index:int
        self.node_type_id_index_dict = {}
        # node_type:str => node_index:int => node_id:str
        self.node_type_index_id_dict = {}
        # node_type:str => node_index:int => node_attrdict: dict
        self.node_type_index_attrdict_dict = {}
        # node_type0:str => node_type1:str => node_index:int => neighbor_node_indices:list
        self.meta_neighbors_dict = {}
        # key0: node_type0 => key1: node_type1 => key2: node_index0 => key3 => node_index1 => value: weight
        self.meta_adj_dict = {}

    def get_or_create_adj_dict(self, node_type0, node_type1):
        sub_meta_adj_dict = dict_get_or_create_value(self.meta_adj_dict, node_type0, {})
        adj_dict = dict_get_or_create_value(sub_meta_adj_dict, node_type1, {})
        return adj_dict

    def get_adj_dict(self, node_type0, node_type1):
        return self.meta_adj_dict[node_type0][node_type1]

    # neighbor_weight_dict
    def get_weight_dict(self, node_type0, node_type1, node_index):
        return self.get_adj_dict(node_type0, node_type1)[node_index]

    def get_or_create_neighbors_dict(self, node_type0, node_type1):
        sub_meta_neighbors_dict = dict_get_or_create_value(self.meta_neighbors_dict, node_type0, {})
        neighbors_dict = dict_get_or_create_value(sub_meta_neighbors_dict, node_type1, {})
        return neighbors_dict

    def get_or_create_neighbors(self, node_type0, node_type1, node_index):
        neighbors_dict = self.get_or_create_neighbors_dict(node_type0, node_type1)
        neighbors = dict_get_or_create_value(neighbors_dict, node_index, [])
        return neighbors

    def get_neighbors(self, node_type0, node_type1, node_index):
        return self.meta_neighbors_dict[node_type0][node_type1][node_index]

    def get_or_create_node_id_index_dict(self, node_type):
        return dict_get_or_create_value(self.node_type_id_index_dict, node_type, {})

    def get_or_create_node_index_id_dict(self, node_type):
        return dict_get_or_create_value(self.node_type_index_id_dict, node_type, {})

    def get_node_id_index_dict(self, node_type):
        return self.node_type_id_index_dict[node_type]

    def get_node_index_id_dict(self, node_type):
        return self.node_type_index_id_dict[node_type]

    def get_or_create_node_attrdict(self, node_type, node_index):
        node_index_attrdict = dict_get_or_create_value(self.node_type_index_attrdict_dict, node_type, {})
        attrdict = dict_get_or_create_value(node_index_attrdict, node_index, {})
        return attrdict

    def get_or_create_node_attr(self, node_type, node_index, attr_name, attr_value):
        attr_dict = self.get_or_create_node_attrdict(node_type, node_index)
        if attr_name in attr_dict:
            return attr_dict[attr_name]
        else:
            attr_dict[attr_name] = attr_value
            return attr_value

    def get_node_attrdict(self, node_type, node_index):
        return self.node_type_index_attrdict_dict[node_type][node_index]

    def get_node_attr(self, node_type, node_index, attr_name):
        return self.get_node_attrdict(node_type, node_index)[attr_name]

    def get_node_attrs(self, node_type, node_indices, attr_name):
        return [self.get_node_attr(node_type, node_index, attr_name) for node_index in node_indices]

    def set_node_attr(self, node_type, node_index, attr_name, attr_value):
        attrdict = self.get_or_create_node_attrdict(node_type, node_index)
        attrdict[attr_name] = attr_value

    # add_edge by node indices and node types
    def add_edge(self, node_type0, node_type1, node_index0, node_index1, weight=1.0):
        adj_dict = self.get_or_create_adj_dict(node_type0, node_type1)
        weight_dict = dict_get_or_create_value(adj_dict, node_index0, {})
        weight_dict[node_index1] = weight

        neighbors = self.get_or_create_neighbors(node_type0, node_type1, node_index0)
        if node_index1 not in neighbors:
            neighbors.append(node_index1)

    def add_edges(self, node_type0, node_type1, node_index0, node_index1, weight=1.0):
        self.add_edge(node_type0, node_type1, node_index0, node_index1, weight=weight)
        self.add_edge(node_type1, node_type0, node_index1, node_index0, weight=weight)

    # get node_index if node_id exists
    # otherwise create node_index for node_id
    def get_or_create_node_index(self, node_type, node_id):
        node_id_index_dict = self.get_or_create_node_id_index_dict(node_type)
        if node_id in node_id_index_dict:
            return node_id_index_dict[node_id]
        else:
            node_index = self.num_nodes(node_type)
            node_id_index_dict[node_id] = node_index
            node_index_id_dict = self.get_or_create_node_index_id_dict(node_type)
            node_index_id_dict[node_index] = node_id
            return node_index

    # will raise exception when node_id does not exist
    def get_node_index(self, node_type, node_id):
        node_id_index_dict = self.get_node_id_index_dict(node_type)
        return node_id_index_dict[node_id]

    def get_node_indices(self, node_type, node_ids):
        return [self.get_node_index(node_id) for node_id in node_ids]

    def get_node_id(self, node_type, node_index):
        node_index_id_dict = self.get_node_index_id_dict(node_type)
        return node_index_id_dict[node_index]

    def get_node_ids(self, node_type, node_indices):
        return [self.get_node_id(node_type, node_index) for node_index in node_indices]

    def has_node_id(self, node_type, node_id):
        node_id_index_dict = self.get_node_id_index_dict(node_type)
        return node_id in node_id_index_dict

    def num_nodes(self, node_type):
        return len(self.node_type_id_index_dict[node_type])

    # if sparse, return a csr_matrix
    def adj_matrix(self, node_type0, node_type1, sparse=False):
        data = []
        row = []
        col = []
        adj_dict = self.get_adj_dict(node_type0, node_type1)
        for node_index0 in adj_dict:
            weight_dict = adj_dict[node_index0]
            for node_index1 in weight_dict:
                data.append(weight_dict[node_index1])
                row.append(node_index0)
                col.append(node_index1)
        adj = csr_matrix((data, (row, col)), shape=(self.num_nodes(node_type0), self.num_nodes(node_type1)))
        if sparse:
            return adj
        else:
            return adj.todense()
            # if sparse:
            #     adj = csr_matrix((self.num_nodes(), self.num_nodes()), dtype=np.float32)
            # else:
            #     adj = np.zeros((self.num_nodes(), self.num_nodes()), dtype=np.float32)
            #
            # for node_index0 in self.adj_dict:
            #     weight_dict = self.adj_dict[node_index0]
            #     for node_index1 in weight_dict:
            #         adj[node_index0, node_index1] = weight_dict[node_index1]
            # return adj

    def split_train_and_test(self, node_type, training_rate):
        num_nodes = self.num_nodes(node_type)
        random_node_indices = np.random.permutation(num_nodes)
        training_size = int(num_nodes * training_rate)
        train_node_indices = random_node_indices[:training_size]
        test_node_indices = random_node_indices[training_size:]
        train_masks = np.zeros_like(random_node_indices, dtype=np.int32)
        train_masks[train_node_indices] = 1
        test_masks = np.zeros_like(random_node_indices, dtype=np.int32)
        test_masks[test_node_indices] = 1
        return train_node_indices, test_node_indices, train_masks, test_masks

    def random_node_index(self, node_type, excluded_node_indices=None):
        while True:
            random_node_index = random.randint(0, self.num_nodes(node_type) - 1)
            if excluded_node_indices is not None and random_node_index in excluded_node_indices:
                continue
            return random_node_index

    def random_neighbor_node_index(self, node_type0, node_type1, node_index):
        neighbors = self.get_or_create_neighbors(node_type0, node_type1, node_index)
        if len(neighbors) == 0:
            return None
        i = random.randint(0, len(neighbors) - 1)
        return neighbors[i]

    def random_walk(self, node_types, start_node_index=None, padding=True):
        if start_node_index is None:
            start_node_index = self.random_node_index(node_types[0])
        path = [start_node_index]
        for i, node_type in enumerate(node_types[:-1]):
            node_type0 = node_types[i]
            node_type1 = node_types[i+1]
            node_index0 = path[-1]
            node_index1 = self.random_neighbor_node_index(node_type0, node_type1, node_index0)
            if node_index1 is None:
                break
            path.append(node_index1)

        while len(path) < len(node_types):
            node_type = node_types[len(path)]
            random_node_index = self.random_node_index(node_type, excluded_node_indices=path)
            path.append(random_node_index)
        return path

    def multi_random_walk(self, node_types, start_node_indices=None, num_paths=None, num_threads=None):
        if (start_node_indices is None) == (num_paths is None):
            print("please specify either 'start_node_indices' or 'num_paths'")
        if start_node_indices is None:
            start_node_indices = [None] * num_paths
        if num_threads is None:
            num_paths = num_paths

        def random_walk_func(start_node_index):
            return self.random_walk(node_types, start_node_index)

        pool = ThreadPool(4)
        paths = pool.map(random_walk_func, start_node_indices)

        return paths