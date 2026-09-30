import json
from functools import wraps

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.forms import UserCreationForm
from django.db import IntegrityError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST
from django.views.generic import DetailView, TemplateView

from .models import ItemCardapio, ItemPedido, Pedido, Reserva

CARRINHO_SESSION_KEY = "carrinho"


def api_login_required(view):
    """Como o login_required, mas para endpoints JSON: em vez de redirecionar
    para a página de login (HTML), responde 401 com uma mensagem em JSON."""
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"erro": "Faça login para continuar."}, status=401)
        return view(request, *args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------------
# Páginas
# ---------------------------------------------------------------------------

class IndexView(TemplateView):
    template_name = "app/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cardapio_por_categoria = []
        for valor, rotulo in ItemCardapio.CATEGORIA_CHOICES:
            itens = ItemCardapio.objects.filter(categoria=valor)
            cardapio_por_categoria.append((valor, rotulo, itens))
        context["cardapio_por_categoria"] = cardapio_por_categoria
        return context


class ReservaView(LoginRequiredMixin, TemplateView):
    template_name = "app/reserva.html"


class ProdutoDetailView(LoginRequiredMixin, DetailView):
    model = ItemCardapio
    template_name = "app/produto_detail.html"
    context_object_name = "produto"
    slug_field = "slug"
    slug_url_kwarg = "slug"


# ---------------------------------------------------------------------------
# Autenticação
# ---------------------------------------------------------------------------

def cadastro(request):
    if request.user.is_authenticated:
        return redirect("index")

    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Bem-vindo(a), {user.username}!")
            return redirect("index")
    else:
        form = UserCreationForm()

    for campo in form.fields.values():
        campo.widget.attrs["class"] = "form-control"

    return render(request, "app/cadastro.html", {"form": form})


# ---------------------------------------------------------------------------
# Carrinho (guardado na sessão do usuário)
#
# Formato salvo em request.session["carrinho"]:
# { "e1": 2, "m3": 1, ... }  -> slug do produto: quantidade
# ---------------------------------------------------------------------------

def _get_carrinho(request):
    return request.session.get(CARRINHO_SESSION_KEY, {})


def _salvar_carrinho(request, carrinho):
    request.session[CARRINHO_SESSION_KEY] = carrinho
    request.session.modified = True


def _carrinho_detalhado(request):
    """Retorna a lista de itens do carrinho já com nome/preço/subtotal,
    e o total geral — usado no template do carrinho."""
    carrinho = _get_carrinho(request)
    itens = []
    total = 0
    for slug, quantidade in carrinho.items():
        produto = ItemCardapio.objects.filter(slug=slug).first()
        if not produto:
            continue
        subtotal = produto.preco * quantidade
        total += subtotal
        itens.append({
            "produto": produto,
            "quantidade": quantidade,
            "subtotal": subtotal,
        })
    return itens, total


@login_required
@require_POST
def carrinho_adicionar(request, slug):
    produto = get_object_or_404(ItemCardapio, slug=slug)

    try:
        quantidade = int(request.POST.get("quantidade", 1))
    except ValueError:
        quantidade = 1
    quantidade = max(1, quantidade)

    carrinho = _get_carrinho(request)
    carrinho[slug] = carrinho.get(slug, 0) + quantidade
    _salvar_carrinho(request, carrinho)

    messages.success(request, f"{produto.nome} adicionado ao carrinho.")
    return redirect("carrinho_ver")


@login_required
def carrinho_ver(request):
    itens, total = _carrinho_detalhado(request)
    return render(request, "app/carrinho.html", {
        "itens": itens,
        "total": total,
        "tipo_entrega_choices": Pedido.TIPO_ENTREGA_CHOICES,
    })


@login_required
@require_POST
def carrinho_remover(request, slug):
    carrinho = _get_carrinho(request)
    carrinho.pop(slug, None)
    _salvar_carrinho(request, carrinho)
    return redirect("carrinho_ver")


@login_required
@require_POST
def carrinho_finalizar(request):
    itens, total = _carrinho_detalhado(request)

    if not itens:
        messages.error(request, "Seu carrinho está vazio.")
        return redirect("carrinho_ver")

    tipo_entrega = request.POST.get("tipo_entrega", "mesa")
    mesa = request.POST.get("mesa", "").strip()
    endereco = request.POST.get("endereco", "").strip()
    telefone = request.POST.get("telefone", "").strip()

    if tipo_entrega == "mesa" and not mesa:
        messages.error(request, "Informe o número da mesa.")
        return redirect("carrinho_ver")
    if tipo_entrega == "entrega" and not endereco:
        messages.error(request, "Informe o endereço de entrega.")
        return redirect("carrinho_ver")

    pedido = Pedido.objects.create(
        usuario=request.user,
        tipo_entrega=tipo_entrega,
        mesa=mesa,
        endereco=endereco,
        telefone=telefone,
    )

    for item in itens:
        ItemPedido.objects.create(
            pedido=pedido,
            item=item["produto"],
            nome=item["produto"].nome,
            preco=item["produto"].preco,
            quantidade=item["quantidade"],
        )

    _salvar_carrinho(request, {})
    messages.success(request, f"Pedido #{pedido.pk} realizado com sucesso!")
    return redirect("index")


# ---------------------------------------------------------------------------
# API — Cardápio
# ---------------------------------------------------------------------------

def api_cardapio(request):
    itens = ItemCardapio.objects.all()
    data = []
    for item in itens:
        item_dict = item.as_dict()
        item_dict["categoria"] = item.categoria
        data.append(item_dict)
    return JsonResponse({"itens": data})


@api_login_required
@require_http_methods(["POST"])
def api_estoque_toggle(request, item_id):
    item = get_object_or_404(ItemCardapio, slug=item_id)
    item.esgotado = not item.esgotado
    item.save(update_fields=["esgotado"])
    return JsonResponse(item.as_dict())


# ---------------------------------------------------------------------------
# API — Pedidos
# ---------------------------------------------------------------------------

@api_login_required
def api_pedidos_list(request):
    pedidos = Pedido.objects.filter(excluido=False)
    return JsonResponse({"pedidos": [p.as_dict() for p in pedidos]})


@api_login_required
@require_http_methods(["POST"])
def api_pedidos_create(request):
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"erro": "JSON inválido."}, status=400)

    mesa = (payload.get("mesa") or "").strip()
    itens_payload = payload.get("itens") or []

    if not mesa:
        return JsonResponse({"erro": "Informe a mesa."}, status=400)
    if not itens_payload:
        return JsonResponse({"erro": "O pedido precisa ter ao menos um item."}, status=400)

    pedido = Pedido.objects.create(mesa=mesa)

    for entrada in itens_payload:
        slug = entrada.get("item_id") or entrada.get("id")
        quantidade = int(entrada.get("quantidade", 1))
        item = ItemCardapio.objects.filter(slug=slug).first()

        if item:
            nome, preco = item.nome, item.preco
        else:
            nome = entrada.get("nome", "Item")
            preco = entrada.get("preco", 0)

        ItemPedido.objects.create(
            pedido=pedido,
            item=item,
            nome=nome,
            preco=preco,
            quantidade=quantidade,
        )

    return JsonResponse(pedido.as_dict(), status=201)


@api_login_required
@require_http_methods(["POST"])
def api_pedido_avancar(request, pedido_id):
    pedido = get_object_or_404(Pedido, pk=pedido_id)
    proximo = {"recebido": "preparando", "preparando": "pronto"}
    pedido.status = proximo.get(pedido.status, pedido.status)
    pedido.save(update_fields=["status"])
    return JsonResponse(pedido.as_dict())


@api_login_required
@require_http_methods(["POST"])
def api_pedido_pagamento(request, pedido_id):
    pedido = get_object_or_404(Pedido, pk=pedido_id)
    pedido.excluido = True
    pedido.excluido_em = timezone.now()
    pedido.save(update_fields=["excluido", "excluido_em"])
    return JsonResponse(pedido.as_dict())


@api_login_required
@require_http_methods(["POST"])
def api_pedido_excluir(request, pedido_id):
    pedido = get_object_or_404(Pedido, pk=pedido_id)
    pedido.excluido = True
    pedido.excluido_em = timezone.now()
    pedido.save(update_fields=["excluido", "excluido_em"])
    return JsonResponse(pedido.as_dict())


@api_login_required
@require_http_methods(["POST"])
def api_pedido_restaurar(request, pedido_id):
    pedido = get_object_or_404(Pedido, pk=pedido_id)
    pedido.excluido = False
    pedido.excluido_em = None
    pedido.save(update_fields=["excluido", "excluido_em"])
    return JsonResponse(pedido.as_dict())


@api_login_required
@require_http_methods(["POST"])
def api_pedido_apagar(request, pedido_id):
    pedido = get_object_or_404(Pedido, pk=pedido_id)
    pedido.delete()
    return JsonResponse({"ok": True})


# ---------------------------------------------------------------------------
# API — Reservas
# ---------------------------------------------------------------------------

@api_login_required
def api_reservas_list(request):
    reservas = Reserva.objects.filter(excluido=False)
    return JsonResponse({"reservas": [r.as_dict() for r in reservas]})


@api_login_required
@require_http_methods(["POST"])
def api_reservas_create(request):
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"erro": "JSON inválido."}, status=400)

    nome = (payload.get("nome") or "").strip()
    data = payload.get("data")
    horario = payload.get("horario")
    pessoas = payload.get("pessoas")
    observacao = payload.get("observacao", "")

    if not all([nome, data, horario, pessoas]):
        return JsonResponse(
            {"erro": "Preencha nome, data, horário e número de pessoas."}, status=400
        )

    try:
        reserva = Reserva.objects.create(
            nome=nome,
            data=data,
            horario=horario,
            pessoas=pessoas,
            observacao=observacao,
        )
    except IntegrityError:
        return JsonResponse(
            {"erro": "Já existe uma reserva para essa data e horário."}, status=409
        )

    return JsonResponse(reserva.as_dict(), status=201)


@api_login_required
@require_http_methods(["POST"])
def api_reserva_excluir(request, reserva_id):
    reserva = get_object_or_404(Reserva, pk=reserva_id)
    reserva.excluido = True
    reserva.excluido_em = timezone.now()
    reserva.save(update_fields=["excluido", "excluido_em"])
    return JsonResponse(reserva.as_dict())


@api_login_required
@require_http_methods(["POST"])
def api_reserva_restaurar(request, reserva_id):
    reserva = get_object_or_404(Reserva, pk=reserva_id)
    reserva.excluido = False
    reserva.excluido_em = None
    reserva.save(update_fields=["excluido", "excluido_em"])
    return JsonResponse(reserva.as_dict())


@api_login_required
@require_http_methods(["POST"])
def api_reserva_apagar(request, reserva_id):
    reserva = get_object_or_404(Reserva, pk=reserva_id)
    reserva.delete()
    return JsonResponse({"ok": True})