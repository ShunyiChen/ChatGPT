# 创建一个项目目录
mkdir ChatGPT-Server
----------------------------------
# 安装Django
pipenv install django
# 安装redis
pipenv install django-redis
# 安装JWT
pipenv install PyJWT
----------------------------------
# 激活
To activate this project's virtualenv, run `pipenv shell`.
# 创建项目
django-admin startproject chatgptserver .
# 迁移数据表
python manage.py migrate
# 创建超级管理员
python manage.py createsuperuser
admin/cDe3@wsx
# 启动项目
python manage.py runserver 9000
----------------------------------




架构
----
1.网站首页（openai时间定格在2023/10/25,随后改版再说）
2.登录
3.注册
4.OpenAI - 验证你的邮件
5.API抽象层（ChatGPT与TXZY等实现）

组件
----
Postgres, Redis, SMTP服务, 腾讯云, 域名, Nginx






