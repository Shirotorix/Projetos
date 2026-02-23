#!/usr/bin/env python3
"""Automação de relatórios semanais a partir de um CSV de atividades.

Formato esperado do CSV de entrada (cabeçalho):
    data,equipe,projeto,horas,status,descricao

Exemplo:
    2026-02-17,Backend,Portal,4.5,Concluído,Ajuste de autenticação
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Atividade:
    data: date
    equipe: str
    projeto: str
    horas: float
    status: str
    descricao: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gera relatórios semanais (Markdown + CSV consolidado)."
    )
    parser.add_argument(
        "--entrada",
        default="atividades.csv",
        help="Arquivo CSV com as atividades (padrão: atividades.csv).",
    )
    parser.add_argument(
        "--saida",
        default="relatorios",
        help="Diretório de saída dos relatórios (padrão: relatorios).",
    )
    parser.add_argument(
        "--data-base",
        default=None,
        help="Data de referência no formato YYYY-MM-DD. Se omitida, usa hoje.",
    )
    parser.add_argument(
        "--inicio-semana",
        type=int,
        default=0,
        choices=range(0, 7),
        metavar="{0..6}",
        help="Dia de início da semana (0=segunda, 6=domingo).",
    )
    return parser.parse_args()


def inicio_fim_semana(data_base: date, inicio_semana: int = 0) -> tuple[date, date]:
    deslocamento = (data_base.weekday() - inicio_semana) % 7
    inicio = data_base - timedelta(days=deslocamento)
    fim = inicio + timedelta(days=6)
    return inicio, fim


def carregar_atividades(caminho_csv: Path) -> list[Atividade]:
    atividades: list[Atividade] = []
    with caminho_csv.open("r", encoding="utf-8", newline="") as arquivo:
        leitor = csv.DictReader(arquivo)
        campos_obrigatorios = {"data", "equipe", "projeto", "horas", "status", "descricao"}
        if not leitor.fieldnames or not campos_obrigatorios.issubset(set(leitor.fieldnames)):
            faltantes = campos_obrigatorios - set(leitor.fieldnames or [])
            raise ValueError(f"Colunas ausentes no CSV: {', '.join(sorted(faltantes))}")

        for linha_num, linha in enumerate(leitor, start=2):
            try:
                atividades.append(
                    Atividade(
                        data=datetime.strptime(linha["data"], "%Y-%m-%d").date(),
                        equipe=linha["equipe"].strip(),
                        projeto=linha["projeto"].strip(),
                        horas=float(linha["horas"]),
                        status=linha["status"].strip(),
                        descricao=linha["descricao"].strip(),
                    )
                )
            except Exception as erro:  # validação de linha para facilitar depuração
                raise ValueError(f"Erro na linha {linha_num}: {erro}") from erro
    return atividades


def filtrar_periodo(atividades: Iterable[Atividade], inicio: date, fim: date) -> list[Atividade]:
    return [a for a in atividades if inicio <= a.data <= fim]


def consolidar(atividades: Iterable[Atividade]) -> dict[str, dict[str, float | int]]:
    resumo: dict[str, dict[str, float | int]] = defaultdict(
        lambda: {"total_horas": 0.0, "quantidade_tarefas": 0}
    )
    for atividade in atividades:
        chave = f"{atividade.equipe} :: {atividade.projeto}"
        resumo[chave]["total_horas"] += atividade.horas
        resumo[chave]["quantidade_tarefas"] += 1
    return dict(sorted(resumo.items(), key=lambda item: item[0]))


def salvar_csv_resumo(resumo: dict[str, dict[str, float | int]], caminho_saida: Path) -> None:
    with caminho_saida.open("w", encoding="utf-8", newline="") as arquivo:
        campos = ["grupo", "total_horas", "quantidade_tarefas", "media_horas_por_tarefa"]
        escritor = csv.DictWriter(arquivo, fieldnames=campos)
        escritor.writeheader()
        for grupo, dados in resumo.items():
            qtd = int(dados["quantidade_tarefas"])
            total_horas = float(dados["total_horas"])
            media = total_horas / qtd if qtd else 0.0
            escritor.writerow(
                {
                    "grupo": grupo,
                    "total_horas": f"{total_horas:.2f}",
                    "quantidade_tarefas": qtd,
                    "media_horas_por_tarefa": f"{media:.2f}",
                }
            )


def montar_markdown(
    atividades_semana: list[Atividade],
    resumo: dict[str, dict[str, float | int]],
    inicio: date,
    fim: date,
) -> str:
    total_horas = sum(float(item["total_horas"]) for item in resumo.values())
    total_tarefas = sum(int(item["quantidade_tarefas"]) for item in resumo.values())

    linhas = [
        f"# Relatório Semanal ({inicio.isoformat()} a {fim.isoformat()})",
        "",
        "## Indicadores gerais",
        f"- Total de horas registradas: **{total_horas:.2f}h**",
        f"- Total de tarefas registradas: **{total_tarefas}**",
        "",
        "## Consolidado por equipe/projeto",
        "| Grupo | Horas | Tarefas |",
        "|---|---:|---:|",
    ]

    for grupo, dados in resumo.items():
        linhas.append(
            f"| {grupo} | {float(dados['total_horas']):.2f} | {int(dados['quantidade_tarefas'])} |"
        )

    linhas.extend(["", "## Atividades da semana", ""])
    if not atividades_semana:
        linhas.append("Nenhuma atividade encontrada no período.")
    else:
        linhas.append("| Data | Equipe | Projeto | Horas | Status | Descrição |")
        linhas.append("|---|---|---|---:|---|---|")
        for atividade in sorted(atividades_semana, key=lambda a: a.data):
            linhas.append(
                "| {data} | {equipe} | {projeto} | {horas:.2f} | {status} | {descricao} |".format(
                    data=atividade.data.isoformat(),
                    equipe=atividade.equipe,
                    projeto=atividade.projeto,
                    horas=atividade.horas,
                    status=atividade.status,
                    descricao=atividade.descricao.replace("|", "/"),
                )
            )

    return "\n".join(linhas) + "\n"


def salvar_markdown(texto: str, caminho_saida: Path) -> None:
    caminho_saida.write_text(texto, encoding="utf-8")


def main() -> None:
    args = parse_args()
    data_base = (
        datetime.strptime(args.data_base, "%Y-%m-%d").date() if args.data_base else date.today()
    )

    inicio, fim = inicio_fim_semana(data_base, args.inicio_semana)
    entrada = Path(args.entrada)
    saida = Path(args.saida)
    saida.mkdir(parents=True, exist_ok=True)

    atividades = carregar_atividades(entrada)
    atividades_semana = filtrar_periodo(atividades, inicio, fim)
    resumo = consolidar(atividades_semana)

    sufixo = f"{inicio.isoformat()}_a_{fim.isoformat()}"
    arquivo_csv = saida / f"resumo_{sufixo}.csv"
    arquivo_md = saida / f"relatorio_{sufixo}.md"

    salvar_csv_resumo(resumo, arquivo_csv)
    markdown = montar_markdown(atividades_semana, resumo, inicio, fim)
    salvar_markdown(markdown, arquivo_md)

    print(f"Relatórios gerados com sucesso:")
    print(f"- CSV: {arquivo_csv}")
    print(f"- Markdown: {arquivo_md}")


if __name__ == "__main__":
    main()
