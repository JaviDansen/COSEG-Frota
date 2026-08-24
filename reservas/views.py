import json

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import Count
from django.db.models.deletion import ProtectedError
from django.http import JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt

from .models import Marca, Reserva, Veiculo


def resposta_erro(mensagem, status=400, detalhes=None):
    resposta = {"erro": mensagem}
    if detalhes:
        resposta["detalhes"] = detalhes
    return JsonResponse(resposta, status=status)


def ler_json(request):
    try:
        dados = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, resposta_erro("JSON inválido.")
    if not isinstance(dados, dict):
        return None, resposta_erro("O corpo deve ser um objeto JSON.")
    return dados, None


def obrigatorios(dados, campos):
    faltantes = [campo for campo in campos if campo not in dados]
    if faltantes:
        return resposta_erro("Campos obrigatórios ausentes.", detalhes={"campos": faltantes})


def salvar(objeto):
    try:
        objeto.full_clean()
        objeto.save()
    except ValidationError as erro:
        return resposta_erro("Dados inválidos.", detalhes=erro.message_dict)
    except IntegrityError:
        return resposta_erro("Não foi possível salvar o registro.")


def marca_json(marca):
    return {"id": marca.id, "nome": marca.nome}


def veiculo_json(veiculo):
    return {
        "id": veiculo.id, "codigo": veiculo.codigo, "placa": veiculo.placa,
        "modelo": veiculo.modelo,
        "capacidade": veiculo.capacidade, "ano": veiculo.ano, "cor": veiculo.cor,
        "tipo": veiculo.tipo, "marca_id": veiculo.marca_id,
        "marca": marca_json(veiculo.marca),
    }


def reserva_json(reserva):
    return {
        "id": reserva.id, "solicitante": reserva.solicitante, "setor": reserva.setor,
        "atividade": reserva.atividade, "origem": reserva.origem, "destino": reserva.destino,
        "veiculo_id": reserva.veiculo_id, "veiculo": veiculo_json(reserva.veiculo),
        "numero_passageiros": reserva.numero_passageiros,
        "data_hora_saida": reserva.data_hora_saida.isoformat(),
        "data_hora_retorno": reserva.data_hora_retorno.isoformat(),
        "observacoes": reserva.observacoes,
    }


def buscar(modelo, identificador, mensagem, relacionamentos=()):
    try:
        return modelo.objects.select_related(*relacionamentos).get(pk=identificador)
    except (modelo.DoesNotExist, TypeError, ValueError):
        return resposta_erro(mensagem, status=404)


@csrf_exempt
def marcas(request):
    if request.method == "GET":
        return JsonResponse({"marcas": [marca_json(marca) for marca in Marca.objects.all()]})
    if request.method == "POST":
        dados, erro = ler_json(request)
        if erro:
            return erro
        nome = dados.get("nome")
        if not isinstance(nome, str) or not nome.strip():
            return resposta_erro("O campo 'nome' é obrigatório e não pode estar vazio.")
        marca = Marca(nome=nome.strip())
        return salvar(marca) or JsonResponse(marca_json(marca), status=201)
    return resposta_erro("Método não permitido.", status=405)


@csrf_exempt
def marca_detalhe(request, marca_id):
    marca = buscar(Marca, marca_id, "Marca não encontrada.")
    if isinstance(marca, JsonResponse):
        return marca
    if request.method == "GET":
        return JsonResponse(marca_json(marca))
    if request.method == "PUT":
        dados, erro = ler_json(request)
        if erro:
            return erro
        nome = dados.get("nome")
        if not isinstance(nome, str) or not nome.strip():
            return resposta_erro("O campo 'nome' é obrigatório e não pode estar vazio.")
        marca.nome = nome.strip()
        return salvar(marca) or JsonResponse(marca_json(marca))
    if request.method == "DELETE":
        try:
            marca.delete()
        except ProtectedError:
            return resposta_erro("Não é possível excluir uma marca que possui veículos.", status=409)
        return JsonResponse({"mensagem": "Marca excluída com sucesso."})
    return resposta_erro("Método não permitido.", status=405)


def preencher_veiculo(veiculo, dados):
    codigo = dados["codigo"]
    if not isinstance(codigo, str) or not codigo.strip():
        return resposta_erro("O campo 'codigo' é obrigatório e não pode estar vazio.")
    codigo = codigo.strip()
    if Veiculo.objects.filter(codigo=codigo).exclude(pk=veiculo.pk).exists():
        return resposta_erro("Já existe um veículo com este código.", status=409)

    veiculo.codigo = codigo
    for campo in ("placa", "modelo", "capacidade", "ano", "cor", "tipo"):
        setattr(veiculo, campo, dados[campo])
    marca = buscar(Marca, dados["marca_id"], "Marca não encontrada.")
    if isinstance(marca, JsonResponse):
        return marca
    veiculo.marca = marca


@csrf_exempt
def veiculos(request, veiculo_id=None):
    campos = ["codigo", "placa", "modelo", "capacidade", "ano", "cor", "tipo", "marca_id"]
    if veiculo_id is None:
        if request.method == "GET":
            itens = Veiculo.objects.select_related("marca")
            return JsonResponse({"veiculos": [veiculo_json(item) for item in itens]})
        if request.method == "POST":
            dados, erro = ler_json(request)
            if erro:
                return erro
            if erro := obrigatorios(dados, campos):
                return erro
            veiculo = Veiculo()
            return preencher_veiculo(veiculo, dados) or salvar(veiculo) or JsonResponse(veiculo_json(veiculo), status=201)
        return resposta_erro("Método não permitido.", status=405)

    veiculo = buscar(Veiculo, veiculo_id, "Veículo não encontrado.", ("marca",))
    if isinstance(veiculo, JsonResponse):
        return veiculo
    if request.method == "GET":
        return JsonResponse(veiculo_json(veiculo))
    if request.method == "PUT":
        dados, erro = ler_json(request)
        if erro:
            return erro
        if erro := obrigatorios(dados, campos):
            return erro
        return preencher_veiculo(veiculo, dados) or salvar(veiculo) or JsonResponse(veiculo_json(veiculo))
    if request.method == "DELETE":
        if veiculo.reservas.exists():
            return resposta_erro("Não é possível excluir um veículo que possui reservas.", status=409)
        veiculo.delete()
        return JsonResponse({"mensagem": "Veículo excluído com sucesso."})
    return resposta_erro("Método não permitido.", status=405)


def preencher_reserva(reserva, dados):
    campos = ("solicitante", "setor", "atividade", "origem", "destino", "numero_passageiros", "data_hora_saida", "data_hora_retorno")
    for campo in campos:
        setattr(reserva, campo, dados[campo])
    reserva.observacoes = dados.get("observacoes", "")
    veiculo = buscar(Veiculo, dados["veiculo_id"], "Veículo não encontrado.", ("marca",))
    if isinstance(veiculo, JsonResponse):
        return veiculo
    reserva.veiculo = veiculo


def normalizar_intervalo(saida_valor, retorno_valor):
    saida = parse_datetime(saida_valor) if isinstance(saida_valor, str) else saida_valor
    retorno = parse_datetime(retorno_valor) if isinstance(retorno_valor, str) else retorno_valor
    if not saida or not retorno:
        return resposta_erro("As datas devem estar no formato ISO 8601 válido.")
    if timezone.is_naive(saida):
        saida = timezone.make_aware(saida)
    if timezone.is_naive(retorno):
        retorno = timezone.make_aware(retorno)
    if saida < timezone.now():
        return resposta_erro("A data/hora de saída não pode estar no passado.")
    if retorno <= saida:
        return resposta_erro("A data/hora de retorno deve ser posterior à data/hora de saída.")
    return saida, retorno


def validar_reserva(reserva, reserva_id=None):
    for campo in ("solicitante", "setor", "atividade", "origem", "destino"):
        valor = getattr(reserva, campo)
        if not isinstance(valor, str) or not valor.strip():
            return resposta_erro(f"O campo '{campo}' é obrigatório e não pode estar vazio.")
    if not isinstance(reserva.observacoes, str):
        return resposta_erro("O campo 'observacoes' deve ser um texto.")
    try:
        if isinstance(reserva.numero_passageiros, bool):
            raise ValueError
        reserva.numero_passageiros = int(reserva.numero_passageiros)
    except (TypeError, ValueError):
        return resposta_erro("'numero_passageiros' deve ser um número inteiro maior que zero.")
    if reserva.numero_passageiros <= 0:
        return resposta_erro("'numero_passageiros' deve ser maior que zero.")
    if reserva.numero_passageiros > reserva.veiculo.capacidade:
        return resposta_erro("O número de passageiros excede a capacidade do veículo selecionado.")

    intervalo = normalizar_intervalo(reserva.data_hora_saida, reserva.data_hora_retorno)
    if isinstance(intervalo, JsonResponse):
        return intervalo
    reserva.data_hora_saida, reserva.data_hora_retorno = intervalo
    conflitos = Reserva.objects.filter(
        veiculo=reserva.veiculo,
        data_hora_saida__lt=reserva.data_hora_retorno,
        data_hora_retorno__gt=reserva.data_hora_saida,
    )
    if reserva_id is not None:
        conflitos = conflitos.exclude(pk=reserva_id)
    if conflitos.exists():
        return resposta_erro("O veículo já possui uma reserva sobreposta nesse período.")


def disponibilidade(request):
    if request.method != "GET":
        return resposta_erro("Método não permitido.", status=405)
    saida = request.GET.get("data_hora_saida")
    retorno = request.GET.get("data_hora_retorno")
    passageiros = request.GET.get("numero_passageiros")
    if saida is None or retorno is None or passageiros is None:
        return resposta_erro("Informe data_hora_saida, data_hora_retorno e numero_passageiros.")
    try:
        if isinstance(passageiros, bool):
            raise ValueError
        passageiros = int(passageiros)
    except (TypeError, ValueError):
        return resposta_erro("'numero_passageiros' deve ser um número inteiro maior que zero.")
    if passageiros <= 0:
        return resposta_erro("'numero_passageiros' deve ser maior que zero.")
    intervalo = normalizar_intervalo(saida, retorno)
    if isinstance(intervalo, JsonResponse):
        return intervalo
    saida, retorno = intervalo
    veiculos_com_conflito = Reserva.objects.filter(
        data_hora_saida__lt=retorno,
        data_hora_retorno__gt=saida,
    ).values("veiculo_id")
    veiculos = Veiculo.objects.select_related("marca").filter(
        capacidade__gte=passageiros,
    ).exclude(pk__in=veiculos_com_conflito)
    return JsonResponse({"veiculos": [veiculo_json(veiculo) for veiculo in veiculos]})


def dashboard(request):
    if request.method != "GET":
        return resposta_erro("Método não permitido.", status=405)
    por_trimestre = {f"{numero}º trimestre": 0 for numero in range(1, 5)}
    for reserva in Reserva.objects.only("data_hora_saida"):
        trimestre = ((reserva.data_hora_saida.month - 1) // 3) + 1
        por_trimestre[f"{trimestre}º trimestre"] += 1
    por_tipo = {
        Veiculo.Tipo.LEVE.label: 0,
        Veiculo.Tipo.COLETIVO.label: 0,
    }
    rotulos_por_tipo = {
        Veiculo.Tipo.LEVE: Veiculo.Tipo.LEVE.label,
        Veiculo.Tipo.COLETIVO: Veiculo.Tipo.COLETIVO.label,
    }
    for item in Reserva.objects.values("veiculo__tipo").annotate(total=Count("id")):
        rotulo = rotulos_por_tipo.get(item["veiculo__tipo"])
        if rotulo:
            por_tipo[rotulo] = item["total"]
    return JsonResponse({
        "total_reservas": Reserva.objects.count(),
        "total_veiculos": Veiculo.objects.count(),
        "reservas_por_trimestre": por_trimestre,
        "reservas_por_tipo_veiculo": por_tipo,
    })


@csrf_exempt
def reservas(request, reserva_id=None):
    campos = ["solicitante", "setor", "atividade", "origem", "destino", "veiculo_id", "numero_passageiros", "data_hora_saida", "data_hora_retorno"]
    if reserva_id is None:
        if request.method == "GET":
            itens = Reserva.objects.select_related("veiculo__marca")
            return JsonResponse({"reservas": [reserva_json(item) for item in itens]})
        if request.method == "POST":
            dados, erro = ler_json(request)
            if erro:
                return erro
            if erro := obrigatorios(dados, campos):
                return erro
            reserva = Reserva()
            return preencher_reserva(reserva, dados) or validar_reserva(reserva) or salvar(reserva) or JsonResponse(reserva_json(reserva), status=201)
        return resposta_erro("Método não permitido.", status=405)

    reserva = buscar(Reserva, reserva_id, "Reserva não encontrada.", ("veiculo__marca",))
    if isinstance(reserva, JsonResponse):
        return reserva
    if request.method == "GET":
        return JsonResponse(reserva_json(reserva))
    if request.method == "PUT":
        dados, erro = ler_json(request)
        if erro:
            return erro
        if erro := obrigatorios(dados, campos):
            return erro
        return preencher_reserva(reserva, dados) or validar_reserva(reserva, reserva.id) or salvar(reserva) or JsonResponse(reserva_json(reserva))
    if request.method == "DELETE":
        reserva.delete()
        return JsonResponse({"mensagem": "Reserva excluída com sucesso."})
    return resposta_erro("Método não permitido.", status=405)
