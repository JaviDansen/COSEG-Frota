import json

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.http import JsonResponse
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
        "id": veiculo.id, "placa": veiculo.placa, "modelo": veiculo.modelo,
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
def marcas(request, marca_id=None):
    if marca_id is None:
        if request.method == "GET":
            return JsonResponse({"marcas": [marca_json(marca) for marca in Marca.objects.all()]})
        if request.method == "POST":
            dados, erro = ler_json(request)
            if erro:
                return erro
            if erro := obrigatorios(dados, ["nome"]):
                return erro
            marca = Marca(nome=dados["nome"])
            return salvar(marca) or JsonResponse(marca_json(marca), status=201)
        return resposta_erro("Método não permitido.", status=405)

    marca = buscar(Marca, marca_id, "Marca não encontrada.")
    if isinstance(marca, JsonResponse):
        return marca
    if request.method == "GET":
        return JsonResponse(marca_json(marca))
    if request.method == "PUT":
        dados, erro = ler_json(request)
        if erro:
            return erro
        if erro := obrigatorios(dados, ["nome"]):
            return erro
        marca.nome = dados["nome"]
        return salvar(marca) or JsonResponse(marca_json(marca))
    if request.method == "DELETE":
        if marca.veiculos.exists():
            return resposta_erro("Não é possível excluir uma marca que possui veículos.", status=409)
        marca.delete()
        return JsonResponse({"mensagem": "Marca excluída com sucesso."})
    return resposta_erro("Método não permitido.", status=405)


def preencher_veiculo(veiculo, dados):
    for campo in ("placa", "modelo", "capacidade", "ano", "cor", "tipo"):
        setattr(veiculo, campo, dados[campo])
    marca = buscar(Marca, dados["marca_id"], "Marca não encontrada.")
    if isinstance(marca, JsonResponse):
        return marca
    veiculo.marca = marca


@csrf_exempt
def veiculos(request, veiculo_id=None):
    campos = ["placa", "modelo", "capacidade", "ano", "cor", "tipo", "marca_id"]
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
    campos = ("solicitante", "setor", "atividade", "origem", "destino", "numero_passageiros", "data_hora_saida", "data_hora_retorno", "observacoes")
    for campo in campos:
        setattr(reserva, campo, dados[campo])
    veiculo = buscar(Veiculo, dados["veiculo_id"], "Veículo não encontrado.", ("marca",))
    if isinstance(veiculo, JsonResponse):
        return veiculo
    reserva.veiculo = veiculo


@csrf_exempt
def reservas(request, reserva_id=None):
    campos = ["solicitante", "setor", "atividade", "origem", "destino", "veiculo_id", "numero_passageiros", "data_hora_saida", "data_hora_retorno", "observacoes"]
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
            return preencher_reserva(reserva, dados) or salvar(reserva) or JsonResponse(reserva_json(reserva), status=201)
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
        return preencher_reserva(reserva, dados) or salvar(reserva) or JsonResponse(reserva_json(reserva))
    if request.method == "DELETE":
        reserva.delete()
        return JsonResponse({"mensagem": "Reserva excluída com sucesso."})
    return resposta_erro("Método não permitido.", status=405)
