# =====================================================================
# Fluxo de reservas (versão simples, sem banco para a lista de espera)
# Adicione nos arquivos correspondentes do seu projeto.
# =====================================================================

# ---------- views.py ----------
from django.shortcuts import render


def reserva_servicos(request):
    """Tela inicial: reserva de mesa, lista de espera ou cardápio."""
    return render(request, 'restaurante/servicos.html')


def reserva_espera(request):
    """Lista de espera (demonstração: o formulário só valida e confirma na tela)."""
    return render(request, 'restaurante/espera.html')


# ---------- urls.py ----------
# 'reserva' passa a ser a tela inicial do fluxo, então o botão "Reservas" da dock
# e o "Reservar mesa" do hero já levam pra ela sem mexer na index.html.
#
#     path('reserva/', views.reserva_servicos, name='reserva'),
#     path('reserva/mesa/', views.reserva, name='reserva_mesa'),   # sua view atual, nova URL/nome
#     path('reserva/espera/', views.reserva_espera, name='reserva_espera'),