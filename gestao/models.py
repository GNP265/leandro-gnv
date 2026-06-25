from django.db import models
from django.contrib.auth.models import User

class Colaborador(models.Model):
    nome = models.CharField(max_length=100)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nome']
        verbose_name_plural = 'Colaboradores'

    def __str__(self):
        return self.nome

class OrdemServico(models.Model):
    STATUS_CHOICES = [
        ('Aberta', 'Aberta'),
        ('Em andamento', 'Em andamento'),
        ('Concluída', 'Concluída'),
        ('Garantia', 'Garantia'),
    ]
    PAGAMENTO_CHOICES = [
        ('Dinheiro', 'Dinheiro'), ('PIX', 'PIX'),
        ('Cartão crédito', 'Cartão crédito'), ('Cartão débito', 'Cartão débito'),
        ('Transferência', 'Transferência'), ('Fiado', 'Fiado'),
    ]

    # Cliente
    nome_cliente = models.CharField('Nome do cliente', max_length=200)
    telefone = models.CharField(max_length=20, blank=True, default='')

    # Veículo
    marca = models.CharField(max_length=50, blank=True, default='')
    modelo = models.CharField(max_length=80, blank=True, default='')
    placa = models.CharField(max_length=10)
    km = models.PositiveIntegerField('KM do veículo', null=True, blank=True)

    # Serviço
    servico = models.CharField('Tipo de serviço', max_length=200)
    colaborador = models.ForeignKey(Colaborador, on_delete=models.SET_NULL, null=True, blank=True)
    data = models.DateField('Data do serviço')
    garantia_dias = models.PositiveIntegerField('Garantia (dias)', default=90)
    descricao = models.TextField('Descrição / serviços realizados', blank=True, default='')

    # Financeiro
    valor = models.DecimalField('Valor cobrado', max_digits=10, decimal_places=2, default=0)
    material = models.DecimalField('Custo de material', max_digits=10, decimal_places=2, default=0)
    comissao = models.DecimalField('Comissão', max_digits=10, decimal_places=2, default=0)
    pagamento = models.CharField('Forma de pagamento', max_length=30, choices=PAGAMENTO_CHOICES, blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Concluída')

    # Checklist (armazena como texto separado por ;)
    checklist = models.TextField(blank=True, default='')

    # Meta
    criado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-data', '-criado_em']
        verbose_name = 'Ordem de Serviço'
        verbose_name_plural = 'Ordens de Serviço'

    def __str__(self):
        return f'OS #{self.pk} — {self.nome_cliente} — {self.servico}'

    @property
    def lucro(self):
        return self.valor - self.material - self.comissao

    @property
    def garantia_vencimento(self):
        from datetime import timedelta
        if self.data and self.garantia_dias:
            return self.data + timedelta(days=self.garantia_dias)
        return None
