# Copyright 2026 Juan S. Cely G.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from os.path import join

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import (AppendEnvironmentVariable, DeclareLaunchArgument,
                            IncludeLaunchDescription)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution


def generate_launch_description():

    pkg_share = get_package_share_directory('large_warehouse_world')

    world_arg = DeclareLaunchArgument(
        'world',
        default_value='large_warehouse_world.sdf',
        description='World file inside large_warehouse_world/worlds')

    gz_args_arg = DeclareLaunchArgument(
        'gz_args',
        default_value='-r',
        description='Extra arguments for gz sim (e.g. "-r -s" for headless)')

    # Makes the package models available as model://<name>
    gz_resource_path = AppendEnvironmentVariable(
        'GZ_SIM_RESOURCE_PATH', join(pkg_share, 'models'))

    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            join(get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py')),
        launch_arguments={
            'gz_args': [
                PathJoinSubstitution([pkg_share, 'worlds', LaunchConfiguration('world')]),
                ' ',
                LaunchConfiguration('gz_args'),
            ],
            'on_exit_shutdown': 'true',
        }.items(),
    )

    ld = LaunchDescription()
    ld.add_action(world_arg)
    ld.add_action(gz_args_arg)
    ld.add_action(gz_resource_path)
    ld.add_action(gz_sim)
    return ld
