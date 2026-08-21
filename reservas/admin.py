from django.contrib import admin

from .models import Marca, Reserva, Veiculo


@admin.register(Marca)
class MarcaAdmin(admin.ModelAdmin):
    list_display = ("id", "nome")
    search_fields = ("nome",)
    ordering = ("nome",)


@admin.register(Veiculo)
class VeiculoAdmin(admin.ModelAdmin):
    list_display = ("placa", "modelo", "marca", "tipo", "capacidade", "ano")
    search_fields = ("placa", "modelo")
    list_filter = ("tipo", "marca")
    ordering = ("placa",)


@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = (
        "solicitante",
        "veiculo",
        "numero_passageiros",
        "data_hora_saida",
        "data_hora_retorno",
    )
    search_fields = ("solicitante", "setor", "origem", "destino", "veiculo__placa")
    list_filter = ("veiculo", "veiculo__tipo", "data_hora_saida")
    ordering = ("data_hora_saida",)
