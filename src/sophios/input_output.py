import argparse
import copy
import json
from pathlib import Path
import sys
from typing import Any, List, Tuple

import yaml

from . import auto_gen_header
from .wic_types import (Namespaces, NodeData, RoseTree, Yaml, ExplicitEdgeCalls, Json)


def read_lines_pairs(filename: Path) -> List[Tuple[str, str]]:
    """Reads a whitespace-delimited file containing two paired entries per line (i.e. a serialized Dict).

    Args:
        filename (Path): The full path of the file to be read.

    Raises:
        Exception: If any non-blank, non-comment lines do not contain exactly two entries.

    Returns:
        List[Tuple[str, str]]: The file contents, with blank lines and comments removed.
    """
    with open(filename, mode='r', encoding='utf-8') as f:
        lines = []
        for line in f.readlines():
            if line.strip() == '':  # Skip blank lines
                continue
            if line.startswith('#'):  # Skip comment lines
                continue
            l_s = line.split()
            if not len(l_s) == 2:
                print(line)
                raise Exception("Error! Line must contain exactly two entries!")
            lines.append((l_s[0], l_s[1]))
    return lines


# snakeyaml (a cromwell dependency) refuses to parse yaml files with more than
# 50 anchors/aliases to prevent Billion Laughs attacks.
# See https://en.wikipedia.org/wiki/Billion_laughs_attack
# Solution: Inline the contents of the aliases into the anchors.
# See https://ttl255.com/yaml-anchors-and-aliases-and-how-to-disable-them/#override


class NoAliasDumper(yaml.SafeDumper):
    def ignore_aliases(self, data: Any) -> bool:
        return True


def write_to_disk(rose_tree: RoseTree, path: Path, relative_run_path: bool, inputs_file: str = '') -> None:
    """Writes the compiled CWL files and their associated yml inputs files to disk.

    NOTE: Only the yml input file associated with the root workflow is
    guaranteed to have all inputs. In other words, subworkflows will all have
    valid CWL files, but may not be executable due to 'missing' inputs.
    Additional inputs can be explicitly passed in in this case.

    Args:
        rose_tree (RoseTree): The data associated with compiled subworkflows
        path (Path): The directory in which to write the files
        relative_run_path (bool): Controls whether to use subdirectories or just one directory.
        inputs_file (str): Optional additional inputs
    """
    inputs = {}
    if inputs_file:
        with open(inputs_file, mode='r', encoding='utf-8') as f:
            inputs = yaml.safe_load(f.read())
        for key, val in inputs.items():
            if 'location' in val and not Path(val['location']).is_absolute():
                # Change relative paths for class: File and class: Dir
                # to be w.r.t. autogenerated/
                val['location'] = '../' + val['location']
    _write_to_disk(rose_tree, path, relative_run_path, inputs)


def _write_to_disk(rose_tree: RoseTree, path: Path, relative_run_path: bool, inputs: Yaml = {}) -> None:
    """Writes the compiled CWL files and their associated yml inputs files to disk.

    NOTE: Only the yml input file associated with the root workflow is
    guaranteed to have all inputs. In other words, subworkflows will all have
    valid CWL files, but may not be executable due to 'missing' inputs.
    Additional inputs can be explicitly passed in in this case.

    Args:
        rose_tree (RoseTree): The data associated with compiled subworkflows
        path (Path): The directory in which to write the files
        relative_run_path (bool): Controls whether to use subdirectories or just one directory.
        inputs (Yaml): Optional additional inputs
    """
    node_data: NodeData = rose_tree.data
    namespaces = node_data.namespaces
    yaml_stem = node_data.name
    cwl_tree = node_data.compiled_cwl
    yaml_inputs = {**node_data.workflow_inputs_file, **inputs}

    path.mkdir(parents=True, exist_ok=True)
    if relative_run_path:
        filename_cwl = f'{yaml_stem}.cwl'
        filename_yml = f'{yaml_stem}_inputs.yml'
    else:
        filename_cwl = '___'.join(namespaces + [f'{yaml_stem}.cwl'])
        filename_yml = '___'.join(namespaces + [f'{yaml_stem}_inputs.yml'])

    # Dump the compiled CWL file contents to disk.
    # Use sort_keys=False to preserve the order of the steps.
    yaml_content = yaml.dump(cwl_tree, sort_keys=False, line_break='\n', indent=2, Dumper=NoAliasDumper)
    with open(path / filename_cwl, mode='w', encoding='utf-8') as w:
        w.write('#!/usr/bin/env cwl-runner\n')
        w.write(auto_gen_header)
        w.write(''.join(yaml_content))

    yaml_content = yaml.dump(yaml_inputs, sort_keys=False, line_break='\n', indent=2, Dumper=NoAliasDumper)
    with open(path / filename_yml, mode='w', encoding='utf-8') as inp:
        inp.write(auto_gen_header)
        inp.write(yaml_content)

    for sub_rose_tree in rose_tree.sub_trees:
        subpath = path
        if relative_run_path:
            sub_node_data: NodeData = sub_rose_tree.data
            sub_step_name = sub_node_data.namespaces[-1]
            subpath = path / sub_step_name
        _write_to_disk(sub_rose_tree, subpath, relative_run_path, inputs)


def write_config_to_disk(config: Json, config_file: Path) -> None:
    """Writes config json object to config_file

    Args:
        config (Json): The json object that is to be written to disk
        config_file (Path): The file path where it is to be written
    """
    config_dir = Path(config_file).parent
    # make the full path if it doesn't exist
    config_dir.mkdir(parents=True, exist_ok=True)
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f)


def get_config(config_file: Path, default_config_file: Path) -> Json:
    """Returns the config json object from config_file with absolute paths

    Args:
        config_file (Path): The path of the user specified config file
        default_config_file (Path): The default path of the config file if user hasn't specified one

    Returns:
        Json: The config json object with absolute filepaths
    """
    global_config: Json = {}
    if not config_file.exists():
        if config_file == default_config_file:
            global_config = get_default_config()
            # write the default config object to the 'global_config.json' file in user's ~/wic directory
            # for user to inspect and or modify the config json file
            write_config_to_disk(global_config, default_config_file)
            print(f'default config file : {default_config_file} generated')
        else:
            print(f"Error user specified config file {config_file} doesn't exist")
            sys.exit()
    else:
        # reading user specified config file only if it exists
        # never overwrite user's config file or generate another file in user's non-default directory
        # TODO : Validate the json inside 'read_config_from_disk' function
        global_config = read_config_from_disk(config_file)
    return global_config


def read_config_from_disk(config_file: Path) -> Json:
    """Returns the config json object from config_file with absolute paths

    Args:
        config_file (Path): The path of json file where it is to be read from

    Returns:
        Json: The config json object with absolute filepaths
    """
    config: Json = {}
    # config_file can contain absolute or relative paths
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    conf_tags = ['search_paths_cwl', 'search_paths_wic']
    for tag in conf_tags:
        config[tag] = get_absolute_paths(config[tag])
    return config


def get_default_config() -> Json:
    """Returns the default config with absolute paths

    Returns:
        Json: The config json object with absolute filepaths
    """
    src_dir = Path(__file__).parent
    default_config: Json = {}
    # config.json can contain absolute or relative paths
    # read_config_from_disk handles converting them to absolute paths
    default_config = read_config_from_disk(src_dir/'config.json')
    return default_config


def get_absolute_paths(sub_config: Json) -> Json:
    """Update the paths within the sub_config json object as absolute paths

    Args:
        sub_config (dict): The json (sub)object where filepaths are stored

    Returns:
        Json: The json (sub)object with absolute filepaths
    """
    abs_sub_config = copy.deepcopy(sub_config)
    for ns in abs_sub_config:
        abs_paths = [str(Path(path).absolute()) for path in abs_sub_config[ns]]
        abs_sub_config[ns] = abs_paths
    return abs_sub_config


def write_absolute_yaml_tags(args: argparse.Namespace, in_dict_in: Yaml, namespaces: Namespaces,
                             step_name_i: str, explicit_edge_calls_copy: ExplicitEdgeCalls) -> None:
    """cwl_subinterpreter requires all paths to be absolute.

    Args:
        args (argparse.Namespace): The command line arguments
        in_dict_in (Yaml): The in: subtag of a cwl_subinterpreter: tag. (Mutates in_dict_in)
        namespaces (Namespaces): Specifies the path in the yml AST to the current subworkflow
        step_name_i (str): The name of the current workflow step
        explicit_edge_calls_copy (ExplicitEdgeCalls): Stores the (path, value) of the explicit edge call sites
    """

    # cachedir_path needs to be an absolute path, but for reproducibility
    # we don't want users' home directories in the yml files.
    cachedir_path = Path(args.cachedir).absolute()
    # print('setting cachedir_path to', cachedir_path)
    in_dict_in['root_workflow_yml_path'] = {'wic_inline_input': str(Path(args.yaml).parent.absolute())}

    in_dict_in['cachedir_path'] = {'wic_inline_input': str(cachedir_path)}
    in_dict_in['homedir'] = {'wic_inline_input': args.homedir}

    # Add a 'dummy' values to explicit_edge_calls, because
    # that determines sub_args_provided when the recursion returns.
    arg_keys_ = ['root_workflow_yml_path', 'cachedir_path', 'homedir']
    for arg_key_ in arg_keys_:
        in_name_ = f'{step_name_i}___{arg_key_}'  # {step_name_i}_input___{arg_key}
        explicit_edge_calls_copy.update({in_name_: (namespaces + [step_name_i], arg_key_)})