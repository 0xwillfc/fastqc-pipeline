# fastqc-pipeline

Pipeline simples e reprodutível para controle de qualidade (QC) de dados de sequenciamento em formato FASTQ usando **FastQC** e **MultiQC**, com checagem automática de limiares de qualidade.

## Visão geral

Este pipeline:

1. Encontra todos os arquivos `*.fastq`/`*.fastq.gz` em um diretório de entrada.
2. Roda **FastQC** em paralelo nas amostras.
3. Agrega os relatórios com **MultiQC**.
4. Extrai métricas principais dos relatórios do FastQC.
5. Compara com limiares definidos em `config/thresholds.ini`.
6. Gera um `qc_summary.json` indicando quais amostras passaram (`PASS`) ou falharam (`FAIL`).

## Instalação

### Via Conda

Na raiz do projeto:

```bash
conda env create -f environment.yml
conda activate fastqc-pipeline
```

Verifique se `fastqc`, `multiqc` e `python` estão disponíveis no `PATH` após ativar o ambiente.

## Uso básico

Suponha que seus FASTQs estejam em `data/` e você queira salvar resultados em `results/`:

```bash
bash bin/run_qc.sh \
  -i data/ \
  -o results/ \
  -t 4
```

Argumentos principais:

- `-i`: diretório com os arquivos FASTQ (`*.fastq` ou `*.fastq.gz`).
- `-o`: diretório onde serão salvos os relatórios de FastQC, MultiQC e `qc_summary.json`.
- `-t`: número de threads (padrão: 4).
- `-c`: arquivo de configuração de limiares (opcional; padrão: `config/thresholds.ini`).

## Estrutura de saída

Depois de rodar o pipeline, a estrutura típica em `results/` será:

```text
results/
  fastqc/       # relatórios individuais do FastQC (.html e .zip)
  multiqc/      # relatório agregado do MultiQC (multiqc_report.html)
  qc_json/
    qc_summary.json  # status PASS/FAIL por amostra e motivos
```

## Configuração de limiares

Os limiares de qualidade são definidos em `config/thresholds.ini`:

```ini
[thresholds]
min_reads = 100000
min_gc    = 30.0
max_gc    = 70.0
max_adapter_content = 5.0
```

Você pode ajustar esses valores sem mexer no código. O script `bin/check_thresholds.py` lê esse arquivo e aplica as regras a cada amostra.

## Dados de teste

Coloque FASTQs pequenos de teste em `tests/test_data/` (por exemplo, arquivos subsampleados com ~1k reads) e rode:

```bash
bash bin/run_qc.sh \
  -i tests/test_data/ \
  -o tests/results/ \
  -t 2
```

Verifique se:

- A pasta `tests/results/fastqc` contém relatórios FastQC.
- A pasta `tests/results/multiqc` contém `multiqc_report.html`.
- `tests/results/qc_json/qc_summary.json` foi criado com métricas e status por amostra.

## Licença

Este projeto é distribuído sob a licença MIT. Veja o arquivo `LICENSE` para detalhes.
