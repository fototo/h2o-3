import h2o
import math
from h2o.estimators import H2OXGBoostEstimator

class H2OTree():
    """
    Represents a model of a Tree built by one of H2O's algorithms (GBM, Random Forest).
    """

    def __init__(self, model, tree_number, tree_class=None):
        params = {"model": model.model_id,
                  "tree_number": tree_number,
                  "tree_class": tree_class}
        response = h2o.api(endpoint="GET /3/Tree", data=params)

        self._left_children = response['left_children']
        self._right_children = response['right_children']
        self._node_ids = self.__extract_internal_ids(response['root_node_id'])
        self._descriptions = response['descriptions']
        self._model_id = model.model_id
        self._tree_number = response['tree_number']
        self._tree_class = response['tree_class']
        self._thresholds = self.__convert_threshold_nans(response['thresholds'])
        self._features = response['features']
        self._levels = self.__decode_categoricals(model, response['levels'])
        self._nas = response['nas']
        self._predictions = response['predictions']
        self._root_node = self.__assemble_tree(0)

    @property
    def left_children(self):
        """An array with left child nodes of tree's nodes"""
        return self._left_children

    @property
    def right_children(self):
        """An array with right child nodes of tree's nodes"""
        return self._right_children

    @property
    def node_ids(self):
        """Array with identification numbers of nodes. Node IDs are generated by H2O."""
        return self._node_ids

    @property
    def descriptions(self):
        """Descriptions for each node to be found in the tree.
         Contains split threshold if the split is based on numerical column.
         For cactegorical splits, it contains list of categorical levels for transition from the parent node.
         """
        return self._descriptions

    @property
    def model_id(self):
        """
        Name (identification) of the model this tree is related to.
        """
        return self._model_id

    @property
    def tree_number(self):
        """The order in which the tree has been built in the model."""
        return self._tree_number

    @property
    def tree_class(self):
        """The name of a tree's class. Number of tree classes equals to the number of levels in
         categorical response column.

         As there is exactly one class per categorical level, name of tree's class equals to the corresponding
          categorical level of response column.

         In case of regression and binomial, the name of the categorical level is ignored can be omitted,
          as there is exactly one tree built in both cases.
          """
        return self._tree_class

    @property
    def thresholds(self):
        """Node split thresholds. Split thresholds are not only related to numerical splits, but might be present
         in case of categorical split as well."""
        return self._thresholds

    @property
    def features(self):
        """Names of the feature/column used for the split."""
        return self._features

    @property
    def levels(self):
        """Categorical levels on split from parent's node belonging into this node. None for root node or
         non-categorical splits."""
        return self._levels

    @property
    def nas(self):
        """representing if NA values go to the left node or right node. The value may be None if node is a leaf
        or there is no possibility of an NA value appearing on a node."""
        return self._nas

    @property
    def root_node(self):
        """An instance of H2ONode representing the beginning of the tree behind the model.
         Allows further tree traversal.
         """
        return self._root_node

    @property
    def predictions(self):
        """Values predicted on tree's nodes."""
        return self._predictions

    def __convert_threshold_nans(self, thresholds):
        for i in range(0, len(thresholds)):
            if thresholds[i] == "NaN": thresholds[i] = float('nan')
        return thresholds

    def __assemble_tree(self, node):
        if node == -1: return None

        left_child = self._left_children[node]
        right_child = self._right_children[node]

        if left_child == -1 and right_child == -1:
            return H2OLeafNode(node_id=self._node_ids[node],
                               prediction=self._predictions[node])
        else:
            return H2OSplitNode(node_id=self._node_ids[node],
                                left_child=self.__assemble_tree(left_child),
                                right_child=self.__assemble_tree(right_child),
                                threshold=self._thresholds[node],
                                split_feature=self._features[node],
                                na_direction=self._nas[node],
                                left_levels=self._levels[left_child],
                                right_levels = self._levels[right_child])

    def __decode_categoricals(self, model, levels):
        string_levels = len(self._left_children) * [None]

        if type(model) is H2OXGBoostEstimator:
            return string_levels

        for i in range(0, len(self._left_children)):
            if (self._features[i] is None): continue
            left_node = self._left_children[i]
            right_node = self._right_children[i]
            split_column_index = model._model_json["output"]["names"].index(self._features[i])
            domain = model._model_json["output"]["domains"][split_column_index]
            if domain is None: continue

            if left_node != -1:
                left_levels = []
                if levels[left_node] is not None:
                    for lvl_index in levels[left_node]:
                        left_levels.append(domain[lvl_index])

                string_levels[left_node] = left_levels

            if right_node != -1:
                right_levels = []
                if levels[right_node] is not None:
                    for lvl_index in levels[right_node]:
                        right_levels.append(domain[lvl_index])

                string_levels[right_node] = right_levels

        return string_levels

    def __extract_internal_ids(self, root_node_id):
        node_index = 0
        node_ids = [root_node_id]
        for i in range(0, len(self._left_children)):
            if (self._left_children[i] != -1):
                node_index = node_index + 1
                node_ids.append(self._left_children[i])
                self._left_children[i] = node_index
            else:
                self._left_children[i] = -1

            if (self._right_children[i] != -1):
                node_index = node_index + 1
                node_ids.append(self._right_children[i])
                self._right_children[i] = node_index
            else:
                self._right_children[i] = -1

        return node_ids

    def __len__(self):
        return len(self._node_ids)

    def __str__(self):
        return "Tree related to model {}. Tree number is {}, tree class is '{}'\n\n".format(self._model_id,
                                                                                            self._tree_number,
                                                                                            self._tree_class)

    def show(self):
        print(self.__str__())


class H2ONode():
    """
    Represents a single abstract node in an H2OTree
    """

    def __init__(self, node_id):
        self._id = node_id

    @property
    def id(self):
        """Node's unique identifier (integer). Generated by H2O."""
        return self._id

    def __str__(self):
        return "Node ID {} \n".format(self._id)


class H2OLeafNode(H2ONode):
    """
    Represents a single terminal node in an H2OTree with final prediction.
    """

    def __init__(self, node_id, prediction):
        H2ONode.__init__(self, node_id)
        self._prediction = prediction

    @property
    def id(self):
        """Node's unique identifier (integer). Generated by H2O."""
        return self._id

    @property
    def prediction(self):
        """Prediction value in the terminal node (numeric floating point)"""
        return self._prediction

    def __str__(self):
        return "Leaf node ID {}. Predicted value at leaf node is {} \n".format(self._id, self._prediction)

    def show(self):
        print(self.__str__())


class H2OSplitNode(H2ONode):
    """
    Represents a single node with either numerical or categorical split in an H2OTree with all its attributes.
    """

    def __init__(self, node_id, threshold, left_child, right_child, split_feature, na_direction, left_levels, right_levels):
        H2ONode.__init__(self, node_id)
        self._threshold = threshold
        self._left_child = left_child
        self._right_child = right_child
        self._split_feature = split_feature
        self._na_direction = na_direction
        self._left_levels = left_levels
        self._right_levels = right_levels

    @property
    def id(self):
        """Node's unique identifier (integer). Generated by H2O."""
        return self._id

    @property
    def threshold(self):
        """Split threshold, typically when the split column is numerical."""
        return self._threshold

    @property
    def left_child(self):
        """
        Integer identifier of the left child node, if there is any. Otherwise None.
        """
        return self._left_child

    @property
    def right_child(self):
        """Integer identifier of the right child node, if there is any. Otherwise None."""
        return self._right_child

    @property
    def split_feature(self):
        """The name of the column this node splits on."""
        return self._split_feature

    @property
    def na_direction(self):
        """The direction of NA values. LEFT means NA values go to the left child node, RIGH means NA values
         go to the right child node.

         A value of None means occurance of NA for the given split column is not possible on this node due to
         an earlier split on the very same feature.
         """
        return self._na_direction

    @property
    def left_levels(self):
        """Categorical levels on the edge from this node to the left child node.
         None for non-categorical splits."""
        return self._left_levels

    @property
    def right_levels(self):
        """Categorical levels on the edge from this node to the right child node.
         None for non-categorical splits."""
        return self._right_levels

    def __str__(self):
        out = "Node ID {} \n".format(self._id)
        if self._split_feature is not None:
            if self._left_child is not None:
                out += "Left child node ID = {}\n".format(self.left_child.id)
            else:
                out += "There is no left child\n"
            if self._right_child is not None:
                out += "Right child node ID = {}\n".format(self.right_child.id)
            else:
                out += "There is no right child\n"

            out += "\nSplits on column {}\n".format(self._split_feature)

        else:
            out += "This is a terminal node"

        if math.isnan(self._threshold):
            if self._left_child is not None:
                out += "  - Categorical levels going to the left node: {}\n".format(self._left_levels)
            if self._right_child is not None:
                out += "  - Categorical levels going to the right node: {}\n".format(self._right_levels)

        else:
            out += "Split threshold < {} to the left node, >= {} to the right node \n".format(self._threshold,
                                                                                              self._threshold)

        if self._na_direction is not None: out += "\nNA values go to the {}".format(self._na_direction)

        return out

    def show(self):
        print(self.__str__())
