# coding=utf-8


class Enum(object):
    def __init__(self, rels):
        self._rels = rels
        for r in rels:
            key, sym, desc = r
            assert sym[0].isupper()
            setattr(self, sym, key)

    def __getitem__(self, item):
        for r in self._rels:
            rkey, rsym, rdesc = r
            if rsym == item:
                return rkey

    @property
    def keys(self):
        keys = []
        for r in self._rels:
            key, sym, desc = r
            keys.append(key)
        return keys

    def desc_from_key(self, key):
        for r in self._rels:
            rkey, rsym, rdesc = r
            if rkey == key:
                return rdesc

    def __contains__(self, k):
        if self.desc_from_key(k): return True
        return False


# 平台类型
PLATFORM_TYPE = Enum([
    (0, "IOS", u"ios"),
    (1, "ANDROID", u"android"),
    (2, "PC", u"pc"),
    (10, "UNKNOWN", u'unknown')
])


RPC_ERROR_CODE = Enum([
    (9, 'OPERATION_NOT_SUPPORTED', u'操作不允许'),
    (401, 'LOGIN_REQUIRED', u'登录过期，请重新登录'),

    (15430, "COUPON_IS_EMPTY", u'美券已抢完'),
    (15431, "COUPON_CLAIMED", u'美券已被他人领走'),
    (15432, "COUPON_DOES_NOT_EXIST", u'美券不存在'),
    (15433, "COUPON_LAUNCH_DOES_NOT_EXIST", u"该美券投放信息不存在"),
    (15434, "COUPON_YOU_HAVE_GOT_ONE", u"已经领取过此次的美券"),
    (15435, "COUPON_UNAVAILABLE", u'美券无效'),
    (16000, "GAME_GODDESS_BEYOND_LIMIT", u'已达到优惠上限'),
    (16001, "GAME_GODDESS_HAS_PARTICIPATED", u"已砍过"),

    (20006, 'TOPIC_REPLY_NOT_FOUND', u'该回复被所长关小黑屋了'),
    (20007, 'TOPIC_REPLY_HAS_VOTED', u'已经赞过啦'),
    (20001, 'TOPIC_NOT_FOUND', u'该帖子被所长关小黑屋了'),
    (20008, 'TOPIC_HAS_VOTED', u'已经赞过啦'),

    (22001, 'INVALID_CODE', u'请输入正确验证码'),
    (22002, "PHONE_PASSWORD_INVALID", u'请输入正确信息'),
    (22003, "PLEASE_RESET_PASSWORD", (u'该手机号还未设置过密码，'
                                      u'请使用验证码登录，然后设置密码')),
    (23001, "PERSON_EXIST", u'该手机号已注册过更美'),
    (23002, 'PERSON_NOT_FOUND', u'该手机号未注册过更美，请先注册'),

    (42004, "COUPON_HAS_BEEN_USED", u"美券已经被使用"),
    (44001, "SECKILL_UNAVAILABLE", u"对不起，秒杀已结束"),

    (99003, "USER_MAX_RETIES", u'达到最大尝试次数'),
])