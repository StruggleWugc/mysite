from django.shortcuts import render
from django.shortcuts import redirect
from . import models
from . import forms
import hashlib
import datetime
from django.conf import settings
from django.contrib.auth.views import login_required
from stronghold.decorators import public


# Create your views here.
def send_email(email, code):
    from django.core.mail import EmailMultiAlternatives
    subject = "注册验证码"
    text_content = """如果你看到这条消息，说明你的邮箱服务器不提供HTML链接功能，请联系管理员！"""
    html_content = """
    <p>感谢注册<a href="http://{}/confirm/?code={}" target=blank>www.baidu.com</a>，\
                    这里是刘江的博客和教程站点，专注于Python、Django和机器学习技术的分享！</p>
                    <p>请点击站点链接完成注册确认！</p>
                    <p>此链接有效期为{}天！</p>
    """.format('127.0.0.1:8000', code, settings.CONFIRM_DAYS)
    msg = EmailMultiAlternatives(subject, text_content, settings.EMAIL_HOST_USER, [email])
    msg.attach_alternative(html_content, 'text/html')
    msg.send()


def make_confirm_string(user):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    code = hash_code(user.name, now)
    models.ConfirmString.objects.create(code=code, user=user)
    return code


def hash_code(s, salt='mysite'):
    h = hashlib.sha256()
    s += salt
    h.update(s.encode())
    return h.hexdigest()


def user_confirm(request):
    code = request.GET.get('code', None)
    message = ''
    try:
        confirm = models.ConfirmString.objects.get(code=code)
    except:
        message = "无效的确认请求"
        return render(request, 'login/confirm.html', locals())

    c_time = confirm.c_time
    now = datetime.datetime.now()
    if now > c_time + datetime.timedelta(settings.CONFIRM_DAYS):
        confirm.user.delete()
        message = "您的邮件已过期！请重新注册！"
        return render(request, 'login/confirm.html', locals())
    else:
        confirm.user.has_confirmed = True
        confirm.user.save()
        confirm.delete()
        message = "感谢确认，请使用账户登录！"
        return render(request, 'login/confirm.html', locals())


@login_required(login_url='/login/')
def index(request):
    return render(request, 'login/index.html')


@public
def login(request):
    login_form = forms.UserForm()
    if request.session.get('is_login', None):
        return redirect('/index/')
    if request.method == 'POST':
        login_form = forms.UserForm(request.POST)
        message = '请检查填写的内容！'
        if login_form.is_valid():
            username = login_form.cleaned_data.get('username')
            password = login_form.cleaned_data.get('password')
            try:
                user = models.User.objects.get(name=username)
            except:
                message = "用户不存在！"
                return render(request, 'login/login.html', locals())

            if not user.has_confirmed:
                message = "该用户还未进行邮件确认！"
                return render(request, 'login/login.html', locals())

            if user.password == hash_code(password):
                request.session['is_login'] = True
                request.session['user_id'] = user.id
                request.session['user_name'] = user.name
                return redirect('/index/')
            else:
                message = "密码错误！"
                return render(request, 'login/login.html', locals())
        else:
            return render(request, 'login/login.html', locals())
    return render(request, 'login/login.html', locals())


def register(request):
    register_form = forms.RegisterForm()
    if request.session.get('is_login', None):
        return redirect('/index/')

    if request.method == 'POST':
        register_form = forms.RegisterForm(request.POST)
        message = "请检查填写内容"
        if register_form.is_valid():
            username = register_form.cleaned_data.get('username')
            password1 = register_form.cleaned_data.get('password1')
            password2 = register_form.cleaned_data.get('password2')
            email = register_form.cleaned_data.get('email')
            sex = register_form.cleaned_data.get('sex')

            if password1 != password2:
                message = "两次密码输入不一致！"
                return render(request, 'login/register.html', locals())
            else:
                try:
                    models.User.objects.get(name=username)
                    message = "用户已存在！"
                    return render(request, 'login/register.html', locals())
                except models.User.DoesNotExist:
                    pass
                try:
                    models.User.objects.get(email=email)
                    message = "该邮箱已经注册过了！"
                    return render(request, 'login/register.html', locals())
                except models.User.DoesNotExist:
                    pass
                new_user = models.User()
                new_user.name = username
                new_user.email = email
                new_user.password = hash_code(password1)
                new_user.sex = sex
                new_user.save()

                code = make_confirm_string(new_user)
                send_email(email, code)

                message = "请前往邮箱进行确认！"
                return redirect('/login/')
        else:
            return render(request, 'login/register.html', locals())

    return render(request, 'login/register.html', locals())


def logout(request):
    if not request.session.get('is_login', None):
        return render(request, 'login/login.html')
    request.session.flush()
    return redirect('/login/')
