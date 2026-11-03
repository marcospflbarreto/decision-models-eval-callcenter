"""Suíte de Testes de Modelos de Decisão para Call Center Bancário (10 Departamentos em Português)."""
from __future__ import annotations

import json
from pathlib import Path
from arena.config import DATASETS, write_json
from arena.contracts import Case, Question

DEPARTMENTS = [
    "cartoes_e_limite",
    "faturas_e_cobranca",
    "conta_corrente_e_pix",
    "emprestimos_e_financiamento",
    "investimentos_e_poupanca",
    "fraude_e_seguranca",
    "suporte_tecnico_app",
    "seguros_e_assistencia",
    "encerramento_de_conta",
    "ouvidoria_e_reclamacoes",
]

DEPARTMENT_NAMES = {
    "cartoes_e_limite": "Cartões e Limite de Crédito",
    "faturas_e_cobranca": "Faturas e Cobrança",
    "conta_corrente_e_pix": "Conta Corrente e PIX",
    "emprestimos_e_financiamento": "Empréstimos e Financiamentos",
    "investimentos_e_poupanca": "Investimentos e Poupança",
    "fraude_e_seguranca": "Fraude e Segurança",
    "suporte_tecnico_app": "Suporte Técnico e App",
    "seguros_e_assistencia": "Seguros e Assistência",
    "encerramento_de_conta": "Encerramento de Conta",
    "ouvidoria_e_reclamacoes": "Ouvidoria e Reclamações",
}

DEPARTMENT_DESCRIPTIONS = {
    "cartoes_e_limite": "Aumento ou alteração de limite de crédito, solicitação de 2ª via de cartão físico/virtual, bloqueio/desbloqueio temporário por viagem ou perda.",
    "faturas_e_cobranca": "Dúvidas sobre encargos na fatura, segunda via de boleto/fatura, parcelamento de fatura, renegociação de dívidas em atraso e contestação de cobrança indevida de anuidade.",
    "conta_corrente_e_pix": "Extrato de conta, comprovante de transferência, limites diários de transação PIX/TED, cadastro de chave PIX e tarifas de manutenção de conta.",
    "emprestimos_e_financiamento": "Simulação e contratação de empréstimo pessoal/consignado, financiamento de veículos/imóveis, quitação antecipada com desconto e emissão de boletos de parcelas.",
    "investimentos_e_poupanca": "Aplicações e resgates em CDB, LCI, Tesouro Direto, fundos de investimento, rendimentos de poupança e atualização de perfil de investidor (API/Suitability).",
    "fraude_e_seguranca": "Notificação de compras não reconhecidas, suspeita de golpe do PIX, clonagem de cartão, roubo/furto de celular com acesso ao banco e acionamento de MED (Mecanismo Especial de Devolução).",
    "suporte_tecnico_app": "Erros no aplicativo móvel ou Internet Banking, falhas no reconhecimento facial, senha do app bloqueada, problemas com recebimento de código SMS/Token e erro de conexão.",
    "seguros_e_assistencia": "Acionamento de sinistros, apólices de seguro cartão protegido, seguro de vida, residencial e auto, consulta de coberturas e cancelamento de apólice de seguro.",
    "encerramento_de_conta": "Solicitação formal de cancelamento de conta corrente/pagamento, portabilidade de saída de salário e emissão de termo de quitação para fechamento de conta.",
    "ouvidoria_e_reclamacoes": "Reclamação formal contra atendimento em agência ou SAC, descumprimento de prazos anteriores, contestação de decisões do suporte e denúncias.",
}

RAW_CASES = [
    # 1. cartoes_e_limite (10 casos)
    {
        "id": "banking-cc-001",
        "gold": "cartoes_e_limite",
        "dialogue": "Cliente: Boa tarde. Vou viajar para o exterior na próxima semana e gostaria de solicitar um aumento temporário do limite do meu cartão de crédito internacional."
    },
    {
        "id": "banking-cc-002",
        "gold": "cartoes_e_limite",
        "dialogue": "Cliente: Perdi meu cartão físico de débito e crédito no shopping hoje cedo. Preciso bloquear o cartão antigo e pedir a segunda via."
    },
    {
        "id": "banking-cc-003",
        "gold": "cartoes_e_limite",
        "dialogue": "Cliente: Meu novo cartão de crédito chegou pelos correios ontem. Como faço para realizar o desbloqueio para começar a usar?"
    },
    {
        "id": "banking-cc-004",
        "gold": "cartoes_e_limite",
        "dialogue": "Cliente: Gostaria de pedir um cartão adicional para o meu filho dependente com um limite mensal estipulado de R$ 1.000."
    },
    {
        "id": "banking-cc-005",
        "gold": "cartoes_e_limite",
        "dialogue": "Cliente: O chip do meu cartão físico está bastante descascado e as maquininhas não estão conseguindo ler. Preciso da emissão de um novo cartão."
    },
    {
        "id": "banking-cc-006",
        "gold": "cartoes_e_limite",
        "dialogue": "Cliente: Qual é o meu limite total de crédito atual e quanto eu ainda tenho disponível para compras neste mês?"
    },
    {
        "id": "banking-cc-007",
        "gold": "cartoes_e_limite",
        "dialogue": "Cliente: Tentei fazer uma compra de R$ 2.000 no cartão mas deu transação recusada por limite diário excedido no cartão. É possível ajustar esse limite diário?"
    },
    {
        "id": "banking-cc-008",
        "gold": "cartoes_e_limite",
        "dialogue": "Cliente: Esqueci a senha de 4 dígitos do meu cartão físico de crédito. Como solicito a redefinição dessa senha?"
    },
    {
        "id": "banking-cc-009",
        "gold": "cartoes_e_limite",
        "dialogue": "Cliente: Quero criar um cartão de crédito virtual temporário de uso único para fazer uma compra em um site na internet com mais segurança."
    },
    {
        "id": "banking-cc-010",
        "gold": "cartoes_e_limite",
        "dialogue": "Cliente: Olá, gostaria de verificar os requisitos necessários para conseguir a isenção permanente da anuidade do meu cartão Mastercard Black."
    },

    # 2. faturas_e_cobranca (10 casos)
    {
        "id": "banking-cc-011",
        "gold": "faturas_e_cobranca",
        "dialogue": "Cliente: Não recebi a fatura do meu cartão de crédito que vence amanhã. Pode enviar a 2ª via do boleto em formato PDF para o meu e-mail?"
    },
    {
        "id": "banking-cc-012",
        "gold": "faturas_e_cobranca",
        "dialogue": "Cliente: Veio uma cobrança de juros e multa por atraso na fatura deste mês, mas eu paguei no dia do vencimento. Quero o estorno desses encargos."
    },
    {
        "id": "banking-cc-013",
        "gold": "faturas_e_cobranca",
        "dialogue": "Cliente: O valor total da minha fatura ficou muito alto este mês. Quais são as opções de parcelamento da fatura em até 12 vezes?"
    },
    {
        "id": "banking-cc-014",
        "gold": "faturas_e_cobranca",
        "dialogue": "Cliente: Efectuei o pagamento da minha fatura há 3 dias via PIX mas o saldo do meu limite ainda não foi restabelecido e a fatura consta como aberta."
    },
    {
        "id": "banking-cc-015",
        "gold": "faturas_e_cobranca",
        "dialogue": "Cliente: Gostaria de entender o cálculo da cobrança de IOF e taxa de conversão cambial na fatura da minha última viagem internacional."
    },
    {
        "id": "banking-cc-016",
        "gold": "faturas_e_cobranca",
        "dialogue": "Cliente: Identifiquei duas cobranças de anuidade no mesmo mês na fatura do cartão. Preciso do cancelamento de uma das cobranças duplicadas."
    },
    {
        "id": "banking-cc-017",
        "gold": "faturas_e_cobranca",
        "dialogue": "Cliente: Estou com duas faturas em atraso e gostaria de negociar uma entrada e renegociar o saldo restante com desconto nos juros."
    },
    {
        "id": "banking-cc-018",
        "gold": "faturas_e_cobranca",
        "dialogue": "Cliente: Quero alterar o dia do vencimento da minha fatura do dia 10 para o dia 25 de todos os meses."
    },
    {
        "id": "banking-cc-019",
        "gold": "faturas_e_cobranca",
        "dialogue": "Cliente: O aplicativo do banco estava fora do ar no dia do vencimento e por isso não consegui pagar o boleto. Gostaria de isenção da multa de atraso."
    },
    {
        "id": "banking-cc-020",
        "gold": "faturas_e_cobranca",
        "dialogue": "Cliente: Qual é o valor exato do pagamento mínimo da minha fatura atual e qual será a taxa de juros do rotativo se eu pagar somente o mínimo?"
    },

    # 3. conta_corrente_e_pix (10 casos)
    {
        "id": "banking-cc-021",
        "gold": "conta_corrente_e_pix",
        "dialogue": "Cliente: Digitei a chave PIX errada ao fazer uma transferência de R$ 300 e o dinheiro foi para a conta de um desconhecido. Como posso tentar reaver esse valor?"
    },
    {
        "id": "banking-cc-022",
        "gold": "conta_corrente_e_pix",
        "dialogue": "Cliente: Preciso realizar um PIX de R$ 15.000 para comprar um carro hoje, mas meu limite diário é de R$ 5.000. Como solicito o aumento imediato do limite de PIX?"
    },
    {
        "id": "banking-cc-023",
        "gold": "conta_corrente_e_pix",
        "dialogue": "Cliente: Preciso do extrato completo da minha conta corrente dos últimos 6 meses em PDF para apresentar na comprovação de renda do aluguel."
    },
    {
        "id": "banking-cc-024",
        "gold": "conta_corrente_e_pix",
        "dialogue": "Cliente: Fiz uma transferência TED ontem de manhã, o valor saiu da minha conta mas o destinatário alega que ainda não recebeu. Podem emitir o comprovante com o código de controle bancário?"
    },
    {
        "id": "banking-cc-025",
        "gold": "conta_corrente_e_pix",
        "dialogue": "Cliente: Foi debitada uma tarifa mensal de manutenção de conta de R$ 42,00. Gostaria de solicitar a conversão da minha conta para o pacote de Serviços Essenciais gratuito."
    },
    {
        "id": "banking-cc-026",
        "gold": "conta_corrente_e_pix",
        "dialogue": "Cliente: Minha conta ficou com saldo negativo de R$ 150 devido a um débito automático não planejado. Quero saber o valor dos juros de cheque especial cobrados."
    },
    {
        "id": "banking-cc-027",
        "gold": "conta_corrente_e_pix",
        "dialogue": "Cliente: Tentei cadastrar meu CPF como chave PIX na minha conta mas apareceu uma mensagem dizendo que a chave já pertence a outra instituição. Como faço a portabilidade?"
    },
    {
        "id": "banking-cc-028",
        "gold": "conta_corrente_e_pix",
        "dialogue": "Cliente: Recebi um PIX de R$ 4.000 e o valor consta no extrato como bloqueado temporariamente para análise de segurança. Quanto tempo dura esse bloqueio preventivo?"
    },
    {
        "id": "banking-cc-029",
        "gold": "conta_corrente_e_pix",
        "dialogue": "Cliente: Gostaria de consultar os comprovantes de pagamentos de contas de luz e água que realizei pelo Internet Banking no mês passado."
    },
    {
        "id": "banking-cc-030",
        "gold": "conta_corrente_e_pix",
        "dialogue": "Cliente: Qual é o meu limite contratado de cheque especial disponível na conta e qual é o prazo máximo para usar sem incidência de multa adicional?"
    },

    # 4. emprestimos_e_financiamento (10 casos)
    {
        "id": "banking-cc-031",
        "gold": "emprestimos_e_financiamento",
        "dialogue": "Cliente: Gostaria de fazer uma simulação de pré-aprovação de empréstimo pessoal de R$ 20.000 parcelado em 36 vezes para reforma da casa."
    },
    {
        "id": "banking-cc-032",
        "gold": "emprestimos_e_financiamento",
        "dialogue": "Cliente: Tenho um financiamento de veículo com 18 parcelas restantes. Gostaria de calcular o valor para liquidação antecipada com o desconto proporcional dos juros futuros."
    },
    {
        "id": "banking-cc-033",
        "gold": "emprestimos_e_financiamento",
        "dialogue": "Cliente: Sou aposentado do INSS e gostaria de consultar a minha margem consignável disponível para contratação de empréstimo consignado."
    },
    {
        "id": "banking-cc-034",
        "gold": "emprestimos_e_financiamento",
        "dialogue": "Cliente: Estou com duas parcelas em atraso do meu financiamento imobiliário. Gostaria de solicitar a renegociação ou incorporação do atraso nas parcelas futuras."
    },
    {
        "id": "banking-cc-035",
        "gold": "emprestimos_e_financiamento",
        "dialogue": "Cliente: Preciso da 2ª via do boleto da parcela de número 12 do financiamento do meu carro que vence nesta sexta-feira."
    },
    {
        "id": "banking-cc-036",
        "gold": "emprestimos_e_financiamento",
        "dialogue": "Cliente: Recebi uma proposta de portabilidade do meu empréstimo consignado para outro banco com taxa de juros menor. Como obtenho o DED (Demonstrativo de Evolução da Dívida)?"
    },
    {
        "id": "banking-cc-037",
        "gold": "emprestimos_e_financiamento",
        "dialogue": "Cliente: Fiz uma simulação de crédito pessoal e gostaria de tirar dúvidas sobre a composição do CET (Custo Efetivo Total), especialmente as tarifas administrativas."
    },
    {
        "id": "banking-cc-038",
        "gold": "emprestimos_e_financiamento",
        "dialogue": "Cliente: Acabei contratando um empréstimo pessoal por engano no caixa eletrônico há 2 dias. Estou no prazo de 7 dias de arrependimento e quero devolver o valor e cancelar o contrato."
    },
    {
        "id": "banking-cc-039",
        "gold": "emprestimos_e_financiamento",
        "dialogue": "Cliente: Gostaria de antecipar 5 períodos do meu Saque-Aniversário do FGTS utilizando o saldo como garantia de crédito."
    },
    {
        "id": "banking-cc-040",
        "gold": "emprestimos_e_financiamento",
        "dialogue": "Cliente: Terminei de pagar a última parcela do financiamento do meu carro no mês passado. Quando será realizada a baixa do gravame no Detran e a emissão do termo de quitação?"
    },

    # 5. investimentos_e_poupanca (10 casos)
    {
        "id": "banking-cc-041",
        "gold": "investimentos_e_poupanca",
        "dialogue": "Cliente: Gostaria de efetuar o resgate total de R$ 5.000 que tenho aplicado em um CDB com liquidez diária para a minha conta corrente."
    },
    {
        "id": "banking-cc-042",
        "gold": "investimentos_e_poupanca",
        "dialogue": "Cliente: Qual é a tabela regressiva de Imposto de Renda aplicada no resgate de títulos do Tesouro Direto mantidos por mais de 2 anos?"
    },
    {
        "id": "banking-cc-043",
        "gold": "investimentos_e_poupanca",
        "dialogue": "Cliente: Tenho R$ 10.000 parados na conta corrente e gostaria de investir em um fundo de renda fixa ou CDB que pague pelo menos 100% do CDI."
    },
    {
        "id": "banking-cc-044",
        "gold": "investimentos_e_poupanca",
        "dialogue": "Cliente: Meu aplicativo está informando que meu questionário de perfil de investidor (suitability) está expirado e não posso aplicar em fundos. Como refazer o teste?"
    },
    {
        "id": "banking-cc-045",
        "gold": "investimentos_e_poupanca",
        "dialogue": "Cliente: Gostaria de entender em qual dia do mês ocorre o aniversário dos meus depósitos na poupança para não perder o rendimento mensal ao resgatar."
    },
    {
        "id": "banking-cc-046",
        "gold": "investimentos_e_poupanca",
        "dialogue": "Cliente: Quais são as opções disponíveis de LCI e LCA isentas de Imposto de Renda para pessoa física com prazo de carência de 90 dias?"
    },
    {
        "id": "banking-cc-047",
        "gold": "investimentos_e_poupanca",
        "dialogue": "Cliente: Preciso solicitar a transferência de custódia (STVM) de algumas ações da Bolsa que tenho guardadas na corretora do banco para outra instituição."
    },
    {
        "id": "banking-cc-048",
        "gold": "investimentos_e_poupanca",
        "dialogue": "Cliente: Onde encontro no aplicativo o informe de rendimentos consolidado de todos os meus investimentos para a declaração de Imposto de Renda?"
    },
    {
        "id": "banking-cc-049",
        "gold": "investimentos_e_poupanca",
        "dialogue": "Cliente: Gostaria de ativar o recurso de aplicação automática do saldo excedente da conta corrente em CDB de liquidez diária ao final de cada dia."
    },
    {
        "id": "banking-cc-050",
        "gold": "investimentos_e_poupanca",
        "dialogue": "Cliente: Qual é o valor mínimo necessário para aplicação inicial em Letras Financeiras com rentabilidade pré-fixada?"
    },

    # 6. fraude_e_seguranca (10 casos)
    {
        "id": "banking-cc-051",
        "gold": "fraude_e_seguranca",
        "dialogue": "Cliente: URGENTE! Recebi uma ligação de alguém se dizendo do setor de segurança do banco pedindo um PIX de confirmação e acabei caindo em um golpe! Preciso bloquear minha conta e acionar a emergência!"
    },
    {
        "id": "banking-cc-052",
        "gold": "fraude_e_seguranca",
        "dialogue": "Cliente: Acabei de receber uma notificação de compra presencial de R$ 3.800 em uma loja de eletrônicos no Rio de Janeiro, mas estou em São Paulo e com o meu cartão no bolso! Clonaram meu cartão!"
    },
    {
        "id": "banking-cc-053",
        "gold": "fraude_e_seguranca",
        "dialogue": "Cliente: Meu celular foi furtado na rua agora há pouco. O aplicativo do banco estava instalado e com acesso. Preciso que bloqueiem imediatamente o acesso ao app e todas as senhas de atendimento!"
    },
    {
        "id": "banking-cc-054",
        "gold": "fraude_e_seguranca",
        "dialogue": "Cliente: Apareceram duas compras em dólares no meu cartão de crédito que eu não reconheço, feitas em um site de games estrangeiro. Não fiz essas compras e quero contestar por fraude!"
    },
    {
        "id": "banking-cc-055",
        "gold": "fraude_e_seguranca",
        "dialogue": "Cliente: Fiz uma transferência PIX após ser enganado por um anúncio falso de vendas no Instagram. Quero abrir a solicitação do MED (Mecanismo Especial de Devolução) do Banco Central para tentar reaver o dinheiro."
    },
    {
        "id": "banking-cc-056",
        "gold": "fraude_e_seguranca",
        "dialogue": "Cliente: Recebi um aviso por e-mail de que houve 5 tentativas seguidas de login mal-sucedidas na minha conta vindas de um computador no exterior. Quero alterar minhas credenciais por segurança."
    },
    {
        "id": "banking-cc-057",
        "gold": "fraude_e_seguranca",
        "dialogue": "Cliente: Perdi minha bolsa onde estava meu cartão e infelizmente a senha anotada no papel. Já efetuaram um saque de R$ 1.000 na minha conta corrente! Bloqueiem a conta agora!"
    },
    {
        "id": "banking-cc-058",
        "gold": "fraude_e_seguranca",
        "dialogue": "Cliente: Cliquei por engano em um link suspeito enviado por SMS fingindo ser atualização de segurança do banco e digitei minhas senhas. Suspeito de ter sido vítima de phishing!"
    },
    {
        "id": "banking-cc-059",
        "gold": "fraude_e_seguranca",
        "dialogue": "Cliente: Um suposto técnico do banco pediu para eu instalar um aplicativo de suporte remoto no celular para resolver um erro e vi minha tela mexendo sozinha! Desconectem minha conta de todos os dispositivos!"
    },
    {
        "id": "banking-cc-060",
        "gold": "fraude_e_seguranca",
        "dialogue": "Cliente: Uma compra de alto valor foi autorizada no meu cartão de crédito sem exigir o código de verificação SMS ou aprovação no aplicativo. Quero reportar a falha de segurança e cancelar o débito."
    },

    # 7. suporte_tecnico_app (10 casos)
    {
        "id": "banking-cc-061",
        "gold": "suporte_tecnico_app",
        "dialogue": "Cliente: Não estou conseguindo acessar a conta pelo aplicativo porque a validação por biometria facial fica dando erro de 'Rosto não identificado' toda vez que tento entrar."
    },
    {
        "id": "banking-cc-062",
        "gold": "suporte_tecnico_app",
        "dialogue": "Cliente: Após atualizar o aplicativo para a versão mais recente no Android, o app fecha sozinho imediatamente toda vez que clico no ícone da conta."
    },
    {
        "id": "banking-cc-063",
        "gold": "suporte_tecnico_app",
        "dialogue": "Cliente: Digitei minha senha de 6 dígitos do aplicativo incorretamente por 3 vezes seguidas e agora a conta aparece com status 'Acesso bloqueado por motivo de segurança'. Como faço para desbloquear pelo suporte?"
    },
    {
        "id": "banking-cc-064",
        "gold": "suporte_tecnico_app",
        "dialogue": "Cliente: Troquei de celular e preciso validar o novo aparelho, mas o código SMS de confirmação nunca chega no meu número de telefone cadastrado."
    },
    {
        "id": "banking-cc-065",
        "gold": "suporte_tecnico_app",
        "dialogue": "Cliente: Estou tentando anexar a foto do meu comprovante de residência no cadastro do aplicativo para atualizar meus dados, mas a tela fica travada em 'Enviando arquivo...' sem concluir."
    },
    {
        "id": "banking-cc-066",
        "gold": "suporte_tecnico_app",
        "dialogue": "Cliente: Ao tentar realizar qualquer operação no Internet Banking pelo computador aparece a mensagem de erro 'Falha de comunicação com o servidor - Código ERR-503'. O sistema de vocês está fora do ar?"
    },
    {
        "id": "banking-cc-067",
        "gold": "suporte_tecnico_app",
        "dialogue": "Cliente: Como faço para sincronizar o iToken/Token Virtual no meu aplicativo novo para conseguir autorizar pagamentos de boleto acima de R$ 1.000?"
    },
    {
        "id": "banking-cc-068",
        "gold": "suporte_tecnico_app",
        "dialogue": "Cliente: Quando abro o leitor de código de barras no aplicativo a câmera fica totalmente preta e não consegue escanear a conta de luz."
    },
    {
        "id": "banking-cc-069",
        "gold": "suporte_tecnico_app",
        "dialogue": "Cliente: O chaveiro token físico que utilizo para acessar a conta da minha empresa começou a apresentar a mensagem 'Bateria Fraca - BATT LOW' e os códigos gerados não estão sendo aceitos."
    },
    {
        "id": "banking-cc-070",
        "gold": "suporte_tecnico_app",
        "dialogue": "Cliente: Tento baixar o comprovante de pagamento em formato PDF no meu celular através do aplicativo mas dá mensagem de erro 'Permissão de armazenamento negada pelo sistema'."
    },

    # 8. seguros_e_assistencia (10 casos)
    {
        "id": "banking-cc-071",
        "gold": "seguros_e_assistencia",
        "dialogue": "Cliente: Fui assaltado e levaram meus pertences sob ameaça. Gostaria de acionar a cobertura de roubo e furto qualificado do meu seguro Cartão Protegido contratado com o banco."
    },
    {
        "id": "banking-cc-072",
        "gold": "seguros_e_assistencia",
        "dialogue": "Cliente: Meu carro quebrou na rodovia agora à noite. Preciso solicitar o envio de um guincho de emergência através da assistência 24h do meu seguro auto do banco."
    },
    {
        "id": "banking-cc-073",
        "gold": "seguros_e_assistencia",
        "dialogue": "Cliente: Gostaria de cancelar a cobrança mensal da apólice do Seguro de Vida que consta em débito automático na minha conta corrente."
    },
    {
        "id": "banking-cc-074",
        "gold": "seguros_e_assistencia",
        "dialogue": "Cliente: Preciso atualizar a lista de beneficiários cadastrados no meu Seguro de Vida para incluir o nascimento do meu filho."
    },
    {
        "id": "banking-cc-075",
        "gold": "seguros_e_assistencia",
        "dialogue": "Cliente: Gostaria de solicitar a segunda via do certificado individual e da apólice completa do meu Seguro Residencial contratado ano passado."
    },
    {
        "id": "banking-cc-076",
        "gold": "seguros_e_assistencia",
        "dialogue": "Cliente: Qual é o período de carência estabelecido em contrato para início da cobertura de seguro desemprego involuntário em caso de demissão sem justa causa?"
    },
    {
        "id": "banking-cc-077",
        "gold": "seguros_e_assistencia",
        "dialogue": "Cliente: Como faço para enviar os laudos médicos e a documentação necessária para abertura do processo de sinistro por invalidez permanente?"
    },
    {
        "id": "banking-cc-078",
        "gold": "seguros_e_assistencia",
        "dialogue": "Cliente: Vendi o imóvel protegido no mês passado mas continuam debitando a mensalidade do Seguro Residencial. Quero o cancelamento e o estorno da última mensalidade cobrada."
    },
    {
        "id": "banking-cc-079",
        "gold": "seguros_e_assistencia",
        "dialogue": "Cliente: Gostaria de consultar o valor da indenização máxima coberta (capital segurado) no meu plano de Seguro Proteção Familiar."
    },
    {
        "id": "banking-cc-080",
        "gold": "seguros_e_assistencia",
        "dialogue": "Cliente: Tive uma emergência médica durante uma viagem internacional e precisei pagar a consulta do meu bolso. Como solicito o reembolso das despesas pela apólice do Seguro Viagem do cartão?"
    },

    # 9. encerramento_de_conta (10 casos)
    {
        "id": "banking-cc-081",
        "gold": "encerramento_de_conta",
        "dialogue": "Cliente: Gostaria de dar entrada na solicitação formal de encerramento definitivo da minha conta corrente individual neste banco."
    },
    {
        "id": "banking-cc-082",
        "gold": "encerramento_de_conta",
        "dialogue": "Cliente: Abri uma conta em outra instituição financeira e por isso desejo cancelar minha conta pagamento e encerrar todos os vínculos com este banco."
    },
    {
        "id": "banking-cc-083",
        "gold": "encerramento_de_conta",
        "dialogue": "Cliente: Eu e minha ex-esposa nos divorciamos e precisamos encerrar a nossa conta corrente conjunta mantida na instituição."
    },
    {
        "id": "banking-cc-084",
        "gold": "encerramento_de_conta",
        "dialogue": "Cliente: Solicitei o encerramento da conta na semana passada pelo app e gostaria de receber o termo de quitação e encerramento comprovando que não tenho mais débitos pendentes."
    },
    {
        "id": "banking-cc-085",
        "gold": "encerramento_de_conta",
        "dialogue": "Cliente: Quero cancelar o recebimento do meu salário nesta conta e fazer a solicitação de portabilidade de saída para o meu novo banco."
    },
    {
        "id": "banking-cc-086",
        "gold": "encerramento_de_conta",
        "dialogue": "Cliente: Tentei encerrar minha conta pelo aplicativo mas apareceu uma mensagem dizendo que o pedido foi recusado por conta de um saldo de R$ 0,45 esquecido. Como transfiro ou zero esse valor para concluir o fechamento?"
    },
    {
        "id": "banking-cc-087",
        "gold": "encerramento_de_conta",
        "dialogue": "Cliente: Me formei na faculdade e minha conta universitária perdeu os benefícios. Gostaria de solicitar o encerramento em vez de migrar para a conta tradicional cobrada."
    },
    {
        "id": "banking-cc-088",
        "gold": "encerramento_de_conta",
        "dialogue": "Cliente: Sou o inventariante responsável pelo espólio do meu pai falecido. Quais documentos preciso apresentar para solicitar o encerramento da conta bancária dele?"
    },
    {
        "id": "banking-cc-089",
        "gold": "encerramento_de_conta",
        "dialogue": "Cliente: Existe alguma pendência de tarifa, cheque a compensar ou contrato ativo que esteja impedindo a conclusão automática do meu pedido de cancelamento de conta?"
    },
    {
        "id": "banking-cc-090",
        "gold": "encerramento_de_conta",
        "dialogue": "Cliente: Antes de pedir o encerramento final da minha conta, preciso cancelar todos os cadastros de débito automático de fatura, luz e telefone vinculados a ela."
    },

    # 10. ouvidoria_e_reclamacoes (10 casos)
    {
        "id": "banking-cc-091",
        "gold": "ouvidoria_e_reclamacoes",
        "dialogue": "Cliente: Quero registrar uma reclamação gravíssima contra o atendimento presencial na agência 0451 hoje pela manhã. O gerente foi extremamente rude e desrespeitoso comigo."
    },
    {
        "id": "banking-cc-092",
        "gold": "ouvidoria_e_reclamacoes",
        "dialogue": "Cliente: Abri um protocolo no SAC há 10 dias úteis sobre uma cobrança errada e o prazo de resposta expirou sem solução. Quero abrir um chamado na Ouvidoria informando o número do protocolo estourado."
    },
    {
        "id": "banking-cc-093",
        "gold": "ouvidoria_e_reclamacoes",
        "dialogue": "Cliente: Já liguei três vezes no suporte comum e ninguém resolve a tarifa debitada indevidamente na minha conta. Exijo registrar uma contestação formal no canal da Ouvidoria do banco."
    },
    {
        "id": "banking-cc-094",
        "gold": "ouvidoria_e_reclamacoes",
        "dialogue": "Cliente: Gostaria de contestar formalmente a resposta negativa emitida pela equipe de análise de crédito a respeito do meu pedido de renegociação."
    },
    {
        "id": "banking-cc-095",
        "gold": "ouvidoria_e_reclamacoes",
        "dialogue": "Cliente: Fiquei mais de 1 hora e 40 minutos esperando na fila da agência no dia de pagamento de aposentadorias, descumprindo totalmente a lei municipal do tempo máximo de fila. Quero registrar denúncia."
    },
    {
        "id": "banking-cc-096",
        "gold": "ouvidoria_e_reclamacoes",
        "dialogue": "Cliente: Gostaria de registrar uma reclamação sobre a falta de acessibilidade para pessoas com deficiência física e ausência de rampa de acesso na agência do centro da cidade."
    },
    {
        "id": "banking-cc-097",
        "gold": "ouvidoria_e_reclamacoes",
        "dialogue": "Cliente: Tive meu pedido de isenção de tarifa negado injustamente mesmo preenchendo todos os pré-requisitos contratualmente estabelecidos. Quero recorrer dessa decisão."
    },
    {
        "id": "banking-cc-098",
        "gold": "ouvidoria_e_reclamacoes",
        "dialogue": "Cliente: Solicito a cópia da gravação da ligação telefônica efetuada para o atendimento do banco no dia 15 do mês passado para fins de representação judicial."
    },
    {
        "id": "banking-cc-099",
        "gold": "ouvidoria_e_reclamacoes",
        "dialogue": "Cliente: Quero manifestar minha profunda insatisfação com a alteração unilateral das regras do programa de pontos de recompensa que desvalorizou meus pontos acumulados sem aviso prévio."
    },
    {
        "id": "banking-cc-100",
        "gold": "ouvidoria_e_reclamacoes",
        "dialogue": "Cliente: Gostaria de registrar um elogio formal para a atendente Mariana da agência central, que demonstrou extrema eficiência e cordialidade ao me ajudar em uma situação de emergência durante minha viagem."
    }
]

def make_prompt(dialogue: str) -> str:
    lines = [
        "Você é o sistema de inteligência e triagem de atendimento de um Call Center Bancário.",
        "Sua tarefa é analisar o histórico de conversa do cliente e decidir qual departamento/assunto deve atender a solicitação.",
        "",
        "Lista de 10 Departamentos Elegíveis:",
    ]
    for dept in DEPARTMENTS:
        lines.append(f"- {dept}: {DEPARTMENT_DESCRIPTIONS[dept]}")
    lines.extend([
        "",
        "Histórico do Atendimento:",
        dialogue,
        "",
        "Responda estritamente com o código exato de um dos 10 departamentos acima."
    ])
    return "\n".join(lines)

def banking_callcenter_cases() -> list[Case]:
    """Retorna os 100 casos de teste estruturados para o benchmark de Call Center Bancário."""
    cases: list[Case] = []
    rubric_str = json.dumps(DEPARTMENT_DESCRIPTIONS, ensure_ascii=False)
    
    for c in RAW_CASES:
        prompt_text = make_prompt(c["dialogue"])
        case_obj = Case(
            id=c["id"],
            cluster="banking-callcenter-" + c["gold"],
            pack="Banking Call Center",
            family="classification",
            state=json.dumps({"channel": "call_center", "domain": "banking", "language": "pt"}),
            question=Question(
                id="decision",
                text=prompt_text,
                kind="choice",
                labels=list(DEPARTMENTS),
                rubric=rubric_str,
                criteria=DEPARTMENT_DESCRIPTIONS
            ),
            gold=c["gold"],
            language="pt",
            split="test",
            label_status="formal",
            provenance={
                "dialogue": c["dialogue"],
                "department_code": c["gold"],
                "department_name": DEPARTMENT_NAMES[c["gold"]]
            }
        )
        cases.append(case_obj)
    
    return cases

def ensure_dataset_saved() -> Path:
    """Garante que os 100 casos de teste estejam salvos em JSONL no diretório de datasets."""
    out_path = DATASETS / "banking-callcenter-cases.jsonl"
    cases = banking_callcenter_cases()
    lines = [c.model_dump_json() for c in cases]
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path

if __name__ == "__main__":
    p = ensure_dataset_saved()
    print(f"Salvo 100 casos de teste de Call Center Bancário em {p}")
