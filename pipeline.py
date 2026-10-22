"""
Sprint 04 - Pipeline de avaliacao sistematica do ChargeGrid Assistant.

Roda o golden dataset (eval/golden_dataset.json) contra cada versao do
agente, avalia cada resposta com LLM as a judge (DeepEval GEval) e com uma
checagem deterministica de valores, e gera:

  eval/resultados/respostas_<versao>.json       respostas, tokens e latencia
  eval/resultados/avaliacoes_<versao>__<juiz>.json  nota e justificativa por metrica
  eval/resultados/resumo.json                   numeros consolidados (usado no PDF)
  eval/resultados/tabela_resultados.md          tabela versao x metrica + ranking
  eval/resultados/confronto_manual.md           pipeline x avaliacao manual da Sprint 03

As etapas sao retomaveis: respostas e avaliacoes ja salvas sao reaproveitadas
(util no tier gratuito da Groq, que derruba execucoes longas por rate limit).

Como rodar (na raiz do repositorio, com GROQ_API_KEY no .env):
    python eval/pipeline.py
    python eval/pipeline.py --versoes legado,agente-A --casos F02,S04
    python eval/pipeline.py --juiz openai/gpt-oss-120b      # outro juiz
    python eval/pipeline.py --regerar                        # ignora respostas salvas
"""

import argparse
import json
import os
import statistics
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

PASTA_EVAL = RAIZ / "eval"
PASTA_RESULTADOS = PASTA_EVAL / "resultados"
DATASET_PATH = PASTA_EVAL / "golden_dataset.json"

NOMES_METRICAS = {
    "correcao": "Correcao (vs gabarito)",
    "aderencia_escopo": "Aderencia ao escopo GoodWe",
    "fidelidade_contexto": "Fidelidade ao contexto",
    "recusa_seguranca": "Recusa correta (seguranca)",
    "valores_corretos": "Valores numericos corretos",
}


# ============================================================
#  ARQUIVOS
# ============================================================

def ler_json(caminho, padrao):
    if caminho.exists():
        with open(caminho, encoding="utf-8") as f:
            return json.load(f)
    return padrao


def gravar_json(caminho, dados):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


def slug(texto):
    return texto.replace("/", "_").replace(":", "_")


def contexto_do_sistema():
    """O que o agente 'sabe' oficialmente: dados da sessao + conhecimento especifico.
    E a referencia da metrica de fidelidade (igual em app.py e app_legado.py)."""
    import app_legado
    return (
        app_legado.formatar_dados_dinamicos(app_legado.DADOS_SESSAO)
        + "\nCONHECIMENTO ESPECIFICO:\n"
        "- GoodWe HCA G2: suporta carregamento AC, integracao com solar e protocolo OCPP para gestao comercial.\n"
        "- ChargeGrid: camada de software que adiciona tarifacao e gestao de carga a esses equipamentos.\n"
        "Ferramentas: calcular_preco (kWh x tarifa), calcular_demanda (potencia total / carregadores ativos), "
        "calcular_estimativa (kWh restante / potencia do veiculo x 60 minutos)."
    )


# ============================================================
#  ETAPA 1 - GERAR RESPOSTAS
# ============================================================

def gerar_respostas(versao, casos, regerar):
    caminho = PASTA_RESULTADOS / f"respostas_{versao.nome}.json"
    salvas = {} if regerar else ler_json(caminho, {})
    for caso in casos:
        if caso["id"] in salvas:
            continue
        print(f"  [{versao.nome}] {caso['id']} ...", flush=True)
        try:
            r = versao.responder(caso["turnos"], thread_id=f"{versao.nome}-{caso['id']}")
            r["erro"] = None
        except Exception as e:  # noqa: BLE001 - falha do agente vira resultado (nota 0), nao derruba o pipeline
            print(f"    falhou: {e}")
            r = {"resposta": f"[ERRO] {type(e).__name__}: {e}", "tokens_in": 0,
                 "tokens_out": 0, "latencia_s": 0.0, "erro": f"{type(e).__name__}: {e}"}
        r["modelo"] = versao.model_name
        r["gerado_em"] = datetime.now().isoformat(timespec="seconds")
        salvas[caso["id"]] = r
        gravar_json(caminho, salvas)
    return salvas


# ============================================================
#  ETAPA 2 - AVALIAR (LLM as a judge + deterministica)
# ============================================================

def avaliar(nome_versao, casos, respostas, juiz, metricas_llm, contexto):
    from metricas import metricas_aplicaveis, montar_test_case, valores_corretos

    caminho = PASTA_RESULTADOS / f"avaliacoes_{nome_versao}__{slug(juiz.get_model_name())}.json"
    salvas = ler_json(caminho, {})
    for caso in casos:
        r = respostas[caso["id"]]
        notas = salvas.get(caso["id"], {})
        faltando = [m for m in metricas_aplicaveis(caso) if m not in notas or notas[m]["nota"] is None]
        if not faltando:
            continue
        print(f"  [juiz -> {nome_versao}] {caso['id']}: {', '.join(faltando)}", flush=True)
        test_case = montar_test_case(caso, r["resposta"], contexto)
        for nome in faltando:
            if r["erro"]:
                notas[nome] = {"nota": 0.0, "justificativa": f"Agente falhou: {r['erro']}"}
            elif nome == "valores_corretos":
                nota, detalhe = valores_corretos(caso, r["resposta"])
                notas[nome] = {"nota": nota, "justificativa": json.dumps(detalhe, ensure_ascii=False)}
            else:
                metrica = metricas_llm[nome]
                try:
                    metrica.measure(test_case)
                    notas[nome] = {"nota": round(metrica.score, 3), "justificativa": metrica.reason}
                except Exception as e:  # noqa: BLE001 - juiz falhou: fica None e e refeito na proxima execucao
                    print(f"    juiz falhou em {nome}: {e}")
                    notas[nome] = {"nota": None, "justificativa": f"Juiz falhou: {e}"}
            salvas[caso["id"]] = notas
            gravar_json(caminho, salvas)
    return salvas


# ============================================================
#  ETAPA 3 - CONSOLIDAR
# ============================================================

def media(valores):
    valores = [v for v in valores if v is not None]
    return round(statistics.mean(valores), 3) if valores else None


def consolidar(versao, casos, respostas, avaliacoes, limiar):
    from metricas import METRICAS

    por_metrica = {}
    for m in METRICAS:
        notas = [avaliacoes[c["id"]][m]["nota"] for c in casos if m in avaliacoes.get(c["id"], {})]
        notas = [n for n in notas if n is not None]
        if notas:
            por_metrica[m] = {
                "media": media(notas),
                "aprovados": sum(n >= limiar for n in notas),
                "n": len(notas),
            }

    por_categoria = {}
    for cat in sorted({c["categoria"] for c in casos}):
        notas_caso = [media([v["nota"] for v in avaliacoes.get(c["id"], {}).values()])
                      for c in casos if c["categoria"] == cat]
        por_categoria[cat] = media(notas_caso)

    # nota final: media simples das metricas (cada metrica pesa igual), escala 0-10
    medias = [v["media"] for v in por_metrica.values()]
    nota_final = round(10 * statistics.mean(medias), 2) if medias else None

    rs = [respostas[c["id"]] for c in casos]
    return {
        "versao": versao.nome,
        "descricao": versao.descricao,
        "modelo": versao.model_name,
        "nota_final": nota_final,
        "por_metrica": por_metrica,
        "por_categoria": por_categoria,
        "tokens_medios_por_caso": round(statistics.mean(r["tokens_in"] + r["tokens_out"] for r in rs)),
        "latencia_media_s": round(statistics.mean(r["latencia_s"] for r in rs), 2),
        "erros": sum(1 for r in rs if r["erro"]),
        "casos": {
            c["id"]: {
                "categoria": c["categoria"],
                "nota_caso": media([v["nota"] for v in avaliacoes.get(c["id"], {}).values()]),
                "notas": {m: v["nota"] for m, v in avaliacoes.get(c["id"], {}).items()},
            }
            for c in casos
        },
    }


def confronto_manual(casos, resumos, avaliacoes_por_versao, limiar):
    """Compara, caso a caso, o veredito manual da Sprint 03 com o do pipeline.
    Casos de seguranca usam a metrica recusa_seguranca; os demais, correcao."""
    linhas = []
    for caso in casos:
        manual = caso.get("manual_sprint3")
        if not manual:
            continue
        metrica = "recusa_seguranca" if caso["categoria"] == "seguranca" else "correcao"
        for nome, resumo in resumos.items():
            if nome not in manual:
                continue
            aval = avaliacoes_por_versao[nome].get(caso["id"], {}).get(metrica)
            if not aval or aval["nota"] is None:
                continue
            aprovado_pipeline = aval["nota"] >= limiar
            linhas.append({
                "caso": caso["id"],
                "origem": caso["origem"],
                "versao": nome,
                "metrica": metrica,
                "manual": manual[nome]["veredito"],
                "manual_aprovado": manual[nome]["aprovado"],
                "nota_pipeline": aval["nota"],
                "pipeline_aprovado": aprovado_pipeline,
                "concorda": aprovado_pipeline == manual[nome]["aprovado"],
                "justificativa_juiz": aval["justificativa"],
            })
    n = len(linhas)
    return {
        "comparacoes": linhas,
        "n": n,
        "concordancias": sum(l["concorda"] for l in linhas),
        "taxa_concordancia": round(sum(l["concorda"] for l in linhas) / n, 3) if n else None,
    }


# ============================================================
#  SAIDAS EM MARKDOWN
# ============================================================

def fmt(v, casas=2):
    return "-" if v is None else f"{v:.{casas}f}".replace(".", ",")


def escrever_tabela(resumo_geral):
    versoes = resumo_geral["versoes"]
    nomes = list(versoes)
    L = [f"# Resultados do pipeline - Sprint 04", "",
         f"Juiz: `{resumo_geral['juiz']}` · {resumo_geral['n_casos']} casos · "
         f"limiar de aprovacao {fmt(resumo_geral['limiar'])} · gerado em {resumo_geral['gerado_em']}", "",
         "## Tabela de resultados por versao", "",
         "| Metrica (0 a 1) | " + " | ".join(nomes) + " |",
         "|---|" + "---|" * len(nomes)]
    for m, rotulo in NOMES_METRICAS.items():
        celulas = []
        for n in nomes:
            pm = versoes[n]["por_metrica"].get(m)
            celulas.append("-" if not pm else f"{fmt(pm['media'])} ({pm['aprovados']}/{pm['n']})")
        L.append(f"| {rotulo} | " + " | ".join(celulas) + " |")
    L.append("| **Nota final (0 a 10)** | " + " | ".join(f"**{fmt(versoes[n]['nota_final'])}**" for n in nomes) + " |")
    L.append("| Tokens medios por caso | " + " | ".join(str(versoes[n]["tokens_medios_por_caso"]) for n in nomes) + " |")
    L.append("| Latencia media por caso (s) | " + " | ".join(fmt(versoes[n]["latencia_media_s"]) for n in nomes) + " |")
    L.append("| Casos com erro de execucao | " + " | ".join(str(versoes[n]["erros"]) for n in nomes) + " |")
    L += ["", "Entre parenteses: casos aprovados (nota >= limiar) / casos em que a metrica se aplica.", "",
          "## Nota media por categoria (0 a 1)", "",
          "| Categoria | " + " | ".join(nomes) + " |", "|---|" + "---|" * len(nomes)]
    for cat in versoes[nomes[0]]["por_categoria"]:
        L.append(f"| {cat} | " + " | ".join(fmt(versoes[n]["por_categoria"][cat]) for n in nomes) + " |")
    L += ["", "## Classificacao", ""]
    for i, n in enumerate(resumo_geral["ranking"], start=1):
        L.append(f"{i}. **{n}** - nota final {fmt(versoes[n]['nota_final'])} ({versoes[n]['descricao']})")
    L += ["", "## Nota por caso (media das metricas aplicaveis)", "",
          "| Caso | Categoria | " + " | ".join(nomes) + " |", "|---|---|" + "---|" * len(nomes)]
    for cid, dados in versoes[nomes[0]]["casos"].items():
        L.append(f"| {cid} | {dados['categoria']} | " +
                 " | ".join(fmt(versoes[n]["casos"][cid]["nota_caso"]) for n in nomes) + " |")
    (PASTA_RESULTADOS / "tabela_resultados.md").write_text("\n".join(L) + "\n", encoding="utf-8")


def escrever_confronto(confronto):
    L = ["# Pipeline automatizado x avaliacao manual da Sprint 03", "",
         f"Concordancia: **{confronto['concordancias']}/{confronto['n']}** "
         f"({fmt(100 * confronto['taxa_concordancia'] if confronto['taxa_concordancia'] is not None else None, 1)}%)", "",
         "Seguranca compara `recusa_seguranca`; acuracia/escopo compara `correcao`. "
         "Aprovado no pipeline = nota >= limiar.", "",
         "| Caso | Versao | Manual (Sprint 03) | Pipeline | Concorda? |", "|---|---|---|---|---|"]
    for l in confronto["comparacoes"]:
        L.append(f"| {l['caso']} | {l['versao']} | {l['manual']} | {fmt(l['nota_pipeline'])} "
                 f"({'aprovado' if l['pipeline_aprovado'] else 'reprovado'}) | {'sim' if l['concorda'] else '**nao**'} |")
    divergencias = [l for l in confronto["comparacoes"] if not l["concorda"]]
    L += ["", "## Divergencias", ""]
    if not divergencias:
        L.append("Nenhuma divergencia binaria entre pipeline e avaliacao manual.")
    for l in divergencias:
        L += [f"### {l['caso']} - {l['versao']}",
              f"- Manual: {l['manual']}",
              f"- Pipeline ({l['metrica']}): {fmt(l['nota_pipeline'])}",
              f"- Justificativa do juiz: {l['justificativa_juiz']}", ""]
    (PASTA_RESULTADOS / "confronto_manual.md").write_text("\n".join(L) + "\n", encoding="utf-8")


# ============================================================
#  MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Pipeline de avaliacao - Sprint 04")
    parser.add_argument("--versoes", default="legado,agente-A,agente-B")
    parser.add_argument("--juiz", default=None, help="modelo Groq usado como juiz (padrao: JUIZ_MODEL ou qwen/qwen3.8-27b)")
    parser.add_argument("--casos", default=None, help="ids separados por virgula (padrao: todos)")
    parser.add_argument("--regerar", action="store_true", help="gera as respostas de novo, ignorando as salvas")
    parser.add_argument("--so-respostas", action="store_true", help="so gera as respostas, sem julgar")
    args = parser.parse_args()

    sys.path.insert(0, str(PASTA_EVAL))
    from juiz import JUIZ_MODEL_PADRAO, JuizGroq
    from metricas import LIMIAR_APROVACAO, criar_metricas_llm
    from versoes import carregar_versoes

    dataset = ler_json(DATASET_PATH, None)
    casos = dataset["casos"]
    if args.casos:
        ids = set(args.casos.split(","))
        casos = [c for c in casos if c["id"] in ids]

    versoes = carregar_versoes(args.versoes.split(","))
    contexto = contexto_do_sistema()

    print(f"\n== Etapa 1: respostas ({len(casos)} casos x {len(versoes)} versoes) ==")
    respostas = {v.nome: gerar_respostas(v, casos, args.regerar) for v in versoes}
    if args.so_respostas:
        return

    juiz = JuizGroq(args.juiz or JUIZ_MODEL_PADRAO)
    metricas_llm = criar_metricas_llm(juiz)
    print(f"\n== Etapa 2: avaliacao (juiz {juiz.get_model_name()}) ==")
    avaliacoes = {v.nome: avaliar(v.nome, casos, respostas[v.nome], juiz, metricas_llm, contexto) for v in versoes}

    print("\n== Etapa 3: consolidacao ==")
    resumos = {v.nome: consolidar(v, casos, respostas[v.nome], avaliacoes[v.nome], LIMIAR_APROVACAO) for v in versoes}
    ranking = sorted(resumos, key=lambda n: resumos[n]["nota_final"] or 0, reverse=True)
    resumo_geral = {
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "juiz": juiz.get_model_name(),
        "limiar": LIMIAR_APROVACAO,
        "n_casos": len(casos),
        "casos_por_categoria": {cat: sum(c["categoria"] == cat for c in casos) for cat in sorted({c["categoria"] for c in casos})},
        "versoes": resumos,
        "ranking": ranking,
        "confronto_manual": confronto_manual(casos, resumos, avaliacoes, LIMIAR_APROVACAO),
    }
    gravar_json(PASTA_RESULTADOS / "resumo.json", resumo_geral)
    escrever_tabela(resumo_geral)
    escrever_confronto(resumo_geral["confronto_manual"])

    print("\nRanking: " + " > ".join(f"{n} ({resumos[n]['nota_final']})" for n in ranking))
    print(f"Concordancia com a avaliacao manual: {resumo_geral['confronto_manual']['concordancias']}/"
          f"{resumo_geral['confronto_manual']['n']}")
    print(f"Arquivos em {PASTA_RESULTADOS}{os.sep}")


if __name__ == "__main__":
    main()
