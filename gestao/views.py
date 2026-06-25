from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta, date
from decimal import Decimal
import csv, json
from .models import OrdemServico, Colaborador

SERVICOS_3G = [
    'Regulagem de kit 3ª geração','Pacote limpeza do sistema GNV – 3ª geração',
    'Limpeza de redutor (avulso)','Instalação de kit GNV usado – 3ª geração (só mão de obra)',
    'Variador de avanço cabeado (Panda, Spaid e similares)','Redutor de pressão – 3ª geração',
    'Emulador de bicos injetores','Mangueira – 3ª geração','Caixinha do kit – 3ª geração',
]
SERVICOS_5G = [
    'Regulagem de kit 5ª geração','Pacote limpeza do sistema GNV – 5ª geração',
    'Limpeza de flauta TBI MAP – 5ª geração (avulso)','Instalação de kit GNV usado – 5ª geração (só mão de obra)',
    'Redutor de pressão – 5ª geração','Simulador de sonda IGT S7','Sensor MAP – 5ª geração',
    'Filtro do GNV – 5ª geração','Kit mangueiras 5ª geração (3 mangueiras)',
]
SERVICOS_COMP = [
    'Válvula de abastecimento – marca ITA','Válvula de abastecimento – marca Presso',
    'Válvula de abastecimento – marca IGT','Instalação de válvula externa (boca do tanque)',
    'Troca de tubo de alta – carro de passeio','Troca de tubo de alta – pick-up',
    'Manômetro universal','Sensor de temperatura','Regulagem de fluxo – plástico',
    'Regulagem de fluxo – alumínio',
]
SERVICOS_GER = [
    'Retirada do GNV (mão de obra + nota fiscal)','Teste hidrostático de cilindro (INMETRO)',
    'Vistoria técnica para DETRAN','Laudo de instalação (ART/RRT)','Diagnóstico eletrônico do kit',
]
CHECKLIST_ITEMS = [
    'Teste de estanqueidade (vazamento)','Pressão do sistema GNV','Calibração do redutor',
    'Filtro de gás verificado','Mangueiras sem dobras / rachaduras','Válvula de cilindro operacional',
    'Tubo de alta sem danos','Manômetro funcionando','Fiação elétrica do kit OK',
    'Caixa comutadora operacional','Fixação do cilindro OK','Iluminação do painel OK',
    'Sistema gasolina testado','Partida no gás testada','Comutação GNV ↔ gasolina OK',
]

def _ctx_servicos():
    return {
        'servicos_3g': SERVICOS_3G, 'servicos_5g': SERVICOS_5G,
        'servicos_comp': SERVICOS_COMP, 'servicos_ger': SERVICOS_GER,
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

    recentes = OrdemServico.objects.all()[:6]
    # Serviços mais frequentes
    top_servicos = (OrdemServico.objects.values('servico')
                    .annotate(total=Count('id')).order_by('-total')[:6])
    max_svc = top_servicos[0]['total'] if top_servicos else 1

    ctx = {
        **m, 'recentes': recentes, 'top_servicos': top_servicos, 'max_svc': max_svc,
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
                .annotate(total_os=Count('id'), total_valor=Sum('valor'), ultima=models.Max('data'))
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

    servico = request.POST.get('servico', '')
    if servico == '__outro__':
        servico = request.POST.get('servico_custom', '').strip()
    os.servico = servico

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


# --- Financeiro ---
@login_required
def financeiro(request):
    periodo = request.GET.get('periodo', 'mes')
    qs = _periodo_filter(OrdemServico.objects.all(), periodo)
    m = _metrics(qs)
    ctx = {'ordens_list': qs, **m, 'periodo': periodo, 'page': 'financeiro'}
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
