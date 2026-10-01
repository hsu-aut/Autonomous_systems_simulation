from setuptools import setup

package_name = 'neo_robot_monitor'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/monitor.launch.py']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='maintainer',
    maintainer_email='maintainer@example.com',
    description='Read-only Qt monitor for joint states, base pose and TCP pose.',
    license='MIT',
    entry_points={
        'console_scripts': [
            'monitor = neo_robot_monitor.monitor:main',
        ],
    },
)
