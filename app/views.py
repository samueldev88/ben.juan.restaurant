import json
from datetime import date
from functools import wraps

from django.contrib import messages
from django.db import IntegrityError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods, require_POST
from django.views.generic import DetailView, TemplateView

from .models import ItemCardapio, ItemPedido, Pedido, Reserva

CARRINHO_SESSION_KEY = "carrinho"


def _resposta_nao_autorizado(request):
    """Devolve uma resposta JSON de erro se quem chamou não é da equipe;
    se for da equipe, devolve None (pode seguir)."""
    if not request.user.is_authenticated:
        return JsonResponse({"erro": "Acesso restrito à equipe."}, status=401)
    if not request.user.is_staff:
        return JsonResponse({"erro": "Sem permissão."}, status=403)
    return None


def api_staff_required(view):
    """Protege os endpoints JSON do painel da equipe (pedidos, estoque, lista
    completa de reservas). Clientes não têm conta: só quem entra pelo /admin/
    (usuário com is_staff) consegue chamar esses endpoints."""
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        negado = _resposta_nao_autorizado(request)
        if negado:
            return negado
        return view(request, *args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------------
# Páginas (todas públicas)
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


# Página pública: qualquer visitante pode reservar. O ensure_csrf_cookie
# garante que o navegador receba o cookie "csrftoken" ao abrir a página —
# sem login, ninguém mais ganharia esse cookie, e o fetch() de reserva
# (que envia o token no cabeçalho X-CSRFToken) seria barrado com erro 403.
@method_decorator(ensure_csrf_cookie, name="dispatch")
class ReservaView(TemplateView):
    template_name = "app/reserva.html"


class ProdutoDetailView(DetailView):
    model = ItemCardapio
    template_name = "app/produto_detail.html"
    context_object_name = "produto"
    slug_field = "slug"
    slug_url_kwarg = "slug"


# ---------------------------------------------------------------------------
# Carrinho (guardado na sessão — funciona sem login)
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


def carrinho_ver(request):
    itens, total = _carrinho_detalhado(request)
    return render(request, "app/carrinho.html", {
        "itens": itens,
        "total": total,
        "tipo_entrega_choices": Pedido.TIPO_ENTREGA_CHOICES,
    })


@require_POST
def carrinho_remover(request, slug):
    carrinho = _get_carrinho(request)
    carrinho.pop(slug, None)
    _salvar_carrinho(request, carrinho)
    return redirect("carrinho_ver")


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
    if not request.user.is_authenticated and not telefone:
        messages.error(request, "Informe seu telefone para contato.")
        return redirect("carrinho_ver")

    # Visitante sem conta: usuario fica vazio (o campo precisa aceitar null).
    pedido = Pedido.objects.create(
        usuario=request.user if request.user.is_authenticated else None,
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


@api_staff_required
@require_http_methods(["POST"])
def api_estoque_toggle(request, item_id):
    item = get_object_or_404(ItemCardapio, slug=item_id)
    item.esgotado = not item.esgotado
    item.save(update_fields=["esgotado"])
    return JsonResponse(item.as_dict())


# ---------------------------------------------------------------------------
# API — Pedidos (painel da equipe)
# ---------------------------------------------------------------------------

@api_staff_required
def api_pedidos_list(request):
    pedidos = Pedido.objects.filter(excluido=False)
    return JsonResponse({"pedidos": [p.as_dict() for p in pedidos]})


@api_staff_required
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


@api_staff_required
@require_http_methods(["POST"])
def api_pedido_avancar(request, pedido_id):
    pedido = get_object_or_404(Pedido, pk=pedido_id)
    proximo = {"recebido": "preparando", "preparando": "pronto"}
    pedido.status = proximo.get(pedido.status, pedido.status)
    pedido.save(update_fields=["status"])
    return JsonResponse(pedido.as_dict())


@api_staff_required
@require_http_methods(["POST"])
def api_pedido_pagamento(request, pedido_id):
    pedido = get_object_or_404(Pedido, pk=pedido_id)
    pedido.excluido = True
    pedido.excluido_em = timezone.now()
    pedido.save(update_fields=["excluido", "excluido_em"])
    return JsonResponse(pedido.as_dict())


@api_staff_required
@require_http_methods(["POST"])
def api_pedido_excluir(request, pedido_id):
    pedido = get_object_or_404(Pedido, pk=pedido_id)
    pedido.excluido = True
    pedido.excluido_em = timezone.now()
    pedido.save(update_fields=["excluido", "excluido_em"])
    return JsonResponse(pedido.as_dict())


@api_staff_required
@require_http_methods(["POST"])
def api_pedido_restaurar(request, pedido_id):
    pedido = get_object_or_404(Pedido, pk=pedido_id)
    pedido.excluido = False
    pedido.excluido_em = None
    pedido.save(update_fields=["excluido", "excluido_em"])
    return JsonResponse(pedido.as_dict())


@api_staff_required
@require_http_methods(["POST"])
def api_pedido_apagar(request, pedido_id):
    pedido = get_object_or_404(Pedido, pk=pedido_id)
    pedido.delete()
    return JsonResponse({"ok": True})


# ---------------------------------------------------------------------------
# API — Reservas
#
# Públicos (a página /reserva/ usa, sem login):
#   GET  /api/reservas/?data=AAAA-MM-DD  -> horários já ocupados naquele dia
#   POST /api/reservas/nova/             -> cria a reserva
# Só equipe:
#   GET  /api/reservas/                  -> lista completa (com nomes)
#   excluir / restaurar / apagar
# ---------------------------------------------------------------------------

def _parse_data(valor):
    """Converte 'AAAA-MM-DD' em date; devolve None se for inválida."""
    try:
        return date.fromisoformat(valor)
    except (TypeError, ValueError):
        return None


def api_reservas_list(request):
    data_param = request.GET.get("data")

    if data_param:
        # Público: devolve só os horários ocupados, sem nenhum dado pessoal.
        dia = _parse_data(data_param)
        if dia is None:
            return JsonResponse({"erro": "Data inválida."}, status=400)
        horarios = (
            Reserva.objects.filter(excluido=False, data=dia)
            .values_list("horario", flat=True)
        )
        return JsonResponse({"horarios": [str(h)[:5] for h in horarios]})

    # Sem ?data=: é a lista completa (nomes etc.), só para a equipe.
    negado = _resposta_nao_autorizado(request)
    if negado:
        return negado
    reservas = Reserva.objects.filter(excluido=False)
    return JsonResponse({"reservas": [r.as_dict() for r in reservas]})


@require_http_methods(["POST"])
def api_reservas_create(request):
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "erro": "JSON inválido."}, status=400)

    nome = (payload.get("nome") or "").strip()
    data = payload.get("data")
    horario = payload.get("horario")
    pessoas = payload.get("pessoas")
    observacao = (payload.get("observacao") or "").strip()

    if not all([nome, data, horario, pessoas]):
        return JsonResponse(
            {"ok": False, "erro": "Preencha nome, data, horário e número de pessoas."},
            status=400,
        )

    # Endpoint público: valida o básico pra não aceitar lixo.
    if len(nome) > 100 or len(observacao) > 500:
        return JsonResponse({"ok": False, "erro": "Texto muito longo."}, status=400)

    dia = _parse_data(data)
    if dia is None:
        return JsonResponse({"ok": False, "erro": "Data inválida."}, status=400)
    if dia < timezone.localdate():
        return JsonResponse(
            {"ok": False, "erro": "Escolha uma data a partir de hoje."}, status=400
        )

    try:
        reserva = Reserva.objects.create(
            nome=nome,
            data=dia,
            horario=horario,
            pessoas=pessoas,
            observacao=observacao,
        )
    except IntegrityError:
        return JsonResponse(
            {"ok": False, "erro": "Já existe uma reserva para essa data e horário."},
            status=409,
        )

    # O reserva.html confere o campo "ok" na resposta.
    return JsonResponse({"ok": True, **reserva.as_dict()}, status=201)


@api_staff_required
@require_http_methods(["POST"])
def api_reserva_excluir(request, reserva_id):
    reserva = get_object_or_404(Reserva, pk=reserva_id)
    reserva.excluido = True
    reserva.excluido_em = timezone.now()
    reserva.save(update_fields=["excluido", "excluido_em"])
    return JsonResponse(reserva.as_dict())


@api_staff_required
@require_http_methods(["POST"])
def api_reserva_restaurar(request, reserva_id):
    reserva = get_object_or_404(Reserva, pk=reserva_id)
    reserva.excluido = False
    reserva.excluido_em = None
    reserva.save(update_fields=["excluido", "excluido_em"])
    return JsonResponse(reserva.as_dict())

@api_staff_required
@require_http_methods(["POST"])
def api_reserva_apagar(request, reserva_id):
    reserva = get_object_or_404(Reserva, pk=reserva_id)
    reserva.delete()
    return JsonResponse({"ok": True})

    from django.views.generic import TemplateView

class ServicosView(TemplateView):
    template_name = 'app/servicos.html'

class EsperaView(TemplateView):
    template_name = 'app/espera.html'