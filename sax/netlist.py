# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/06a_netlist.ipynb (unless otherwise specified).

__all__ = ['Component', 'PortEnum', 'Placement', 'Route', 'Netlist', 'RecursiveNetlist', 'netlist', 'load_netlist',
           'load_recursive_netlist', "get_netlist_instances_by_prefix", "get_component_instances"]

# Cell
import os
import re
from enum import Enum
from functools import lru_cache, partial
from typing import Any, Callable, Dict, Optional, Union

import black
import numpy as np
import yaml
from pydantic import BaseModel as _BaseModel
from pydantic import Extra, Field, ValidationError, validator
from .utils import clean_string, get_settings, hash_dict

# Internal Cell
class BaseModel(_BaseModel):
    class Config:
        extra = Extra.ignore
        allow_mutation = False
        frozen = True
        json_encoders = {np.ndarray: lambda arr: np.round(arr, 12).tolist()}

    def __repr__(self):
        s = super().__repr__()
        s = black.format_str(s, mode=black.Mode())
        return s

    def __str__(self):
        return self.__repr__()

    def __hash__(self):
        return hash_dict(self.dict())

# Cell

class Component(BaseModel):
    class Config:
        extra = Extra.ignore
        allow_mutation = False
        frozen = True
        json_encoders = {np.ndarray: lambda arr: np.round(arr, 12).tolist()}

    component: Union[str, Dict[str, Any]] = Field(..., title="Component")
    settings: Optional[Dict[str, Any]] = Field(None, title="Settings")

    # this was added:
    @validator("component")
    def validate_component_name(cls, value):
        if "," in value:
            raise ValueError(
                f"Invalid component string. Should not contain ','. Got: {value}"
            )
        return clean_string(value)


class PortEnum(Enum):
    ce = "ce"
    cw = "cw"
    nc = "nc"
    ne = "ne"
    nw = "nw"
    sc = "sc"
    se = "se"
    sw = "sw"
    center = "center"
    cc = "cc"


class Placement(BaseModel):
    class Config:
        extra = Extra.ignore
        allow_mutation = False
        frozen = True
        json_encoders = {np.ndarray: lambda arr: np.round(arr, 12).tolist()}

    x: Optional[Union[str, float]] = Field(0, title="X")
    y: Optional[Union[str, float]] = Field(0, title="Y")
    xmin: Optional[Union[str, float]] = Field(None, title="Xmin")
    ymin: Optional[Union[str, float]] = Field(None, title="Ymin")
    xmax: Optional[Union[str, float]] = Field(None, title="Xmax")
    ymax: Optional[Union[str, float]] = Field(None, title="Ymax")
    dx: Optional[float] = Field(0, title="Dx")
    dy: Optional[float] = Field(0, title="Dy")
    port: Optional[Union[str, PortEnum]] = Field(None, title="Port")
    rotation: Optional[int] = Field(0, title="Rotation")
    mirror: Optional[bool] = Field(False, title="Mirror")


class Route(BaseModel):
    class Config:
        extra = Extra.ignore
        allow_mutation = False
        frozen = True
        json_encoders = {np.ndarray: lambda arr: np.round(arr, 12).tolist()}

    links: Dict[str, str] = Field(..., title="Links")
    settings: Optional[Dict[str, Any]] = Field(None, title="Settings")
    routing_strategy: Optional[str] = Field(None, title="Routing Strategy")


class Netlist(BaseModel):
    class Config:
        extra = Extra.ignore
        allow_mutation = False
        frozen = True
        json_encoders = {np.ndarray: lambda arr: np.round(arr, 12).tolist()}

    instances: Dict[str, Component] = Field(..., title="Instances")
    connections: Optional[Dict[str, str]] = Field(None, title="Connections")
    ports: Optional[Dict[str, str]] = Field(None, title="Ports")
    placements: Optional[Dict[str, Placement]] = Field(None, title="Placements")

    # these were removed (irrelevant for SAX):

    # routes: Optional[Dict[str, Route]] = Field(None, title='Routes')
    # name: Optional[str] = Field(None, title='Name')
    # info: Optional[Dict[str, Any]] = Field(None, title='Info')
    # settings: Optional[Dict[str, Any]] = Field(None, title='Settings')
    # pdk: Optional[str] = Field(None, title='Pdk')

    # these are extra additions:

    @validator("instances", pre=True)
    def coerce_different_type_instance_into_component_model(cls, instances):
        new_instances = {}
        for k, v in instances.items():
            if isinstance(v, str):
                v = {
                    "component": v,
                    "settings": {},
                }
            new_instances[k] = v

        return new_instances

    @staticmethod
    def clean_instance_string(value):
        if "," in value:
            raise ValueError(
                f"Invalid instance string. Should not contain ','. Got: {value}"
            )
        return clean_string(value)

    @validator("instances")
    def validate_instance_names(cls, instances):
        return {cls.clean_instance_string(k): v for k, v in instances.items()}

    @validator("placements")
    def validate_placement_names(cls, placements):
        return {cls.clean_instance_string(k): v for k, v in placements.items()}

    @classmethod
    def clean_connection_string(cls, value):
        *comp, port = value.split(",")
        comp = cls.clean_instance_string(",".join(comp))
        return f"{comp},{port}"

    @validator("connections")
    def validate_connection_names(cls, connections):
        return {
            cls.clean_connection_string(k): cls.clean_connection_string(v)
            for k, v in connections.items()
        }

    @validator("ports")
    def validate_port_names(cls, ports):
        return {
            cls.clean_instance_string(k): cls.clean_connection_string(v)
            for k, v in ports.items()
        }

# Cell

class RecursiveNetlist(BaseModel):
    class Config:
        extra = Extra.ignore
        allow_mutation = False
        frozen = True

    __root__: Dict[str, Netlist]

# Cell

def netlist(dic: Dict) -> RecursiveNetlist:
    if isinstance(dic, RecursiveNetlist):
        return dic
    elif isinstance(dic, Netlist):
        dic = dic.dict()
    try:
        flat_net = Netlist.parse_obj(dic)
        net = RecursiveNetlist.parse_obj({'top_level': flat_net})
    except ValidationError:
        net = RecursiveNetlist.parse_obj(dic)
    return net

# Cell
@lru_cache()
def load_netlist(pic_path) -> Netlist:
    with open(pic_path, "r") as file:
        net = yaml.safe_load(file.read())
    return Netlist.parse_obj(net)

# Cell
@lru_cache()
def load_recursive_netlist(pic_path, ext='.yml'):
    folder_path = os.path.dirname(os.path.abspath(pic_path))
    _clean_string = lambda path: clean_string(re.sub(ext, "", os.path.split(path)[-1]))
    netlists = {_clean_string(pic_path): None} # the circuit we're interested in should come first.
    for filename in os.listdir(folder_path):
        path = os.path.join(folder_path, filename)
        if not os.path.isfile(path) or not path.endswith(ext):
            continue
        netlists[_clean_string(path)] = load_netlist(path)
    return RecursiveNetlist.parse_obj(netlists)


def get_netlist_instances_by_prefix(
        recursive_netlist: RecursiveNetlist,
        prefix: str,
):
    """
    Returns a list of all instances with a given prefix in a recursive netlist.

    Args:
        recursive_netlist: The recursive netlist to search.
        prefix: The prefix to search for.

    Returns:
        A list of all instances with the given prefix.
    """
    recursive_netlist_root = recursive_netlist.dict()["__root__"]
    result = []
    for key in recursive_netlist_root.keys():
        if key.startswith(prefix):
            result.append(key)
    return result


def get_component_instances(
        recursive_netlist: RecursiveNetlist,
        top_level_prefix: str,
        component_name_prefix: str,
):
    """
    Returns a dictionary of all instances of a given component in a recursive netlist.

    Args:
        recursive_netlist: The recursive netlist to search.
        top_level_prefix: The prefix of the top level instance.
        component_name_prefix: The name of the component to search for.

    Returns:
        A dictionary of all instances of the given component.
    """
    instance_names = []
    recursive_netlist_root = recursive_netlist.dict()["__root__"]
    top_level_prefix = get_netlist_instances_by_prefix(recursive_netlist, prefix=top_level_prefix)[
        0
    ]  # Should only be one in a netlist-to-digraph. Can always be very specified.
    for key in recursive_netlist_root[top_level_prefix]["instances"]:
        if recursive_netlist_root[top_level_prefix]["instances"][key]["component"].startswith(component_name_prefix):
            # Note priority encoding on match.
            instance_names.append(key)
    return {component_name_prefix: instance_names}