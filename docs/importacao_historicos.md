# Importacao em lote de historicos de exercicios

Use este fluxo para importar uma pasta inteira fora da requisicao HTTP. O comando processa um arquivo por vez, com transacao independente por arquivo, e pode ser reexecutado sem duplicar dados ja importados.

## Preparar a pasta

- Separe os arquivos `.xlsx` de historico em uma pasta propria.
- O comando tambem localiza `.csv`, mas o importador de historico de exercicios aceita XLSX; CSV sera relatado como erro de parsing.
- Use nomes de arquivo que ajudem a identificar a planilha com falha. O conteudo das linhas nao e escrito no relatorio.

Checkout local atual:

```bash
cd /home/kris/Documentos/Web/Fisio
```

Substitua `/CAMINHO/REAL/DAS/PLANILHAS` pelo diretorio real das planilhas antes de executar.

## Dry-run

Execute primeiro em backup/staging ou em ambiente local com uma copia segura do banco:

```bash
.venv/bin/python manage.py importar_historicos \
  /CAMINHO/REAL/DAS/PLANILHAS \
  --dry-run \
  --continue-on-error \
  --report /tmp/importacao-dry-run.json
```

`--dry-run` nao altera tabelas. Revise o resumo e o relatorio antes da importacao real.

## Importacao real

```bash
.venv/bin/python manage.py importar_historicos \
  /CAMINHO/REAL/DAS/PLANILHAS \
  --continue-on-error \
  --report /tmp/importacao-final.json
```

Para importar apenas uma aba especifica:

```bash
.venv/bin/python manage.py importar_historicos \
  /CAMINHO/REAL/DAS/PLANILHAS \
  --sheet "Primeira aba" \
  --continue-on-error
```

## Relatorio

`--report` aceita `.json` ou `.csv`. O relatorio contem: arquivo, aba, status, duracao, categorias, exercicios, marcacoes, criados, atualizados, ignorados, tipo de erro e mensagem sanitizada.

Sem `--report`, somente o progresso e o resumo aparecem no terminal.

## Falhas e reexecucao

- Cada arquivo tem sua propria transacao. Se um arquivo falhar durante a persistencia, somente ele e revertido.
- Com `--continue-on-error`, os proximos arquivos continuam sendo processados.
- Sem `--continue-on-error`, o comando para no primeiro erro.
- Reexecute o mesmo comando depois de corrigir a planilha com falha; a importacao e idempotente e nao duplica os dados ja concluidos.

Exit codes:

- `0`: todos os arquivos processados sem erro.
- diferente de `0`: algum arquivo falhou, o caminho era invalido, ou a execucao foi interrompida.

## Exemplo em servidor como usuario fisio

Os caminhos abaixo sao placeholders; substitua pelo caminho real do projeto e das planilhas no servidor.

```bash
sudo -u fisio -H bash
cd /CAMINHO/REAL/DO/PROJETO
source venv/bin/activate

python manage.py importar_historicos \
  /CAMINHO/REAL/DAS/PLANILHAS \
  --dry-run \
  --continue-on-error \
  --report /tmp/importacao-dry-run.json
```

Depois de revisar o dry-run:

```bash
python manage.py importar_historicos \
  /CAMINHO/REAL/DAS/PLANILHAS \
  --continue-on-error \
  --report /tmp/importacao-final.json
```
