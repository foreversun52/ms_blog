from django.shortcuts import render, HttpResponse, redirect
from blog import myforms
from blog import models
from django.http import JsonResponse
from django.contrib import auth
from django.contrib.auth.decorators import login_required
from PIL import Image, ImageDraw, ImageFont
import random
from io import BytesIO
from utils.mypage import Pagination
import json
from django.db.models import F
from django.utils.safestring import mark_safe
from django.db import transaction
from bs4 import BeautifulSoup
from ms_blog import settings
import os


# Create your views here.
def register(request):
    # 产生一个空对象
    form_obj = myforms.MyRegForm()
    if request.method == 'POST':
        back_dic = {'code': 1000, 'msg': ''}
        # 校验数据
        form_obj = myforms.MyRegForm(request.POST)
        if form_obj.is_valid():
            clean_data = form_obj.cleaned_data
            clean_data.pop('confirm_password')  # {'username':'','password':'','email':''}
            file_obj = request.FILES.get('avatar')
            """
            获取用户上传到头像之后 一定要做判断 判断用户是否上传了  如果没有上传  字典中就不加avatar键值对
            """
            if file_obj:
                clean_data['avatar'] = file_obj
            models.UserInfo.objects.create_user(**clean_data)
            back_dic['url'] = '/login/'
        else:
            back_dic['code'] = 2000
            back_dic['msg'] = form_obj.errors
        return JsonResponse(back_dic)
    return render(request, 'register.html', locals())


def login(request):
    if request.method == 'POST':
        back_dic = {'code': 1000, 'msg': ''}
        username = request.POST.get('username')
        password = request.POST.get('password')
        code = request.POST.get('code')
        # 1 先校验验证码是否正确
        if request.session.get('code').upper() == code.upper():
            # 2 校验用户名和密码是否正确
            user_obj = auth.authenticate(username=username, password=password)
            if user_obj:
                # 3 保存用户登录状态
                auth.login(request, user_obj)
                back_dic['url'] = '/home/'
            else:
                back_dic['code'] = 2000
                back_dic['msg'] = '用户名或密码错误'
        else:
            back_dic['code'] = 3000
            back_dic['msg'] = '验证码错误'
        return JsonResponse(back_dic)
    return render(request, 'login.html')


def get_random():
    return random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)


# 图片验证码相关
def get_code(request):
    img_obj = Image.new('RGB', (310, 35), get_random())
    img_draw = ImageDraw.Draw(img_obj)  # 生成一个画笔对象
    img_font = ImageFont.truetype('static/font/111.ttf', 30)  # 字体的样式

    # 随机生成验证码  a~z  A~Z  0~9
    code = ''
    for i in range(5):
        random_upper = chr(random.randint(65, 90))
        random_lower = chr(random.randint(97, 122))
        random_int = str(random.randint(0, 9))
        temp = random.choice([random_upper, random_lower, random_int])
        # 将产生的随机字符写到图片上
        img_draw.text((i * 45 + 45, 0), temp, get_random(), img_font)
        code += temp
    print(code)
    # 将随机验证码存储取来  以便其他函数调用
    request.session['code'] = code

    io_obj = BytesIO()
    img_obj.save(io_obj, 'png')
    return HttpResponse(io_obj.getvalue())


def home(request):
    # 将当前网站上的所有的文章全部展示到前端页面
    article_list = models.Article.objects.all()
    page_obj = Pagination(current_page=request.GET.get('page', 1), all_count=article_list.count())
    page_queryset = article_list[page_obj.start:page_obj.end]
    return render(request, 'home.html', locals())


def serach(request):
    keyword = request.GET.get('keyword')
    # 忽略大小写的模糊查询
    serach_list = models.Article.objects.filter(title__icontains=keyword)
    page_obj = Pagination(current_page=request.GET.get('page', 1), all_count=serach_list.count())
    page_queryset = serach_list[page_obj.start:page_obj.end]
    return render(request, 'serach.html', locals())


@login_required
def logout(request):
    # 删除用户session信息
    auth.logout(request)  # request.session.flush()
    return redirect('/login/')


@login_required
def set_password(request):
    if request.is_ajax():
        back_dic = {'code': 1000, 'msg': ''}
        if request.method == 'POST':
            old_password = request.POST.get('old_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            # 校验两次密码是否一致
            if new_password == confirm_password:
                # 先校验旧密码是否正确
                is_right = request.user.check_password(old_password)
                if is_right:
                    request.user.set_password(new_password)
                    request.user.save()
                    back_dic['url'] = '/login/'
                else:
                    back_dic['code'] = 2000
                    back_dic['msg'] = '原密码错误'
            else:
                back_dic['code'] = 3000
                back_dic['msg'] = '两次密码不一致'
            return JsonResponse(back_dic)


def site(request, username, **kwargs):
    user_obj = models.UserInfo.objects.filter(username=username).first()
    if not user_obj:
        # 返回一个404页面
        return render(request, 'errors.html')
    blog = user_obj.blog
    if blog:
        # 查询当前用户所有的文章数
        article_list = models.Article.objects.filter(blog=blog)
        """侧边栏筛选功能 其实就是对上面的article_list再做一层筛选而已"""
        if kwargs:
            condition = kwargs.get('condition')
            param = kwargs.get('param')
            if condition == 'category':
                article_list = article_list.filter(category_id=param)
            elif condition == 'tag':
                article_list = article_list.filter(tags__id=param)
            else:
                year, month = param.split('-')
                article_list = article_list.filter(create_time__year=year, create_time__month=month)

        return render(request, 'site.html', locals())
    else:
        return render(request, 'blog.html', locals())


def create_blog(request, username):
    if request.method == "POST":
        back_dic = {'code': 1000, 'msg': ''}
        blog_name = request.POST.get('name')
        blog_title = request.POST.get('title')
        blog_obj = models.Blog.objects.create(site_name=blog_name, site_title=blog_title, site_theme='默认样式')
        abc = models.UserInfo.objects.filter(username=username)[0]
        abc.blog_id = blog_obj.id
        abc.save()
        back_dic['url'] = ''
        return JsonResponse(back_dic)


def article_detail(request, username, article_id):
    article_obj = models.Article.objects.filter(pk=article_id).first()
    comment_list = models.Comment.objects.filter(article=article_obj)
    return render(request, 'article_detail.html', locals())


def UpAndDown(request):
    if request.is_ajax():
        if request.method == 'POST':
            back_dic = {'code': 1000, 'msg': ''}
            # 1 判断当前用户是否登录
            if request.user.is_authenticated():
                article_id = request.POST.get('article_id')
                is_up = request.POST.get('is_up')  # true false
                # print(is_up,type(is_up))
                is_up = json.loads(is_up)  # 将前端js数据格式的布尔值类型 转换成后端python格式的布尔值类型
                # print(is_up, type(is_up))
                # 2 判断当前文章是否是当前用户自己写的
                article_obj = models.Article.objects.filter(pk=article_id).first()
                if not article_obj.blog.userinfo == request.user:
                    # 3 校验当前用户是否已经点过了
                    is_click = models.UpAndDown.objects.filter(user=request.user, article=article_obj)
                    if not is_click:
                        # 4 操作数据库 更新记录
                        # 判断用户是点了赞 还是点了踩 从而决定到底给哪个普通字段加一
                        if is_up:
                            models.Article.objects.filter(pk=article_id).update(up_num=F('up_num') + 1)
                            back_dic['msg'] = '点赞成功'
                        else:
                            models.Article.objects.filter(pk=article_id).update(down_num=F('down_num') + 1)
                            back_dic['msg'] = '点踩成功'
                        # 真正的操作 点赞点踩表
                        models.UpAndDown.objects.create(user=request.user, article=article_obj, is_up=is_up)
                    else:
                        back_dic['code'] = 1001
                        back_dic['msg'] = '你已经点过了!'
                else:
                    back_dic['code'] = 1002
                    back_dic['msg'] = '不可以给自己点呢'
            else:
                back_dic['code'] = 1003
                back_dic['msg'] = mark_safe('请先<a href="/login/">登录</a>')
            return JsonResponse(back_dic)


def comment(request):
    if request.is_ajax():
        if request.method == 'POST':
            back_dic = {'code': 1000, 'msg': ''}
            article_id = request.POST.get('article_id')
            content = request.POST.get('content')
            parent_id = request.POST.get('parent_id')
            with transaction.atomic():
                models.Article.objects.filter(pk=article_id).update(comment_num=F("comment_num") + 1)
                models.Comment.objects.create(user=request.user, article_id=article_id, content=content,
                                              parent_id=parent_id)
            back_dic['msg'] = '评论成功'
            return JsonResponse(back_dic)


@login_required
def backend(request):
    # 获取当前用户所有的文章
    article_list = models.Article.objects.filter(blog=request.user.blog)
    article_obj = Pagination(current_page=request.GET.get('page', 1), all_count=article_list.count())
    article_queryset = article_list[article_obj.start:article_obj.end]
    return render(request, 'backend/backend.html', locals())


@login_required
def add_article(request):
    if request.method == "POST":
        title = request.POST.get('title')
        content = request.POST.get('content')
        category_id = request.POST.get('category')
        tag_list = request.POST.getlist('tag')

        # 先生成一个对象
        soup = BeautifulSoup(content, 'html.parser')
        tags = soup.find_all()  # tags 是所有的标签
        for tag in tags:
            #     # tag.name取到标签的名字
            #     print(tag.name)
            if tag.name == 'script':  # # 取出script标签，删除
                tag.decompose()
        # 文章简介
        # 先简单粗暴 截150个字符串
        # desc = content[0:150]
        # 先获取文章文本内容  再截取150个字符
        desc = soup.text[0:150]
        article_obj = models.Article.objects.create(title=title, desc=desc, content=str(soup), category_id=category_id,
                                                    blog=request.user.blog)
        # 关系表是我们自己建的 没法使用add set等方法
        tag_article_list = []
        for i in tag_list:
            tag_article_list.append(models.Article2Tag(article=article_obj, tag_id=i))
        # 批量插入数据
        models.Article2Tag.objects.bulk_create(tag_article_list)
        return redirect('/backend/')
    category_list = models.Category.objects.filter(blog=request.user.blog)
    tag_list = models.Tag.objects.filter(blog=request.user.blog)
    return render(request, 'backend/add_article.html', locals())


def upload_img(request):
    if request.method == 'POST':
        back_dic = {'error': 0, 'message': ''}
        file_obj = request.FILES.get('imgFile')
        file_dir = os.path.join(settings.BASE_DIR, 'media', 'article_img')
        if not os.path.isdir(file_dir):
            os.mkdir(file_dir)  # 自动创建文件夹
        file_path = os.path.join(file_dir, file_obj.name)  # 拼接文件路径
        with open(file_path, 'wb') as f:
            for line in file_obj:
                f.write(line)
        back_dic['url'] = '/media/article_img/%s' % file_obj.name
        return JsonResponse(back_dic)


@login_required
def set_img(request):
    username = request.user.username
    if request.method == "POST":
        file_obj = request.FILES.get("avatar")
        # models.UserInfo.objects.filter(pk=request.user.pk).update(avatar=file_obj)  # 手动拼接路径
        user_obj = request.user
        user_obj.avatar = file_obj
        user_obj.save()
    return render(request, 'set_img.html', locals())


@login_required
def edit_article(request, article_id):
    article_obj = models.Article.objects.filter(pk=article_id).first()
    category_list = models.Category.objects.filter(blog=request.user.blog)
    tag_list = models.Tag.objects.filter(blog=request.user.blog)
    if request.method == "POST":
        tags = models.Article2Tag.objects.filter(article_id=article_id)
        for tag in tags:
            models.Article2Tag.objects.filter(id=tag.id).delete()
        title = request.POST.get('title')
        content = request.POST.get('content')
        category_id = request.POST.get('category')
        tag_list = request.POST.getlist('tag')

        soup = BeautifulSoup(content, 'html.parser')
        tags = soup.find_all()
        for tag in tags:
            if tag.name == 'script':
                tag.decompose()

        desc = soup.text[0:150]
        article_obj = models.Article.objects.filter(pk=article_id).update(title=title, desc=desc, content=str(soup),
                                                                          category_id=category_id,
                                                                          blog=request.user.blog)
        for i in tag_list:
            models.Article2Tag.objects.create(article_id=article_id, tag_id=i)
        return redirect('/backend/')
    return render(request, 'backend/edit_article.html', locals())


@login_required
def del_article(request, article_id):
    tags = models.Article2Tag.objects.filter(article_id=article_id)
    for tag in tags:
        models.Article2Tag.objects.filter(id=tag.id).delete()
    models.Article.objects.filter(pk=article_id).delete()
    return redirect('/backend/')


@login_required
def add_category(request):
    if request.method == "POST":
        back_dic = {'code': 1000, 'msg': ''}
        title = request.POST.get('title')
        check_title = models.Category.objects.filter(name=title, blog=request.user.blog)
        if check_title:
            back_dic['code'] = 2000
            back_dic['msg'] = '该分类名已存在，请重新输入'
        else:
            category_obj = models.Category.objects.create(name=title, blog=request.user.blog)
            if category_obj:
                back_dic['msg'] = f'分类名{title}创建成功'
                back_dic['url'] = ''
        return JsonResponse(back_dic)
    return render(request, 'backend/add_category.html', locals())


@login_required
def category(request):
    category_list = models.Category.objects.filter(blog=request.user.blog)
    category_obj = Pagination(current_page=request.GET.get('page', 1), all_count=category_list.count())
    category_queryset = category_list[category_obj.start:category_obj.end]
    return render(request, 'backend/category.html', locals())


@login_required
def edit_category(request, category_id):
    category_obj = models.Category.objects.filter(pk=category_id)
    category_obj1 = category_obj.first()
    if request.method == 'POST':
        back_dic = {'code': 1000, 'msg': ''}
        name = request.POST.get('title')
        category_obj.update(name=name)
        back_dic['msg'] = '分类名修改成功'
        back_dic['url'] = ''
        return JsonResponse(back_dic)
    return render(request, 'backend/edit_category.html', locals())


@login_required
def del_category(request, category_id):
    models.Category.objects.filter(pk=category_id).delete()
    return redirect('/category/')


# 评论管理
@login_required
def a_comment(request):
    comment_list = models.Comment.objects.filter(user=request.user)
    return render(request, 'backend/comment.html', locals())


# 删除评论
@login_required
def del_comment(request, comment_id):
    models.Comment.objects.filter(pk=comment_id).delete()
    return redirect('/a_comment/')
