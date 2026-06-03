# DentalCore

Guia técnico, funcional e de execução do **DentalCore**, uma aplicação Django para gestão de clínica odontológica.

O objetivo da aplicação é centralizar o fluxo clínico e administrativo em uma única interface, com autenticação, banco SQL, agenda operacional, prontuário odontológico e estrutura preparada para produção.

## Visão Geral

O DentalCore apoia a operação diária de uma clínica odontológica com:

- gestão de pacientes com busca, paginação e perfil detalhado;
- gestão de consultas com duração individual, status e regras de conflito;
- agenda visual por dia, semana e mês;
- prontuário odontológico com anamnese, odontograma, evolução, consultas e documentos;
- dashboard com indicadores do período selecionado;
- perfis básicos de acesso para Administrador, Dentista e Recepcao;
- banco SQL local com suporte a PostgreSQL em produção.

## Funcionalidades

### Autenticação e Acesso

- login e logout;
- cadastro público desativado por padrão;
- criação de usuários pelo admin ou por cadastro público temporariamente habilitado;
- perfis básicos: Administrador, Dentista e Recepcao;
- proteção de rotas por autenticação e função.

### Pacientes

- CRUD completo de pacientes;
- busca por nome, CPF, telefone ou observações;
- listagem paginada;
- detalhe do paciente com dados cadastrais, consultas recentes e histórico clínico recente.

### Consultas e Agenda

- CRUD completo de consultas;
- filtro por período: dia, semana e mês;
- busca por paciente, CPF, procedimento, status ou observações;
- paginação na lista de consultas;
- filtro por status;
- cancelamento de consulta sem remover o registro da agenda;
- exibição de horário de término calculado pela duração;
- calendário mensal com contagem de consultas por dia;
- agenda operacional com blocos por dia e horário;
- totais rápidos de consultas, agendadas, concluídas, canceladas e atrasadas;
- destaque visual para consulta atrasada e próxima consulta ativa;
- cartões de consulta com paciente, telefone, procedimento, duração, status e ações rápidas;
- contexto do paciente e do horário atual ao editar uma consulta;
- mensagem específica quando uma edição altera data/hora ou duração, tratando como reagendamento;
- bloqueio de sobreposição real de horário para consultas ativas;
- consultas canceladas não bloqueiam horário;
- consultas consecutivas são permitidas quando a anterior termina exatamente no início da próxima;
- duração individual por consulta, com padrão configurável por variável de ambiente.

### Prontuário Odontológico

- navegação por abas: Anamnese, Odontograma, Evolução, Consultas e Documentos;
- anamnese estruturada com histórico médico, doenças sistêmicas, alergias, medicações, cirurgias, sangramento, gestação, pressão arterial, histórico odontológico, hábitos e plano de tratamento;
- odontograma com edição e remoção de registros por dente;
- evolução clínica com criação, edição e remoção de procedimentos;
- consultas recentes do paciente no próprio prontuário;
- upload e remoção de documentos anexados ao paciente;
- exportação em PDF com anamnese estruturada, odontograma, evolução clínica e documentos anexados.

### Dashboard

- totais gerais de pacientes e consultas;
- seletor entre dia atual, mês atual e ano atual;
- métricas do período selecionado;
- consultas agendadas, concluídas e canceladas no período;
- taxa de cancelamento;
- pacientes recorrentes;
- minutos ocupados;
- procedimentos mais comuns;
- tempo ocupado por procedimento;
- gráfico visual local em HTML/CSS.

## Arquitetura Técnica

A aplicação segue a arquitetura padrão do Django:

- **Modelos (ORM):** representam pacientes, consultas, prontuários, odontograma, histórico clínico e anexos.
- **Formulários:** validam entrada e regras de negócio, incluindo conflitos de agenda.
- **Views:** orquestram filtros, permissões, mensagens e respostas HTTP.
- **Templates:** renderizam a interface server-side.
- **Static:** concentra os estilos da aplicação.
- **Permissões:** separam acessos de Administrador, Dentista e Recepcao.

Fluxo básico:

1. usuário autenticado acessa uma funcionalidade;
2. dados entram por formulário validado;
3. regras são aplicadas na camada de view/form;
4. persistência ocorre via ORM;
5. resultado é renderizado em templates Django.

## Tecnologias

- Python 3.10+
- Django 5.2.14
- SQLite para desenvolvimento local
- PostgreSQL recomendado para produção
- dj-database-url
- psycopg[binary]
- WhiteNoise
- Gunicorn
- ReportLab
- HTML, CSS e Django Templates

## Estrutura Principal

- `config/`: configurações do projeto Django.
- `app/models.py`: modelos SQL.
- `app/forms.py`: formulários e validações.
- `app/views.py`: regras de negócio e views.
- `app/permissions.py`: regras de acesso por função.
- `app/templates/`: templates HTML.
- `app/static/css/styles.css`: estilos da interface.
- `app/tests.py`: suíte automatizada.
- `app/migrations/`: migrações do banco.
- `Procfile`: comando de execução para plataformas tipo Render/Railway/Heroku.
- `.env.example`: exemplo de variáveis de ambiente.

## Como Subir Localmente

### Opção Rápida

No ambiente atual do projeto:

Exemplo de caminho do projeto no Windows:

```powershell
cd "C:\caminho\para\DentalCore"
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

Acesse:

- aplicação: `http://<host-local>:<porta>/`
- admin: `http://<host-local>:<porta>/admin/`

Exemplo comum em desenvolvimento:

- aplicação: `http://127.0.0.1:8000/`
- admin: `http://127.0.0.1:8000/admin/`

### Ambiente Local do Zero no Windows

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### Linux/macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### Atalho com `run.py`

```bash
python run.py
```

## Usuários e Permissões

Não existe senha padrão de administrador.

Crie um superusuário com:

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser
```

Depois, no admin, associe usuários aos grupos:

- `Administrador`: acesso amplo ao sistema;
- `Dentista`: agenda, pacientes e prontuário clínico;
- `Recepcao`: agenda e pacientes, sem edição de prontuário clínico.

Por padrão, o cadastro público fica desativado. Para abrir cadastro temporariamente:

```env
ALLOW_PUBLIC_REGISTRATION=true
```

Use essa opção apenas quando necessário.

## Variáveis de Ambiente

Copie o exemplo:

```bash
cp .env.example .env
```

Variáveis principais:

```env
SECRET_KEY=troque-por-uma-chave-secreta-forte
DEBUG=true
ALLOWED_HOSTS=<host-local>,<outro-host-local>
CSRF_TRUSTED_ORIGINS=http://<host-local>:<porta>,http://<outro-host-local>:<porta>
DATABASE_URL=
ALLOW_PUBLIC_REGISTRATION=false
DEFAULT_APPOINTMENT_DURATION_MINUTES=60
```

Para produção:

```env
DEBUG=false
DATABASE_URL=postgresql://<usuario>:<senha>@<host>:<porta>/<banco>
ALLOWED_HOSTS=example.com,www.example.com
CSRF_TRUSTED_ORIGINS=https://example.com,https://www.example.com
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=true
SECURE_HSTS_PRELOAD=true
```

O arquivo `.env`, quando existir na raiz do projeto, é carregado automaticamente por `config/settings.py`.

## PostgreSQL Local

1. Crie banco e usuário no PostgreSQL.
2. Configure `DATABASE_URL` no `.env`.
3. Rode:

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Exemplo:

```env
DATABASE_URL=postgresql://<usuario>:<senha>@<host-local>:5432/<nome-do-banco>
```

## Produção com Gunicorn

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export SECRET_KEY="troque-por-uma-chave-secreta-forte"
export DEBUG=false
export ALLOWED_HOSTS="example.com,www.example.com"
export CSRF_TRUSTED_ORIGINS="https://example.com,https://www.example.com"
export DATABASE_URL="postgresql://<usuario>:<senha>@<host>:<porta>/<banco>"
export ALLOW_PUBLIC_REGISTRATION=false
export DEFAULT_APPOINTMENT_DURATION_MINUTES=60

python manage.py migrate
python manage.py collectstatic --noinput
gunicorn config.wsgi --bind 0.0.0.0:8000 --workers 3 --timeout 120
```

## Deploy com Procfile

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

## Validação

Comandos recomendados:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py check --deploy
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py showmigrations app
.\.venv\Scripts\python.exe -m pip check
```

Estado atual esperado:

- `manage.py check`: sem issues;
- `manage.py check --deploy`: sem issues com a configuração atual;
- `manage.py test`: suíte automatizada passando;
- `makemigrations --check --dry-run`: sem mudanças pendentes;
- migrações do app aplicadas até `0007`;
- dependências sem conflitos.

## Regras de Negócio Importantes

- A duração padrão de novas consultas vem de `DEFAULT_APPOINTMENT_DURATION_MINUTES`.
- A validação de agenda considera sobreposição real por duração.
- Uma consulta ativa conflita quando seu intervalo cruza o intervalo de outra consulta ativa.
- Consultas canceladas não bloqueiam horário.
- Consultas consecutivas são permitidas quando a anterior termina exatamente no início da próxima.
- Novas consultas não podem ser criadas no passado.
- Consultas futuras não podem ser marcadas como concluídas.
- Ao concluir uma consulta, o sistema cria histórico clínico relacionado se ainda não houver registro para aquela consulta.
- Ao editar data/hora ou duração, a aplicação informa a ação como reagendamento.

## Problemas Comuns

### `No module named ...`

Instale as dependências:

```bash
pip install -r requirements.txt
```

### `DisallowedHost`

Inclua domínio, IP ou host em `ALLOWED_HOSTS`.

### Falha de conexão com PostgreSQL

Revise:

- `DATABASE_URL`;
- usuário;
- senha;
- host;
- porta;
- existência do banco.

### Static não carrega em produção

Rode:

```bash
python manage.py collectstatic --noinput
```

### Cadastro indisponível

Esse é o padrão seguro. Crie usuários pelo admin ou habilite temporariamente:

```env
ALLOW_PUBLIC_REGISTRATION=true
```

### Logout retorna `405 Method Not Allowed`

O logout do Django moderno deve ser feito via POST. A aplicação usa formulário no menu para enviar logout corretamente.

### Consulta bloqueada por conflito

Verifique se existe consulta ativa no mesmo intervalo. A validação considera duração e ignora consultas canceladas.

### PDF com texto longo

O prontuário usa geração paginada com quebra de texto. Se um conteúdo específico ainda ficar ruim, revise o texto clínico ou amplie o layout do PDF.

## Git e Finais de Linha

O projeto possui `.gitattributes` para normalizar arquivos de texto com LF.

Depois de criar ou alterar a regra, use:

```powershell
git add .gitattributes
git add --renormalize .
```

Avisos de CRLF/LF no Windows são esperados quando o Git normaliza arquivos.

## Observações e Limites Atuais

- O sistema segue o modelo de clínica única: usuários autenticados compartilham a mesma base de pacientes e consultas.
- A restrição de sobreposição é aplicada na camada de formulário; o banco ainda impede apenas horários ativos exatamente iguais.
- Anexos usam `MEDIA_ROOT` local; em produção real, é recomendado avaliar storage privado.
- O projeto ainda não possui Dockerfile ou docker-compose.
- Backups de banco e arquivos de mídia devem ser planejados antes de uso real em produção.
