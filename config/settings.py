"""
Configurações do projeto Ben Juan Restaurant (Django).

Site de restaurante com cardápio, carrinho, reservas e login de clientes,
feito para portfólio.
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

# Desenvolvimento: funciona sem configurar nada (DEBUG ligado).
# Produção: defina as variáveis de ambiente abaixo.
#   DJANGO_DEBUG=0
#   DJANGO_SECRET_KEY=<chave longa e aleatória>
#   DJANGO_ALLOWED_HOSTS=meusite.com,www.meusite.com
_DEV_SECRET_KEY = "django-insecure-troque-esta-chave-antes-de-publicar"

DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", _DEV_SECRET_KEY)

if DEBUG:
    ALLOWED_HOSTS = ["*"]
else:
    ALLOWED_HOSTS = [h.strip() for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if h.strip()]
    if SECRET_KEY == _DEV_SECRET_KEY:
        raise ImproperlyConfigured("Defina DJANGO_SECRET_KEY para rodar com DEBUG desligado.")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # app do site
    "app",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # Não precisamos listar 'DIRS': o Django procura na pasta
        # templates/ de cada app instalado (app/templates/app/...).
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Banco de dados: SQLite (suficiente para portfólio/desenvolvimento).
# Guarda usuários, cardápio, pedidos e reservas. Depois de baixar o projeto
# ou mudar os models, rode: python manage.py migrate
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

# ---- Arquivos estáticos (CSS, imagens) ----
STATIC_URL = "static/"

# Em produção, rode `python manage.py collectstatic`; os arquivos vão
# parar em STATIC_ROOT.
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ---- Autenticação ----
# LOGIN_URL: para onde o @login_required / LoginRequiredMixin mandam quem
# não está logado. Os outros dois definem o destino após entrar e sair.
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "index"
LOGOUT_REDIRECT_URL = "index"