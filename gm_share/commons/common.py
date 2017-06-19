# coding=utf-8
from enums import PLATFORM_TYPE
from distutils.version import LooseVersion


class Config(object):
    qiniu_prefix = 'http://pic.gmei.com'
    gengmei_icon = qiniu_prefix + '/img/icon114.png-thumb'

    wechatline_screenshot = {
        'title': "",
        'content': "http://hera.s.gmei.com/slide/2016/06/02/6a6eb352d8"
    }
    wechat_screenshot = {
        'title': "",
        'content': "http://hera.s.gmei.com/slide/2016/06/02/6a6eb352d8"
    }
    default_apk_download_url = 'http://a.app.qq.com/o/simple.jsp?pkgname=com.wanmeizhensuo.zhensuo'


login_required_data = {
    'message': u'需要登录',
    'error': 1001,
    'data': None
}


# 各个渠道下载地址
DOWNLOAD_URL = {
    'default': {
        'android': 'http://dl.gmei.com/current/perfect/gengmei_perfect.apk',
        'ios': 'https://itunes.apple.com/cn/app/id639234809',
        'name': u'默认'
    },
    'fst': {
        'android': 'http://dl.gmei.com/current/fst/gengmei_fst.apk',
        'ios': 'http://um0.cn/2eeP93',
        'name': u'粉丝通1'
    },
    'fensitong': {
        'android': 'http://dl.gmei.com/current/fensitong/gengmei_fensitong.apk',
        'ios': 'http://um0.cn/5EpTI',
        'name': u'粉丝通2'
    },
    'weibosixin': {
        'android': 'http://dl.gmei.com/current/weibosixin/gengmei_weibosixin.apk',
        'ios': 'http://um0.cn/2eGf5R',
        'name': u'微博私信'
    },
    'youkuqiantiepian': {
        'android': 'http://dl.gmei.com/current/youku/gengmei_youku.apk',
        'ios': 'http://um0.cn/tjezx',
        'name': u'优酷前贴片'
    },
    'youkuzanting': {
        'android': 'http://dl.gmei.com/current/ykzt/gengmei_ykzt.apk',
        'ios': 'http://um0.cn/Lbmfy',
        'name': u'优酷暂停'
    },
    'baiduvip': {
        'android': 'http://dl.gmei.com/current/bdvip/gengmei_bdvip.apk',
        'ios': 'http://um0.cn/3ufMNc',
        'name': u'百度VIP'
    },
    'iqiyiqiantiepian': {
        'android': 'http://dl.gmei.com/current/iqiyi/gengmei_iqiyi.apk',
        'ios': 'http://um0.cn/VwWWC',
        'name': u'爱奇艺'
    },
    'weixin': {
        'android': 'http://dl.gmei.com/current/weixingg/gengmei_weixingg.apk',
        'ios': 'http://um0.cn/3QGIkL',
        'name': u'微信公众号'
    },
    'momo': {
        'android': 'http://dl.gmei.com/current/momo/gengmei_momo.apk',
        'ios': 'http://um0.cn/uTmWM',
        'name': u'陌陌'
    }
}


def get_download_url_from_channel(channel, platform=None):
    if not channel or channel not in DOWNLOAD_URL:
        if platform is None:
            return Config.default_apk_download_url
        elif platform == PLATFORM_TYPE.IOS:
            return DOWNLOAD_URL['default']['ios']
        elif platform == PLATFORM_TYPE.ANDROID:
            return DOWNLOAD_URL['default']['android']
        else:
            return Config.default_apk_download_url

    if platform is None:
        return Config.default_apk_download_url
    elif platform == PLATFORM_TYPE.IOS:
        return DOWNLOAD_URL[channel]['ios']
    elif platform == PLATFORM_TYPE.ANDROID:
        return DOWNLOAD_URL[channel]['android']
    else:
        return Config.default_apk_download_url


def is_hybrid(request):
    return False


def support_new_tags(request):
    """only client version greater than 4.5 will return true."""
    version = request.GET.get('version', '').strip() or '4.4'
    version_under_45 = LooseVersion(version) < LooseVersion('4.5')

    if is_hybrid(request) and not version_under_45:
        return True

    return False

