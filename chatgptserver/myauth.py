import datetime

import pytz
from django.utils.translation import gettext_lazy
from rest_framework.authentication import BaseAuthentication
from rest_framework import exceptions
from rest_framework.authtoken.models import Token
from rest_framework import HTTP_HEADER_ENCODING
from django_redis import get_redis_connection
import pickle

# 连接Redis
con = get_redis_connection("default")


# 获取请求头信息
def get_authorization_header(request):
    """
    Return request's 'Authorization:' header, as a bytestring.

    Hide some test client ickyness where the header can be unicode.
    """
    auth = request.META.get('HTTP_AUTHORIZATION', b'')
    if isinstance(auth, type('')):
        # Work around django test client oddness
        auth = auth.encode(HTTP_HEADER_ENCODING)
    return auth


# 自定义认证方式，这个是后面要添加到设置文件的
class ExpiringTokenAuthentication(BaseAuthentication):
    model = Token

    def authenticate(self, request):
        auth = get_authorization_header(request)
        if not auth:
            return None
        try:
            token = auth.decode()
        except UnicodeError:
            msg = gettext_lazy('Invalid token header. Token string should not contain invalid characters.')
            raise exceptions.AuthenticationFailed(msg)

        return self.authenticate_credentials(token)

    def authenticate_credentials(self, key):
        token_cache = 'token:' + key
        cache_user = con.get(token_cache)
        if cache_user:
            t = pickle.loads(cache_user)
            return t.user, t  # 首先查看token是否在缓存中，若存在，直接返回用户
        try:
            token = self.model.objects.get(key=key)
        except self.model.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid token')

        if not token.user.is_active:
            raise exceptions.AuthenticationFailed('User inactive or deleted')

        print('token.created = ',token.created)
        print('datetime.datetime.now() = ', datetime.datetime.now())
        if token.created < datetime.datetime.now() - datetime.timedelta(hours=1):  # 设定存活时间1小时
            raise exceptions.AuthenticationFailed('Token has expired')

        if token:
            token_cache = 'token:' + key
            pickled_token = pickle.dumps(token)
            con.set(token_cache, pickled_token, 1 * 60 * 60)  # 缓存token1个小时

        return token.user, token

    def authenticate_header(self, request):
        return 'Token'
