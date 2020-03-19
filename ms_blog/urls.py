from django.conf.urls import url, include
from django.contrib import admin
from blog import views
from django.views.static import serve
from django.conf.urls.static import static
from ms_blog import settings


urlpatterns = [
    # 首页
    url(r'^$', views.home),
    url(r'^home/', views.home),

    # 后台管理
    url(r'^xadmin/', admin.site.urls),

    # 注册
    url(r'^register/', views.register),

    # 登陆
    url(r'^login/', views.login),

    # 图片验证码相关
    url(r'^get_code/', views.get_code),

    # 注销
    url(r'^logout/', views.logout),
    # 修改密码
    url(r'^set_password/', views.set_password),

    # 暴露给外界的后端文件资源
    url(r'^media/(?P<path>.*)', serve, {'document_root': settings.MEDIA_ROOT}),

    # 点赞点踩
    url(r'^UpAndDown/', views.UpAndDown),

    # 评论
    url(r'^comment/', views.comment),

    # markdown 编辑器用的
    url(r'mdeditor/', include('mdeditor.urls')),

    ## 后台管理
    # 后台主页
    url(r'^backend/', views.backend, name='backend'),
    # 添加文章
    url(r'^add_article/', views.add_article),
    # 添加分类
    url('^add_category/', views.add_category, name='add_category'),
    # 分类管理
    url('^category/', views.category, name='category'),
    # 评论管理
    url('^a_comment/', views.a_comment, name='a_comment'),

    # 文本编辑器上传图片
    url(r'^upload_img/', views.upload_img),

    # 搜索
    url(r'^serach/', views.serach),

    # 修改用户头像
    url(r'^set_img/', views.set_img),

    # 个人站点
    url(r'^(?P<username>\w+)/$', views.site),

    # 创建个人站点
    url(r'^(?P<username>\w+)/create_blog', views.create_blog),

    # 侧边栏筛选功能
    url(r'^(?P<username>\w+)/(?P<condition>category|tag|archive)/(?P<param>.*)/', views.site),

    # 文章详情页
    url(r'^(?P<username>\w+)/article/(?P<article_id>\d+)/', views.article_detail),
    # 编辑问掌柜
    url('^edit_article/(\d+)/', views.edit_article, name='edit_article'),
    # 删除文章
    url('^del_article/(\d+)/', views.del_article, name='del_article'),
    # 编辑分类
    url('^edit_category/(\d+)/', views.edit_category, name='edit_category'),
    # 删除分类
    url('^del_category/(\d+)/', views.del_category, name='del_category'),
    # 删除评论
    url('^del_comment/(\d+)/', views.del_comment, name='del_comment'),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
