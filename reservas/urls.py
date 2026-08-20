from django.urls import path

from . import views

urlpatterns = [
    path("marcas/", views.marcas, name="marcas"),
    path("marcas/<int:marca_id>/", views.marcas, name="marca-detalhe"),
    path("veiculos/", views.veiculos, name="veiculos"),
    path("veiculos/<int:veiculo_id>/", views.veiculos, name="veiculo-detalhe"),
    path("reservas/", views.reservas, name="reservas"),
    path("reservas/<int:reserva_id>/", views.reservas, name="reserva-detalhe"),
]
