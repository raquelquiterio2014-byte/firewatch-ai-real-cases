# Configurar o Gemini — FireWatch AI Real Cases v0.4

## Executar

Extraia o ZIP, abra a pasta no PyCharm e execute `main.py` com Python 3.12. Esta integração usa HTTPS com a biblioteca padrão do Python; não exige instalação por pip.

## Configurar sua chave

1. Abra a aba **Gemini settings**.
2. Cole sua chave no campo **API key**. O campo é mascarado; a aplicação não salva essa chave em banco, relatórios ou arquivos.
3. Mantenha `gemini-2.5-flash` no campo **Model ID** se ele estiver disponível na sua conta.
4. Clique em **Test Gemini connection**. O teste faz uma requisição de diagnóstico sem dados dos casos. Em falhas temporárias, pode repetir até três tentativas no total.
5. Um resultado com `source: gemini` e `reason: OK` confirma uma resposta da API validada pelo programa.
6. Marque **Enable Gemini for analysis** para autorizar o envio das observações admitidas nas próximas análises. A chave por si só não ativa o envio automático.

Alternativa no PowerShell, válida para a sessão atual do terminal:

```powershell
$env:GEMINI_API_KEY = "SUA_CHAVE_LOCAL"
py -3.12 main.py
```

Alternativa para o PyCharm: Run → Edit Configurations → Environment variables → adicionar `GEMINI_API_KEY` com a chave.

Também é possível copiar `.env.example` para `.env` na pasta do projeto e preencher a chave. Esse arquivo é texto local; guarde-o somente no seu computador. A variável de ambiente tem prioridade sobre `.env`, e o campo da interface permite substituição para a sessão. O programa não executa conteúdo do arquivo `.env`.

Não envie sua chave por mensagem e não a inclua no GitHub. O ZIP entregue contém apenas o arquivo de exemplo vazio.

## Como executar uma análise com Gemini

Os dez casos agora incluem 30 registros documentados, três por caso.

1. Selecione o caso e consulte **Prefilled evidence**.
2. Em **Gemini settings**, configure a chave, teste a conexão e habilite o Gemini.
3. Em **Analysis**, mantenha **Retrospective documents (prefilled)**.
4. Clique **Run analysis** ou **Analyze all 10 cases**. Não precisa preencher a data de corte nesse modo.
5. Leia o relatório e o trace, registre a revisão e exporte os resultados.

O modo **Historical cutoff (original records)** continua disponível separadamente, com as exigências anteriores de registro original e horários comprovados. As evidências pré-preenchidas não entram nesse modo.

A análise documental pode usar relatórios publicados depois do incêndio. As datas dos eventos e de publicação são identificadas, e horários originais desconhecidos permanecem vazios. O Gemini recebe o contexto de que se trata de revisão documental com informação retrospectiva, e não de simulação do que os responsáveis pela resposta sabiam.

Um lote normalmente faz 20 chamadas lógicas (duas por caso), além de tentativas limitadas em falhas transitórias. Após falha persistente de quota, autorização ou acesso ao modelo em um caso, os demais casos usam fallback sem novas chamadas. Cada resultado concluído é salvo durante o lote.

## Ler o resultado

- `llm_assisted`: ambas as etapas retornaram respostas com estrutura, referências e trechos validados localmente.
- `llm_partial_fallback`: somente uma etapa teve resposta aceita; a outra usou fallback.
- `deterministic_fallback`: nenhuma etapa Gemini teve resposta aceita; os gates determinísticos continuam ativos.
- `deterministic_document_analysis`: análise documental offline.
- `deterministic_research_readiness`: avaliação offline dos registros originais no modo de corte histórico.

A validação local confirma formato, IDs e correspondência literal dos trechos com as observações registradas. Ela não prova que a interpretação está correta, que a fonte é autêntica ou que não há conhecimento externo implícito no texto do modelo. Toda interpretação exige revisão humana. O Gemini não altera a data de corte, a classificação de prontidão, o gate humano ou a decisão de uso operacional.

## Diagnóstico

| Código | Significado e próximo passo |
|---|---|
| `MISSING_KEY` | Configure a chave localmente. Nenhuma chamada foi feita. |
| `NO_ADMITTED_EVIDENCE` | Não há evidências verificadas dentro do corte; a análise Gemini não é chamada. O teste de conexão continua disponível. |
| `HTTP_400` | Requisição/configuração não aceita pelo serviço; confira modelo e documentação. |
| `HTTP_401` / `HTTP_403` | Verifique chave, permissões e acesso ao modelo. Sem repetição automática. |
| `HTTP_404` | Confira disponibilidade e nome do modelo na sua conta. Não há troca automática. |
| `HTTP_429` | Quota ou limitação de taxa. Até três tentativas, com espera curta; depois fallback. |
| `NETWORK_ERROR` | Verifique conexão, proxy e firewall. Até três tentativas. |
| `INVALID_STRUCTURED_OUTPUT` | Resposta malformada, referência desconhecida ou trecho sem correspondência; rejeitada e limitada a três tentativas. |
| `INCOMPLETE_OR_BLOCKED` | Resposta não terminou normalmente; não é usada como análise válida. |
| `INPUT_TOO_LARGE` | Solicitação excedeu o limite local de 60 mil caracteres; nenhuma chamada foi feita. |

Cada chamada tem timeout de 25 segundos; as duas etapas podem demorar alguns minutos em caso de falhas e novas tentativas. A interface usa uma tarefa em segundo plano. Espere concluir antes de fechar o aplicativo. A execução só é persistida ao final; encerramentos antecipados podem perder aquela execução.

## Modelo e documentação

A documentação consultada em 16/10/2026 informa restrições de acesso ao Gemini 2.5 para novas contas/projetos. O campo de modelo é editável, e a aplicação não substitui o modelo silenciosamente. Outros modelos podem exigir adaptações de parâmetros; valide a conexão antes de usá-los.

- [Gemini 2.5 Flash](https://ai.google.dev/gemini-api/docs/models/gemini-2.5-flash)
- [REST generateContent](https://ai.google.dev/api/generate-content)
- [Structured output](https://ai.google.dev/gemini-api/docs/generate-content/structured-output)

A integração foi testada com respostas simuladas e falhas controladas. Não foi feita uma chamada autenticada real no ambiente de criação. O botão de teste permite concluir essa verificação no seu computador com a sua chave.

## Dossiê original da v0.4

Em **Reviewed pilot**, escolha um dos cortes e clique **Run pilot cutoff**. Se o Gemini estiver habilitado, ele recebe somente os registros admitidos condicionalmente para aquele corte, com os intervalos de disponibilidade e os limites do método. No corte PRIMARY, os registros posteriores de exposição ficam fora do prompt.

O primeiro dossiê offline já está preparado: **Open first reviewed dossier** não faz chamada de API. A revisão técnica incluída foi feita por IA; a aprovação humana só é registrada quando uma pessoa preenche nome, justificativa e checklist em History & review.
