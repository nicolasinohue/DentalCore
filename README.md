# DentalCore (Django)

Aplicacao completa para consultorio odontologico com:

- Autenticacao (login, logout e cadastro)
- Cadastro de pacientes (CRUD) com busca e paginacao
- Cadastro de consultas (CRUD) com busca, paginacao e duracao individual
- Cancelamento de consultas preservando historico da agenda
- Perfil detalhado do paciente com consultas e historico recentes
- Agenda com filtro por dia, semana e mes
- Calendario visual mensal com contagem de consultas por dia
- Prontuario odontologico detalhado com abas clinicas
- Anamnese estruturada, odontograma, evolucao clinica, consultas e documentos anexados
- Exportacao de prontuario em PDF
- Bloqueio de conflito de horario considerando duracao da consulta
- Dashboard com seletor de dia, mes ou ano atual, status, cancelamento, minutos ocupados e metricas do periodo selecionado
- Perfis basicos de acesso (Administrador, Dentista e Recepcao)
- Auditoria basica de criacao/alteracao para consultas e historico clinico
- Banco SQL com suporte a PostgreSQL para producao

## Requisitos

- Python 3.10+

## Como executar em desenvolvimento

1. Instale as dependencias:

```bash
pip install -r requirements.txt
```

2. Rode as migracoes:

```bash
python manage.py migrate
```

3. Crie um usuario administrador (opcional):

```bash
python manage.py createsuperuser
```

4. Inicie o servidor:

```bash
python manage.py runserver
```

5. Acesse:

- Aplicacao: http://127.0.0.1:8000/
- Admin: http://127.0.0.1:8000/admin/

## PostgreSQL e producao

1. Copie o arquivo de exemplo de ambiente:

```bash
cp .env.example .env
```

2. Ajuste as variaveis no arquivo .env, especialmente:

- SECRET_KEY
- DEBUG=false
- ALLOWED_HOSTS
- CSRF_TRUSTED_ORIGINS
- DATABASE_URL=postgresql://usuario:senha@host:5432/banco
- ALLOW_PUBLIC_REGISTRATION=false
- DEFAULT_APPOINTMENT_DURATION_MINUTES=60
- SECURE_HSTS_SECONDS=31536000
- SECURE_HSTS_INCLUDE_SUBDOMAINS=true
- SECURE_HSTS_PRELOAD=true

Por padrao, o cadastro publico fica desativado. Crie usuarios pelo admin ou habilite
temporariamente `ALLOW_PUBLIC_REGISTRATION=true` apenas quando for necessario.

3. Instale dependencias e rode migracoes:

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
```

4. Execute em modo producao com Gunicorn:

```bash
gunicorn config.wsgi
```

## Estrutura principal

- `config/`: configuracoes do projeto Django (inclui suporte a PostgreSQL)
- `app/models.py`: modelos SQL (Paciente, Consulta e Prontuario)
- `app/views.py`: regras de negocio e views
- `app/forms.py`: formularios e validacoes
- `app/templates/`: frontend HTML
- `app/static/css/styles.css`: estilos da interface
