"""
国际化 (i18n) 配置模块
使用 python-i18n 库，支持 YAML/JSON 格式
"""
import os
import i18n
from core.app import LOG, get_property
from core.events import register_event_handler, SettingsEvent
from core.settings import Settings
from core.utils.path_utils import get_base_dir

_ok: bool = False


def init_i18n(locale: str = 'zh-CN', fallback: str = 'en'):
    """
    初始化 i18n 配置
    
    Args:
        locale: 默认语言
        fallback: 回退语言
    """

    global _ok

    base_dir = get_base_dir()

    i18n_dir = os.path.join(base_dir, 'resources', 'i18n')

    os.makedirs(i18n_dir, exist_ok=True)

    i18n.resource_loader.loaders.clear()

    i18n.load_path.append(i18n_dir)
    i18n.set('locale', locale)
    i18n.set('fallback', fallback)
    i18n.set('enable_memoization', True)
    i18n.set('skip_locale_root_data', True)
    i18n.set('filename_format', '{locale}.{format}')
    i18n.set('file_format', 'json')

    i18n.resource_loader.init_loaders()

    _ok = True

    register_event_handler(SettingsEvent, lambda e: set_locale(e.settings.get('lang')))
    lang = get_property('settings').get('lang')
    set_locale(lang)

    LOG.info(t("i18n.finished_init", lang=locale, dir=i18n_dir))


def set_locale(locale: str):
    """
    切换语言
    
    Args:
        locale: 语言代码，如 'zh-CN', 'en', 'ja'
    """
    i18n.set('locale', locale)


def get_locale() -> str:
    """
    获取当前语言
    
    Returns:
        当前语言代码
    """
    return i18n.config.get('locale')


def t(key: str, **kwargs) -> str:
    """
    翻译快捷函数
    
    Args:
        key: 翻译键
        **kwargs: 插值参数
        
    Returns:
        翻译后的字符串
    """
    if not _ok:
        init_i18n()
    return i18n.t(key, **kwargs)


def get_available_locales() -> list:
    """
    获取可用的语言列表
    
    Returns:
        语言代码列表
    """
    i18n_dir = i18n.config.get('load_path')[0] if i18n.config.get('load_path') else None
    if not i18n_dir or not os.path.exists(i18n_dir):
        return []

    locales = []
    for filename in os.listdir(i18n_dir):
        if filename.endswith('.json') or filename.endswith('.yml') or filename.endswith('.yaml'):
            locale = filename.split('.')[0]
            locales.append(locale)

    return sorted(list(set(locales)))


def haveKey(key: str) -> bool:
    locale = get_locale()
    return key in i18n.translations.container.get(locale, {})


__all__ = ['init_i18n', 'set_locale', 'get_locale', 't', 'get_available_locales', 'i18n']
