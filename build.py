# -*- coding: utf-8 -*-
"""Genera index.html a partir de plantilla.html + contenido.json + medios.json.

Por que existe: el equipo de Danelle edita contenido.json desde el CMS en /admin.
Netlify corre este script en cada guardado y publica el HTML ya relleno, asi que no
hay parpadeo de texto ni dependencia de JavaScript en el navegador.

Tres mecanismos, todos sin librerias:
  data-c="ruta.a.clave"  -> reemplaza el contenido del elemento
  data-loop="nombre"     -> rellena un contenedor VACIO repitiendo su plantilla,
                            declarada como <script type="text/plantilla" data-for="...">
                            con huecos {{campo}}. data-tpl="otra" permite pintar la
                            misma lista con una plantilla distinta.
  {{ruta.a.clave}}       -> sustitucion suelta, para atributos (src, alt, href)

Uso local:  py build.py
"""
import io
import json
import os
import re
import sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
F_PLANTILLA = os.path.join(RAIZ, 'plantilla.html')
F_CONTENIDO = os.path.join(RAIZ, 'contenido.json')
F_MEDIOS = os.path.join(RAIZ, 'medios.json')
F_SALIDA = os.path.join(RAIZ, 'index.html')


def valor(datos, ruta):
    actual = datos
    for parte in ruta.split('.'):
        if not isinstance(actual, dict) or parte not in actual:
            return None
        actual = actual[parte]
    return actual


def construir():
    html = io.open(F_PLANTILLA, encoding='utf-8').read()

    # contenido.json lo edita el CMS; medios.json (rutas de imagenes) no se expone en
    # el CMS, porque un CMS borra al guardar los campos que no tiene declarados.
    datos = json.load(io.open(F_CONTENIDO, encoding='utf-8'))
    datos.update(json.load(io.open(F_MEDIOS, encoding='utf-8')))

    faltan = []

    # ---------- 1. plantillas de lista ----------
    plantillas = {}

    def guardar(m):
        plantillas[m.group(1)] = m.group(2).strip()
        return ''

    html = re.sub(r'[ \t]*<script type="text/plantilla" data-for="([^"]+)">(.*?)</script>\n?',
                  guardar, html, flags=re.S)

    # ---------- 2. contenedores data-loop ----------
    cuenta = {'listas': 0, 'campos': 0}

    def pinta_lista(m):
        tag, attrs, nombre = m.group(1), m.group(2), m.group(3)
        items = valor(datos, nombre)
        mt = re.search(r'\sdata-tpl="([^"]+)"', attrs)
        tpl = plantillas.get(mt.group(1) if mt else nombre)
        if not isinstance(items, list) or tpl is None:
            faltan.append('lista ' + nombre)
            return m.group(0)
        filas = []
        for item in items:
            filas.append(re.sub(r'\{\{(\w+)\}\}',
                                lambda x: u'%s' % item.get(x.group(1), ''), tpl))
        cuenta['listas'] += 1
        return u'<%s%s>\n%s\n</%s>' % (tag, attrs, '\n'.join(filas), tag)

    html = re.sub(r'<(\w+)([^>]*\sdata-loop="([^"]+)"[^>]*)></\1>', pinta_lista, html)

    # ---------- 3. campos sueltos data-c ----------
    def pinta_campo(m):
        tag, attrs, clave = m.group(1), m.group(2), m.group(3)
        v = valor(datos, clave)
        if v is None:
            faltan.append(clave)
            return m.group(0)
        cuenta['campos'] += 1
        return u'<%s%s>%s</%s>' % (tag, attrs, v, tag)

    html = re.sub(r'<(\w+)([^>]*\sdata-c="([^"]+)"[^>]*)>.*?</\1>', pinta_campo, html, flags=re.S)

    # ---------- 4. sustituciones sueltas en atributos ----------
    def pinta_suelto(m):
        v = valor(datos, m.group(1))
        if v is None:
            faltan.append(m.group(1))
            return m.group(0)
        cuenta['campos'] += 1
        return u'%s' % v

    html = re.sub(r'\{\{([\w.]+)\}\}', pinta_suelto, html)

    io.open(F_SALIDA, 'w', encoding='utf-8', newline='').write(html)
    print('index.html generado: %d campos, %d listas.' % (cuenta['campos'], cuenta['listas']))
    if faltan:
        print('AVISO, sin valor: ' + ', '.join(sorted(set(faltan))))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(construir())
