from datetime import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from reservas.models import Marca, Reserva, Veiculo


class Command(BaseCommand):
    help = "Insere os dados iniciais de marcas, veículos e reservas."

    def handle(self, *args, **options):
        marcas = {}
        for nome in (
            "Toyota",
            "Chevrolet",
            "Volkswagen",
            "Fiat",
            "Mercedes-Benz",
            "Renault",
        ):
            marca, _ = Marca.objects.get_or_create(nome=nome)
            marcas[nome] = marca

        veiculos = (
            ("VL-01", "ABC1D01", "Toyota", "Corolla", 4, 2024, "Branco", Veiculo.Tipo.LEVE),
            ("VL-02", "ABC1D02", "Chevrolet", "Onix", 4, 2023, "Prata", Veiculo.Tipo.LEVE),
            ("VL-03", "ABC1D03", "Volkswagen", "Virtus", 4, 2024, "Branco", Veiculo.Tipo.LEVE),
            ("VL-04", "ABC1D04", "Fiat", "Cronos", 4, 2023, "Prata", Veiculo.Tipo.LEVE),
            ("VL-05", "ABC1D05", "Toyota", "Yaris", 4, 2024, "Branco", Veiculo.Tipo.LEVE),
            ("VL-06", "ABC1D06", "Chevrolet", "Onix Plus", 4, 2023, "Preto", Veiculo.Tipo.LEVE),
            ("VL-07", "ABC1D07", "Volkswagen", "Polo", 4, 2024, "Branco", Veiculo.Tipo.LEVE),
            ("VL-08", "ABC1D08", "Fiat", "Argo", 4, 2023, "Prata", Veiculo.Tipo.LEVE),
            ("VC-01", "ABC1V01", "Mercedes-Benz", "Sprinter", 18, 2024, "Branco", Veiculo.Tipo.COLETIVO),
            ("VC-02", "ABC1V02", "Renault", "Master", 18, 2023, "Branco", Veiculo.Tipo.COLETIVO),
        )

        veiculos_por_codigo = {}
        for codigo, placa, marca_nome, modelo, capacidade, ano, cor, tipo in veiculos:
            veiculo, _ = Veiculo.objects.update_or_create(
                codigo=codigo,
                defaults={
                    "placa": placa,
                    "marca": marcas[marca_nome],
                    "modelo": modelo,
                    "capacidade": capacidade,
                    "ano": ano,
                    "cor": cor,
                    "tipo": tipo,
                },
            )
            veiculos_por_codigo[codigo] = veiculo

        def data_hora(valor):
            return timezone.make_aware(datetime.strptime(valor, "%d/%m/%Y %H:%M"))

        reservas = (
            ("VL-01", "18/08/2026 08:00", "18/08/2026 10:00", "reunião administrativa", "João Silva", "Administrativo", "COSEG", "Reitoria", 3),
            ("VL-03", "18/08/2026 14:00", "18/08/2026 17:00", "visita técnica", "Maria Santos", "Engenharia", "COSEG", "Campus Universitário", 4),
            ("VC-01", "19/08/2026 07:00", "19/08/2026 12:00", "transporte de equipe", "Carlos Oliveira", "Operações", "COSEG", "Unidade Operacional", 15),
            ("VL-05", "20/08/2026 09:00", "20/08/2026 11:00", "atividade externa", "Ana Costa", "Administrativo", "COSEG", "Centro Administrativo", 2),
        )

        for (
            codigo_veiculo,
            saida,
            retorno,
            atividade,
            solicitante,
            setor,
            origem,
            destino,
            numero_passageiros,
        ) in reservas:
            data_hora_saida = data_hora(saida)
            Reserva.objects.update_or_create(
                veiculo=veiculos_por_codigo[codigo_veiculo],
                data_hora_saida=data_hora_saida,
                defaults={
                    "data_hora_retorno": data_hora(retorno),
                    "atividade": atividade,
                    "solicitante": solicitante,
                    "setor": setor,
                    "origem": origem,
                    "destino": destino,
                    "numero_passageiros": numero_passageiros,
                    "observacoes": "",
                },
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Carga concluída: "
                f"{Marca.objects.count()} marcas, "
                f"{Veiculo.objects.count()} veículos e "
                f"{Reserva.objects.count()} reservas existentes."
            )
        )
