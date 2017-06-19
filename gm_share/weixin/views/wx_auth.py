# coding=utf-8
from urllib import urlencode

from django.views.generic.base import RedirectView

from base import TemplateView
from gm_share.weixin.wx import WxTkApi


class AuthView(RedirectView):
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        if 'code' in self.request.GET:
            code = self.request.GET['code']
            redirect_url = self.request.GET.get('redirect_url')

            try:
                res = WxTkApi().get_sns_access_token(code=code)
                sns_access_token = res['access_token']
                sns_openid = res['openid']
            except Exception as e:
                print 'get weixin open id failed: %s' % (str(e),)

            return redirect_url + '?' + urlencode({
                'openid': sns_openid,
                'access_token': sns_access_token,
                'from': 'weixin'
            })
        else:
            redirect_url = self.request.GET.get('redirect_url', '')
            if 'http' in redirect_url or 'https' in redirect_url:
                pass
            else:
                redirect_url = self.request.build_absolute_uri()
            auth_url = WxTkApi().get_auth_url(redirect_url, scope='snsapi_userinfo')

            return auth_url


class WeixinAuthBaseView(TemplateView):
    def stage_pre(self, ctx):
        super(WeixinAuthBaseView, self).stage_pre(ctx)
        source = ctx.request.GET.get('from')
        if source and source == 'weixin':
            openid = ctx.request.GET['openid']
            access_token = ctx.request.GET['access_token']
            wxapi = WxTkApi()
            weixin_user_info = wxapi.get_sns_userinfo(access_token, openid)
            nickname = weixin_user_info['nickname']
            try:
                nickname = ''.join([chr(ord(x)) for x in nickname]).decode('utf-8')
            except:
                pass
            weixin_user_info = {
                'nickname': nickname,
                'headimgurl': weixin_user_info['headimgurl'],
                'openid': weixin_user_info['openid']
            }

            # normal_accessk_token = wxapi.get_access_token()
            # user_info = wxapi.get_user_info(normal_accessk_token, openid)
            # if user_info and 'subscribe' in user_info:
            #     wechat_attention = True if user_info['subscribe'] == 1 else False
            # else:
            #     wechat_attention = False

            ctx['weixin_user_info'] = weixin_user_info
            ctx['wechat_attention'] = True

