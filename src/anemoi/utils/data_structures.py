# (C) Copyright 2024 European Centre for Medium-Range Weather Forecasts.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from abc import abstractmethod
from collections import defaultdict
import logging
from functools import cached_property
import numpy as np


LOG = logging.getLogger(__name__)


def flatten_name_to_index(dic):
    new = dict()
    for k, subdict in dic.items():
        for name, v in subdict.items():
            new[name] = (k, v)
    return new


def unflatten_name_to_index(dic):
    new = defaultdict(dict)
    for k, (name, v) in dic.items():
        new[name][k] = v
    return new


def str_(t):
    """Not needed, but useful for debugging"""
    import numpy as np

    if isinstance(t, (list, tuple)):
        return "[" + " , ".join(str_(e) for e in t) + "]"
    if isinstance(t, np.ndarray):
        return "🔢" + str(t.shape).replace(" ", "").replace(",", "-").replace("(", "").replace(")", "")
    if isinstance(t, dict):
        return "{" + " , ".join(f"{k}: {str_(v)}" for k, v in t.items()) + "}"
    try:
        from torch import Tensor

        if isinstance(t, Tensor):
            return "🔥" + str(tuple(t.size())).replace(" ", "").replace(",", "-").replace("(", "").replace(")", "")
    except ImportError:
        pass
    return str(t)


class States:
    _len = None
    _dtype = None

    def __init__(self, name_to_index=None):
        self.name_to_index = name_to_index

    def __len__(self):
        if self._len is None:
            self._len = len(self.states)
        return self._len

    def __iter__(self):
        return iter(self.states)

    def __str__(self):
        return f"{self.__class__.__name__}({len(self)} states)"

    @property
    def states(self):
        raise NotImplementedError

    @property
    def dtype(self):
        assert self._dtype  # this should be set by the subclass
        return self._dtype

    def clone(self):
        raise NotImplementedError


#######################################
# this may move to anemoi-training ?
class TrainingSample(States):
    # subclasses should implement some class method for construction
    # and some methods specific to training samples.

    @abstractmethod
    def to(self, device):
        raise NotImplementedError


class SimpleTrainingSample(TrainingSample):
    # the states are all regular and can be stacked
    # appropriate for Deterministic models
    def __init__(self, array, **kwargs):
        super().__init__(**kwargs)
        print("❗❗❗❗This is for illustration purposes. SimpleTrainingSample has not been tested.")
        self._len = array.shape[0]
        self._array = array

    @classmethod
    def from_numpy_array(cls, array):
        return cls(array)

    @classmethod
    def from_list_of_numpy_arrays(cls, list_of_arrays):
        return cls(np.stack(list_of_arrays))

    def __iter__(self):
        for i in range(self._len):
            yield self._array[i]

    @property
    def states(self):
        return [self._array[i] for i in range(self._len)]

    def to(self, device):
        return self.__class__(self._array.to(device))

    def __str__(self):
        return f"{self.__class__.__name__}({str_(self._array)})"


class NestedTrainingSample(TrainingSample):
    # states are not regular and cannot be stacked
    # appropriate for Observations
    def __init__(self, states, state_type="torch", **kwargs):
        if kwargs: print('❌ the clone method assumes no kwargs')
        super().__init__(**kwargs)
        assert isinstance(states, (list, tuple, NestedTrainingSample)), type(states)
        self._state_type = state_type
        self._state_class = dict(torch=TorchNestedAnemoiTensor, numpy=NumpyNestedAnemoiTensor)[state_type]
        states = tuple(self.cast_to_state(_) for _ in states)
        self._states = states

        self._len = len(states)
        self._dtype = states[0].dtype

    def clone(self):
        return self.__class__(tuple(v.clone() for v in self), state_type=self._state_type)

    @classmethod
    def from_tuple_of_tuple_of_arrays(cls, tuple_of_tuple_of_arrays, **kwargs):
        return cls(tuple_of_tuple_of_arrays, **kwargs)

    def cast_to_state(self, v):
        if isinstance(v, self._state_class):
            return v
        return self._state_class(v, name_to_index=self.name_to_index)

    def __iter__(self):
        return iter(self._states)

    def __getitem__(self, i):
        return self._states[i]

    def __str__(self):
        return f"{self.__class__.__name__}({str_(self._states)})"

    def to(self, device):
        return self.__class__(tuple(s.to(device) for s in self))

    def as_torch(self):
        return self.__class__(tuple(v.as_torch() for v in self))

    def as_native(self):
        return tuple(v.as_native() for v in self)

class EnsembleTrainingSample(TrainingSample):
    # One additional dimension and potentially different behavior
    # but stacking is still possible
    #
    # maybe not needed and we can use SimpleTrainingSample
    pass


# end of: this may move to anemoi-training ?
#######################################


#######################################
# this may move to anemoi-inference ?
class InferenceThingy(States):
    pass


class SimpleInferenceThingy(InferenceThingy):
    pass


class NestedInferenceThingy(InferenceThingy):
    pass


class EnsembleInferenceThingy(InferenceThingy):
    pass


# end of: this may move to anemoi-inference ?
#######################################


class AnemoiTensor:
    def __init__(self, name_to_index=None):
        self.name_to_index = name_to_index


class SimpleAnemoiTensor(AnemoiTensor):
    # This should behave like a torch tensor, maybe it should be a torch.Tensor
    def __init__(self, *args, name_to_index=None, **kwargs):
        super().__init__(name_to_index=name_to_index)

        print("❗❗❗❗This is for illustration purposes. SimpleAnemoiTensor has not been tested")
        from torch import Tensor

        self.forward = Tensor(*args, **kwargs)

    def __getattribute__(self, name):
        return self.forward.__getattribute__(name)


class NestedAnemoiTensor(AnemoiTensor):
    def __init__(self, arrays, **kwargs):
        super().__init__(**kwargs)
        if isinstance(arrays, (list, tuple)):
            arrays = {i: v for i, v in enumerate(arrays)}
        self.arrays = arrays

    def keys(self):
        return self.arrays.keys()

    def clone(self):
        raise NotImplementedError

    def check_array_type(self, arrays):
        _type = None
        for _, a in arrays.items():
            _type = type(a)
            assert isinstance(a, _type), (type(a), _type)

    def __getitem__(self, tupl):
        assert isinstance(tupl, (int, tuple, str)), type(tupl)
        if isinstance(tupl, int) or isinstance(tupl, str):
            return self.arrays[tupl]
        assert len(tupl) == 2
        i, j = tupl
        return self.arrays[i][j]

    def __setitem__(self, tupl, value):
        assert isinstance(tupl, tuple), type(tupl)
        assert len(tupl) == 2
        i, j = tupl
        self.arrays[i][j] = value

    def __len__(self):
        return len(self.arrays)

    def items(self):
        return self.arrays.items()

    @property
    def size(self):
        return sum(v.size for _, v in self.arrays.items())

    def map(self, f):
        return self.__class__({k: f(v) for k, v in self.arrays.items()})

    @cached_property
    def dtype(self):
        dtype = None
        for _, a in self.arrays.items():
            if dtype is None:
                dtype = a.dtype
            assert a.dtype == dtype, (a.dtype, dtype)
        return dtype

    def __repr__(self):
        return f"{self.__class__.__name__}({str_(self.arrays)})"

    def as_list(self):
        return list(self.arrays.values())

    def as_tuple(self):
        return tuple(self.arrays.values())

    def as_native(self):
        return self.arrays

class NumpyNestedAnemoiTensor(NestedAnemoiTensor):
    def flatten(self):
        return np.concatenate([v.flatten() for _, v in self.arrays.items()])

    def as_torch(self):
        return TorchNestedAnemoiTensor(self.arrays)

    def check_array_type(self, arrays):
        for _, a in arrays.items():
            assert isinstance(a, np.ndarray), type(a)
        super().check_array_type(arrays)


class TorchNestedAnemoiTensor(NestedAnemoiTensor):
    def __init__(self, arrays, **kwargs):
        arrays = {k:self._cast_to_torch(v) for k, v in arrays.items()}

        super().__init__(arrays, **kwargs)
        self.check_array_type(arrays)

    def clone(self):
        return self.__class__({k: v.clone() for k, v in self.arrays.items()})


    @classmethod
    def _cast_to_torch(cls, v):
        import torch

        return torch.from_numpy(v) if isinstance(v, np.ndarray) else v

    def to(self, device):
        return self.__class__({k: v.to(device) for k, v in self.arrays.items()})

    def as_torch(self):
        print("WARNING: This is a torch tensor already")
        return self

    def check_array_type(self, arrays):
        import torch

        for _, a in arrays.items():
            assert isinstance(a, torch.Tensor), type(a)
        super().check_array_type(arrays)

    def register_buffer(self, *, caller, name, persistent=False):
        assert '__' not in name, name
        for k, array in self.arrays.items():
            caller.register_buffer(f'{name}__{k}', array, persistent=persistent)


def define_anemoi_tensor(data: dict, sources: list[str], indices: dict) -> TorchNestedAnemoiTensor:
    import torch
    
    tt = {}
    for name in sources:
        valid_values_mask = ~torch.isnan(data[name]).any((0, 2))
        tt[name] = data[name][:, valid_values_mask][..., indices[name]]
        
    return TorchNestedAnemoiTensor(tt)

