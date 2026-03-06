from django.db import models


class TimestampedModel(models.Model):
    """Abstract base model that provides automatic timestamps."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class FichaInscricao(TimestampedModel):
    """Ficha de Inscrição - Registration Form"""
    nome = models.CharField(max_length=200)
    cpf = models.CharField(max_length=14, unique=True)
    email = models.EmailField()
    profissao = models.CharField(max_length=100, blank=True)
    endereco = models.CharField(max_length=300)
    bairro = models.CharField(max_length=100)
    cep = models.CharField(max_length=10)
    telefone = models.CharField(max_length=15, blank=True)
    celular = models.CharField(max_length=15)
    telefone_comercial = models.CharField(max_length=15, blank=True)
    data_nascimento = models.DateField()
    data_matricula = models.DateField()
    plano = models.CharField(max_length=100)
    observacoes = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Ficha de Inscrição'
        verbose_name_plural = 'Fichas de Inscrição'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.nome} - {self.cpf}"


class AnamneseGeral(TimestampedModel):
    """Anamnese Geral - General Anamnesis Form"""
    paciente = models.ForeignKey(FichaInscricao, on_delete=models.CASCADE, null=True, blank=True, related_name='anamneses_geral', verbose_name='Paciente')
    nome = models.CharField(max_length=200)
    profissao = models.CharField(max_length=100)
    data_nascimento = models.DateField()
    data = models.DateTimeField()  # Data de Avaliação - converted to DateTime for scheduling
    concluido = models.BooleanField(default=False)
    
    # Condições
    diabetes = models.BooleanField(default=False)
    anemia = models.BooleanField(default=False)
    hipoglicemia = models.BooleanField(default=False)
    pressao_alta = models.BooleanField(default=False)
    pressao_baixa = models.BooleanField(default=False)
    problema_cardiaco = models.BooleanField(default=False)
    
    usa_medicamentos = models.BooleanField(default=False)
    observacoes = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Anamnese Geral'
        verbose_name_plural = 'Anamneses Gerais'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.nome} - {self.data}"


class AnamneseAcupuntura(TimestampedModel):
    """Anamnese - Acupuntura - Acupuncture Anamnesis Form"""
    paciente = models.ForeignKey(FichaInscricao, on_delete=models.CASCADE, null=True, blank=True, related_name='anamneses_acupuntura', verbose_name='Paciente')
    nome = models.CharField(max_length=200)
    data_consulta = models.DateTimeField()  # Converted to DateTime for scheduling
    endereco = models.CharField(max_length=300)
    telefone = models.CharField(max_length=15)
    data_nascimento = models.DateField()
    profissao = models.CharField(max_length=100)
    religiao = models.CharField(max_length=100, blank=True)
    idade = models.IntegerField()
    estado_civil = models.CharField(max_length=50, blank=True)
    filhos = models.CharField(max_length=100, blank=True)
    ja_fez_acupuntura = models.BooleanField(default=False)
    concluido = models.BooleanField(default=False)
    
    # Medical History
    queixa_principal = models.TextField()
    historia_doenca_atual = models.TextField()
    medicacao = models.TextField(blank=True)
    historia_patologica_pregressa = models.TextField(blank=True)
    doencas_familia = models.TextField(blank=True)
    rotina_diaria = models.TextField(blank=True)
    atividade_fisica = models.TextField(blank=True)
    
    # Examination
    sono = models.TextField(blank=True)
    emocao_predominante = models.CharField(max_length=100, blank=True)
    sabor_preferido = models.CharField(max_length=100, blank=True)
    pulso_direito = models.CharField(max_length=100, blank=True)
    pulso_esquerdo = models.CharField(max_length=100, blank=True)
    lingua = models.TextField(blank=True)
    
    diagnostico = models.TextField(blank=True)
    prescricao = models.TextField(blank=True)
    observacoes = models.TextField(blank=True)

    # generic relation for follow-up sessions
    from django.contrib.contenttypes.fields import GenericRelation
    followups = GenericRelation('FollowUpSession', related_query_name='anamneses_acupuntura')

    class Meta:
        verbose_name = 'Anamnese - Acupuntura'
        verbose_name_plural = 'Anamneses - Acupuntura'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.nome} - Acupuntura - {self.data_consulta}"


class FichaDrenagem(TimestampedModel):
    """Ficha de Avaliação - Drenagem Linfática - Lymphatic Drainage Assessment Form"""
    paciente = models.ForeignKey(FichaInscricao, on_delete=models.CASCADE, null=True, blank=True, related_name='fichas_drenagem', verbose_name='Paciente')
    nome = models.CharField(max_length=200)
    endereco = models.CharField(max_length=300)
    telefone = models.CharField(max_length=15)
    convenio = models.CharField(max_length=100, blank=True)
    data_nascimento = models.DateField()
    idade = models.IntegerField()
    altura = models.DecimalField(max_digits=5, decimal_places=2)  # in cm
    peso = models.DecimalField(max_digits=5, decimal_places=1)    # in kg
    data = models.DateTimeField()  # Converted to DateTime for scheduling
    concluido = models.BooleanField(default=False)
    
    queixa = models.TextField()
    historia_doenca_atual = models.TextField()
    avaliacao = models.TextField()
    historia_patologica_pregressa = models.TextField(blank=True)

    # generic relation for follow-up sessions
    from django.contrib.contenttypes.fields import GenericRelation
    followups = GenericRelation('FollowUpSession', related_query_name='fichas_drenagem')

    class Meta:
        verbose_name = 'Ficha de Avaliação - Drenagem Linfática'
        verbose_name_plural = 'Fichas de Avaliação - Drenagem Linfática'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.nome} - Drenagem - {self.data}"


class FichaExercicios(TimestampedModel):
    """Ficha de Exercícios - Exercise Sheet"""
    paciente = models.ForeignKey(FichaInscricao, on_delete=models.CASCADE, null=True, blank=True, related_name='fichas_exercicios', verbose_name='Paciente')
    aluno = models.CharField(max_length=200)
    objetivo = models.TextField()
    historico_patologico = models.TextField()
    flexibilidade = models.TextField()
    dominancia_muscular = models.TextField()
    observacoes = models.TextField(blank=True)
    dia = models.DateTimeField()  # Converted to DateTime for scheduling
    mes = models.CharField(max_length=7, blank=True)  # For month storage if needed
    concluido = models.BooleanField(default=False)
    
    # generic relation to follow-up sessions
    from django.contrib.contenttypes.fields import GenericRelation
    followups = GenericRelation('FollowUpSession', related_query_name='fichas_exercicios')

    class Meta:
        verbose_name = 'Ficha de Exercícios'
        verbose_name_plural = 'Fichas de Exercícios'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.aluno} - {self.dia}"


class FollowUpSession(models.Model):
    """Generic follow-up session tied to any procedure record."""
    # generic foreign key to support multiple procedure models
    from django.contrib.contenttypes.models import ContentType
    from django.contrib.contenttypes.fields import GenericForeignKey

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    procedure = GenericForeignKey('content_type', 'object_id')

    session_date = models.DateTimeField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-session_date']

    def __str__(self):
        return f"Sessão em {self.session_date} para {self.procedure}"