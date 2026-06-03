# DentalCore — Guia Técnico e de Execução

## 1) Visão Geral

O **DentalCore** é um sistema web para clínica odontológica focado na operação do dia a dia:

- gestão de pacientes com busca e paginação;
- gestão de consultas com duração individual;
- agenda com visual de calendário;
- prontuário odontológico completo;
- indicadores de desempenho no dashboard.

O objetivo da aplicação é centralizar o fluxo clínico e administrativo em uma única interface, com autenticação, banco SQL e estrutura pronta para produção.

---

## 2) Funcionalidades da Aplicação

### 2.1 Autenticação e Acesso

- login e logout;
- cadastro público desativado por padrão;
- criação de usuários pelo admin ou por cadastro público temporariamente habilitado;
- perfis básicos: Administrador, Dentista e Recepcao;
- proteção de rotas com usuário autenticado.

### 2.2 Pacientes

- CRUD completo de pacientes;
- busca por nome, CPF, telefone ou observações;
- listagem paginada.
- detalhe do paciente com dados cadastrais, consultas recentes e histórico clínico recente.

### 2.3 Consultas e Agenda

- CRUD completo de consultas;
- filtro por período;
- busca por paciente, CPF, procedimento, status ou observações;
- paginação na lista de consultas;
- filtro por status;
- cancelamento de consulta sem remover o registro da agenda;
- exibição de horário de término calculado pela duração;
- calendário mensal com contagem de consultas por dia;
- bloqueio de sobreposição real de horário para consultas ativas;
- duração individual por consulta, com padrão configurável por variável de ambiente.

### 2.4 Prontuário Odontológico

- navegação por abas: Anamnese, Odontograma, Evolução, Consultas e Documentos;
- anamnese estruturada com histórico médico, doenças sistêmicas, alergias, medicações, cirurgias, sangramento, gestação, pressão arterial, histórico odontológico, hábitos e plano de tratamento;
- odontograma com edição e remoção de registros por dente;
- evolução clínica com criação, edição e remoção de procedimentos;
- consultas recentes do paciente no próprio prontuário;
- upload e remoção de documentos anexados ao paciente;
- exportação em PDF com anamnese estruturada, odontograma, evolução clínica e documentos anexados.

### 2.5 Dashboard

- totais gerais (pacientes/consultas);
- seletor entre dia atual, mês atual e ano atual;
- métricas do período selecionado (consultas, cancelamentos e taxa de retorno);
- procedimentos mais comuns do período selecionado;
- consultas do período selecionado;
- status do período, percentual de cancelamento e minutos ocupados;
- tempo ocupado por procedimento;
- gráfico visual local em HTML/CSS para apoio à análise.

---

## 3) Arquitetura Técnica

A aplicação segue a arquitetura padrão do Django com separação em camadas:

- **Modelos (ORM):** representam entidades e regras de dados.
- **Formulários:** validam entrada e regras de negócio (ex.: conflito de horário por duração).
- **Views:** orquestram regras, filtros e respostas HTTP.
- **Templates:** renderização server-side com HTML dinâmico.
- **Static:** arquivos de estilo e recursos visuais.
- **Permissões:** perfis de acesso para recepção, dentista e administrador.

Fluxo resumido:

1. usuário autenticado acessa uma funcionalidade;
2. dados entram por formulário validado;
3. regras são aplicadas na camada de view/form;
4. persistência ocorre via ORM no banco SQL;
5. resultado é renderizado no template.

---

## 4) Tecnologias Utilizadas

- **Python:** linguagem principal do backend.
- **Django 5.2.14:** framework web (rotas, auth, ORM, admin e segurança).
- **SQLite (dev):** banco padrão local.
- **PostgreSQL (produção):** banco recomendado para ambientes reais.
- **dj-database-url:** configuração de banco via variável `DATABASE_URL`.
- **psycopg[binary]:** driver PostgreSQL.
- **Whitenoise:** entrega de arquivos estáticos em produção.
- **Gunicorn:** servidor WSGI para execução em produção.
- **ReportLab:** geração de PDF do prontuário.
- **HTML/CSS local:** gráfico do dashboard, sem dependência de CDN externa.
- **HTML + CSS + Django Templates:** frontend server-rendered.

---

## 5) Como Subir a Aplicação

### 5.1 Opção Rápida (ambiente já pronto)

```powershell
cd "c:\Users\win\Desktop\Dev\Pessoal\Python\Odontologia"
.\.venv\Scripts\python.exe manage.py runserver
```

Acesso:

- aplicação: <http://127.0.0.1:8000/>
- admin: <http://127.0.0.1:8000/admin/>

### 5.2 Ambiente Local do Zero (SQLite)

Pré-requisito: Python 3.10+

#### Windows (PowerShell)

```powershell
cd "c:\Users\win\Desktop\Dev\Pessoal\Python\Odontologia"
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

#### Linux/macOS (bash/zsh)

```bash
cd /caminho/para/Odontologia
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### 5.3 Local com PostgreSQL

Passos:

1. criar banco e usuário no PostgreSQL;
2. criar arquivo `.env` com variáveis de ambiente.

O arquivo `.env`, quando existir na raiz do projeto, é carregado automaticamente pelo `config/settings.py` sem sobrescrever variáveis já definidas no ambiente.

Exemplo:

```bash
SECRET_KEY=sua-chave-forte-aqui
DEBUG=true
ALLOWED_HOSTS=127.0.0.1,localhost
CSRF_TRUSTED_ORIGINS=http://127.0.0.1:8000,http://localhost:8000
DATABASE_URL=postgresql://usuario:senha@localhost:5432/odontologia_db
ALLOW_PUBLIC_REGISTRATION=false
DEFAULT_APPOINTMENT_DURATION_MINUTES=60
```

Rodar:

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### 5.4 Produção com Gunicorn (Linux)

```bash
cd /caminho/para/Odontologia
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export SECRET_KEY="chave-forte"
export DEBUG=false
export ALLOWED_HOSTS="seu-dominio.com,www.seu-dominio.com"
export CSRF_TRUSTED_ORIGINS="https://seu-dominio.com,https://www.seu-dominio.com"
export DATABASE_URL="postgresql://usuario:senha@host:5432/banco"
export ALLOW_PUBLIC_REGISTRATION=false
export DEFAULT_APPOINTMENT_DURATION_MINUTES=60

python manage.py migrate
python manage.py collectstatic --noinput
gunicorn config.wsgi --bind 0.0.0.0:8000 --workers 3 --timeout 120
```

### 5.5 Deploy com Procfile (Render/Railway/Heroku-like)

Build:

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
```

Start:

```bash
gunicorn config.wsgi --log-file -
```

Variáveis obrigatórias:

- `SECRET_KEY`
- `DEBUG=false`
- `ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS`
- `DATABASE_URL`

Variáveis recomendadas:

- `ALLOW_PUBLIC_REGISTRATION=false`
- `DEFAULT_APPOINTMENT_DURATION_MINUTES=60`
- `SECURE_HSTS_SECONDS=31536000`
- `SECURE_HSTS_INCLUDE_SUBDOMAINS=true`
- `SECURE_HSTS_PRELOAD=true`

Por padrão, novos usuários devem ser criados pelo admin. Para abrir cadastro temporariamente, configure `ALLOW_PUBLIC_REGISTRATION=true`.

Após criar usuários, associe-os aos grupos adequados no admin:

- `Administrador`: acesso amplo ao sistema;
- `Dentista`: agenda, pacientes e prontuário clínico;
- `Recepcao`: agenda e pacientes, sem edição de prontuário clínico.

### 5.6 Alternativas

Via atalho `run.py`:

```bash
python run.py
```

Sem ativar ambiente virtual (caminho direto no Windows):

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

---

## 6) Checklist de Validação

```bash
python manage.py check
python manage.py test
python manage.py showmigrations
```

No Windows, usando o ambiente virtual local:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe manage.py showmigrations
```

Estado atual esperado:

- `manage.py check`: sem issues;
- `manage.py test`: suíte automatizada passando;
- migrações do app aplicadas.

---

## 7) Problemas Comuns

- **Erro de import (`No module named ...`):**
  - execute `pip install -r requirements.txt`.

- **Falha ao conectar no PostgreSQL:**
  - revise `DATABASE_URL`, usuário, senha e porta.

- **Erro `DisallowedHost`:**
  - inclua domínio/IP em `ALLOWED_HOSTS`.

- **Static não carrega em produção:**
  - execute `python manage.py collectstatic --noinput`.

- **Cadastro aparece indisponível:**
  - este é o padrão seguro do projeto;
  - crie usuários pelo admin ou habilite `ALLOW_PUBLIC_REGISTRATION=true`.

- **Consulta bloqueada por conflito de horário:**
  - a validação considera a duração individual da consulta;
  - `DEFAULT_APPOINTMENT_DURATION_MINUTES` define o padrão usado para novas consultas;
  - consultas canceladas não bloqueiam o horário;
  - consultas consecutivas são permitidas quando a anterior termina exatamente no início da próxima.

- **Consulta no passado ou status concluído:**
  - novas consultas não podem ser criadas no passado;
  - uma consulta futura não pode ser marcada como concluída antes do horário agendado.

- **PDF com texto muito longo:**
  - o prontuário usa geração paginada com quebra de texto;
  - se ainda houver conteúdo específico demais para caber bem, revise o texto ou amplie o layout do PDF.

---

## 8) Observações

- O projeto atualmente **não possui Dockerfile / docker-compose**.
- Se necessário, pode ser adicionada uma stack Docker para dev e produção.
- O sistema segue o modelo de **clínica única**: usuários autenticados compartilham a mesma base de pacientes e consultas.
- A restrição de sobreposição de agenda é feita na camada de formulário; o banco ainda impede apenas horários ativos exatamente iguais.
- Consultas concluídas criam automaticamente um registro clínico relacionado quando ainda não houver histórico para aquela consulta.
