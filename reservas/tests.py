import json
from datetime import datetime, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Marca, Reserva, Veiculo


class ReservasApiTests(TestCase):
    def setUp(self):
        self.marca = Marca.objects.create(nome="Toyota")
        self.veiculo_leve = Veiculo.objects.create(
            codigo="VL-01",
            placa="ABC1D01",
            modelo="Corolla",
            capacidade=4,
            ano=2024,
            cor="Branco",
            marca=self.marca,
            tipo=Veiculo.Tipo.LEVE,
        )
        self.veiculo_coletivo = Veiculo.objects.create(
            codigo="VC-01",
            placa="ABC1V01",
            modelo="Sprinter",
            capacidade=18,
            ano=2024,
            cor="Branco",
            marca=self.marca,
            tipo=Veiculo.Tipo.COLETIVO,
        )
        self.veiculo_insuficiente = Veiculo.objects.create(
            codigo="VL-02",
            placa="ABC1D02",
            modelo="Yaris",
            capacidade=2,
            ano=2024,
            cor="Prata",
            marca=self.marca,
            tipo=Veiculo.Tipo.LEVE,
        )
        self.inicio = (timezone.now() + timedelta(days=2)).replace(
            minute=0, second=0, microsecond=0
        )

    def post_json(self, url, dados):
        return self.client.post(
            url, data=json.dumps(dados), content_type="application/json"
        )

    def reserva_payload(self, **alteracoes):
        dados = {
            "solicitante": "João Silva",
            "setor": "Administrativo",
            "atividade": "Reunião",
            "origem": "COSEG",
            "destino": "Reitoria",
            "veiculo_id": self.veiculo_leve.id,
            "numero_passageiros": 3,
            "data_hora_saida": self.inicio.isoformat(),
            "data_hora_retorno": (self.inicio + timedelta(hours=2)).isoformat(),
        }
        dados.update(alteracoes)
        return dados

    def test_post_marca_valida_cria_marca(self):
        resposta = self.post_json(reverse("marcas"), {"nome": "Fiat"})

        self.assertEqual(resposta.status_code, 201)
        self.assertTrue(Marca.objects.filter(nome="Fiat").exists())

    def test_get_marcas_lista_marcas(self):
        resposta = self.client.get(reverse("marcas"))

        self.assertEqual(resposta.status_code, 200)
        self.assertIn(
            {"id": self.marca.id, "nome": "Toyota"}, resposta.json()["marcas"]
        )

    def test_post_veiculo_valido_cria_veiculo(self):
        dados = {
            "codigo": "VL-03",
            "placa": "ABC1D03",
            "modelo": "Polo",
            "capacidade": 4,
            "ano": 2024,
            "cor": "Preto",
            "tipo": Veiculo.Tipo.LEVE,
            "marca_id": self.marca.id,
        }

        resposta = self.post_json(reverse("veiculos"), dados)

        self.assertEqual(resposta.status_code, 201)
        self.assertTrue(Veiculo.objects.filter(codigo="VL-03").exists())
        self.assertEqual(resposta.json()["codigo"], "VL-03")

    def test_post_veiculo_com_codigo_duplicado_e_recusado(self):
        dados = {
            "codigo": self.veiculo_leve.codigo,
            "placa": "ABC1D99",
            "modelo": "Polo",
            "capacidade": 4,
            "ano": 2024,
            "cor": "Preto",
            "tipo": Veiculo.Tipo.LEVE,
            "marca_id": self.marca.id,
        }

        resposta = self.post_json(reverse("veiculos"), dados)

        self.assertEqual(resposta.status_code, 409)
        self.assertEqual(Veiculo.objects.filter(codigo=self.veiculo_leve.codigo).count(), 1)

    def test_post_reserva_valida_cria_reserva(self):
        resposta = self.post_json(reverse("reservas"), self.reserva_payload())

        self.assertEqual(resposta.status_code, 201)
        self.assertEqual(Reserva.objects.count(), 1)

    def test_reserva_com_zero_passageiros_e_recusada(self):
        resposta = self.post_json(
            reverse("reservas"), self.reserva_payload(numero_passageiros=0)
        )

        self.assertEqual(resposta.status_code, 400)
        self.assertEqual(Reserva.objects.count(), 0)

    def test_reserva_acima_da_capacidade_e_recusada(self):
        resposta = self.post_json(
            reverse("reservas"), self.reserva_payload(numero_passageiros=5)
        )

        self.assertEqual(resposta.status_code, 400)
        self.assertEqual(Reserva.objects.count(), 0)

    def test_reserva_com_19_passageiros_e_recusada(self):
        resposta = self.post_json(
            reverse("reservas"), self.reserva_payload(numero_passageiros=19)
        )

        self.assertEqual(resposta.status_code, 400)
        self.assertEqual(
            resposta.json()["erro"],
            "A quantidade de passageiros não pode ser superior a 18.",
        )
        self.assertEqual(Reserva.objects.count(), 0)

    def test_reserva_com_18_passageiros_em_veiculo_coletivo_e_permitida(self):
        resposta = self.post_json(
            reverse("reservas"),
            self.reserva_payload(
                veiculo_id=self.veiculo_coletivo.id,
                numero_passageiros=18,
            ),
        )

        self.assertEqual(resposta.status_code, 201)
        self.assertTrue(
            Reserva.objects.filter(
                veiculo=self.veiculo_coletivo,
                numero_passageiros=18,
            ).exists()
        )

    def test_reserva_com_retorno_anterior_a_saida_e_recusada(self):
        resposta = self.post_json(
            reverse("reservas"),
            self.reserva_payload(
                data_hora_retorno=(self.inicio - timedelta(hours=1)).isoformat()
            ),
        )

        self.assertEqual(resposta.status_code, 400)
        self.assertEqual(Reserva.objects.count(), 0)

    def test_reserva_com_retorno_igual_a_saida_e_recusada(self):
        resposta = self.post_json(
            reverse("reservas"),
            self.reserva_payload(data_hora_retorno=self.inicio.isoformat()),
        )

        self.assertEqual(resposta.status_code, 400)
        self.assertEqual(Reserva.objects.count(), 0)

    def test_reserva_com_saida_no_passado_e_recusada(self):
        saida = timezone.now() - timedelta(hours=1)
        resposta = self.post_json(
            reverse("reservas"),
            self.reserva_payload(
                data_hora_saida=saida.isoformat(),
                data_hora_retorno=(saida + timedelta(hours=2)).isoformat(),
            ),
        )

        self.assertEqual(resposta.status_code, 400)
        self.assertEqual(Reserva.objects.count(), 0)

    def test_conflito_de_horario_para_mesmo_veiculo_e_recusado(self):
        primeira = self.post_json(reverse("reservas"), self.reserva_payload())
        segunda = self.post_json(
            reverse("reservas"),
            self.reserva_payload(
                solicitante="Maria Santos",
                data_hora_saida=(self.inicio + timedelta(hours=1)).isoformat(),
                data_hora_retorno=(self.inicio + timedelta(hours=3)).isoformat(),
            ),
        )

        self.assertEqual(primeira.status_code, 201)
        self.assertEqual(segunda.status_code, 400)
        self.assertEqual(Reserva.objects.count(), 1)

    def test_reserva_terminando_no_inicio_da_outra_e_permitida(self):
        primeira = self.post_json(reverse("reservas"), self.reserva_payload())
        segunda = self.post_json(
            reverse("reservas"),
            self.reserva_payload(
                solicitante="Maria Santos",
                data_hora_saida=(self.inicio + timedelta(hours=2)).isoformat(),
                data_hora_retorno=(self.inicio + timedelta(hours=4)).isoformat(),
            ),
        )

        self.assertEqual(primeira.status_code, 201)
        self.assertEqual(segunda.status_code, 201)
        self.assertEqual(Reserva.objects.count(), 2)

    def test_reserva_iniciando_no_termino_da_outra_e_permitida(self):
        primeira = self.post_json(
            reverse("reservas"),
            self.reserva_payload(
                solicitante="Maria Santos",
                data_hora_saida=(self.inicio + timedelta(hours=2)).isoformat(),
                data_hora_retorno=(self.inicio + timedelta(hours=4)).isoformat(),
            ),
        )
        segunda = self.post_json(reverse("reservas"), self.reserva_payload())

        self.assertEqual(primeira.status_code, 201)
        self.assertEqual(segunda.status_code, 201)
        self.assertEqual(Reserva.objects.count(), 2)

    def test_put_reserva_revalida_capacidade(self):
        reserva = Reserva.objects.create(
            solicitante="João Silva",
            setor="Administrativo",
            atividade="Reunião",
            origem="COSEG",
            destino="Reitoria",
            veiculo=self.veiculo_leve,
            numero_passageiros=3,
            data_hora_saida=self.inicio,
            data_hora_retorno=self.inicio + timedelta(hours=2),
        )
        dados = self.reserva_payload(numero_passageiros=5)

        resposta = self.client.put(
            reverse("reserva-detalhe", args=[reserva.id]),
            data=json.dumps(dados),
            content_type="application/json",
        )

        self.assertEqual(resposta.status_code, 400)
        reserva.refresh_from_db()
        self.assertEqual(reserva.numero_passageiros, 3)

    def test_put_reserva_com_19_passageiros_mantem_quantidade_original(self):
        reserva = Reserva.objects.create(
            solicitante="João Silva",
            setor="Administrativo",
            atividade="Reunião",
            origem="COSEG",
            destino="Reitoria",
            veiculo=self.veiculo_leve,
            numero_passageiros=3,
            data_hora_saida=self.inicio,
            data_hora_retorno=self.inicio + timedelta(hours=2),
        )

        resposta = self.client.put(
            reverse("reserva-detalhe", args=[reserva.id]),
            data=json.dumps(self.reserva_payload(numero_passageiros=19)),
            content_type="application/json",
        )

        self.assertEqual(resposta.status_code, 400)
        self.assertEqual(
            resposta.json()["erro"],
            "A quantidade de passageiros não pode ser superior a 18.",
        )
        reserva.refresh_from_db()
        self.assertEqual(reserva.numero_passageiros, 3)

    def test_disponibilidade_filtra_capacidade_e_conflito(self):
        Reserva.objects.create(
            solicitante="João Silva",
            setor="Administrativo",
            atividade="Reunião",
            origem="COSEG",
            destino="Reitoria",
            veiculo=self.veiculo_leve,
            numero_passageiros=3,
            data_hora_saida=self.inicio,
            data_hora_retorno=self.inicio + timedelta(hours=2),
        )

        resposta = self.client.get(
            reverse("disponibilidade"),
            {
                "data_hora_saida": self.inicio.isoformat(),
                "data_hora_retorno": (self.inicio + timedelta(hours=2)).isoformat(),
                "numero_passageiros": 4,
            },
        )
        codigos = {veiculo["codigo"] for veiculo in resposta.json()["veiculos"]}

        self.assertEqual(resposta.status_code, 200)
        self.assertNotIn(self.veiculo_leve.codigo, codigos)
        self.assertNotIn(self.veiculo_insuficiente.codigo, codigos)
        self.assertIn(self.veiculo_coletivo.codigo, codigos)

    def test_disponibilidade_com_19_passageiros_e_recusada(self):
        resposta = self.client.get(
            reverse("disponibilidade"),
            {
                "data_hora_saida": self.inicio.isoformat(),
                "data_hora_retorno": (self.inicio + timedelta(hours=2)).isoformat(),
                "numero_passageiros": 19,
            },
        )

        self.assertEqual(resposta.status_code, 400)
        self.assertEqual(
            resposta.json()["erro"],
            "A quantidade de passageiros não pode ser superior a 18.",
        )

    def test_disponibilidade_com_18_passageiros_retorna_veiculo_compativel(self):
        resposta = self.client.get(
            reverse("disponibilidade"),
            {
                "data_hora_saida": self.inicio.isoformat(),
                "data_hora_retorno": (self.inicio + timedelta(hours=2)).isoformat(),
                "numero_passageiros": 18,
            },
        )
        codigos = {veiculo["codigo"] for veiculo in resposta.json()["veiculos"]}

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(codigos, {self.veiculo_coletivo.codigo})

    def test_dashboard_calcula_totais_trimestres_e_tipos(self):
        fuso = timezone.get_current_timezone()
        Reserva.objects.create(
            solicitante="João Silva",
            setor="Administrativo",
            atividade="Reunião",
            origem="COSEG",
            destino="Reitoria",
            veiculo=self.veiculo_leve,
            numero_passageiros=3,
            data_hora_saida=timezone.make_aware(datetime(2026, 2, 10, 8, 0), fuso),
            data_hora_retorno=timezone.make_aware(datetime(2026, 2, 10, 10, 0), fuso),
        )
        Reserva.objects.create(
            solicitante="Maria Santos",
            setor="Operações",
            atividade="Treinamento",
            origem="COSEG",
            destino="Campus",
            veiculo=self.veiculo_coletivo,
            numero_passageiros=10,
            data_hora_saida=timezone.make_aware(datetime(2026, 8, 10, 8, 0), fuso),
            data_hora_retorno=timezone.make_aware(datetime(2026, 8, 10, 10, 0), fuso),
        )

        resposta = self.client.get(reverse("dashboard"))
        dados = resposta.json()

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(dados["total_veiculos"], 3)
        self.assertEqual(dados["total_reservas"], 2)
        self.assertEqual(dados["reservas_por_trimestre"]["1º trimestre"], 1)
        self.assertEqual(dados["reservas_por_trimestre"]["3º trimestre"], 1)
        self.assertEqual(
            dados["reservas_por_tipo_veiculo"][Veiculo.Tipo.LEVE.label], 1
        )
        self.assertEqual(
            dados["reservas_por_tipo_veiculo"][Veiculo.Tipo.COLETIVO.label], 1
        )
