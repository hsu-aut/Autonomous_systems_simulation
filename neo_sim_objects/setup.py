from glob import glob
from setuptools import setup

package_name = 'neo_sim_objects'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
        ('share/' + package_name + '/config', glob('config/*.yaml')),
        ('share/' + package_name + '/models', glob('models/*.sdf')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='maintainer',
    maintainer_email='maintainer@example.com',
    description='Puts objects into the Gazebo simulation, or moves them back.',
    license='MIT',
    entry_points={
        'console_scripts': [
            'spawn_objects = neo_sim_objects.spawn_objects:main',
        ],
    },
)
