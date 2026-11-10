def classificar_frete(peso, distancia, urgente, fragil, regiao):
    custo = 10.0
    if peso > 30:
        custo += 20
    elif peso > 10:
        custo += 8
    if distancia > 500:
        custo *= 1.5
    if urgente and fragil:
        custo += 25
    elif urgente or fragil:
        custo += 15
    if regiao == "norte":
        custo += 12
    elif regiao == "nordeste":
        custo += 9
    elif regiao == "centro-oeste":
        custo += 6
    return custo


def classificar_peca(preco, condicao, ano, quilometragem):
    nota = 0
    if condicao == "nova":
        nota += 3
    elif condicao == "excedente":
        nota += 2
    if ano >= 2020:
        nota += 2
    elif ano >= 2015:
        nota += 1
    if quilometragem < 50000:
        nota += 2
    elif quilometragem < 100000:
        nota += 1
    if preco < 100 and nota > 4:
        nota += 1
    return "A" if nota >= 7 else "B"
