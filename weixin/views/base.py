# coding=utf-8

from __future__ import unicode_literals

import sys
import re
import json
import time
import traceback
import inspect
from urllib import urlencode
import six

from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.conf import settings, urls
from django.core.urlresolvers import reverse

import helios.rpc
from helios.rpc.exceptions import RPCFaultException
from gm_logging.django.middleware import get_client_info_of_request
from gm_types.error import ERROR

from libs.rpc import get_base_rpc_invoker
from libs.redis_db import db as cache
from libs.log import error_logger, exception_logger, info_logger
from weixin.wx import WxTkApi, WxTkApiErr
from commons.common import *
from commons.enums import RPC_ERROR_CODE


_context_key = '_the_long_long_long_name_for_dict'


class Context(object):
    def __init__(self):
        self.__dict__[_context_key] = dict()

    def __getitem__(self, item):
        return self.__dict__[_context_key][item]

    def __setitem__(self, key, value):
        self.__dict__[_context_key][key] = value

    def __delitem__(self, key):
        del self.__dict__[_context_key][key]

    def __getattr__(self, item):
        try:
            return self.__dict__[_context_key][item]
        except KeyError:
            raise AttributeError(item)

    def __setattr__(self, key, value):
        self.__dict__[_context_key][key] = value

    def __delattr__(self, item):
        del self.__dict__[_context_key][item]


def extract_context(obj):
    if obj is None:
        return obj
    if isinstance(obj, (int, float)):
        return obj
    if isinstance(obj, six.string_types):
        return obj
    if isinstance(obj, dict):
        return dict((extract_context(k), extract_context(v)) for k, v in obj.items())
    if isinstance(obj, (list, tuple)):
        return [extract_context(x) for x in obj]
    if isinstance(obj, Context):
        return extract_context(getattr(obj, _context_key))
    if isinstance(obj, helios.rpc.RPCResult):
        try:
            return ['RPCResult', obj.unwrap()]
        except:
            exc_type, exc_value, exc_trace = sys.exc_info()
            return {
                'exc-type': extract_context(exc_type),
                'exc-value': extract_context(exc_value),
                'traceback': extract_context(exc_trace)
            }
    if inspect.istraceback(obj):
        return extract_context(traceback.extract_tb(obj))
    return repr(obj)


def get_url_patterns_from_modules(prefix, modules):
    view_class_list = []
    for m in modules:
        for c in m.__dict__.values():
            if not inspect.isclass(c):
                continue
            mro = inspect.getmro(c)
            for base in mro:
                if base == BaseView:
                    view_class_list.append(c)
    url_entry_list = []
    for c in view_class_list:
        url_entry = c.as_url_entry()
        if url_entry is None:
            continue
        url_entry_list.append(url_entry)
    return urls.patterns(prefix, *url_entry_list)


class FastHttpResponse(Exception):
    def __init__(self, response):
        self.response = response


class BaseView(object):
    disabled = False
    url_regex = None
    url_name = None
    url_kwargs = None

    methods = (
        'get', 'post',
    )

    stage_list = (
        'pre!', 'init', 'fetch', 'transform', 'decorate!', 'render', 'response!', 'post!',
    )

    decorators = ()

    def get_error_message_from_errorcode(self, code, default=u'服务器开小差啦~'):
        return ERROR.getDesc(code, default)

    def set_track(self, ctx, *args, **kwargs):
        """
        Set track：埋点
        :param ctx:
        :param args:
        :return:
        """
        data = {}
        for k in args:
            v = ctx.request.GET.get(k) or ctx.request.POST.get(k)
            if v:
                data.update({k: v})

        for k, v in kwargs.items():
            data.update({k: v})
        ctx.request.logger.app(**data)

    def stage_pre(self, ctx):
        pass

    def handle_init(self, ctx, *args, **kwargs):
        return {}

    def stage_init(self, ctx):
        return self.handle_init(ctx, *ctx.args, **ctx.kwargs)

    def stage_fetch(self, ctx):
        return {}

    def stage_transform(self, ctx):
        return {}

    def stage_decorate(self, ctx):
        return ctx.transform

    def stage_render(self, ctx):
        pass

    def stage_response(self, ctx):
        ctx.response = ctx.render

    def stage_post(self, ctx):
        pass

    def run_stage(self, stage, ctx):
        proc = False
        if stage.endswith('!'):
            stage = stage[:-1]
            proc = True
        func = getattr(self, 'stage_' + stage)
        ret = func(ctx)
        if not proc:
            ctx[stage] = ret
            ctx.prev = ret

    def process(self, ctx):
        for stage in self.stage_list:
            self.run_stage(stage, ctx)

    def dispatch_ctx(self, ctx):
        try:
            self.process(ctx)
        except RPCFaultException as e:
            # global handle rpc 401 Login Required error
            if e.error == RPC_ERROR_CODE.LOGIN_REQUIRED:
                is_ajax = 'HTTP_X_REQUESTED_WITH' in ctx.request.META
                if is_ajax:
                    ctx.response = json_http_response(login_required_data)
                else:
                    ctx.response = HttpResponseRedirect(_login_url(ctx))
            else:
                raise
        except FastHttpResponse as e:
            ctx.response = e.response

    def __call__(self, request, *args, **kwargs):
        if request.method.lower() not in self.methods:
            return HttpResponse(status=405, content='Method Not Allowed')  # 405 Method Not Allowed
        ctx = Context()
        ctx.request = request
        ctx.args = args
        ctx.kwargs = kwargs
        self.ctx = ctx
        try:
            ctx.logger = request.logger
        except AttributeError:
            pass
        self.dispatch_ctx(ctx)
        return ctx.response

    def __init__(self):
        if self.disabled:
            raise Exception("View disabled.")
        if isinstance(self.methods, six.string_types):
            self.methods = [self.methods]
            self.methods = [x.lower() for x in self.methods]

    @classmethod
    def as_view(cls):
        return cls()

    @classmethod
    def as_url_entry(cls):
        if cls.disabled:
            return None
        view = cls.as_view()
        if view.url_regex is None:
            return None
        regex = view.url_regex
        kwargs = view.url_kwargs or dict()
        if view.url_name is not None:
            assert 'name' not in kwargs
            kwargs['name'] = view.url_name

        for decor in cls.decorators[::-1]:
            view = decor(view)

        return urls.url(regex, view, **kwargs)

    def gen(self, content):
        raise FastHttpResponse(
            HttpResponse(content=json.dumps(content), content_type="application/json; charset=UTF-8"))


class CommonView(BaseView):

    def stage_pre(self, ctx):
        super(CommonView, self).stage_pre(ctx)
        req = ctx.request

        session_key = req.COOKIES.get(Config.session_cookie_name) or None
        ctx.session_key = session_key
        ctx.has_login = session_key is not None

        client_info = get_client_info_of_request(req)

        ctx.rpc = get_base_rpc_invoker().with_config(
            session_key=session_key,
            client_info=client_info,
        )

        self.is_hybrid = False
        ctx.is_hybrid = False

        # compitable with client vesion under 4.5
        self.support_new_tags = support_new_tags(ctx.request)

        # 根据UA判断是iOS还是Android
        user_agent = ctx.request.META.get('HTTP_USER_AGENT')
        ctx.user_agent = user_agent

        def get_client_and_platform(user_agent=None):
            from_client = False
            platform = None
            if re.search(r'Gengmei', user_agent, re.IGNORECASE):
                from_client = True
            if re.search(r'gmdoctor', user_agent, re.IGNORECASE):
                from_client = True

            if (
                    re.search(r'iPhone', user_agent, re.IGNORECASE) or
                    re.search(r'iPad', user_agent, re.IGNORECASE)
            ):
                platform = PLATFORM_TYPE.IOS
            elif re.search(r'Android', user_agent, re.IGNORECASE):
                platform = PLATFORM_TYPE.ANDROID
            else:
                platform = PLATFORM_TYPE.PC
            return platform, from_client
        if not user_agent:
            ctx.platform = PLATFORM_TYPE.UNKNOWN
            ctx.from_client = False
        else:
            ctx.platform, ctx.from_client = get_client_and_platform(user_agent)

    if settings.DEBUG:
        def dispatch_ctx(self, ctx):
            debug = 'debug' in ctx.request.GET
            debug_item = ctx.request.GET.get('debug', None)
            try:
                super(CommonView, self).dispatch_ctx(ctx=ctx)

            except helios.rpc.RPCSystemException as e:
                if not e.http_response:
                    raise

                ctx.response = HttpResponse(
                    e.http_response.text,
                    content_type=e.http_response.content_type
                )
                return

            except:
                traceback.print_exc()
                ctx.dispatch = sys.exc_info()
                if not debug:
                    raise

            if debug:
                if debug_item == 'data':
                    debug_object = ctx.transform
                else:
                    try:
                        del ctx.prev
                    except:
                        pass
                    ctx.allowed_methods = self.methods
                    ctx.stage_list = self.stage_list
                    debug_object = extract_context(ctx)
                try:
                    debug_output = json.dumps(
                        debug_object,
                        ensure_ascii=False,
                        allow_nan=True,
                        indent=4,
                        sort_keys=True
                    )
                except:
                    debug_output = json.dumps(
                        debug_object,
                        ensure_ascii=True,
                        allow_nan=True,
                        indent=4,
                        sort_keys=True
                    )

                ctx.response = HttpResponse(
                    content=debug_output,
                    content_type='application/json; charset=utf-8'
                )


def _login_url(ctx):
    login = reverse('login')
    if ctx.request.method.lower() == 'get':
        location = login + '?' + urlencode([('next_url', ctx.request.get_full_path())])
    else:
        location = login
    print(location)
    return location


class TemplateView(CommonView):
    template = None
    template_smart_lookup = False
    # 是否返回微信签名 默认不返回
    return_weixin_config = False

    def stage_pre(self, ctx):
        super(TemplateView, self).stage_pre(ctx)
        ctx.template = self.template

    def stage_decorate(self, ctx):
        obj = ctx.prev
        obj['url_base'] = Config.url_base
        obj['tdk'] = self.build_tdk(ctx)
        obj['config'] = {
            'url_base': Config.url_base,
            'has_login': ctx.session_key is not None,
        }

        if ctx.session_key:
            try:
                user_info = ctx.rpc['api/user_info']().unwrap()
                obj['current_user'] = user_info['user_id']
            except:
                obj['current_user'] = None
        else:
            obj['current_user'] = None

        if self.return_weixin_config:
            try:
                wxapi = WxTkApi()
                access_token = wxapi.get_access_token()
                jsapi_ticket = wxapi.get_jsapi_ticket(access_token)
                wxconfig = wxapi.get_jsapi_sign(jsapi_ticket, ctx.request.build_absolute_uri())
                obj['wechat_sdk'] = wxconfig
                obj['wechat_sdk']['appId'] = settings.WX_APP_ID
            except Exception as e:
                error_logger.error(u'取微信签名报错 %s', e.message)
                obj['wechat_sdk'] = {
                    'nonceStr': '',
                    'jsapi_ticket': '',
                    'timestamp': '',
                    'url': '',
                    'appId': ''
                }

        channel = ctx.request.COOKIES.get(Config.channel_cookie_name)
        obj['download_url'] = get_download_url_from_channel(channel, ctx.platform)

    def stage_render(self, ctx):
        obj = ctx.prev
        return render(ctx.request, ctx.template, obj)

    def build_tdk(self, ctx):
        return settings.TDK


class AuthenticatedTemplateView(TemplateView):
    def stage_pre(self, ctx):
        super(AuthenticatedTemplateView, self).stage_pre(ctx)

        # TODO: Handle POST method
        if not ctx.has_login:
            raise FastHttpResponse(HttpResponseRedirect(_login_url(ctx)))


class JsonView(CommonView):
    def stage_render(self, ctx):
        obj = ctx.prev
        output_data = json.dumps(obj)
        return HttpResponse(content=output_data)


class AuthenticatedJsonView(JsonView):
    methods = ('get', 'post')

    def stage_pre(self, ctx):
        super(AuthenticatedJsonView, self).stage_pre(ctx)
        if not ctx.has_login:
            raise FastHttpResponse(json_http_response(login_required_data))


def json_http_response(result, status=200):
    return HttpResponse(json.dumps(result),
                        content_type="application/json; charset=UTF-8", status=status)


class WeixinLoginRequiredMixin(object):
    """all weixin login required view should inherite this base."""

    _wx_session_key = 'wxsid'

    def _redirect_to_authurl(self):
        redirect_url = self.ctx.request.build_absolute_uri()
        redirect_url = WxTkApi().get_auth_url(redirect_url, scope='snsapi_userinfo')
        raise FastHttpResponse(HttpResponseRedirect(redirect_url))

    def save_accesstoken_to_session(self, at):
        self.ctx.request.session[self._wx_session_key] = json.dumps(at)

    def accesstoken_valid(self, at):
        born_at = at['born_at']
        now = time.time()
        if born_at + at['expires_in'] < now:
            try:
                refresh_token = at['refresh_token']
                res = WxTkApi().get_accesstoken_by_refresh(refresh_token=refresh_token)
                res = self._update_accesstoken(res)
                self.save_accesstoken_to_session(res)
                return True
            except Exception as e:
                exception_logger.error(e)
                return False

        return True

    def _update_accesstoken(self, at):
        # add extra 1 mins, so the token will be invalid in advance
        now = int(time.time()) + 60
        at['born_at'] = now
        return at

    def _clean_session(self):
        try:
            del self.ctx.request.session[self._wx_session_key]
        except:
            pass

    def auth(self):
        # if debug mode and has query args nologin, dont call weixin auth
        if settings.DEBUG and 'nologin' in self.ctx.request.GET:
            self.wx_openid = 'hackersjoke'
            return

        # try to get token from session
        access_token = self.ctx.request.session.get(self._wx_session_key)
        if access_token:
            access_token = json.loads(access_token)

        elif 'code' in self.ctx.request.GET:
            # check is callback from weixin
            try:
                code = self.ctx.request.GET.get('code')
                res = WxTkApi().get_sns_access_token(code=code)
                res = self._update_accesstoken(res)
                self.save_accesstoken_to_session(res)
                access_token = res
            except WxTkApiErr as e:
                exception_logger.error(e)
                self._redirect_to_authurl()

            # first time in, log userinfo
            try:
                user_data = WxTkApi().get_sns_userinfo(access_token['access_token'], access_token['openid'])
                info_logger.info(user_data)
            except Exception as e:
                exception_logger.error(e)

        else:
            # can not find accesstoken from session, and no code found, ask use to auth
            self._redirect_to_authurl()

        if not self.accesstoken_valid(access_token):
            # delete session
            self._clean_session()

            # return redirect auth url directly
            self._redirect_to_authurl()

        # here we are ok to use wx accesstoken
        self.wx_openid = access_token['openid']


class WexinLoginRequiredTemplateView(TemplateView, WeixinLoginRequiredMixin):
    def stage_pre(self, ctx):
        self.auth()
        super(WexinLoginRequiredTemplateView, self).stage_pre(ctx)


class WexinLoginRequiredJsonView(JsonView, WeixinLoginRequiredMixin):
    def stage_pre(self, ctx):
        self.auth()
        super(WexinLoginRequiredJsonView, self).stage_pre(ctx)


class CacheMixinForHtml(object):

    def get_page_cache_key(self, key_suffix=''):
        return 'c:%s:ps:%s' % (self.url_name, key_suffix)

    def return_from_cache_direclty(self, key_suffix=''):
        """get cached page from cache.

        NOTE: this will raise FastHttpResponse
        """
        k = self.get_page_cache_key(key_suffix)
        html = cache.get(k)
        if html:
            #raise FastHttpResponse(HttpResponse(html))
            pass

    def cache_render_page(self, ctx, seconds, key_suffix=''):
        """cache rendered html to redis."""
        k = self.get_page_cache_key(key_suffix)
        cache.setex(k, seconds, ctx.render.content)
