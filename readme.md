# Ben Juan Restaurant — Django + banco de dados 🍽️

Versão do projeto de portfólio com **back-end de verdade**: além de servir
os templates HTML/CSS/JS, o Django agora guarda em banco de dados o
**cardápio**, os **pedidos** e as **reservas**, com uma API própria que o
JavaScript do site consome via `fetch()`.

O restaurante continua sendo fictício (os avisos ao clicar em
Instagram/WhatsApp continuam lá, e o pagamento do app de pedidos continua
simulado) — o que mudou é que agora existe persistência real por trás da
interface.

## O que é real agora

| Antes (100% front-end)                          | Agora (Django + banco)                                   |
|--------------------------------------------------|------------------------------------------------------------|
| Cardápio do app de pedidos hardcoded em JS       | Model `ItemCardapio`, editável em `/admin/`                |
| Pedidos só na memória da aba aberta               | Model `Pedido`, salvo no banco, com API `/api/pedidos/`     |
| Reservas só na memória da aba aberta              | Model `Reserva`, salvo no banco, com API `/api/reservas/`   |
| "Painel da equipe" só mostrava dados fictícios    | Painel real (🔒 Acesso da equipe) lê pedidos/reservas do banco, com atualização automática (polling) a cada 4s |
| Checagem de horário ocupado feita só em JS        | `UniqueConstraint` no banco garante isso mesmo com 2 pessoas reservando ao mesmo tempo |

O **"Modo demonstração"** (link "Ver com dados fictícios de demonstração",
dentro do app de pedidos) continua existindo à parte, com dados 100% em
memória — útil pra mostrar a interface cheia sem precisar criar pedidos e
reservas reais toda vez que for demonstrar o projeto.

## Estrutura

```
benjuan_project/
├── manage.py
├── requirements.txt
├── benjuan/                     # configuração do projeto
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
└── restaurante/                  # app Django
    ├── models.py                # ItemCardapio, Pedido, Reserva
    ├── admin.py                 # gerenciamento via /admin/
    ├── views.py                 # páginas + endpoints da API
    ├── urls.py
    ├── migrations/
    │   ├── 0001_initial.py
    │   └── 0002_seed_cardapio.py # popula o cardápio inicial automaticamente
    ├── templates/restaurante/
    │   ├── index.html
    │   ├── pedidos.html
    │   └── reserva.html
    └── static/restaurante/
        ├── css/style.css
        └── img/quiosque-foto.jpg
```

## Como rodar localmente

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements.txt

python manage.py migrate           # cria as tabelas e já popula o cardápio
python manage.py createsuperuser   # opcional, pra acessar /admin/

python manage.py runserver
```

Depois abra:
- `http://127.0.0.1:8000/` → página inicial
- `http://127.0.0.1:8000/pedidos/` → app de pedidos (cliente)
- `http://127.0.0.1:8000/reserva/` → reserva de mesa
- `http://127.0.0.1:8000/admin/` → gerenciar cardápio, pedidos e reservas direto no banco

## Testando o fluxo real ponta a ponta

1. Abra `/pedidos/`, adicione itens ao carrinho e confirme o pedido —
   isso já cria um registro em `Pedido` no banco.
2. Clique em **"🔒 Acesso da equipe"** — diferente de antes, esse botão
   agora carrega os pedidos e reservas **reais** do banco (não dados
   fictícios). Se você abrir a mesma URL em outra aba/dispositivo, o
   pedido aparece lá também.
3. Avance o status do pedido, mova pra lixeira, restaure — tudo isso
   grava no banco via a API (`restaurante/views.py`).
4. Abra `/admin/` com o superusuário criado acima pra ver os mesmos
   dados de outro ângulo (útil pra debug ou correções manuais).

## Endpoints da API (uso interno do front-end)

Todos retornam JSON e a maioria exige o cookie de CSRF (já configurado
nas páginas `pedidos.html` e `reserva.html` via `ensure_csrf_cookie`).

| Método | Rota                                  | Descrição |
|--------|----------------------------------------|-----------|
| GET    | `/api/cardapio/`                       | Cardápio agrupado por categoria |
| POST   | `/api/estoque/<item_id>/`              | Alterna "esgotado" de um item |
| GET    | `/api/pedidos/`                        | Lista todos os pedidos |
| POST   | `/api/pedidos/novo/`                   | Cria um pedido a partir do carrinho |
| POST   | `/api/pedidos/<id>/avancar/`           | Avança o status (recebido → preparando → pronto) |
| POST   | `/api/pedidos/<id>/pagamento/`         | Marca pagamento como aprovado |
| POST   | `/api/pedidos/<id>/excluir/`           | Move pra lixeira (soft delete) |
| POST   | `/api/pedidos/<id>/restaurar/`         | Restaura da lixeira |
| POST   | `/api/pedidos/<id>/apagar/`            | Apaga definitivamente |
| GET    | `/api/reservas/?data=AAAA-MM-DD`       | Horários ocupados nesse dia |
| GET    | `/api/reservas/`                       | Lista todas as reservas |
| POST   | `/api/reservas/nova/`                  | Cria uma reserva |
| POST   | `/api/reservas/<id>/excluir/`          | Move pra lixeira |
| POST   | `/api/reservas/<id>/restaurar/`        | Restaura da lixeira |
| POST   | `/api/reservas/<id>/apagar/`           | Apaga definitivamente |

## Publicando

Como agora existe banco de dados de verdade, o GitHub Pages **não serve
mais** (ele só hospeda arquivos estáticos). Pra publicar, escolha um
serviço que rode Python/Django, por exemplo Render, Railway ou
PythonAnywhere (todos têm free tier). Antes do deploy:

```bash
python manage.py collectstatic
```

E em `benjuan/settings.py`:
- `DEBUG = False`
- `ALLOWED_HOSTS = ["seu-dominio.com"]`
- troque `SECRET_KEY` por um valor novo (idealmente via variável de ambiente)
- troque o banco `sqlite3` por Postgres se o serviço escolhido não
  persistir arquivos locais entre deploys (Render e Railway, por
  exemplo, costumam oferecer um Postgres gratuito à parte)

## Próximos passos sugeridos

- Autenticação real para o "Acesso da equipe" (hoje qualquer visitante
  pode clicar no botão e ver o painel — dá pra proteger com
  `django.contrib.auth` + `@login_required` nas views/endpoints da equipe).
- WebSockets (Django Channels) no lugar do polling a cada 4s, pra
  atualização instantânea do painel.
- Cardápio de vitrine do `index.html` (fotos e descrições) também vindo
  do banco, unificando com o `ItemCardapio` usado no app de pedidos.
