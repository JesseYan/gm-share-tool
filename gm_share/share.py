# coding=utf-8

import re
from urllib import urlencode

from django.utils.html import strip_tags

from gm_share.commons.common import Config


_link = re.compile(
    r'(?<!!)\[('
    r'(?:\[[^^\]]*\]|[^\[\]]|\](?=[^\[]*\]))*'
    r')\]\('
    r'''\s*<?([\s\S]*?)>?(?:\s+['"]([\s\S]*?)['"])?\s*'''
    r'\)'
)
_image_link = re.compile(
    r'!\[('
    r'(?:\[[^^\]]*\]|[^\[\]]|\](?=[^\[]*\]))*'
    r')\]\('
    r'''\s*<?([\s\S]*?)>?(?:\s+['"]([\s\S]*?)['"])?\s*'''
    r'\)'
)

_iframe = re.compile(
    r'<iframe.*?</iframe>'
)

gengmei_link = re.compile(
    r'\[.*?\]\(gengmei://.*?\)'
)


def strip_markdown_links(md_txt, keep_image=False):
    """strip markdown link and image."""
    striped = _link.sub('', md_txt)
    if keep_image:
        return striped

    striped = _image_link.sub('', striped)
    striped = _iframe.sub('', striped)
    striped = gengmei_link.sub('', striped)
    return striped


def _striper(x):
    _x = strip_tags(strip_markdown_links(x))
    return _x.strip()


def patch_url_parameter(url, **kwargs):
    """
    add get parameters to a url.
    :param url:
    :param kwargs:
    :return:
    """
    return url + "&" + urlencode(kwargs) if "?" in url else url + "?" + urlencode(kwargs)


class ShareData(object):
    """
    分享数据结构
    """
    weibo_share_max_length = 140
    weixin_content_max_length = 200

    def __init__(self, image=None, url='', wechat_title='', wechat_content='', wechat_line='', weibo='', weibo_check_url=''):
        self.wechat_title = _striper(wechat_title)
        self.wechat_content = _striper(wechat_content)
        self.wechat_line = _striper(wechat_line)
        self.weibo = weibo
        self.url = url
        self.image = image
        self.weibo_check_url = weibo_check_url

        if len(self.wechat_title) > self.weixin_content_max_length:
            self.wechat_title = self.wechat_title[0:self.weixin_content_max_length]
        if len(self.wechat_content) > self.weixin_content_max_length:
            self.wechat_content = self.wechat_content[0:self.weixin_content_max_length]
        if len(self.wechat_line) > self.weixin_content_max_length:
            self.wechat_line = self.wechat_line[0:self.weixin_content_max_length]

        if isinstance(self.weibo, (list, tuple)):
            _weibo = [_striper(x) for x in weibo]
            weibo_prefix, weibo_suffix = _weibo
            if len(weibo_suffix) > self.weibo_share_max_length:
                self.weibo = weibo_suffix[0:self.weibo_share_max_length]
            elif len(weibo_prefix + weibo_suffix) > self.weibo_share_max_length:
                prefix_max_len = self.weibo_share_max_length - len(weibo_suffix)
                weibo_prefix = weibo_prefix[0:prefix_max_len]
                self.weibo = weibo_prefix + weibo_suffix
            else:
                self.weibo = weibo_prefix + weibo_suffix

        if self.image is None:
            self.image = Config.gengmei_icon

    @property
    def share_data(self):
        result = {
            'image': self.image,
            'url': self.url,
            'wechat': {
                'title': self.wechat_title,
                "content": self.wechat_content
            },
            'wechatline': {
                'title': self.wechat_line,
                'content': self.wechat_line
            },
            'qq': {
                'title': self.wechat_title,
                'content': self.wechat_content
            },
            'weibo': {
                'title': self.weibo,
                'content': self.weibo
            }
        }

        """微博升级: 至少含有一个不跨域名的URL"""
        if self.weibo_check_url not in result['weibo']['content']:
            # 默认放在分享文字后面
            result['weibo']['content'] = result['weibo']['content'][:self.weibo_share_max_length - len(self.weibo_check_url)] \
                                         + self.weibo_check_url
        return result

    @property
    def share_data_for_88(self):
        result = {
            'image': self.image,
            'url': self.url,
            'wechat': {
                'title': self.wechat_title,
                "content": self.wechat_content
            },
            'wechatline': {
                'title': self.wechat_line,
                'content': self.wechat_line
            },
            'qq': {
                'title': self.wechat_title,
                'content': self.wechat_content
            },
            'weibo': {
                'title': self.weibo,
                'content': self.weibo
            },
            'wechat_screenshot': Config.wechat_screenshot,
            'wechatline_screenshot': Config.wechatline_screenshot
        }

        """微博升级: 至少含有一个不跨域名的URL"""
        if self.weibo_check_url not in result['weibo']['content']:
            # 默认放在分享文字后面
            result['weibo']['content'] = result['weibo']['content'][:self.weibo_share_max_length - len(self.weibo_check_url)] \
                                         + self.weibo_check_url
        return result
