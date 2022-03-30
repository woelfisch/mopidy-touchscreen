import pathlib

from mopidy import config, ext

__version__ = '1.2.0'

class Extension(ext.Extension):
    dist_name = 'Mopidy-Touchscreen'
    ext_name = 'touchscreen'
    version = __version__

    def get_default_config(self):
        return config.read(pathlib.Path(__file__).parent / "ext.conf")

    def get_config_schema(self):
        schema = super(Extension, self).get_config_schema()
        schema['screen_width'] = config.Integer(minimum=1)
        schema['screen_height'] = config.Integer(minimum=1)
        schema['resolution_factor'] = config.Integer(minimum=6)
        schema['start_screen'] = config.String()
        schema['main_screen'] = config.String()
        schema['cursor'] = config.Boolean()
        schema['fullscreen'] = config.Boolean()
        schema['cache_dir'] = config.Path()
        schema['sdl_videodriver'] = config.String()
        schema['sdl_video_render_driver'] = config.String()
        schema['sdl_video_device_index'] = config.String()
        schema['sdl_video_device'] = config.String()
        schema['sdl_mousedriver'] = config.String()
        schema['sdl_mousedev'] = config.String()
        schema['sdl_audiodriver'] = config.String()
        schema['sdl_path_dsp'] = config.String()
        return schema

    def setup(self, registry):
        from .actor import TouchScreen
        registry.add('frontend', TouchScreen)
