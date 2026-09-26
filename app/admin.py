"""
restaurante/admin.py

Substitua o conteúdo do seu admin.py por este arquivo. Depois de rodar
"python manage.py createsuperuser", você consegue editar o cardápio,
ver os pedidos e as reservas em /admin/.
"""
from django.contrib import admin

from .models import ItemCardapio, ItemPedido, Pedido, Reserva


class ItemPedidoInline(admin.TabularInline):
    model = ItemPedido
    extra = 0
    readonly_fields = ["item", "nome", "preco", "quantidade"]
    can_delete = False


@admin.register(ItemCardapio)
class ItemCardapioAdmin(admin.ModelAdmin):
    list_display = ["slug", "nome", "categoria", "preco", "esgotado", "ordem"]
    list_editable = ["esgotado", "preco", "ordem"]
    list_filter = ["categoria", "esgotado"]
    search_fields = ["nome", "slug"]


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ["id", "mesa", "status", "criado_em", "excluido"]
    list_filter = ["status", "excluido"]
    inlines = [ItemPedidoInline]
    readonly_fields = ["criado_em"]


@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ["nome", "data", "horario", "pessoas", "excluido"]
    list_filter = ["data", "excluido"]
    search_fields = ["nome"]