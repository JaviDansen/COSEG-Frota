# Sistema de Gestão de Veículos — COSEG

## Sobre o projeto

O COSEG necessita centralizar o controle de reservas de veículos para reduzir conflitos de agendamento, registros inconsistentes e a utilização de veículos com capacidade inadequada. Este repositório contém o back-end desenvolvido para o PBL 1 de Programação Web, construído para gerenciar marcas, veículos e reservas.

## Tecnologias utilizadas

- Python
- Django
- SQLite

## Funcionalidades

- Gerenciamento de marcas, veículos e reservas por API JSON.
- Validação da capacidade do veículo e da quantidade de passageiros.
- Validação do período da reserva, incluindo bloqueio de saídas no passado.
- Detecção de conflitos de horários para o mesmo veículo.
- Consulta de disponibilidade por período e quantidade de passageiros.
- Dashboard com totais, utilização trimestral e utilização por tipo de veículo.
- Gerenciamento dos dados também pelo Django Admin.

## Modelagem

### Marca

- `id`
- `nome`

### Veículo

- `id`
- `codigo`
- `placa`
- `modelo`
- `capacidade`
- `ano`
- `cor`
- `marca`
- `tipo`

### Reserva

- `id`
- `solicitante`
- `setor`
- `atividade`
- `origem`
- `destino`
- `veiculo`
- `numero_passageiros`
- `data_hora_saida`
- `data_hora_retorno`
- `observacoes`

Relacionamentos:

- Marca 1:N Veículo
- Veículo 1:N Reserva

Os tipos de veículo disponíveis são **Veículo Leve (VL)** e **Veículo Coletivo (Van) (VC)**.

## Regras de negócio principais

- A quantidade de passageiros deve ser maior que zero.
- Cada reserva está associada a um único veículo.
- Nesta versão, a quantidade máxima aceita por reserva é 18 passageiros.
- Solicitações que necessitem transportar mais de 18 passageiros não são atendidas pelo fluxo atual.
- A quantidade de passageiros não pode superar a capacidade do veículo.
- O retorno deve ser posterior à saída.
- Reservas com saída no passado não são permitidas.
- Um veículo não pode possuir reservas com períodos sobrepostos.
- Períodos adjacentes são permitidos: uma reserva pode terminar exatamente quando outra começa.
- Alterações de reserva revalidam as regras de negócio.
- Toda reserva deve estar associada a um veículo válido.

## Como executar o projeto

No Windows, usando PowerShell:

1. Clone o repositório.

   ```powershell
   git clone https://github.com/JaviDansen/ProgramacaoWeb.git
   ```

2. Entre na pasta do projeto.

   ```powershell
   cd ProgramacaoWeb
   ```

3. Crie o ambiente virtual.

   ```powershell
   python -m venv .venv
   ```

4. Ative o ambiente virtual.

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

5. Instale as dependências.

   ```powershell
   pip install -r requirements.txt
   ```

6. Aplique as migrations.

   ```powershell
   python manage.py migrate
   ```

7. Insira os dados iniciais.

   ```powershell
   python manage.py seed_data
   ```

8. Opcionalmente, para utilizar o Django Admin, crie um superusuário.

   ```powershell
   python manage.py createsuperuser
   ```

9. Execute o servidor de desenvolvimento.

   ```powershell
   python manage.py runserver
   ```

A API estará disponível a partir de `http://127.0.0.1:8000/api/`. O Django Admin estará disponível em `http://127.0.0.1:8000/admin/`.

## Dados iniciais

O comando abaixo cria a carga inicial do projeto:

```powershell
python manage.py seed_data
```

A carga possui 6 marcas, 10 veículos e 4 reservas. O comando usa operações idempotentes para que possa ser executado novamente sem duplicar os registros controlados.

## API

As rotas da API possuem o prefixo `/api/` e retornam respostas JSON.

### Marcas

- `GET /api/marcas/` — lista marcas.
- `POST /api/marcas/` — cria uma marca.
- `GET /api/marcas/<id>/` — consulta uma marca.
- `PUT /api/marcas/<id>/` — atualiza uma marca.
- `DELETE /api/marcas/<id>/` — exclui uma marca, quando não há veículos associados.

### Veículos

- `GET /api/veiculos/` — lista veículos.
- `POST /api/veiculos/` — cria um veículo.
- `GET /api/veiculos/<id>/` — consulta um veículo.
- `PUT /api/veiculos/<id>/` — atualiza um veículo.
- `DELETE /api/veiculos/<id>/` — exclui um veículo, quando não há reservas associadas.

### Reservas

- `GET /api/reservas/` — lista reservas.
- `POST /api/reservas/` — cria uma reserva após validar as regras de negócio.
- `GET /api/reservas/<id>/` — consulta uma reserva.
- `PUT /api/reservas/<id>/` — atualiza uma reserva e revalida as regras.
- `DELETE /api/reservas/<id>/` — exclui uma reserva.

### Disponibilidade

- `GET /api/disponibilidade/` — informa os veículos disponíveis.

Parâmetros obrigatórios:

- `data_hora_saida` — data e hora no formato ISO 8601.
- `data_hora_retorno` — data e hora no formato ISO 8601.
- `numero_passageiros` — quantidade de passageiros.

A consulta considera a capacidade mínima e a ausência de reservas em conflito com o período informado.

### Dashboard

- `GET /api/dashboard/` — retorna o total de reservas, total de veículos, reservas por trimestre e reservas por tipo de veículo.

## Testes automatizados

Execute a suíte de testes com:

```powershell
python manage.py test
```

A versão atual possui 16 testes automatizados. A cobertura inclui marca, veículo, reserva, capacidade, períodos inválidos, data passada, conflitos, períodos adjacentes, revalidação no `PUT`, disponibilidade e dashboard.

## Estrutura principal

```text
ProgramacaoWeb/
├── core/
├── reservas/
│   ├── management/
│   │   └── commands/
│   │       └── seed_data.py
│   ├── migrations/
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── tests.py
│   ├── urls.py
│   └── views.py
├── manage.py
├── requirements.txt
└── README.md
```

## Observação sobre o PBL

Este repositório corresponde à implementação do back-end do PBL 1. A integração com uma interface completa e o suporte à alocação de múltiplos veículos para uma solicitação fazem parte de evoluções posteriores do projeto.
