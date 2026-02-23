# Projetos

Repositório com scripts em Python.

## Automação de relatórios semanais

O script `automacao_relatorios_semanais.py` lê um CSV de atividades e gera:

- um **resumo em CSV** com horas e quantidade de tarefas por equipe/projeto;
- um **relatório em Markdown** com indicadores e detalhamento das atividades da semana.

### Formato do CSV de entrada

Cabeçalho obrigatório:

```csv
data,equipe,projeto,horas,status,descricao
```

### Exemplo de uso

```bash
python3 automacao_relatorios_semanais.py \
  --entrada atividades_exemplo.csv \
  --saida relatorios \
  --data-base 2026-02-21
```

Arquivos de saída esperados:

- `relatorios/resumo_2026-02-16_a_2026-02-22.csv`
- `relatorios/relatorio_2026-02-16_a_2026-02-22.md`

> Dica: agende a execução semanal via `cron` (Linux/macOS) ou Agendador de Tarefas (Windows).
