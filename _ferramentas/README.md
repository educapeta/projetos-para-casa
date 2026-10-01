# 🛠️ Ferramentas — como as imagens deste repositório foram geradas

Todas as imagens de preview deste repositório saíram de um script caseiro: não usei CAD nem
renderizador 3D comercial, só **Python + Pillow**. A ideia era ter uma foto de cada peça sem
precisar abrir o SolidWorks.

## Arquivos

| Script | O que faz |
|---|---|
| `render_stl.py` | Lê um `.STL` (binário ou ASCII) ou `.OBJ` e desenha um PNG isométrico |
| `build_previews.py` | Varre a pasta do repositório e gera `preview.png` (peça principal) e `partes.png` (folha de contato com todas as peças) de cada modelagem |

## Como funciona o render

1. **Leitura da malha** — STL binário (header de 84 bytes + 50 bytes por triângulo) ou STL ASCII; OBJ por `v`/`f`.
2. **Projeção isométrica 3/4** — uma base ortonormal (direita/cima/profundidade) a partir de *azimute* e *elevação*; nada de perspectiva, o que dá aquele visual "de catálogo".
3. **Algoritmo do pintor** — os triângulos são ordenados pela profundidade do centróide e desenhados do fundo para a frente.
4. **Sombreamento flat** — intensidade por face (luz direcional + ambiente + brilho especular suave) e cores aplicadas direto no `ImageDraw.polygon`.
5. **Antialiasing** — renderiza em 2× e reduz com LANCZOS; malhas gigantes (acima de ~90 mil faces) caem para 1× e são amostradas para não demorar.

## Uso

```bash
pip install pillow

# uma unica peca
python render_stl.py caminho\peca.STL saida.png 900 675

# todas as pastas deste repositorio (gera preview.png e partes.png)
python build_previews.py ..\        # ou: python build_previews.py C:\caminho\do\repo
```

## Limitações (honestidade acima de tudo)

- É um render **sem transparência, sem sombra no chão e sem cor por peça** — serve para mostrar o formato, não para vender o produto.
- Malhas muito densas (escaneamentos de centenas de milhares de triângulos) são amostradas: o contorno fica levemente serrilhado.
- O resultado **não substitui a visualização 3D** do GitHub, que continua funcionando ao clicar em qualquer `.STL`/`.OBJ` no repositório.

[← Voltar ao índice](../README.md)
