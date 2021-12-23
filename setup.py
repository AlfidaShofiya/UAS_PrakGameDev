from setuptools import setup

setup(
    name="ANIMALHUNTER",
    options = {
        'build_apps': {
            'include_patterns': [
                '**/*.png',
                '**/*.jpg',
                '**/*.egg',
            ],
            'gui_apps': {
                'ANIMALHUNTER': 'main.py',
            },
            'log_filename': '$USER_APPDATA/ANIMALHUNTER/output.log',
            'log_append': False,
            'plugins': [
                'pandagl',
                'p3openal_audio',
            ],
        }
    }
)
