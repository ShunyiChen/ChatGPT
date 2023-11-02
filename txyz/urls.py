from django.urls import path
from . import views

urlpatterns = [
    path('signin/', views.signin),
    path('signup/', views.signup),
    path('sign-out/', views.sign_out),
    path('get_settings/', views.get_settings),
    path('categories/', views.categories),
    path('feed/', views.feed),
    path('arxiv/', views.arxiv),
    path('post/', views.post),
    path('get/', views.get),
    path('conversations/', views.conversations),
    path('rename_conversation/', views.rename_conversation),
    path('del_conversation/', views.del_conversation),
    path('del_all_conversations/', views.del_all_conversations),
]