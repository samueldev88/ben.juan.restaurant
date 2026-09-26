"""
app/models.py
"""
from django.conf import settings
from django.db import models
from django.db.models import Q


class ItemCardapio(models.Model):
    CATEGORIA_CHOICES = [
        ("entradas", "Entradas"),
        ("principais", "Pratos Principais"),
        ("sobremesas", "Sobremesas"),
        ("bebidas", "Bebidas"),
        ("drinks", "Drinks"),
    ]

    # slug é o "id" curto usado pelo front-end (e1, m1, s1, b1, d1...)
    slug = models.SlugField(max_length=10, primary_key=True)
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES)
    nome = models.CharField(max_length=100)
    preco = models.DecimalField(max_digits=6, decimal_places=2)
    esgotado = models.BooleanField(default=False)
    ordem = models.PositiveIntegerField(default=0)
    descricao = models.TextField(blank=True, default="")
    foto = models.ImageField(upload_to="cardapio/", blank=True, null=True)

    class Meta:
        ordering = ["categoria", "ordem"]

    def __str__(self):
        return self.nome

    def as_dict(self):
        return {
            "id": self.slug,
            "name": self.nome,
            "price": float(self.preco),
            "esgotado": self.esgotado,
        }


class Pedido(models.Model):
    STATUS_CHOICES = [
        ("recebido", "Recebido"),
        ("preparando", "Preparando"),
        ("pronto", "Pronto"),
    ]
    TIPO_ENTREGA_CHOICES = [
        ("mesa", "Consumo no restaurante"),
        ("retirada", "Retirada no local"),
        ("entrega", "Entrega em casa"),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pedidos",
    )
    tipo_entrega = models.CharField(max_length=20, choices=TIPO_ENTREGA_CHOICES, default="mesa")
    mesa = models.CharField(max_length=10, blank=True, default="")
    endereco = models.CharField(max_length=255, blank=True, default="")
    telefone = models.CharField(max_length=20, blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="recebido")
    criado_em = models.DateTimeField(auto_now_add=True)
    excluido = models.BooleanField(default=False)
    excluido_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):
        return f"Pedido #{self.pk} - {self.get_tipo_entrega_display()}"

    @property
    def total(self):
        return sum((i.subtotal for i in self.itens.all()), start=0)

    def as_dict(self):
        return {
            "id": self.pk,
            "usuario": self.usuario.username if self.usuario else None,
            "tipo_entrega": self.tipo_entrega,
            "mesa": self.mesa,
            "endereco": self.endereco,
            "telefone": self.telefone,
            "items": [f"{i.quantidade}x {i.nome}" for i in self.itens.all()],
            "time": self.criado_em.strftime("%H:%M"),
            "total": float(self.total),
            "status": self.status,
            "excluido": self.excluido,
        }


class ItemPedido(models.Model):
    pedido = models.ForeignKey(Pedido, related_name="itens", on_delete=models.CASCADE)
    item = models.ForeignKey(ItemCardapio, on_delete=models.SET_NULL, null=True, blank=True)
    # snapshot: guarda nome/preço no momento do pedido, mesmo se o item do
    # cardápio mudar de preço ou for removido depois.
    nome = models.CharField(max_length=100)
    preco = models.DecimalField(max_digits=6, decimal_places=2)
    quantidade = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantidade}x {self.nome}"

    @property
    def subtotal(self):
        return self.preco * self.quantidade


class Reserva(models.Model):
    nome = models.CharField(max_length=150)
    data = models.DateField()
    horario = models.CharField(max_length=5)  # ex: "19:00"
    pessoas = models.CharField(max_length=20)
    observacao = models.TextField(blank=True, default="")
    criado_em = models.DateTimeField(auto_now_add=True)
    excluido = models.BooleanField(default=False)
    excluido_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["data", "horario"]
        constraints = [
            # Garante no banco que duas reservas ativas não fiquem com a
            # mesma data + horário, mesmo se duas pessoas confirmarem ao
            # mesmo tempo. Reservas na lixeira (excluido=True) não contam.
            models.UniqueConstraint(
                fields=["data", "horario"],
                condition=Q(excluido=False),
                name="reserva_unica_por_horario_ativo",
            )
        ]

    def __str__(self):
        return f"{self.nome} - {self.data} {self.horario}"

    def as_dict(self):
        return {
            "id": self.pk,
            "nome": self.nome,
            "data": self.data.isoformat(),
            "pessoas": self.pessoas,
            "horario": self.horario,
            "observacao": self.observacao,
            "excluido": self.excluido,
        }