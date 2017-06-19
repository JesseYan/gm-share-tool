# coding=utf-8

import hashlib
import json
import random
import string
import time
from datetime import timedelta, datetime
from urllib import urlencode

import requests
from django.conf import settings
from django.utils import timezone

from gm_share.libs.redis_db import db
from gm_share.libs.log import info_logger, exception_logger, error_logger


datetime_format = '%Y-%m-%dT%H:%M:%S.%fZ'


class WxTkApiErr(Exception):
    def __init__(self, desc, res):
        self.desc = desc
        self.res = res

    def __str__(self):
        return self.desc


class WxTkApi(object):
    API_DOMAIN = 'https://api.weixin.qq.com'

    def __init__(self, app_id=None, app_secret=None):
        if app_id:
            self.app_id = app_id
        else:
            self.app_id = settings.WX_APP_ID
        if app_secret:
            self.app_secret = app_secret
        else:
            self.app_secret = settings.WX_APP_SECRET

    def get_access_token(self):
        cached_access_token = db.get('wx:access_token')

        if cached_access_token is None:
            return self._get_wx_token()

        expired_time = db.get('wx:access_token:expired_time')
        expired_time = datetime.strptime(expired_time, datetime_format)

        if datetime.utcnow() < expired_time:
            return cached_access_token
        else:
            return self._get_wx_token()

    def _get_wx_token(self):
        url = WxTkApi.API_DOMAIN + ('/cgi-bin/token')
        payload = {
            'grant_type': 'client_credential',
            'appid': self.app_id,
            'secret': self.app_secret,
        }
        try:
            r = requests.get(url, params=payload, timeout=4)
            res = r.json()
        except requests.exceptions.Timeout:
            raise WxTkApiErr('timeout', None)
        except Exception:
            raise WxTkApiErr('unknown', None)

        if not 'access_token' in res:
            raise WxTkApiErr('error', r.text)

        now = timezone.now()
        expired_time = now + timedelta(seconds=res['expires_in'] - 60)
        expired_time = expired_time.strftime(datetime_format)
        db.set('wx:access_token', res['access_token'])
        db.set('wx:access_token:expired_time', expired_time)

        return res['access_token']

    def get_jsapi_ticket(self, access_token):
        cached_jsapi_ticket = db.get('wx:jsapi_ticket')

        if cached_jsapi_ticket is None:
            return self._get_jsapi_ticket(access_token)

        expired_time = db.get('wx:jsapi_ticket:expired_time')
        expired_time = datetime.strptime(expired_time, datetime_format)

        if datetime.utcnow() < expired_time:
            return cached_jsapi_ticket
        else:
            return self._get_jsapi_ticket(access_token)

    def _get_jsapi_ticket(self, access_token):
        url = WxTkApi.API_DOMAIN + ('/cgi-bin/ticket/getticket')
        payload = {
            'access_token': access_token,
            'type': 'jsapi',
        }

        try:
            r = requests.get(url, params=payload, timeout=4)
            res = r.json()
        except requests.exceptions.Timeout:
            raise WxTkApiErr('timeout', None)
        except Exception as e:
            error_logger.error(u'_get_jsapi_ticket 报错 %s', e.message)
            raise WxTkApiErr('unknown', None)

        if not 'ticket' in res:
            raise WxTkApiErr('error', r.text)

        now = timezone.now()
        expired_time = now + timedelta(seconds=res['expires_in'] - 60)
        expired_time = expired_time.strftime(datetime_format)
        db.set('wx:jsapi_ticket', res['ticket'])
        db.set('wx:jsapi_ticket:expired_time', expired_time)

        return res['ticket']

    def get_jsapi_sign(self, jsapi_ticket, url):
        nonce_str = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(15))
        timestamp = int(time.time())

        ret = {
            'nonceStr': nonce_str,
            'jsapi_ticket': jsapi_ticket,
            'timestamp': timestamp,
            'url': url,
        }

        str1 = '&'.join(['%s=%s' % (key.lower(), ret[key]) for key in sorted(ret)])
        sign = hashlib.sha1(str1).hexdigest()
        ret['signature'] = sign
        del ret['jsapi_ticket']
        return ret

    def get_media(self, access_token, media_id):
        url = 'http://file.api.weixin.qq.com/cgi-bin/media/get'
        payload = {
            'access_token': access_token,
            'media_id': media_id,
        }

        try:
            r = requests.get(url, params=payload, timeout=4)
        except requests.exceptions.Timeout:
            raise WxTkApiErr('timeout', None)
        except Exception:
            raise WxTkApiErr('unknown', None)

        if int(r.status_code) != 200:
            raise WxTkApiErr('http error code %s' % r.status_code, None)
        elif 'errcode' in r.text:
            res_json = json.loads(r.text)
            raise WxTkApiErr(res_json, None)

        return r.content

    def get_auth_url(self, redirect_url, scope='snsapi_base', state='STATE'):
        auth_url = 'https://open.weixin.qq.com/connect/oauth2/authorize?' + urlencode([
            # here comes a bug for weixin, which needs urls params strictly to be in the following order
            # so we should use tuples instead of dict
            ('appid', self.app_id),
            ('redirect_uri', redirect_url),  # key is URI, not URL
            ('response_type', 'code'),
            ('scope', scope),
            ('state', state),
        ]) + '#wechat_redirect'
        info_logger.info(u'wexin_auth:%s', auth_url)
        return auth_url

    def get_accesstoken_by_refresh(self, refresh_token):
        url = 'https://api.weixin.qq.com/sns/oauth2/refresh_token?appid=%s&grant_type=refresh_token&refresh_token=%s'
        url = url % (self.app_id, refresh_token)
        try:
            r = requests.get(url)
            res = r.json()
        except Exception as e:
            exception_logger.error(e)
            raise WxTkApiErr('error', r.text)

        if 'access_token' not in res:
            raise WxTkApiErr('error', r.text)

        return res

    def get_sns_access_token(self, code):
        '''
        CORRECT:
        {
            "access_token":"ACCESS_TOKEN",
            "expires_in":7200,
            "refresh_token":"REFRESH_TOKEN",
            "openid":"OPENID",
            "scope":"SCOPE"
        }
        '''
        url = WxTkApi.API_DOMAIN + '/sns/oauth2/access_token?' + 'appid=' + self.app_id + '&secret=' + self.app_secret + '&code=' + code + '&grant_type=authorization_code'

        try:
            r = requests.get(url, timeout=4)
            info_logger.info("%s%s" % (code, r.content))
            res = r.json()
        except requests.exceptions.Timeout:
            raise WxTkApiErr('timeout', None)
        except Exception:
            raise WxTkApiErr('unknown', None)

        if 'access_token' not in res:
            exception_logger.error(res)
            raise WxTkApiErr('error', r.text)

        return res

    def get_sns_userinfo(self, access_token, openid):
        '''
        CORRECT:
        {
            "openid":"OPENID",
            "nickname":"NICKNAME",
            "sex":1,
            "province":"PROVINCE",
            "city":"CITY",
            "country":"COUNTRY",
            "headimgurl": "http://wx.qlogo.cn/mmopen/g3MonUZtNHkdmzicIlibx6iaFqAc56vxLSUfpb6n5WKSYVY0ChQKkiaJSgQ1dZuTOgvLLrhJbERQQ4eMsv84eavHiaiceqxibJxCfHe/0",
            "privilege":[
            "PRIVILEGE1",
            "PRIVILEGE2"
            ],
            "unionid": " o6_bmasdasdsad6_2sgVt7hMZOPfL"

        }
        '''
        url = WxTkApi.API_DOMAIN + '/sns/userinfo'
        payload = {
            'access_token': access_token,
            'openid': openid,
            'lang': 'zh_CN',
        }

        try:
            r = requests.get(url, params=payload, timeout=4)
            res = r.json()
        except requests.exceptions.Timeout:
            raise WxTkApiErr('timeout', None)
        except Exception:
            raise WxTkApiErr('unknown', None)

        if not 'openid' in res:
            error_logger.error(u'get_sns_userinfo 报错 %s, access_token:%s, openid:%s', r.text, access_token, openid)
            raise WxTkApiErr('error', r.text)

        return res

    def get_user_info(self, access_token, openid):
        '''
        {
            "subscribe": 1,  # 1 表示用户关注过该公众号  0表示未关注
            "openid": "o6_bmjrPTlm6_2sgVt7hMZOPfL2M",
            "nickname": "Band",
            "sex": 1,
            "language": "zh_CN",
            "city": "广州",
            "province": "广东",
            "country": "中国",
            "headimgurl": "http://wx.qlogo.cn/mmopen/g3MonUZtNHkdmzicIlibx6iaFqAc56vxLSUfpb6n5WKSYVY0ChQKkiaJSgQ1dZuTOgvLLrhJbERQQ4eMsv84eavHiaiceqxibJxCfHe/0",
            "subscribe_time": 1382694957,
            "unionid": " o6_bmasdasdsad6_2sgVt7hMZOPfL",
            "remark": "",
            "groupid": 0
        }
        '''
        url = WxTkApi.API_DOMAIN + '/cgi-bin/user/info'
        payload = {
            'access_token': access_token,
            'openid': openid,
            'lang': 'zh_CN',
        }

        try:
            r = requests.get(url, params=payload, timeout=4)
            res = r.json()
        except requests.exceptions.Timeout:
            raise WxTkApiErr('timeout', None)
        except Exception:
            raise WxTkApiErr('unknown', None)

        return res


def get_wechat_sdk(absolute_url):
    """
    Get wechat sdk data pack.
    :param absolute_url:
    :return:
    """
    wechat_sdk = {}
    try:
        wxapi = WxTkApi()
        access_token = wxapi.get_access_token()
        jsapi_ticket = wxapi.get_jsapi_ticket(access_token)
        wxconfig = wxapi.get_jsapi_sign(jsapi_ticket, absolute_url)
        wechat_sdk['wechat_sdk'] = wxconfig
        wechat_sdk['wechat_sdk']['appId'] = settings.WX_APP_ID
    except Exception as e:
        error_logger.error(u'取微信签名报错 %s', e.message)
        wechat_sdk['wechat_sdk'] = {
            'nonceStr': '',
            'jsapi_ticket': '',
            'timestamp': '',
            'url': '',
            'appId': ''
        }
    return wechat_sdk
