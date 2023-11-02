import json

from django.contrib import auth
from django.shortcuts import render
from django.http import HttpResponse
from django.http.response import JsonResponse
from django.http import HttpResponseNotAllowed
from django.conf import settings
from django.middleware.csrf import get_token
from datetime import datetime
from django_redis import get_redis_connection
from django.core.cache import cache
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from django.contrib.auth.models import User
import requests
import uuid

# Create your views here.
con = get_redis_connection("default")

# 状态码
SUCCESS = 0
ERROR = 1


# 时间标签


# 登录
@api_view(['POST'])
def signin(request):
    username = request.data.get('username')
    pwd = request.data.get('password')
    # content = {
    #     'user': str(request.user),  # `django.contrib.auth.User` instance.
    #     'auth': str(request.auth),  # None
    # }
    try:
        user = auth.authenticate(username=username, password=pwd)
        old_token = Token.objects.filter(user=user)
        old_token.delete()
        token = Token.objects.create(user=user)
        print(token.key)
        return JsonResponse({'Output': 'Signin Successfully', 'Status': SUCCESS})
    except Exception as e:
        return JsonResponse({'Output': 'Please enter the correct username and password for a staff account. Note that '
                                       'both fields may be case-sensitive.', 'Status': ERROR})


@api_view(['POST'])
def sign_out(request):
    auth = request.META.get('HTTP_AUTHORIZATION', b'')
    if auth is not None:
        # 删除表Token
        token = Token.objects.filter(key=auth)
        token.delete()
        # 删除缓存
        con.delete('token:' + str(auth))
    return JsonResponse({'Output': 'Sign out Successfully', 'Status': SUCCESS})


@api_view(['POST'])
def signup(request):
    print(str(request.user), ' will be logged out')
    username = request.data.get('username')
    password = request.data.get('password')
    if username is None or password is None:
        return JsonResponse(
            {'Output': 'Please enter the correct username and password for a staff account', 'Status': ERROR})
    else:
        try:
            u = User.objects.get(username=username)
            if u is not None:
                return JsonResponse({'Output': 'User already exist', 'Status': ERROR})
        except User.DoesNotExist:
            user = User.objects.create_user(username, username, password)
            user.save()
            return JsonResponse({'Output': 'Register Successfully', 'Status': SUCCESS})


# 取设置信息
@api_view(['POST'])
def get_settings(request):
    if request.user.is_authenticated:
        values = con.hget("settings", "version")
        return JsonResponse({'Output': values.decode('utf-8'), 'Status': SUCCESS})
    else:
        return JsonResponse({'Output': 'Unauthorized', 'Status': ERROR})


@api_view(['GET'])
def categories(request):
    if request.user.is_authenticated:
        x = requests.get('https://txyz.ai/api/feed/categories')
        return JsonResponse({'Output': x, 'Status': SUCCESS})
    else:
        return JsonResponse({'Output': 'Unauthorized', 'Status': ERROR})


@api_view(['GET'])
def feed(request):
    if request.user.is_authenticated:
        x = requests.get('https://txyz.ai/api/feed/feed?code_name=cs.AI')
        return JsonResponse({'Output': x.json(), 'Status': SUCCESS})
    else:
        return JsonResponse({'Output': 'Unauthorized', 'Status': ERROR})


@api_view(['POST'])
def arxiv(request):
    if request.user.is_authenticated:
        x = requests.post('https://txyz.ai/api/upload/arxiv', data=request.data)
        return JsonResponse({'Output': x.json(), 'Status': SUCCESS})
    else:
        return JsonResponse({'Output': 'Unauthorized', 'Status': ERROR})


@api_view(['POST'])
def post(request):
    global x
    if request.user.is_authenticated:
        paper_id = request.data.get('paper_id')
        query = request.data.get('query')
        chat_history = []
        arxiv_id = request.data.get('arxiv_id')
        new_chat = request.data.get('new_chat')
        chat_id = request.data.get('chat_id')
        if new_chat:
            chat_id = str(uuid.uuid4())
            con.hset("chats", f"chat:{chat_id}:{str(request.user)}",
                     json.dumps({'text': query, 'date_created': str(datetime.now())}))
        # else:
        #     # 准备chat_history
        #     sorted_messages = []
        #     for i in con.hscan_iter("messages", match="message:*:" + chat_id):
        #         obj = json.loads(i[1])
        #         sorted_messages.append(obj)
        #     # 按创建日期排序
        #     sorted_messages = sorted(sorted_messages, key=lambda p: p['date_created'], reverse=False)
        #     d = None
        #     for index, obj in enumerate(sorted_messages):
        #         if index % 2 == 0:
        #             d = json.loads(json.dumps({"question": "", "response": ""}))
        #             chat_history.append(d)
        #         if obj['role'] == 'user':
        #             d['question'] = obj['text']
        #         elif obj['role'] == 'assistant':
        #             d['response'] = obj['text']
        #
        #     print('chat_history=',chat_history)

        # 先插入自己的问题
        message_id = str(uuid.uuid4())
        con.hset("messages", f"message:{message_id}:{chat_id}",
                 json.dumps({'role': 'user', 'text': query, 'date_created': str(datetime.now())}))
        # 请求外部服务
        try:
            data = {'paper_id': paper_id, 'query': query, "chat_history": chat_history, 'arxiv_id': arxiv_id}
            x = requests.post('https://txyz.ai/api/paper/chat', data=data)
        except Exception as e:
            # 再插入机器意外的回答
            message_id = str(uuid.uuid4())
            con.hset("messages", f"message:{message_id}:{chat_id}",
                     json.dumps({'role': 'assistant', 'text': '[Error]Something went wrong. Please try again later.',
                                 'date_created': str(datetime.now())}))

        # 再插入机器的回答
        message_id = str(uuid.uuid4())
        con.hset("messages", f"message:{message_id}:{chat_id}",
                 json.dumps({'role': 'assistant', 'text': x.text, 'date_created': str(datetime.now())}))

        return JsonResponse({'Output': x.text, 'Status': SUCCESS})
    else:
        return JsonResponse({'Output': 'Unauthorized', 'Status': ERROR})


# 获取conversation内容
@api_view(['POST'])
def get(request):
    if request.user.is_authenticated:
        models = []
        chat_id = request.data.get('chat_id')
        for i in con.hscan_iter("messages", match="message:*:" + chat_id):
            message_id = str(i[0]).split(':')[1]
            message = json.loads(i[1])
            # 添加message_id属性
            message['message_id'] = message_id
            models.append(message)
        # 正序排序
        sorted_models = sorted(models, key=lambda p: p['date_created'], reverse=False)
        return JsonResponse({'Output': sorted_models, 'Status': SUCCESS})
    else:
        return JsonResponse({'Output': 'Unauthorized', 'Status': ERROR})


@api_view(['POST'])
def conversations(request):
    if request.user.is_authenticated:
        print(str(request.user))
        user_id = str(request.user)
        conversation_list = []
        for i in con.hscan_iter("chats", match="chat:*:" + user_id):
            chat = json.loads(i[1])
            # 截取chat_id
            chat_id = str(i[0]).split(':')[1]
            # 追加chat_id属性
            chat['chat_id'] = chat_id
            conversation_list.append(chat)
        # # 正序排序
        sorted_conversations = sorted(conversation_list, key=lambda p: p['date_created'], reverse=True)
        return JsonResponse({'Output': sorted_conversations, 'Status': SUCCESS})
    else:
        return JsonResponse({'Output': 'Unauthorized', 'Status': ERROR})


# 重命名conversation
@api_view(['POST'])
def rename_conversation(request):
    if request.user.is_authenticated:
        user_id = str(request.user)
        chat_id = request.data.get('chat_id')
        # 取新名称
        new_name = request.data.get('new_name')
        old_chat = con.hget("chats", "chat:" + chat_id + ":" + user_id)
        new_chat = json.loads(old_chat)
        new_chat['text'] = new_name
        con.hset("chats", "chat:" + chat_id + ":" + user_id, json.dumps(new_chat))
        return JsonResponse({'Output': 'success', 'Status': SUCCESS})
    else:
        return JsonResponse({'Output': 'Unauthorized', 'Status': ERROR})


# 删除单个conversation
@api_view(['DELETE'])
def del_conversation(request):
    if request.user.is_authenticated:
        user_id = str(request.user)
        chat_id = request.data.get('chat_id')
        if con.hexists("chats", "chat:" + chat_id + ":" + user_id):
            # 删除conversation下所有Message
            for i in con.hscan_iter("messages", match="message:*:" + chat_id):
                message_id = str(i[0]).split(':')[1]
                if con.hexists("messages", "message:" + message_id + ":" + chat_id):
                    con.hdel("messages", "message:" + message_id + ":" + chat_id)
            # 删除conversation
            con.hdel("chats", "chat:" + chat_id + ":" + user_id)
        return JsonResponse({'Output': 'success', 'Status': SUCCESS})
    else:
        return JsonResponse({'Output': 'Unauthorized', 'Status': ERROR})


# 删除全部conversations
@api_view(['DELETE'])
def del_all_conversations(request):
    if request.user.is_authenticated:
        user_id = str(request.user)
        for i in con.hscan_iter("chats", match="chat:*:" + user_id):
            chat_id = str(i[0]).split(':')[1]
            if con.hexists("chats", "chat:" + chat_id + ":" + user_id):
                # 删除conversation下所有Message
                for j in con.hscan_iter("messages", match="message:*:" + chat_id):
                    message_id = str(j[0]).split(':')[1]
                    if con.hexists("messages", "message:" + message_id + ":" + chat_id):
                        con.hdel("messages", "message:" + message_id + ":" + chat_id)
                # 删除conversation
                con.hdel("chats", "chat:" + chat_id + ":" + user_id)
        return JsonResponse({'Output': 'success', 'Status': SUCCESS})
    else:
        return JsonResponse({'Output': 'Unauthorized', 'Status': ERROR})
