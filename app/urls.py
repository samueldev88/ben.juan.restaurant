from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    # Páginas
    path("", views.IndexView.as_view(), name="index"),
    path("reserva/", views.ReservaView.as_view(), name="reserva"),

    # Autenticação
    path("login/", auth_views.LoginView.as_view(template_name="app/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("cadastro/", views.cadastro, name="cadastro"),

    # Produto / Carrinho
    path("produto/<slug:slug>/", views.ProdutoDetailView.as_view(), name="produto_detail"),
    path("produto/<slug:slug>/adicionar/", views.carrinho_adicionar, name="carrinho_adicionar"),
    path("carrinho/", views.carrinho_ver, name="carrinho_ver"),
    path("carrinho/remover/<slug:slug>/", views.carrinho_remover, name="carrinho_remover"),
    path("carrinho/finalizar/", views.carrinho_finalizar, name="carrinho_finalizar"),

    # API — cardápio
    path("api/cardapio/", views.api_cardapio, name="api_cardapio"),
    path("api/estoque/<str:item_id>/", views.api_estoque_toggle, name="api_estoque_toggle"),
    # API — pedidos
    path("api/pedidos/", views.api_pedidos_list, name="api_pedidos_list"),
    path("api/pedidos/novo/", views.api_pedidos_create, name="api_pedidos"),
    path("api/pedidos/<int:pedido_id>/avancar/", views.api_pedido_avancar, name="api_pedido_avancar"),
    path("api/pedidos/<int:pedido_id>/pagamento/", views.api_pedido_pagamento, name="api_pedido_pagamento"),
    path("api/pedidos/<int:pedido_id>/excluir/", views.api_pedido_excluir, name="api_pedido_excluir"),
    path("api/pedidos/<int:pedido_id>/restaurar/", views.api_pedido_restaurar, name="api_pedido_restaurar"),
    path("api/pedidos/<int:pedido_id>/apagar/", views.api_pedido_apagar, name="api_pedido_apagar"),
    # API — reservas
    path("api/reservas/", views.api_reservas_list, name="api_reservas_list"),
    path("api/reservas/nova/", views.api_reservas_create, name="api_reservas"),
    path("api/reservas/<int:reserva_id>/excluir/", views.api_reserva_excluir, name="api_reserva_excluir"),
    path("api/reservas/<int:reserva_id>/restaurar/", views.api_reserva_restaurar, name="api_reserva_restaurar"),
    path("api/reservas/<int:reserva_id>/apagar/", views.api_reserva_apagar, name="api_reserva_apagar"),
]