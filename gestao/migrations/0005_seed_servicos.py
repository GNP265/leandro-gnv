from django.db import migrations

SERVICOS = {
    '3ª Geração': [
        'Regulagem de kit 3ª geração', 'Pacote limpeza do sistema GNV – 3ª geração',
        'Limpeza de redutor (avulso)', 'Instalação de kit GNV usado – 3ª geração (só mão de obra)',
        'Variador de avanço cabeado (Panda, Spaid e similares)', 'Redutor de pressão – 3ª geração',
        'Emulador de bicos injetores', 'Mangueira – 3ª geração', 'Caixinha do kit – 3ª geração',
    ],
    '5ª Geração': [
        'Regulagem de kit 5ª geração', 'Pacote limpeza do sistema GNV – 5ª geração',
        'Limpeza de flauta TBI MAP – 5ª geração (avulso)', 'Instalação de kit GNV usado – 5ª geração (só mão de obra)',
        'Redutor de pressão – 5ª geração', 'Simulador de sonda IGT S7', 'Sensor MAP – 5ª geração',
        'Filtro do GNV – 5ª geração', 'Kit mangueiras 5ª geração (3 mangueiras)',
    ],
    'Componentes': [
        'Válvula de abastecimento – marca ITA', 'Válvula de abastecimento – marca Presso',
        'Válvula de abastecimento – marca IGT', 'Instalação de válvula externa (boca do tanque)',
        'Troca de tubo de alta – carro de passeio', 'Troca de tubo de alta – pick-up',
        'Manômetro universal', 'Sensor de temperatura', 'Regulagem de fluxo – plástico',
        'Regulagem de fluxo – alumínio',
    ],
    'Geral': [
        'Retirada do GNV (mão de obra + nota fiscal)', 'Teste hidrostático de cilindro (INMETRO)',
        'Vistoria técnica para DETRAN', 'Laudo de instalação (ART/RRT)', 'Diagnóstico eletrônico do kit',
    ],
}


def criar_servicos(apps, schema_editor):
    Servico = apps.get_model('gestao', 'Servico')
    for categoria, nomes in SERVICOS.items():
        for nome in nomes:
            Servico.objects.get_or_create(nome=nome, defaults={'categoria': categoria})


def remover_servicos(apps, schema_editor):
    Servico = apps.get_model('gestao', 'Servico')
    nomes = [n for lista in SERVICOS.values() for n in lista]
    Servico.objects.filter(nome__in=nomes).delete()


class Migration(migrations.Migration):
    dependencies = [('gestao', '0004_servico')]
    operations = [migrations.RunPython(criar_servicos, remover_servicos)]
