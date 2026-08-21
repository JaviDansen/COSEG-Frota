from django.db import models


class Marca(models.Model):
    nome = models.CharField(max_length=100)

    def __str__(self):
        return self.nome


class Veiculo(models.Model):
    class Tipo(models.TextChoices):
        VAN = "Van", "Van"
        CARRO_DE_PASSEIO = "Carro de passeio", "Carro de passeio"

    codigo = models.CharField(max_length=10, unique=True)
    placa = models.CharField(max_length=10, unique=True)
    modelo = models.CharField(max_length=100)
    capacidade = models.PositiveIntegerField()
    ano = models.PositiveIntegerField()
    cor = models.CharField(max_length=50)
    marca = models.ForeignKey(
        Marca, on_delete=models.PROTECT, related_name="veiculos"
    )
    tipo = models.CharField(max_length=20, choices=Tipo.choices)

    def __str__(self):
        return f"{self.codigo} - {self.modelo} ({self.placa})"


class Reserva(models.Model):
    solicitante = models.CharField(max_length=100)
    setor = models.CharField(max_length=100)
    atividade = models.CharField(max_length=200)
    origem = models.CharField(max_length=100)
    destino = models.CharField(max_length=100)
    veiculo = models.ForeignKey(
        Veiculo, on_delete=models.PROTECT, related_name="reservas"
    )
    numero_passageiros = models.PositiveIntegerField()
    data_hora_saida = models.DateTimeField()
    data_hora_retorno = models.DateTimeField()
    observacoes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.solicitante}: {self.origem} → {self.destino}"
