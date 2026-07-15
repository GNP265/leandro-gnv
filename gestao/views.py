from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Count, Q, Max
from django.utils import timezone
from datetime import timedelta, date
from decimal import Decimal
from collections import Counter
import csv, json, calendar as cal
from .models import OrdemServico, Colaborador, ContaPagar, Servico

CHECKLIST_ITEMS = [
    'Teste de estanqueidade (vazamento)','Pressão do sistema GNV','Calibração do redutor',
    'Filtro de gás verificado','Mangueiras sem dobras / rachaduras','Válvula de cilindro operacional',
    'Tubo de alta sem danos','Manômetro funcionando','Fiação elétrica do kit OK',
    'Caixa comutadora operacional','Fixação do cilindro OK','Iluminação do painel OK',
    'Sistema gasolina testado','Partida no gás testada','Comutação GNV ↔ gasolina OK',
]

def _ctx_servicos():
    ativos = list(Servico.objects.filter(ativo=True))
    grupos = []
    for cat, _ in Servico.CATEGORIA_CHOICES:
        itens = [s for s in ativos if s.categoria == cat]
        if itens:
            grupos.append((cat, itens))
    return {
        'servicos_grupos': grupos,
        'servicos_precos': {s.nome: [float(s.valor), float(s.custo)] for s in ativos},
        'checklist_items': CHECKLIST_ITEMS,
        'colaboradores': Colaborador.objects.filter(ativo=True),
        'pagamento_choices': OrdemServico.PAGAMENTO_CHOICES,
        'status_choices': OrdemServico.STATUS_CHOICES,
    }

def _periodo_filter(qs, periodo):
    hoje = date.today()
    if periodo == 'semana':
        return qs.filter(data__gte=hoje - timedelta(days=7))
    elif periodo == 'mes':
        return qs.filter(data__year=hoje.year, data__month=hoje.month)
    elif periodo == 'trimestre':
        return qs.filter(data__gte=hoje - timedelta(days=90))
    elif periodo == 'ano':
        return qs.filter(data__year=hoje.year)
    return qs

def _metrics(qs):
    agg = qs.aggregate(
        total_os=Count('id'),
        faturamento=Sum('valor'),
        custo_mat=Sum('material'),
        comissoes=Sum('comissao'),
    )
    fat = agg['faturamento'] or Decimal('0')
    mat = agg['custo_mat'] or Decimal('0')
    com = agg['comissoes'] or Decimal('0')
    return {
        'total_os': agg['total_os'],
        'faturamento': fat,
        'custo_mat': mat,
        'comissoes': com,
        'lucro': fat - mat - com,
    }


# --- Auth ---
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        user = authenticate(request, username=request.POST.get('username'), password=request.POST.get('password'))
        if user:
            login(request, user)
            return redirect(request.GET.get('next', 'dashboard'))
        messages.error(request, 'Usuário ou senha incorretos.')
    return render(request, 'registration/login.html')

def logout_view(request):
    logout(request)
    return redirect('login')


# --- Dashboard ---
@login_required
def dashboard(request):
    hoje = date.today()
    os_mes = OrdemServico.objects.filter(data__year=hoje.year, data__month=hoje.month)
    m = _metrics(os_mes)

    # Contas a pagar do mês entram no cálculo do lucro
    contas_mes_total = (ContaPagar.objects
                        .filter(vencimento__year=hoje.year, vencimento__month=hoje.month)
                        .aggregate(t=Sum('valor'))['t'] or Decimal('0'))
    m['lucro'] = m['lucro'] - contas_mes_total

    # Mini calendário: contas dos próximos 7 dias
    DOW = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
    fim_semana = hoje + timedelta(days=6)
    contas_por_dia = {}
    for c in ContaPagar.objects.filter(vencimento__gte=hoje, vencimento__lte=fim_semana):
        contas_por_dia.setdefault(c.vencimento, []).append(c)
    semana = []
    for i in range(7):
        d = hoje + timedelta(days=i)
        semana.append({'dia': d, 'dow': DOW[d.weekday()], 'hoje': d == hoje,
                       'contas': contas_por_dia.get(d, [])})
    total_semana = sum((c.valor for cs in contas_por_dia.values() for c in cs), Decimal('0'))

    recentes = OrdemServico.objects.all()[:6]
    # Serviços mais frequentes (cada serviço da OS conta separadamente)
    cnt = Counter()
    for sv in OrdemServico.objects.values_list('servico', flat=True):
        for parte in sv.split(' + '):
            parte = parte.strip()
            if parte:
                cnt[parte] += 1
    top_servicos = [{'servico': s, 'total': t} for s, t in cnt.most_common(6)]
    max_svc = top_servicos[0]['total'] if top_servicos else 1

    ctx = {
        **m, 'recentes': recentes, 'top_servicos': top_servicos, 'max_svc': max_svc,
        'contas_mes_total': contas_mes_total,
        'semana': semana, 'total_semana': total_semana,
        'periodo_label': hoje.strftime('%B de %Y'), 'page': 'dashboard',
    }
    return render(request, 'gestao/dashboard.html', ctx)


# --- Ordens de Serviço ---
@login_required
def ordens(request):
    hoje = date.today()
    os_mes = OrdemServico.objects.filter(data__year=hoje.year, data__month=hoje.month)
    m_mes = _metrics(os_mes)
    m_all = _metrics(OrdemServico.objects.all())

    q = request.GET.get('q', '')
    status = request.GET.get('status', '')
    tab = request.GET.get('tab', 'os')

    qs = OrdemServico.objects.all()
    if q:
        qs = qs.filter(
            Q(nome_cliente__icontains=q) | Q(placa__icontains=q) |
            Q(modelo__icontains=q) | Q(servico__icontains=q) | Q(pk__icontains=q)
        )
    if status:
        qs = qs.filter(status=status)

    # Clientes agregados
    clientes = (OrdemServico.objects.values('nome_cliente','telefone')
                .annotate(total_os=Count('id'), total_valor=Sum('valor'), ultima=Max('data'))
                .order_by('-ultima'))
    if q and tab == 'clientes':
        clientes = clientes.filter(nome_cliente__icontains=q)

    ctx = {
        'ordens_list': qs, 'clientes': clientes,
        'q': q, 'status_filter': status, 'tab': tab,
        'os_mes': m_mes['total_os'], 'total_os': m_all['total_os'],
        'fat_mes': m_mes['faturamento'], 'lucro_mes': m_mes['lucro'],
        **_ctx_servicos(),
        'page': 'ordens',
    }
    return render(request, 'gestao/ordens.html', ctx)

# Need to import models for Max
from django.db import models as db_models

@login_required
def os_save(request):
    if request.method != 'POST':
        return redirect('ordens')

    os_id = request.POST.get('os_id')
    os = OrdemServico.objects.get(pk=os_id) if os_id else OrdemServico()

    os.nome_cliente = request.POST.get('nome_cliente', '').strip()
    os.telefone = request.POST.get('telefone', '')
    os.marca = request.POST.get('marca', '')
    os.modelo = request.POST.get('modelo', '')
    os.placa = request.POST.get('placa', '').upper().strip()
    km = request.POST.get('km', '')
    os.km = int(km) if km else None

    # Múltiplos serviços: cada linha do formulário envia um par (servico, servico_custom)
    servicos = request.POST.getlist('servico')
    customs = request.POST.getlist('servico_custom')
    lista = []
    for i, sv in enumerate(servicos):
        if sv == '__outro__':
            sv = customs[i].strip() if i < len(customs) else ''
        sv = sv.strip()
        if sv and sv not in lista:
            lista.append(sv)
    os.servico = ' + '.join(lista)

    colab_id = request.POST.get('colaborador', '')
    os.colaborador = Colaborador.objects.get(pk=colab_id) if colab_id else None
    os.data = request.POST.get('data')
    os.garantia_dias = int(request.POST.get('garantia_dias', 90) or 90)
    os.descricao = request.POST.get('descricao', '')

    os.valor = Decimal(request.POST.get('valor', '0') or '0')
    os.material = Decimal(request.POST.get('material', '0') or '0')
    os.comissao = Decimal(request.POST.get('comissao', '0') or '0')
    os.pagamento = request.POST.get('pagamento', '')
    os.status = request.POST.get('status', 'Concluída')

    checklist = request.POST.getlist('checklist')
    os.checklist = ';'.join(checklist)

    if not os.criado_por:
        os.criado_por = request.user

    os.save()
    messages.success(request, f'OS #{os.pk} salva com sucesso!')
    return redirect('ordens')

@login_required
def os_delete(request, pk):
    os = get_object_or_404(OrdemServico, pk=pk)
    os.delete()
    messages.success(request, 'OS excluída.')
    return redirect('ordens')

@login_required
def os_detail_json(request, pk):
    os = get_object_or_404(OrdemServico, pk=pk)
    return JsonResponse({
        'id': os.pk, 'nome_cliente': os.nome_cliente, 'telefone': os.telefone,
        'marca': os.marca, 'modelo': os.modelo, 'placa': os.placa,
        'km': os.km, 'servico': os.servico,
        'colaborador_id': os.colaborador_id, 'colaborador_nome': str(os.colaborador) if os.colaborador else '',
        'data': str(os.data), 'garantia_dias': os.garantia_dias,
        'garantia_vencimento': str(os.garantia_vencimento) if os.garantia_vencimento else '',
        'descricao': os.descricao,
        'valor': str(os.valor), 'material': str(os.material),
        'comissao': str(os.comissao), 'lucro': str(os.lucro),
        'pagamento': os.pagamento, 'status': os.status,
        'checklist': os.checklist.split(';') if os.checklist else [],
    })


# --- Cadastro de Serviços ---
@login_required
def servicos(request):
    q = request.GET.get('q', '')
    lista = Servico.objects.filter(ativo=True)
    if q:
        lista = lista.filter(nome__icontains=q)
    ctx = {
        'servicos_list': lista, 'q': q,
        'total_servicos': Servico.objects.filter(ativo=True).count(),
        'categoria_choices': Servico.CATEGORIA_CHOICES,
        'page': 'servicos',
    }
    return render(request, 'gestao/servicos.html', ctx)

@login_required
def servico_save(request):
    if request.method != 'POST':
        return redirect('servicos')
    servico_id = request.POST.get('servico_id')
    s = Servico.objects.get(pk=servico_id) if servico_id else Servico()
    nome = request.POST.get('nome', '').strip()
    if not nome:
        messages.error(request, 'O nome do serviço é obrigatório.')
        return redirect('servicos')
    if Servico.objects.filter(nome=nome).exclude(pk=s.pk or 0).exists():
        messages.warning(request, f'Já existe um serviço chamado "{nome}".')
        return redirect('servicos')
    s.nome = nome
    s.categoria = request.POST.get('categoria', 'Outros')
    s.valor = Decimal(request.POST.get('valor', '0') or '0')
    s.custo = Decimal(request.POST.get('custo', '0') or '0')
    s.save()
    messages.success(request, f'Serviço "{s.nome}" salvo!')
    return redirect('servicos')

@login_required
def servico_delete(request, pk):
    s = get_object_or_404(Servico, pk=pk)
    nome = s.nome
    s.delete()
    messages.success(request, f'Serviço "{nome}" excluído. (As OS antigas que o usaram não são alteradas.)')
    return redirect('servicos')

@login_required
def servico_detail_json(request, pk):
    s = get_object_or_404(Servico, pk=pk)
    return JsonResponse({'id': s.pk, 'nome': s.nome, 'categoria': s.categoria,
                         'valor': str(s.valor), 'custo': str(s.custo)})


# --- Financeiro ---
def _serie_evolucao():
    """Séries diária (30 dias), semanal (12 semanas) e mensal (12 meses)
    de faturamento, custos (material+comissão) e lucro bruto."""
    hoje = date.today()
    inicio = date(hoje.year - 1, hoje.month, 1)
    registros = (OrdemServico.objects.filter(data__gte=inicio)
                 .values_list('data', 'valor', 'material', 'comissao'))

    # Contas a pagar por dia de vencimento (entram no lucro)
    contas_dia = {}
    for venc, val in (ContaPagar.objects.filter(vencimento__gte=inicio)
                      .values_list('vencimento', 'valor')):
        contas_dia[venc] = contas_dia.get(venc, 0.0) + float(val or 0)

    dia = {}
    for d, v, mt, cm in registros:
        v, mt, cm = float(v or 0), float(mt or 0), float(cm or 0)
        b = dia.setdefault(d, [0.0, 0.0])
        b[0] += v
        b[1] += mt + cm
    # garante que dias que só têm contas também apareçam no lucro
    for d in contas_dia:
        dia.setdefault(d, [0.0, 0.0])

    def ponto(fat, custo, contas):
        return round(fat, 2), round(custo, 2), round(fat - custo - contas, 2)

    # Diário — últimos 30 dias
    diario = {'labels': [], 'fat': [], 'custo': [], 'lucro': []}
    for i in range(29, -1, -1):
        d = hoje - timedelta(days=i)
        fat, custo = dia.get(d, [0.0, 0.0])
        f, c, l = ponto(fat, custo, contas_dia.get(d, 0.0))
        diario['labels'].append(d.strftime('%d/%m'))
        diario['fat'].append(f); diario['custo'].append(c); diario['lucro'].append(l)

    # Semanal — últimas 12 semanas (segunda a domingo)
    semanal = {'labels': [], 'fat': [], 'custo': [], 'lucro': []}
    seg_atual = hoje - timedelta(days=hoje.weekday())
    for i in range(11, -1, -1):
        ini = seg_atual - timedelta(weeks=i)
        fim = ini + timedelta(days=6)
        fat = custo = contas = 0.0
        for d, b in dia.items():
            if ini <= d <= fim:
                fat += b[0]; custo += b[1]; contas += contas_dia.get(d, 0.0)
        f, c, l = ponto(fat, custo, contas)
        semanal['labels'].append(ini.strftime('%d/%m'))
        semanal['fat'].append(f); semanal['custo'].append(c); semanal['lucro'].append(l)

    # Mensal — últimos 12 meses
    MESES = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez']
    mensal = {'labels': [], 'fat': [], 'custo': [], 'lucro': []}
    ano, mes = hoje.year, hoje.month
    chaves = []
    for _ in range(12):
        chaves.append((ano, mes))
        mes -= 1
        if mes == 0:
            mes = 12; ano -= 1
    for a, m in reversed(chaves):
        fat = custo = contas = 0.0
        for d, b in dia.items():
            if d.year == a and d.month == m:
                fat += b[0]; custo += b[1]; contas += contas_dia.get(d, 0.0)
        f, c, l = ponto(fat, custo, contas)
        mensal['labels'].append(f'{MESES[m-1]}/{str(a)[2:]}')
        mensal['fat'].append(f); mensal['custo'].append(c); mensal['lucro'].append(l)

    return {'diario': diario, 'semanal': semanal, 'mensal': mensal}

def _rank_servicos():
    """Ranking de serviços (top 5 por lucro e por quantidade), total e por mês.
    Em OS com vários serviços, o lucro é dividido igualmente entre eles."""
    MESES = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho',
             'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']
    hoje = date.today()
    inicio = date(hoje.year - 1, hoje.month, 1)

    lucro_tot, qtd_tot = Counter(), Counter()
    lucro_mes, qtd_mes = {}, {}
    for os_data, valor, material, comissao, servico in (
            OrdemServico.objects.filter(data__gte=inicio)
            .values_list('data', 'valor', 'material', 'comissao', 'servico')):
        partes = [s.strip() for s in servico.split(' + ') if s.strip()]
        if not partes:
            continue
        lucro_por_servico = float((valor or 0) - (material or 0) - (comissao or 0)) / len(partes)
        chave = f'{os_data.year}-{os_data.month:02d}'
        lm = lucro_mes.setdefault(chave, Counter())
        qm = qtd_mes.setdefault(chave, Counter())
        for p in partes:
            lucro_tot[p] += lucro_por_servico
            qtd_tot[p] += 1
            lm[p] += lucro_por_servico
            qm[p] += 1

    def top5(cnt, arredonda=False):
        return [[nome, round(v, 2) if arredonda else v] for nome, v in cnt.most_common(5)]

    dados = {'todos': {'lucro': top5(lucro_tot, True), 'qtd': top5(qtd_tot)}}
    meses_opcoes = [['todos', 'Últimos 12 meses']]
    for chave in sorted(lucro_mes.keys(), reverse=True):
        a, m = chave.split('-')
        meses_opcoes.append([chave, f'{MESES[int(m)-1]}/{a}'])
        dados[chave] = {'lucro': top5(lucro_mes[chave], True), 'qtd': top5(qtd_mes[chave])}
    return {'meses': meses_opcoes, 'dados': dados}

def _contas_periodo(periodo):
    """Total de contas a pagar com vencimento dentro do período selecionado."""
    hoje = date.today()
    qs = ContaPagar.objects.all()
    if periodo == 'mes':
        qs = qs.filter(vencimento__year=hoje.year, vencimento__month=hoje.month)
    elif periodo == 'trimestre':
        qs = qs.filter(vencimento__gte=hoje - timedelta(days=90), vencimento__lte=hoje)
    return qs.aggregate(t=Sum('valor'))['t'] or Decimal('0')

@login_required
def financeiro(request):
    periodo = request.GET.get('periodo', 'mes')
    qs = _periodo_filter(OrdemServico.objects.all(), periodo)
    m = _metrics(qs)
    contas_total = _contas_periodo(periodo)
    m['lucro'] = m['lucro'] - contas_total
    ctx = {
        'ordens_list': qs, **m, 'contas_total': contas_total,
        'periodo': periodo, 'page': 'financeiro',
        'chart_data': _serie_evolucao(),
        'rank_data': _rank_servicos(),
    }
    return render(request, 'gestao/financeiro.html', ctx)


# --- Colaboradores ---
@login_required
def colaboradores(request):
    periodo = request.GET.get('periodo', 'semana')
    colabs = Colaborador.objects.filter(ativo=True)
    colab_data = []
    for c in colabs:
        qs = _periodo_filter(OrdemServico.objects.filter(colaborador=c), periodo)
        m = _metrics(qs)
        ticket = m['faturamento'] / m['total_os'] if m['total_os'] else Decimal('0')
        colab_data.append({'colab': c, **m, 'ticket': ticket})

    periodo_labels = {'semana': 'esta semana', 'mes': 'este mês', 'trimestre': 'no trimestre', 'ano': 'este ano'}
    ctx = {'colab_data': colab_data, 'periodo': periodo, 'periodo_label': periodo_labels.get(periodo, ''), 'page': 'colaboradores'}
    return render(request, 'gestao/colaboradores.html', ctx)

@login_required
def colab_add(request):
    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        if nome:
            if not Colaborador.objects.filter(nome=nome).exists():
                Colaborador.objects.create(nome=nome)
                messages.success(request, f'{nome} adicionado.')
            else:
                messages.warning(request, 'Colaborador já existe.')
    return redirect('colaboradores')

@login_required
def colab_remove(request, pk):
    c = get_object_or_404(Colaborador, pk=pk)
    c.ativo = False
    c.save()
    messages.success(request, f'{c.nome} removido.')
    return redirect('colaboradores')


# --- Contas a Pagar ---
@login_required
def contas(request):
    hoje = date.today()
    try:
        ano = int(request.GET.get('ano', hoje.year))
        mes = int(request.GET.get('mes', hoje.month))
        date(ano, mes, 1)
    except (ValueError, TypeError):
        ano, mes = hoje.year, hoje.month

    # Navegação de meses
    prev_ano, prev_mes = (ano - 1, 12) if mes == 1 else (ano, mes - 1)
    next_ano, next_mes = (ano + 1, 1) if mes == 12 else (ano, mes + 1)

    contas_mes = ContaPagar.objects.filter(vencimento__year=ano, vencimento__month=mes)
    agg = contas_mes.aggregate(total=Sum('valor'))
    total_mes = agg['total'] or Decimal('0')
    pagas = contas_mes.filter(pago=True)
    abertas = contas_mes.filter(pago=False)
    total_pago = pagas.aggregate(t=Sum('valor'))['t'] or Decimal('0')
    total_aberto = abertas.aggregate(t=Sum('valor'))['t'] or Decimal('0')
    vencidas = ContaPagar.objects.filter(pago=False, vencimento__lt=hoje).count()

    # Calendário: semanas do mês (domingo a sábado), com as contas de cada dia
    contas_por_dia = {}
    grade = cal.Calendar(firstweekday=6).monthdatescalendar(ano, mes)
    datas_visiveis = [d for semana in grade for d in semana]
    for c in ContaPagar.objects.filter(vencimento__gte=datas_visiveis[0], vencimento__lte=datas_visiveis[-1]):
        contas_por_dia.setdefault(c.vencimento, []).append(c)
    semanas = [[{'dia': d, 'no_mes': d.month == mes, 'hoje': d == hoje,
                 'contas': contas_por_dia.get(d, [])} for d in semana] for semana in grade]

    MESES = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho',
             'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']

    ctx = {
        'semanas': semanas, 'contas_mes': contas_mes,
        'mes_label': f'{MESES[mes-1]} de {ano}',
        'prev_ano': prev_ano, 'prev_mes': prev_mes,
        'next_ano': next_ano, 'next_mes': next_mes,
        'ano': ano, 'mes': mes,
        'total_mes': total_mes, 'total_pago': total_pago,
        'total_aberto': total_aberto, 'vencidas': vencidas,
        'categoria_choices': ContaPagar.CATEGORIA_CHOICES,
        'page': 'contas',
    }
    return render(request, 'gestao/contas.html', ctx)

def _proximo_mes(d):
    """Mesmo dia no mês seguinte (ajustando para meses mais curtos, ex: dia 31)."""
    ano, mes = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
    ultimo_dia = cal.monthrange(ano, mes)[1]
    return date(ano, mes, min(d.day, ultimo_dia))

def _datas_recorrencia(inicio, recorrencia, prazo_final):
    """Lista de vencimentos da série. Sem prazo final, gera um horizonte padrão:
    diária = 60 dias, semanal = 26 semanas, mensal = 12 meses. Limite: 120 contas."""
    if prazo_final:
        fim = prazo_final
    elif recorrencia == 'Diária':
        fim = inicio + timedelta(days=59)
    elif recorrencia == 'Semanal':
        fim = inicio + timedelta(weeks=25)
    else:  # Mensal
        fim = inicio
        for _ in range(11):
            fim = _proximo_mes(fim)
    datas, d = [], inicio
    while d <= fim and len(datas) < 120:
        datas.append(d)
        if recorrencia == 'Diária':
            d = d + timedelta(days=1)
        elif recorrencia == 'Semanal':
            d = d + timedelta(weeks=1)
        else:
            d = _proximo_mes(d)
    return datas

@login_required
def conta_save(request):
    if request.method != 'POST':
        return redirect('contas')
    conta_id = request.POST.get('conta_id')
    c = ContaPagar.objects.get(pk=conta_id) if conta_id else ContaPagar()
    c.descricao = request.POST.get('descricao', '').strip()
    c.categoria = request.POST.get('categoria', 'Boleto')
    c.valor = Decimal(request.POST.get('valor', '0') or '0')
    c.vencimento = request.POST.get('vencimento')
    c.observacao = request.POST.get('observacao', '')
    c.pago = request.POST.get('pago') == 'on'

    recorrencia = request.POST.get('recorrencia', '')
    venc = c.vencimento if isinstance(c.vencimento, date) else date.fromisoformat(c.vencimento)

    # Recorrência só se aplica a contas novas (na edição altera-se só aquela conta)
    if not conta_id and recorrencia in ('Diária', 'Semanal', 'Mensal'):
        prazo_final = None
        if request.POST.get('duracao') == 'prazo':
            p = request.POST.get('prazo_final', '')
            if p:
                prazo_final = date.fromisoformat(p)
        datas = _datas_recorrencia(venc, recorrencia, prazo_final)
        import uuid
        grupo = uuid.uuid4().hex[:12]
        for i, d in enumerate(datas):
            ContaPagar.objects.create(
                descricao=c.descricao, categoria=c.categoria, valor=c.valor,
                vencimento=d, observacao=c.observacao,
                pago=c.pago if i == 0 else False,
                recorrencia=recorrencia, grupo=grupo,
            )
        messages.success(request, f'{len(datas)} contas criadas (recorrência {recorrencia.lower()}) até {datas[-1].strftime("%d/%m/%Y")}.')
    else:
        c.save()
        messages.success(request, f'Conta "{c.descricao}" salva!')
    return redirect(f'/contas/?ano={venc.year}&mes={venc.month}')

@login_required
def conta_toggle_pago(request, pk):
    c = get_object_or_404(ContaPagar, pk=pk)
    c.pago = not c.pago
    c.save()
    messages.success(request, f'Conta "{c.descricao}" marcada como {"paga" if c.pago else "em aberto"}.')
    return redirect(f'/contas/?ano={c.vencimento.year}&mes={c.vencimento.month}')

@login_required
def conta_delete(request, pk):
    c = get_object_or_404(ContaPagar, pk=pk)
    ano, mes = c.vencimento.year, c.vencimento.month
    if request.GET.get('serie') == '1' and c.grupo:
        total, _ = ContaPagar.objects.filter(grupo=c.grupo).delete()
        messages.success(request, f'Série recorrente excluída ({total} contas).')
    else:
        c.delete()
        messages.success(request, 'Conta excluída.')
    return redirect(f'/contas/?ano={ano}&mes={mes}')

@login_required
def conta_detail_json(request, pk):
    c = get_object_or_404(ContaPagar, pk=pk)
    return JsonResponse({
        'id': c.pk, 'descricao': c.descricao, 'categoria': c.categoria,
        'valor': str(c.valor), 'vencimento': str(c.vencimento),
        'pago': c.pago, 'observacao': c.observacao,
    })


# --- Exportar CSV ---
@login_required
def exportar_csv(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="leandro_gnv_os.csv"'
    response.write('\ufeff')
    writer = csv.writer(response)
    writer.writerow(['ID','Nome','Telefone','Marca','Modelo','Placa','KM','Serviço',
                     'Colaborador','Data','Garantia','Descrição','Valor','Material',
                     'Pagamento','Comissão','Lucro','Status','Checklist'])
    for os in OrdemServico.objects.all():
        writer.writerow([os.pk, os.nome_cliente, os.telefone, os.marca, os.modelo,
                         os.placa, os.km or '', os.servico, os.colaborador or '',
                         os.data, os.garantia_dias, os.descricao, os.valor, os.material,
                         os.pagamento, os.comissao, os.lucro, os.status, os.checklist])
    return response
